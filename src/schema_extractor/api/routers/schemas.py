import uuid

from fastapi import APIRouter

from schema_extractor.api.deps import CurrentUser, DbSession, SchemaAgentDep
from schema_extractor.api.payloads import (
    SchemaCreateIn,
    SchemaDetailOut,
    SchemaEditIn,
    SchemaOut,
    SchemaRefineIn,
    SchemaRollbackIn,
    SchemaVersionOut,
)
from schema_extractor.db.models import Schema, SchemaVersion
from schema_extractor.services import schema_service

router = APIRouter(prefix="/schemas", tags=["schemas"])


def _detail(schema: Schema, version: SchemaVersion) -> SchemaDetailOut:
    return SchemaDetailOut(
        id=schema.id,
        name=schema.name,
        request_text=schema.request_text,
        created_at=schema.created_at,
        latest_version=SchemaVersionOut.model_validate(version),
    )


@router.post("", response_model=SchemaDetailOut, status_code=201)
def create_schema(
    data: SchemaCreateIn, db: DbSession, user: CurrentUser, agent: SchemaAgentDep
):
    schema, version = schema_service.create_schema_from_prompt(
        db, user_id=user.id, request_text=data.request_text, agent=agent
    )
    return _detail(schema, version)


@router.get("/{schema_id}", response_model=SchemaDetailOut)
def get_schema(schema_id: uuid.UUID, db: DbSession, user: CurrentUser):
    schema, version = schema_service.get_schema_with_latest(
        db, user_id=user.id, schema_id=schema_id
    )
    return _detail(schema, version)


@router.get("", response_model=list[SchemaOut])
def list_schemas(db: DbSession, user: CurrentUser):
    return schema_service.list_user_schemas(db, user_id=user.id)


@router.get("/{schema_id}/versions", response_model=list[SchemaVersionOut])
def list_versions(schema_id: uuid.UUID, db: DbSession, user: CurrentUser):
    return schema_service.list_schema_versions(db, user_id=user.id, schema_id=schema_id)


@router.post("/{schema_id}/revisions", response_model=SchemaVersionOut, status_code=201)
def refine_schema(
    schema_id: uuid.UUID,
    data: SchemaRefineIn,
    db: DbSession,
    user: CurrentUser,
    agent: SchemaAgentDep,
):
    return schema_service.refine_schema(
        db, user_id=user.id, schema_id=schema_id, feedback=data.feedback, agent=agent
    )


@router.put("/{schema_id}", response_model=SchemaVersionOut)
def edit_schema(
    schema_id: uuid.UUID, data: SchemaEditIn, db: DbSession, user: CurrentUser
):
    return schema_service.edit_schema(
        db,
        user_id=user.id,
        schema_id=schema_id,
        spec=data.spec,
        expected_version=data.expected_version,
    )


@router.post("/{schema_id}/rollback", response_model=SchemaVersionOut, status_code=201)
def rollback_schema(
    schema_id: uuid.UUID, data: SchemaRollbackIn, db: DbSession, user: CurrentUser
):
    return schema_service.rollback_schema(
        db, user_id=user.id, schema_id=schema_id, version_number=data.version
    )
