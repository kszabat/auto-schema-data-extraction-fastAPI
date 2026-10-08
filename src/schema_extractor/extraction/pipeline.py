from pydantic import BaseModel
from pydantic_ai.models import Model

from schema_extractor.agents.extraction_agent import (
    build_extraction_agent,
    extract_from_document,
)
from schema_extractor.documents.multimodal import load_binary_content
from schema_extractor.schema.builder import build_extraction_model
from schema_extractor.schema.meta_models import TemplateSpec


async def run_extraction(
    data: bytes,
    spec: TemplateSpec,
    *,
    model: Model,
    max_bytes: int | None = None,
) -> BaseModel:
    document = load_binary_content(data, max_bytes=max_bytes)
    output_model = build_extraction_model(spec)
    agent = build_extraction_agent(model, output_model)
    return await extract_from_document(document, agent=agent)
