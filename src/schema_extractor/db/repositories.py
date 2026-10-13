import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from schema_extractor.db.models import (
    Schema,
    SchemaVersion,
    User,
    VersionSource,
)
from schema_extractor.errors import VersionConflictError
from schema_extractor.schema.meta_models import TemplateSpec


def create_user(db: Session, *, email: str, hashed_password: str):
    user = User(email=email, hashed_password=hashed_password)
    db.add(user)
    db.flush()
    return user


def get_user_by_email(db: Session, *, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_schema(db: Session, *, user_id: uuid.UUID, schema_id: uuid.UUID):
    return db.scalar(
        select(Schema).where(Schema.id == schema_id, Schema.user_id == user_id)
    )


def list_schemas(db: Session, *, user_id: uuid.UUID) -> list[Schema]:
    stmt = (
        select(Schema)
        .where(Schema.user_id == user_id)
        .order_by(Schema.created_at.desc())
    )
    return list(db.scalars(stmt))


def get_latest_version(db: Session, *, schema_id: uuid.UUID) -> SchemaVersion | None:
    stmt = (
        select(SchemaVersion)
        .where(SchemaVersion.schema_id == schema_id)
        .order_by(SchemaVersion.version_number.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def get_version(
    db: Session, *, schema_id: uuid.UUID, version_number: int
) -> SchemaVersion | None:
    return db.scalar(
        select(SchemaVersion).where(
            SchemaVersion.schema_id == schema_id,
            SchemaVersion.version_number == version_number,
        )
    )


def list_versions(db: Session, *, schema_id: uuid.UUID) -> list[SchemaVersion]:
    stmt = (
        select(SchemaVersion)
        .where(SchemaVersion.schema_id == schema_id)
        .order_by(SchemaVersion.version_number)
    )
    return list(db.scalars(stmt))


def create_schema(
    db: Session, *, user_id: uuid.UUID, request_text: str, spec: TemplateSpec
) -> tuple[Schema, SchemaVersion]:
    schema = Schema(user_id=user_id, name=spec.name, request_text=request_text)
    db.add(schema)
    db.flush()

    version = SchemaVersion(
        schema_id=schema.id,
        version_number=1,
        definition=spec.model_dump(mode="json"),
        instruction=request_text,
        source=VersionSource.AI_GENERATED,
    )
    db.add(version)
    db.flush()
    return schema, version


def add_version(
    db: Session,
    *,
    schema: Schema,
    spec: TemplateSpec,
    source: VersionSource,
    instruction: str | None = None,
    expected_latest: int | None = None,
) -> SchemaVersion:
    db.execute(select(Schema.id).where(Schema.id == schema.id).with_for_update())

    latest = (
        db.scalar(
            select(func.max(SchemaVersion.version_number)).where(
                SchemaVersion.schema_id == schema.id
            )
        )
        or 0
    )
    if expected_latest is not None and latest != expected_latest:
        raise VersionConflictError(expected=expected_latest, actual=latest)

    version = SchemaVersion(
        schema_id=schema.id,
        version_number=latest + 1,
        definition=spec.model_dump(mode="json"),
        instruction=instruction,
        source=source,
    )
    db.add(version)
    db.flush()
    return version
