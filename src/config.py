import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# This project's own root, resolved from this file rather than the working
# directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

# Scoped deliberately. A bare load_dotenv() searches parent directories, so a
# git worktree under .claude/worktrees/ silently inherited the main checkout's
# .env: the worktree ran on someone else's provider, database, and feature
# flags with nothing on screen to say so. Tests that assert the code's own safe
# defaults failed locally while passing in CI, which is the "works on my
# machine" symptom inverted.
load_dotenv(ENV_FILE)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Absolute, for the same reason: env_file=".env" resolves against the
        # working directory, so behaviour depended on where the process started.
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "AI20K Agent"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default_factory=lambda: int(os.getenv("PORT", os.getenv("APP_PORT", "8000"))), ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Auth
    # No default: a hardcoded fallback secret lets anyone who can read this
    # repository forge valid tokens. validate_security_settings() refuses to
    # start without it outside development.
    secret_key: str = ""
    google_client_id: str = ""
    google_redirect_uri: str = ""
    # Seeding a known admin account is a development convenience only. In any
    # other environment it is a publicly known credential on a public host.
    seed_default_admin: bool = False
    seed_admin_username: str = "admin"
    seed_admin_password: str = ""

    # Demo researcher accounts for trying the app without registering. These are
    # real rows with real passwords that log in through the normal endpoint and
    # receive normal tokens -- they are a shortcut past the signup form, not past
    # authentication. Development only, and the password is never in source.
    seed_demo_accounts: bool = False
    seed_demo_password: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # LLM
    openai_api_key: str = ""
    openai_embedding_api_key: str = ""
    openai_embedding_api_base: str = ""
    openai_api_base: str = ""
    gemini_api_key: str = ""
    google_api_key: str = ""
    serpapi_api_key: str = ""
    model_name: str = ""
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
    embedding_provider: Literal["local", "gemini", "openai", "hash-debug"] = "openai"
    # Used only when embedding_provider="local". "local" means a real local semantic
    # model (sentence-transformers via langchain-huggingface), not a fallback -- use
    # embedding_provider="hash-debug" to explicitly opt into the non-semantic hash
    # embedding (smoke-test/demo only, no downloads required).
    local_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

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
            self.llm_model
            or os.getenv("LLM_MODEL", "")
            or self.model_name
            or os.getenv("MODEL_NAME", "")
            or "gpt-4o-mini"
        ).strip()
        key = self.effective_openai_api_key
        if key and key.startswith("sk-xt-"):
            if model in ["deepseek-chat", "deepseek", "deepseek-v3", "gpt-4o-mini", "gpt-4o"]:
                return "deepseek/deepseek-v3.2"
        if key and key.startswith("sk-or-v1-"):
            if "/" not in model:
                return f"openai/{model}"
        return model

    @property
    def effective_gemini_api_key(self) -> str:
        """Return the first configured Gemini key.

        Deliberately deterministic. This used to call ``random.choice`` on every
        read, so two reads inside one request could authenticate against two
        different Google projects -- which made cost attribution impossible and
        errors non-reproducible. Rotating across several keys is a scheduling
        concern for a credential pool, not something a config getter should do
        by chance on each access.
        """
        tokens = self.all_gemini_api_keys
        if not tokens:
            return ""
        aiza_tokens = [t for t in tokens if t.startswith("AIzaSy")]
        return aiza_tokens[0] if aiza_tokens else tokens[0]

    @property
    def all_gemini_api_keys(self) -> list[str]:
        raw = self.gemini_api_key or self.google_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEYS") or ""
        return [t.strip(' "\'') for t in raw.split(",") if t.strip(' "\'')]

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

    # Reranker selection. "identity" performs NO reranking -- it is the safe,
    # deterministic default so importing/running fast_v2 (and CI) never
    # downloads a checkpoint. "cross_encoder" is the reranker the validated
    # Evidence-First / Dimension-Aware v1 experiments actually used
    # (cross-encoder/ms-marco-MiniLM-L-6-v2, see
    # src/synthesis/fast_v2/selection/cross_encoder.py for the provenance
    # citations). It must be opted into explicitly; a typo fails loudly rather
    # than silently changing which evidence reaches the bank.
    fast_v2_reranker: Literal["identity", "cross_encoder"] = "identity"
    fast_v2_reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Generator selection. "fake" loads nothing and calls nothing -- the safe,
    # deterministic default so importing/running fast_v2 (and CI) never needs a
    # GPU or a network call. "remote_openscholar" talks HTTP to a warm GPU
    # service (see scripts/fast_v2_openscholar_gpu_service.py) and must never
    # be loaded in-process in the CPU backend. "local_vllm" is the in-process
    # vLLM adapter for when the backend itself runs on the GPU box. Must be
    # opted into explicitly; a typo fails loudly rather than silently
    # changing latency/cost.
    fast_v2_generator: Literal["fake", "local_vllm", "remote_openscholar", "hosted_api"] = "fake"
    # Required only when fast_v2_generator="remote_openscholar".
    fast_v2_openscholar_base_url: str = ""
    # Required only when fast_v2_generator="hosted_api". Generic OpenAI-
    # compatible chat-completions endpoint (base_url/api_key/model), so this
    # is provider-agnostic -- no single vendor is hardcoded.
    fast_v2_hosted_api_base_url: str = ""
    fast_v2_hosted_api_key: str = ""
    fast_v2_hosted_api_model: str = ""

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


class SecurityConfigurationError(RuntimeError):
    """Raised at startup when a security-critical setting is missing.

    Failing to boot is the correct behaviour: the alternative is running with a
    known-public secret or a known-public admin password.
    """


def validate_security_settings(settings: "Settings") -> None:
    """Refuse to start with a missing or unsafe security configuration."""
    problems: list[str] = []

    if not settings.secret_key.strip():
        problems.append(
            "SECRET_KEY is not set. Generate one with "
            "`python -c \"import secrets; print(secrets.token_urlsafe(48))\"` "
            "and put it in .env. It signs every access token."
        )
    elif len(settings.secret_key.strip()) < 32:
        problems.append("SECRET_KEY is shorter than 32 characters.")

    if settings.seed_default_admin:
        if settings.app_env != "development":
            problems.append(
                "SEED_DEFAULT_ADMIN is only allowed when APP_ENV=development."
            )
        if not settings.seed_admin_password.strip():
            problems.append(
                "SEED_DEFAULT_ADMIN=true requires SEED_ADMIN_PASSWORD."
            )

    if settings.seed_demo_accounts:
        if settings.app_env != "development":
            problems.append(
                "SEED_DEMO_ACCOUNTS is only allowed when APP_ENV=development. "
                "Demo accounts have a shared, discoverable password."
            )
        if not settings.seed_demo_password.strip():
            problems.append(
                "SEED_DEMO_ACCOUNTS=true requires SEED_DEMO_PASSWORD."
            )

    if problems:
        raise SecurityConfigurationError(
            "Refusing to start due to security configuration problems:\n  - "
            + "\n  - ".join(problems)
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
