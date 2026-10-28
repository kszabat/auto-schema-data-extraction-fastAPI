import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from schema_extractor.db.models import ExtractionStatus, VersionSource
from schema_extractor.schema.meta_models import TemplateSpec


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SchemaCreateIn(BaseModel):
    request_text: str = Field(min_length=1, max_length=4000)


class SchemaRefineIn(BaseModel):
    feedback: str = Field(min_length=1, max_length=2000)


class SchemaEditIn(BaseModel):
    spec: TemplateSpec
    expected_version: int | None = Field(default=None, ge=1)


class SchemaRollbackIn(BaseModel):
    version: int = Field(ge=1)


class SchemaVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_number: int
    definition: TemplateSpec
    instruction: str | None
    source: VersionSource
    created_at: datetime


class SchemaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    request_text: str
    created_at: datetime


class SchemaDetailOut(SchemaOut):
    latest_version: SchemaVersionOut


class ExtractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    schema_version_id: uuid.UUID
    filename: str
    status: ExtractionStatus
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
