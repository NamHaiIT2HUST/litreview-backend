import os
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "AI20K Agent"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:3000"

    # LLM
    openai_api_key: str = ""
    openai_api_base: str = ""
    gemini_api_key: str = ""
    google_api_key: str = ""
    model_name: str = "gemini-1.5-flash"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    synthesis_temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    embedding_model: str = "text-embedding-004"

    @property
    def get_api_base(self) -> str:
        if self.openai_api_base:
            return self.openai_api_base
        env_base = os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL")
        if env_base:
            return env_base
        if self.openai_api_key and self.openai_api_key.startswith("sk-or-v1-"):
            return "https://openrouter.ai/api/v1"
        return ""

    # Database
    database_url: str = "sqlite:///./data/app.db"

    # Vector Store
    # If CHROMA_HOST is set, use Chroma client/server mode. If empty, use
    # embedded persistence for single-process local development only.
    chroma_host: str = ""
    chroma_port: int = Field(default=8000, ge=1, le=65535)
    chroma_ssl: bool = False
    chroma_persist_dir: str = "./data/chroma"

    # Background synthesis
    redis_url: str = "redis://localhost:6379/0"
    synthesis_max_papers: int = Field(default=15, ge=1, le=100)


@lru_cache
def get_settings() -> Settings:
    return Settings()
