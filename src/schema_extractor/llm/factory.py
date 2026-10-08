from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from schema_extractor.config import LLModelConfig


def build_llm(config: LLModelConfig) -> Model:
    provider_prefix, _, model_name = config.name.partition(":")

    match provider_prefix:
        case "google":
            provider = (
                GoogleProvider(api_key=config.api_key.get_secret_value())
                if config.api_key
                else GoogleProvider()
            )
            return GoogleModel(model_name, provider=provider)
        case _:
            raise NotImplementedError(
                f"Provider {provider_prefix} is not implemented. Modify 'src/auto_schema_data_extraction/models/factory.py' to add support for this provider."
            )
