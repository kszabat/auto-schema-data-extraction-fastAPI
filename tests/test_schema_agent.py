import pytest
from pydantic_ai import UnexpectedModelBehavior
from pydantic_ai.models.test import TestModel

from schema_extractor.agents.schema_agent import (
    build_refine_prompt,
    build_schema_agent,
    generate_template_spec,
    refine_template_spec,
)
from schema_extractor.schema.meta_models import TemplateSpec

VALID_OUTPUT = {
    "name": "invoice",
    "fields": [
        {"name": "invoice_number", "type": "str", "description": "Invoice number"}
    ],
}


def make_spec() -> TemplateSpec:
    return TemplateSpec.model_validate(VALID_OUTPUT)


async def test_generate_returns_validated_spec():
    agent = build_schema_agent(model=TestModel(custom_output_args=VALID_OUTPUT))
    spec = await generate_template_spec(user_prompt="Invoice with number", agent=agent)
    assert spec == make_spec()


async def test_refine_returns_validated_spec():
    agent = build_schema_agent(model=TestModel(custom_output_args=VALID_OUTPUT))
    spec = await refine_template_spec(current=make_spec(), feedback="add date", agent=agent)
    assert isinstance(spec, TemplateSpec)


async def test_invalid_output_exhausts_retries():
    invalid = {
        # invalid field name (starts with underscore)
        "name": "invoice",
        "fields": [{"name": "_id", "type": "str", "description": "x"}],
    }
    agent = build_schema_agent(model=TestModel(custom_output_args=invalid))
    with pytest.raises(UnexpectedModelBehavior):
        await generate_template_spec(user_prompt="Invoice", agent=agent)

def test_refine_prompt_contains_current_spec_and_feedback():
    prompt = build_refine_prompt(current=make_spec(), feedback="add tax number")
    assert "invoice_number" in prompt
    assert "add tax number" in prompt