import pytest
from pydantic import SecretStr
from pydantic_ai.models.google import GoogleModel

from schema_extractor.config import LLModelConfig
from schema_extractor.llm.factory import build_llm


def test_google_model_is_built_with_api_key():
    config = LLModelConfig(name="google:gemini-test", api_key="fake-key")
    model = build_llm(config)
    assert isinstance(model, GoogleModel)
    assert model.model_name == "gemini-test"


def test_unknown_provider_raises():
    with pytest.raises(NotImplementedError, match="openai"):
        build_llm(LLModelConfig(name="openai:gpt-x"))


def test_api_key_is_not_exposed():
    api_key = LLModelConfig(name="google:gemini-test", api_key="fake-key").api_key
    assert isinstance(api_key, SecretStr)
    assert str(api_key) != "fake-key"