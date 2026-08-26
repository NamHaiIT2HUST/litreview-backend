"""Guards for the embedding identity contract.

These exist because the contract has already been broken once and nobody
noticed. Commit 5fbc555 made build_embeddings raise on a missing key and shipped
a test for it; two days later a07f35a replaced the raise with a silent fallback
to random vectors, under a commit message that read like an improvement. The
behaviour these tests describe is the kind that looks safe to relax, so it needs
something that fails loudly when someone tries.

The invariant, stated once: an embedding model defines the coordinate space of a
persisted index. Substituting one for another is a schema change, not a
fallback. Rotating a credential inside the same provider and model is not.
"""
from types import SimpleNamespace

import pytest

from src.services.embedding_manager import (
    EmbeddingConfigurationError,
    EmbeddingIdentity,
    EmbeddingIndexMismatchError,
    chroma_metadata_for,
    collection_name_for,
    identity_from_metadata,
    resolve_runtime_identity,
    verify_identity_match,
)


def _settings(**overrides):
    base = {
        "embedding_provider": "openai",
        "embedding_model": "text-embedding-3-small",
        "local_embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestRuntimeIdentity:
    def test_resolves_provider_model_and_dimension(self):
        identity = resolve_runtime_identity(_settings())
        assert identity == EmbeddingIdentity("openai", "text-embedding-3-small", 1536)

    def test_local_provider_reads_its_own_model_setting(self):
        identity = resolve_runtime_identity(_settings(embedding_provider="local"))
        assert identity.model == "sentence-transformers/all-MiniLM-L6-v2"
        assert identity.dimension == 384

    def test_provider_and_model_mismatch_is_rejected_at_configuration_time(self):
        # The exact landmine EMBEDDING_MODEL being one shared field creates:
        # switch the provider, forget the model, and the old provider's model
        # name is handed to the new provider.
        with pytest.raises(EmbeddingConfigurationError, match="Unknown embedding model"):
            resolve_runtime_identity(
                _settings(embedding_provider="gemini", embedding_model="text-embedding-3-small")
            )

    def test_unknown_model_is_rejected_rather_than_guessed(self):
        with pytest.raises(EmbeddingConfigurationError):
            resolve_runtime_identity(_settings(embedding_model="text-embedding-4-imaginary"))


class TestCollectionNaming:
    def test_name_describes_the_contents(self):
        identity = EmbeddingIdentity("openai", "text-embedding-3-small", 1536)
        name = collection_name_for(identity)
        assert "openai" in name and "text-embedding-3-small" in name and "1536" in name

    def test_same_provider_different_model_gets_a_different_collection(self):
        # Changing model inside one provider is just as breaking as changing
        # provider, so the two must not share a collection.
        small = EmbeddingIdentity("openai", "text-embedding-3-small", 1536)
        large = EmbeddingIdentity("openai", "text-embedding-3-large", 3072)
        assert collection_name_for(small) != collection_name_for(large)

    def test_version_separates_a_migration_from_the_live_index(self):
        identity = EmbeddingIdentity("openai", "text-embedding-3-small", 1536)
        assert collection_name_for(identity, version=1) != collection_name_for(identity, version=2)


class TestIdentityVerification:
    def test_matching_identity_passes(self):
        identity = EmbeddingIdentity("openai", "text-embedding-3-small", 1536)
        verify_identity_match(collection_name="c", expected=identity, actual=identity)

    def test_different_provider_at_the_same_dimension_still_fails(self):
        # 1536 == 1536 proves nothing: the spaces are unrelated.
        expected = EmbeddingIdentity("openai", "text-embedding-3-small", 1536)
        actual = EmbeddingIdentity("gemini", "some-1536-model", 1536)
        with pytest.raises(EmbeddingIndexMismatchError):
            verify_identity_match(collection_name="c", expected=expected, actual=actual)

    def test_different_model_within_one_provider_fails(self):
        expected = EmbeddingIdentity("openai", "text-embedding-3-small", 1536)
        actual = EmbeddingIdentity("openai", "text-embedding-3-large", 3072)
        with pytest.raises(EmbeddingIndexMismatchError):
            verify_identity_match(collection_name="c", expected=expected, actual=actual)

    def test_mismatch_carries_an_actionable_payload(self):
        expected = EmbeddingIdentity("openai", "text-embedding-3-small", 1536)
        actual = EmbeddingIdentity("gemini", "text-embedding-004", 768)
        with pytest.raises(EmbeddingIndexMismatchError) as exc_info:
            verify_identity_match(collection_name="index_v1_openai", expected=expected, actual=actual)

        payload = exc_info.value.to_error_payload()
        assert payload["error_code"] == "EMBEDDING_INDEX_MISMATCH"
        assert payload["required_action"] == "REINDEX"
        assert payload["details"]["expected"]["provider"] == "openai"
        assert payload["details"]["actual"]["provider"] == "gemini"


class TestChromaSelfDescription:
    def test_metadata_round_trips(self):
        identity = EmbeddingIdentity("openai", "text-embedding-3-small", 1536)
        assert identity_from_metadata(chroma_metadata_for(identity)) == identity

    def test_collection_without_identity_reads_as_unknown_not_as_matching(self):
        # Collections created before identity tracking must not be assumed
        # compatible; "no information" is not "the same".
        assert identity_from_metadata(None) is None
        assert identity_from_metadata({}) is None
        assert identity_from_metadata({"embedding_provider": "openai"}) is None


class TestCredentialRotationIsNotAModelChange:
    def test_identity_ignores_credentials(self):
        # The distinction the whole design rests on: swapping a spent API key
        # for another one on the same provider and model leaves every existing
        # vector valid, so it must not change the identity or the collection.
        before = resolve_runtime_identity(_settings(openai_api_key="sk-first-key"))
        after = resolve_runtime_identity(_settings(openai_api_key="sk-second-key"))
        assert before == after
        assert collection_name_for(before) == collection_name_for(after)


class TestNoSilentFallback:
    def test_openai_without_a_key_raises_instead_of_substituting(self):
        # Regression guard for a07f35a, which replaced this raise with a
        # fallback to Gemini and then to FakeEmbeddings(size=1536).
        from src.services.vector_store import build_embeddings

        settings = _settings(
            openai_embedding_api_key="",
            effective_openai_api_key="",
            openai_api_key="",
            effective_gemini_api_key="AIzaSyLooksPlausibleEnoughToTempt",
            gemini_api_key="AIzaSyLooksPlausibleEnoughToTempt",
        )
        with pytest.raises(RuntimeError, match="requires OPENAI_EMBEDDING_API_KEY"):
            build_embeddings(settings)

    def test_fake_embeddings_are_not_reachable_from_production_code(self):
        # FakeEmbeddings is legitimate in tests. What must not exist is a path
        # that reaches it without anyone asking for it.
        import inspect

        from src.services import vector_store

        source = inspect.getsource(vector_store)
        executable = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        assert "FakeEmbeddings" not in executable
