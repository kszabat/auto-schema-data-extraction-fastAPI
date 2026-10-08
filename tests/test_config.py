import pytest
from pydantic import ValidationError

from schema_extractor.config import LLModelConfig, Settings


def make_settings(**kwargs):
    return Settings(_env_file=None, secret_key="test-secret", **kwargs)


def test_model_slash_is_normalized():
    assert LLModelConfig(name="gugl/gemuni-x").name == "gugl:gemuni-x"


def test_use_same_model_copies_schema_model():
    settings = make_settings(use_same_model=True, schema_model={"name": "gugl:xyz"})
    assert settings.extraction_model.name == "gugl:xyz"


def test_secret_key_is_required(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
