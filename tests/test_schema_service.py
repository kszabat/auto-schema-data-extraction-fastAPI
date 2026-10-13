import uuid

import pytest
from pydantic_ai.models.test import TestModel

from schema_extractor.agents.schema_agent import build_schema_agent
from schema_extractor.db import repositories
from schema_extractor.db.models import VersionSource
from schema_extractor.errors import (
    SchemaGenerationError,
    SchemaNotFoundError,
    VersionConflictError,
    VersionNotFoundError,
)
from schema_extractor.schema.meta_models import TemplateSpec
from schema_extractor.services import schema_service

SPEC_V1 = {
    "name": "invoice",
    "fields": [{"name": "invoice_number", "type": "str", "description": "Number"}],
}
SPEC_V2 = {
    "name": "invoice",
    "fields": [
        {"name": "invoice_number", "type": "str", "description": "Number"},
        {"name": "issue_date", "type": "date", "description": "Issue date"},
    ],
}
INVALID = {
    "name": "invoice",
    "fields": [{"name": "_id", "type": "str", "description": "x"}],
}


def agent_returning(output: dict):
    return build_schema_agent(TestModel(custom_output_args=output))


@pytest.fixture()
def user(db):
    return repositories.create_user(db, email="a@example.com", hashed_password="h")


@pytest.fixture()
def other_user(db):
    return repositories.create_user(db, email="b@example.com", hashed_password="h")


@pytest.fixture()
def schema(db, user):
    created, _ = schema_service.create_schema_from_prompt(
        db, user_id=user.id, request_text="faktura", agent=agent_returning(SPEC_V1)
    )
    return created


def refine(db, user, schema, output=SPEC_V2, feedback="dodaj datę"):
    return schema_service.refine_schema(
        db,
        user_id=user.id,
        schema_id=schema.id,
        feedback=feedback,
        agent=agent_returning(output),
    )


def test_create_schema_makes_version_one(db, user):
    schema, version = schema_service.create_schema_from_prompt(
        db, user_id=user.id, request_text="faktura", agent=agent_returning(SPEC_V1)
    )
    assert schema.name == "invoice"
    assert version.version_number == 1
    assert version.source == VersionSource.AI_GENERATED
    assert TemplateSpec.model_validate(version.definition) == TemplateSpec(**SPEC_V1)


def test_invalid_agent_output_leaves_no_schema(db, user):
    with pytest.raises(SchemaGenerationError):
        schema_service.create_schema_from_prompt(
            db, user_id=user.id, request_text="faktura", agent=agent_returning(INVALID)
        )
    assert repositories.list_schemas(db, user_id=user.id) == []


def test_refine_adds_version_and_keeps_old_one(db, user, schema):
    version = refine(db, user, schema)

    assert version.version_number == 2
    assert version.source == VersionSource.AI_REFINED
    assert version.instruction == "dodaj datę"

    versions = schema_service.list_schema_versions(
        db, user_id=user.id, schema_id=schema.id
    )
    assert [v.version_number for v in versions] == [1, 2]
    assert TemplateSpec.model_validate(versions[0].definition) == TemplateSpec(
        **SPEC_V1
    )

    _, current = schema_service.get_schema_with_latest(
        db, user_id=user.id, schema_id=schema.id
    )
    assert current.version_number == 2


def test_failed_refine_does_not_add_version(db, user, schema):
    with pytest.raises(SchemaGenerationError):
        refine(db, user, schema, output=INVALID)

    versions = schema_service.list_schema_versions(
        db, user_id=user.id, schema_id=schema.id
    )
    assert [v.version_number for v in versions] == [1]


def test_rollback_creates_new_version_copying_old_one(db, user, schema):
    refine(db, user, schema)

    version = schema_service.rollback_schema(
        db, user_id=user.id, schema_id=schema.id, version_number=1
    )

    assert version.version_number == 3
    assert version.source == VersionSource.ROLLBACK
    assert TemplateSpec.model_validate(version.definition) == TemplateSpec(**SPEC_V1)
    versions = schema_service.list_schema_versions(
        db, user_id=user.id, schema_id=schema.id
    )
    assert len(versions) == 3


def test_rollback_to_missing_version_fails(db, user, schema):
    with pytest.raises(VersionNotFoundError):
        schema_service.rollback_schema(
            db, user_id=user.id, schema_id=schema.id, version_number=99
        )


def test_manual_edit_adds_version(db, user, schema):
    version = schema_service.edit_schema(
        db, user_id=user.id, schema_id=schema.id, spec=TemplateSpec(**SPEC_V2)
    )
    assert version.version_number == 2
    assert version.source == VersionSource.MANUAL_EDIT


def test_edit_with_stale_expected_version_conflicts(db, user, schema):
    refine(db, user, schema)  # najnowsza wersja to teraz 2

    with pytest.raises(VersionConflictError):
        schema_service.edit_schema(
            db,
            user_id=user.id,
            schema_id=schema.id,
            spec=TemplateSpec(**SPEC_V2),
            expected_version=1,
        )


def test_other_user_cannot_access_schema(db, schema, other_user):
    with pytest.raises(SchemaNotFoundError):
        schema_service.get_schema_with_latest(
            db, user_id=other_user.id, schema_id=schema.id
        )
    with pytest.raises(SchemaNotFoundError):
        refine(db, other_user, schema)
    with pytest.raises(SchemaNotFoundError):
        schema_service.rollback_schema(
            db, user_id=other_user.id, schema_id=schema.id, version_number=1
        )

    assert repositories.list_schemas(db, user_id=other_user.id) == []
    assert len(repositories.list_versions(db, schema_id=schema.id)) == 1


def test_unknown_schema_id_raises_not_found(db, user):
    with pytest.raises(SchemaNotFoundError):
        schema_service.get_schema_with_latest(
            db, user_id=user.id, schema_id=uuid.uuid4()
        )
