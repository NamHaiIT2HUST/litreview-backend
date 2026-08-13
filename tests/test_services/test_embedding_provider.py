from types import SimpleNamespace

from src.services.vector_store import should_use_gemini_embeddings


def test_local_embedding_provider_does_not_switch_to_gemini_when_key_exists():
    settings = SimpleNamespace(
        embedding_provider="local",
        gemini_api_key="secret",
        google_api_key="",
    )

    assert should_use_gemini_embeddings(settings) is False
