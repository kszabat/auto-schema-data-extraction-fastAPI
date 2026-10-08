import datetime
from typing import Any

from pydantic import BaseModel, Field, create_model

from schema_extractor.schema.meta_models import (
    FieldDefinition,
    TemplateSpec,
)

TYPE_MAP: dict[str, Any] = {
    "str": str,
    "int": int,
    "float": float,
    "date": datetime.date,
    "bool": bool,
    "list[str]": list[str],
}


def _field_tuple(field: FieldDefinition) -> tuple[Any, Any]:
    python_type = TYPE_MAP[field.type]

    if field.required:
        return python_type, Field(description=field.description)

    return python_type | None, Field(default=None, description=field.description)


def build_extraction_model(spec: TemplateSpec) -> type[BaseModel]:
    fields = {field.name: _field_tuple(field) for field in spec.fields}
    return create_model(
        spec.name, **fields, __doc__=f"Extraction template: {spec.name}"
    )
