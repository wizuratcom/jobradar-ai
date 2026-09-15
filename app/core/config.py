from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    candidate_profile_path: Path = Path("candidate.example.yaml")
    jwt_secret: SecretStr = SecretStr("change-me-for-local-development-32b")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=60, gt=0, le=1440)
    llm_enabled: bool = False
    llm_provider: Literal["disabled", "fake", "openai_compatible"] = "disabled"
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None
    llm_model: str | None = None
    llm_timeout_seconds: float = Field(default=30, gt=0, le=120)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    ai_default_grade: int = Field(default=1, ge=0, le=3)
    ai_grade1_model: str = "gpt-5.6-luna"
    ai_grade2_model: str = "gpt-5.6-luna"
    ai_grade3_model: str = "gpt-5.6-terra"
    ai_grade1_reasoning: str = "low"
    ai_grade2_reasoning: str = "medium"
    ai_grade3_reasoning: str = "high"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
