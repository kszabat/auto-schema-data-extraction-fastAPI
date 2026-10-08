import datetime

import pytest
from pydantic_ai import UnexpectedModelBehavior
from pydantic_ai.models.test import TestModel

from schema_extractor.documents.exceptions import UnsupportedFileTypeError
from schema_extractor.extraction.pipeline import run_extraction
from schema_extractor.schema.meta_models import TemplateSpec

PDF = b"%PDF-1.7\n%fake"

SPEC = TemplateSpec.model_validate(
    {
        "name": "invoice",
        "fields": [
            {"name": "invoice_number", "type": "str", "description": "Invoice number"},
            {"name": "issue_date", "type": "date", "description": "Issue date"},
            {
                "name": "total",
                "type": "float",
                "description": "Total",
                "required": False,
            },
        ],
    }
)


async def test_run_extraction_returns_validated_model():
    model = TestModel(
        custom_output_args={"invoice_number": "FV/1", "issue_date": "2026-01-05"}
    )
    result = await run_extraction(PDF, SPEC, model=model)

    assert result.invoice_number == "FV/1"
    assert result.issue_date == datetime.date(2026, 1, 5)
    assert result.total is None
    assert result.model_dump(mode="json")["issue_date"] == "2026-01-05"


async def test_missing_required_field_fails_after_retries():
    model = TestModel(custom_output_args={"issue_date": "2026-01-05"})
    with pytest.raises(UnexpectedModelBehavior):
        await run_extraction(PDF, SPEC, model=model)


async def test_unsupported_file_is_rejected_before_calling_model():
    with pytest.raises(UnsupportedFileTypeError):
        await run_extraction(b"to nie jest dokument", SPEC, model=TestModel())
