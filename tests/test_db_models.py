import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from schema_extractor.db.models import (
    Extraction,
    ExtractionStatus,
    Schema,
    SchemaVersion,
    User,
    VersionSource,
)
from schema_extractor.schema.meta_models import TemplateSpec

SPEC = TemplateSpec.model_validate(
    {
        "name": "invoice",
        "fields": [
            {"name": "invoice_number", "type": "str", "description": "Invoice number"}
        ],
    }
)


def make_user(db, email="a@example.com") -> User:
    user = User(email=email, hashed_password="hash")
    db.add(user)
    db.flush()
    return user


def make_schema(db, user, number=1) -> tuple[Schema, SchemaVersion]:
    schema = Schema(
        user_id=user.id, name="invoice", request_text="Extract invoice schema"
    )
    db.add(schema)
    db.flush()
    version = SchemaVersion(
        schema_id=schema.id,
        version_number=number,
        definition=SPEC.model_dump(),
        source=VersionSource.AI_GENERATED,
    )
    db.add(version)
    db.flush()
    return schema, version


def test_user_email_is_unique(db):
    make_user(db, email="anc@example.com")
    with pytest.raises(IntegrityError):
        make_user(db, email="anc@example.com")


def test_definition_roundtrips_through_jsonb(db):
    _, version = make_schema(db, make_user(db))
    db.expire_all()
    loaded = db.get(SchemaVersion, version.id)
    assert TemplateSpec.model_validate(loaded.definition) == SPEC


def test_version_numbers_are_unique_per_schema(db):
    schema, _ = make_schema(db, make_user(db))
    db.add(
        SchemaVersion(
            schema_id=schema.id,
            version_number=1,
            definition=SPEC.model_dump(),
            source=VersionSource.AI_REFINED,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_deleting_schema_cascades_to_versions(db):
    schema, _ = make_schema(db, make_user(db))
    db.delete(schema)
    db.flush()
    assert db.scalars(select(SchemaVersion)).all() == []


def test_version_used_by_extraction_cannot_be_deleted(db):
    user = make_user(db)
    schema, version = make_schema(db, user)
    db.add(
        Extraction(
            user_id=user.id,
            schema_version_id=version.id,
            filename="invoice.pdf",
            storage_key="abc123",
        )
    )
    db.flush()

    db.delete(schema)
    with pytest.raises(IntegrityError):
        db.flush()


def test_extraction_defaults(db):
    user = make_user(db)
    _, version = make_schema(db, user)
    extraction = Extraction(
        user_id=user.id,
        schema_version_id=version.id,
        filename="faktura.pdf",
        storage_key="abc123",
    )
    db.add(extraction)
    db.flush()
    db.refresh(extraction)

    assert extraction.status == ExtractionStatus.PENDING
    assert extraction.result is None
    assert extraction.created_at is not None

    raw = db.execute(text("SELECT status FROM extractions")).scalar_one()
    assert raw == "pending"
