from __future__ import annotations

import keyword
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_RESERVED_NAMES = frozenset(dir(BaseModel))

FieldType = Literal["str", "int", "float", "date", "bool", "list[str]"]


def _validate_identifier(value: str, what: str) -> str:
    value = value.strip()
    if not value.isidentifier() or keyword.iskeyword(value):
        raise ValueError(
            f"{what} {value!r} must be a valid Python identifier and not a reserved keyword."
        )
    return value


class FieldDefinition(BaseModel):
    """Definition of a single field to extract from a document."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        max_length=64,
        description=(
            "Field name in snake_case, used as the attribute name on the "
            "resulting extracted object (e.g. 'invoice_number'). "
            "Should be a valid Python identifier and not a reserved keyword."
        ),
    )
    type: FieldType = Field(description="Python type of the field's value.")
    description: str = Field(
        max_length=500,
        description=(
            "Clear, unambiguous description of what to extract for this "
            "field - used later to guide extraction from a real document."
        ),
    )
    required: bool = Field(
        default=True,
        description="If False, a missing value in the document becomes None instead of failing extraction.",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = _validate_identifier(v, "Field name")
        if v.startswith(("_", "model_")) or v in _RESERVED_NAMES:
            raise ValueError(f"Field name {v!r} is reserved, choose a different one.")
        return v


class TemplateSpec(BaseModel):
    """Specification of a document-extraction template, generated from a user prompt."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        max_length=64,
        description=(
            "Short, descriptive template name in snake_case (e.g. 'invoice', 'employment_contract'). "
            "Should be a valid Python identifier and not a reserved keyword."
        ),
    )
    fields: list[FieldDefinition] = Field(
        min_length=1,
        max_length=50,
        description="Fields to extract from the document.",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_identifier(v, "Template name")

    @model_validator(mode="after")
    def validate_unique_field_names(self) -> TemplateSpec:
        names = [f.name for f in self.fields]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(f"Duplicate field names: {sorted(duplicates)}")
        return self
