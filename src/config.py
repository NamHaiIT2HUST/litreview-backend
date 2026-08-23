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
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    synthesis_temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    synthesis_llm_provider: Literal["gemini", "groq", "openai"] = "openai"
    synthesis_model: str = "gpt-4o-mini"
    synthesis_llm_max_concurrency: int = Field(default=1, ge=1, le=10)
    groq_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_provider: Literal["local", "gemini", "openai", "hash-debug"] = "openai"
    # Used only when embedding_provider="local". "local" means a real local semantic
    # model (sentence-transformers via langchain-huggingface), not a fallback -- use
    # embedding_provider="hash-debug" to explicitly opt into the non-semantic hash
    # embedding (smoke-test/demo only, no downloads required).
    local_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    @property
    def effective_gemini_api_key(self) -> str:
        raw = self.gemini_api_key or self.google_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEYS") or ""
        tokens = [t.strip() for t in raw.split(",") if t.strip()]
        for token in tokens:
            if token.startswith("AIzaSy"):
                return token
        return tokens[0] if tokens else ""

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

    # Synthesis pipeline selection.
    # "legacy" is the ONLY supported production path and MUST stay the default.
    # "fast_v2_experimental" opts into the Evidence-First / Hygiene /
    # Dimension-Aware / OpenScholar pipeline documented in
    # docs/architecture/FAST_SYNTHESIS_V2.md. That path is EXPERIMENTAL: its
    # generation latency is validated but its claim-level factual grounding is
    # NOT. Never make it the default without the promotion criteria in that doc.
    synthesis_mode: Literal["legacy", "fast_v2_experimental"] = "legacy"

    @property
    def fast_v2_enabled(self) -> bool:
        """True only when fast_v2 was explicitly and exactly selected."""
        return self.synthesis_mode == "fast_v2_experimental"

    # Fast v2 experimental knobs (inert while synthesis_mode="legacy").
    fast_v2_generator_model: str = "NeuML/Llama-3.1_OpenScholar-8B-AWQ"
    fast_v2_max_evidence_per_dimension: int = Field(default=3, ge=1, le=20)
    # NOT a calibrated production threshold -- frozen experimental default only.
    # See docs/architecture/FAST_SYNTHESIS_V2.md section L.
    fast_v2_relevance_threshold: float = 0.0
    fast_v2_candidates_per_dimension: int = Field(default=40, ge=1, le=200)

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
