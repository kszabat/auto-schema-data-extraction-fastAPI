import datetime

import pytest
from pydantic import ValidationError
from schema_extractor.schema.builder import build_extraction_model

from schema_extractor.schema.meta_models import FieldDefinition, TemplateSpec


def make_spec() -> TemplateSpec:
    return TemplateSpec(
        name="invoice",
        fields=[
            FieldDefinition(
                name="invoice_number", type="str", description="Invoice number"
            ),
            FieldDefinition(name="issue_date", type="date", description="Issue date"),
            FieldDefinition(
                name="total", type="float", description="Total", required=False
            ),
        ],
    )


def test_built_model_accepts_valid_data():
    model = build_extraction_model(make_spec())
    obj = model(invoice_number="FV/1", issue_date="2026-10-08")
    assert obj.issue_date == datetime.date(2026, 10, 8)
    assert obj.total is None


def test_missing_required_field_raises():
    model = build_extraction_model(make_spec())
    with pytest.raises(ValidationError):
        model(issue_date="2026-01-05")
        model(invoice_number="FV/3")


def test_field_descriptions_end_up_in_json_schema():
    model = build_extraction_model(make_spec())
    props = model.model_json_schema()["properties"]
    assert props["total"]["description"] == "Total"


@pytest.mark.parametrize(
    "bad_name", ["class", "_id", "model_x", "schema", "copy", "1abc", "with space"]
)
def test_invalid_field_names_are_rejected(bad_name):
    with pytest.raises(ValidationError):
        FieldDefinition(name=bad_name, type="str", description="x")


def test_duplicate_field_names_are_rejected():
    field = FieldDefinition(name="a", type="str", description="x")
    with pytest.raises(ValidationError):
        TemplateSpec(name="spec1", fields=[field, field])


def test_template_needs_at_least_one_field():
    with pytest.raises(ValidationError):
        TemplateSpec(name="t", fields=[])
