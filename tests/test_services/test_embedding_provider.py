from types import SimpleNamespace

import pytest

from src.services.vector_store import LightweightHashEmbeddings, build_embeddings


class _FakeHuggingFace:
    def __init__(self, model_name):
        self.model_name = model_name


def test_local_provider_does_not_switch_to_gemini_when_gemini_key_exists():
    """embedding_provider="local" must always build the local semantic backend,
    never silently switch providers based on which keys happen to be set."""
    settings = SimpleNamespace(
        embedding_provider="local",
        gemini_api_key="secret",
        google_api_key="",
        local_embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    )

    result = build_embeddings(settings, huggingface_cls=_FakeHuggingFace)

    assert isinstance(result, _FakeHuggingFace)
    assert result.model_name == "sentence-transformers/all-MiniLM-L6-v2"


def test_local_provider_raises_when_semantic_backend_unavailable(monkeypatch):
    """No silent fallback to the hash embedding: a missing sentence-transformers/
    langchain-huggingface install must fail loudly, not degrade quietly."""
    import builtins

    settings = SimpleNamespace(embedding_provider="local", local_embedding_model="x")

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name == "langchain_huggingface":
            raise ImportError("simulated: package not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)

    with pytest.raises(RuntimeError, match="EMBEDDING_PROVIDER=local requires"):
        build_embeddings(settings)


def test_gemini_provider_raises_without_key():
    settings = SimpleNamespace(embedding_provider="gemini", gemini_api_key="", google_api_key="")
    with pytest.raises(RuntimeError, match="EMBEDDING_PROVIDER=gemini requires"):
        build_embeddings(settings)


def test_openai_provider_raises_without_key():
    settings = SimpleNamespace(embedding_provider="openai", openai_api_key="")
    with pytest.raises(RuntimeError, match="EMBEDDING_PROVIDER=openai requires"):
        build_embeddings(settings)


def test_hash_debug_is_explicit_opt_in_only():
    settings = SimpleNamespace(embedding_provider="hash-debug")
    result = build_embeddings(settings)
    assert isinstance(result, LightweightHashEmbeddings)


def test_unknown_provider_raises():
    settings = SimpleNamespace(embedding_provider="nonsense")
    with pytest.raises(RuntimeError, match="Unsupported EMBEDDING_PROVIDER"):
        build_embeddings(settings)
