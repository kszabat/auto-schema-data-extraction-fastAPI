import asyncio
import uuid

from pydantic_ai import UnexpectedModelBehavior
from pydantic_ai.agent import Agent
from sqlalchemy.orm import Session

from schema_extractor.agents.schema_agent import (
    generate_template_spec,
    refine_template_spec,
)
from schema_extractor.db import repositories
from schema_extractor.db.models import Schema, SchemaVersion, VersionSource
from schema_extractor.errors import (
    SchemaGenerationError,
    SchemaNotFoundError,
    VersionNotFoundError,
)
from schema_extractor.schema.meta_models import TemplateSpec

SchemaAgent = Agent[None, TemplateSpec]


def _get_owned_schema(db: Session, user_id: uuid.UUID, schema_id: uuid.UUID) -> Schema:
    schema = repositories.get_schema(db, user_id=user_id, schema_id=schema_id)
    if schema is None:
        raise SchemaNotFoundError(schema_id)
    return schema


def _latest_version(db: Session, schema: Schema) -> SchemaVersion:
    version = repositories.get_latest_version(db, schema_id=schema.id)
    if version is None:
        raise VersionNotFoundError(schema.id, 1)
    return version


def create_schema_from_prompt(
    db: Session, *, user_id: uuid.UUID, request_text: str, agent: SchemaAgent
) -> tuple[Schema, SchemaVersion]:
    try:
        spec = asyncio.run(
            generate_template_spec(user_prompt=request_text, agent=agent)
        )
    except UnexpectedModelBehavior as e:
        raise SchemaGenerationError(str(e)) from e

    schema, version = repositories.create_schema(
        db, user_id=user_id, request_text=request_text, spec=spec
    )
    db.commit()
    return schema, version


def refine_schema(
    db: Session,
    *,
    user_id: uuid.UUID,
    schema_id: uuid.UUID,
    feedback: str,
    agent: SchemaAgent,
) -> SchemaVersion:
    schema = _get_owned_schema(db, user_id, schema_id)
    latest = _latest_version(db, schema)
    current = TemplateSpec.model_validate(latest.definition)
    base_version = latest.version_number
    db.commit()

    try:
        refined = asyncio.run(refine_template_spec(current, feedback, agent=agent))
    except UnexpectedModelBehavior as e:
        raise SchemaGenerationError(str(e)) from e

    version = repositories.add_version(
        db,
        schema=schema,
        spec=refined,
        source=VersionSource.AI_REFINED,
        instruction=feedback,
        expected_latest=base_version,
    )
    db.commit()
    return version


def edit_schema(
    db: Session,
    *,
    user_id: uuid.UUID,
    schema_id: uuid.UUID,
    spec: TemplateSpec,
    expected_version: int | None = None,
) -> SchemaVersion:
    schema = _get_owned_schema(db, user_id, schema_id)
    version = repositories.add_version(
        db,
        schema=schema,
        spec=spec,
        source=VersionSource.MANUAL_EDIT,
        expected_latest=expected_version,
    )
    db.commit()
    return version


def rollback_schema(
    db: Session, *, user_id: uuid.UUID, schema_id: uuid.UUID, version_number: int
) -> SchemaVersion:
    schema = _get_owned_schema(db, user_id, schema_id)
    target = repositories.get_version(
        db, schema_id=schema.id, version_number=version_number
    )
    if target is None:
        raise VersionNotFoundError(schema.id, version_number)

    version = repositories.add_version(
        db,
        schema=schema,
        spec=TemplateSpec.model_validate(target.definition),
        source=VersionSource.ROLLBACK,
        instruction=f"Rollback to version {version_number}",
    )
    db.commit()
    return version


def get_schema_with_latest(
    db: Session, *, user_id: uuid.UUID, schema_id: uuid.UUID
) -> tuple[Schema, SchemaVersion]:
    schema = _get_owned_schema(db, user_id, schema_id)
    return schema, _latest_version(db, schema)


def list_user_schemas(db: Session, *, user_id: uuid.UUID) -> list[Schema]:
    return repositories.list_schemas(db, user_id=user_id)


def list_schema_versions(
    db: Session, *, user_id: uuid.UUID, schema_id: uuid.UUID
) -> list[SchemaVersion]:
    schema = _get_owned_schema(db, user_id, schema_id)
    return repositories.list_versions(db, schema_id=schema.id)
