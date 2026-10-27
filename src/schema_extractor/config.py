from functools import lru_cache
from pathlib import Path

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "google:gemini-3-flash-preview"
    api_key: SecretStr | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        if isinstance(v, str) and "/" in v:
            return v.replace("/", ":", 1)
        return v


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # LLM
    use_same_model: bool = False
    schema_model: LLModelConfig = Field(default_factory=LLModelConfig)
    extraction_model: LLModelConfig = Field(default_factory=LLModelConfig)

    # DB and authentication
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    secret_key: SecretStr
    access_token_expire_minutes: int = 30

    # uploads
    storage_dir: Path = Path("data/uploads")
    max_upload_mb: int = 10
    max_pdf_pages: int = 50
    max_active_extractions_per_user: int = 3

    @model_validator(mode="after")
    def sync_extr_model(self):
        if self.use_same_model:
            self.extraction_model = self.schema_model.model_copy()
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
