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
    serpapi_api_key: str = ""
    model_name: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_provider: str = ""
    deepseek_api_key: str = ""
    openrouter_api_key: str = ""
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    synthesis_temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    synthesis_llm_provider: Literal["gemini", "groq", "openai"] = "openai"
    synthesis_model: str = "gpt-4o-mini"
    synthesis_llm_max_concurrency: int = Field(default=1, ge=1, le=10)
    groq_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_provider: Literal["local", "gemini", "openai"] = "openai"

    @property
    def effective_openai_api_key(self) -> str:
        return (
            self.openai_api_key
            or self.llm_api_key
            or self.deepseek_api_key
            or self.openrouter_api_key
            or os.getenv("OPENAI_API_KEY", "")
            or os.getenv("LLM_API_KEY", "")
            or os.getenv("DEEPSEEK_API_KEY", "")
            or os.getenv("OPENROUTER_API_KEY", "")
        ).strip()

    @property
    def effective_model_name(self) -> str:
        model = (
            self.model_name
            or self.llm_model
            or os.getenv("MODEL_NAME", "")
            or os.getenv("LLM_MODEL", "")
            or "deepseek/deepseek-v3.2"
        ).strip()
        key = self.effective_openai_api_key
        if key and key.startswith("sk-xt-"):
            if model in ["deepseek-chat", "deepseek", "deepseek-v3", "gpt-4o-mini", "gpt-4o"]:
                return "deepseek/deepseek-v3.2"
        return model

    @property
    def effective_gemini_api_key(self) -> str:
        import random
        tokens = self.all_gemini_api_keys
        if not tokens:
            return ""
        aiza_tokens = [t for t in tokens if t.startswith("AIzaSy")]
        if aiza_tokens:
            return random.choice(aiza_tokens)
        return ""

    @property
    def all_gemini_api_keys(self) -> list[str]:
        raw = self.gemini_api_key or self.google_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEYS") or ""
        return [t.strip() for t in raw.split(",") if t.strip()]

    @property
    def get_api_base(self) -> str:
        if self.openai_api_base:
            return self.openai_api_base
        env_base = (
            os.getenv("OPENAI_API_BASE")
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("LLM_API_BASE")
            or os.getenv("DEEPSEEK_API_BASE")
        )
        if env_base:
            return env_base
        key = self.effective_openai_api_key
        if key:
            if key.startswith("sk-or-v1-"):
                return "https://openrouter.ai/api/v1"
            if key.startswith("sk-xt-"):
                return "https://api.xkiro.com/v1"
        prov = (self.llm_provider or os.getenv("LLM_PROVIDER") or "").lower().strip()
        if prov == "deepseek":
            return "https://api.deepseek.com/v1"
        if prov == "openrouter":
            return "https://openrouter.ai/api/v1"
        if prov == "xkiro":
            return "https://api.xkiro.com/v1"
        if prov == "groq":
            return "https://api.groq.com/openai/v1"
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
