import pytest
from pydantic_ai import models


@pytest.fixture(autouse=True)
def block_model_requests(monkeypatch):
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
