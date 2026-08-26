"""Embedding identity: what a vector index was built with, and whether the
current runtime is allowed to touch it.

An embedding model defines a coordinate space. Vectors produced by one model
cannot be compared against vectors produced by another, even when both are the
same length -- similarity scores come out looking perfectly ordinary and mean
nothing at all. That makes the embedding configuration part of the *schema* of a
persisted index, not a provider preference that can be swapped at runtime.

Two consequences run through this module:

* Nothing here falls back. If the configured provider cannot be built, that is a
  configuration error. Substituting a different model would silently change the
  meaning of every vector written afterwards.

* Runtime configuration does not get to decide how historical data is repaired.
  When vectors for an old ingestion need rebuilding, the identity recorded for
  that index decides which model to use -- not whatever ``.env`` says today.

Rotating an API key inside the same provider and model is unaffected by all of
this: the identity is (provider, model, dimension), and a credential is not part
of it.
"""
from __future__ import annotations

from dataclasses import dataclass

# Dimensionality per (provider, model). Recorded rather than probed, so a
# mismatch is caught before anything is written. Extend this table when adding a
# model; an unknown model is rejected rather than guessed at, because guessing
# wrong produces exactly the silent corruption this module exists to prevent.
KNOWN_EMBEDDING_DIMENSIONS: dict[tuple[str, str], int] = {
    ("openai", "text-embedding-3-small"): 1536,
    ("openai", "text-embedding-3-large"): 3072,
    ("openai", "text-embedding-ada-002"): 1536,
    # OpenRouter exposes OpenAI's embedding models under a prefixed name.
    ("openai", "openai/text-embedding-3-small"): 1536,
    ("openai", "openai/text-embedding-3-large"): 3072,
    ("gemini", "text-embedding-004"): 768,
    ("gemini", "models/text-embedding-004"): 768,
    ("gemini", "gemini-embedding-001"): 3072,
    ("local", "sentence-transformers/all-MiniLM-L6-v2"): 384,
    ("local", "sentence-transformers/all-mpnet-base-v2"): 768,
    ("hash-debug", "lightweight-hash"): 128,
}

# Providers whose model name comes from LOCAL_EMBEDDING_MODEL rather than
# EMBEDDING_MODEL, or which have no configurable model at all.
_FIXED_MODEL_PROVIDERS = {"hash-debug": "lightweight-hash"}


class EmbeddingConfigurationError(RuntimeError):
    """The configured embedding provider/model cannot be used as given."""


class EmbeddingIndexMismatchError(RuntimeError):
    """A vector index was built with a different model than the one in use.

    Carries enough detail for an API layer to turn it into a structured error
    the UI can act on, rather than an opaque 500.
    """

    def __init__(self, *, collection_name: str, expected: EmbeddingIdentity, actual: EmbeddingIdentity):
        self.collection_name = collection_name
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Collection {collection_name!r} was built with "
            f"{expected.provider}/{expected.model} ({expected.dimension} dimensions), "
            f"but the current configuration is "
            f"{actual.provider}/{actual.model} ({actual.dimension} dimensions). "
            "Searching across two embedding spaces returns meaningless results. "
            "Re-index the collection to change embedding model."
        )

    def to_error_payload(self) -> dict:
        return {
            "error_code": "EMBEDDING_INDEX_MISMATCH",
            "message": str(self),
            "required_action": "REINDEX",
            "details": {
                "collection_name": self.collection_name,
                "expected": self.expected.as_dict(),
                "actual": self.actual.as_dict(),
            },
        }


@dataclass(frozen=True)
class EmbeddingIdentity:
    """What makes two vector sets comparable.

    Deliberately excludes the API key: rotating a credential within the same
    provider and model leaves every existing vector valid and needs no re-index.
    Deliberately includes the model, because changing it inside one provider
    (text-embedding-3-small to -3-large, say) is just as breaking as changing
    provider.
    """

    provider: str
    model: str
    dimension: int

    def as_dict(self) -> dict:
        return {"provider": self.provider, "model": self.model, "dimension": self.dimension}

    @property
    def collection_slug(self) -> str:
        """Filesystem/URL-safe form of the identity, for collection names."""
        model_slug = self.model.replace("/", "-").replace(".", "-").replace(" ", "-")
        return f"{self.provider}_{model_slug}_{self.dimension}"


def resolve_runtime_identity(settings) -> EmbeddingIdentity:
    """Read the configured embedding identity, or explain why it is unusable.

    Validates at configuration time rather than at the first API call, so a
    typo like EMBEDDING_PROVIDER=gemini with EMBEDDING_MODEL left at an OpenAI
    model name surfaces immediately instead of after documents are already
    being processed.
    """
    provider = (getattr(settings, "embedding_provider", "") or "local").strip()

    if provider in _FIXED_MODEL_PROVIDERS:
        model = _FIXED_MODEL_PROVIDERS[provider]
    elif provider == "local":
        model = (getattr(settings, "local_embedding_model", "") or "").strip()
        if not model:
            raise EmbeddingConfigurationError(
                "EMBEDDING_PROVIDER=local requires LOCAL_EMBEDDING_MODEL."
            )
    else:
        model = (getattr(settings, "embedding_model", "") or "").strip()
        if not model:
            raise EmbeddingConfigurationError(
                f"EMBEDDING_PROVIDER={provider} requires EMBEDDING_MODEL."
            )

    dimension = KNOWN_EMBEDDING_DIMENSIONS.get((provider, model))
    if dimension is None:
        known_for_provider = sorted(m for p, m in KNOWN_EMBEDDING_DIMENSIONS if p == provider)
        raise EmbeddingConfigurationError(
            f"Unknown embedding model {model!r} for provider {provider!r}. "
            f"Known models for this provider: {known_for_provider or '(none)'}. "
            "Add it to KNOWN_EMBEDDING_DIMENSIONS in "
            "src/services/embedding_manager.py with its dimensionality -- the "
            "dimensionality is not guessed, because guessing it wrong corrupts "
            "the index silently."
        )

    return EmbeddingIdentity(provider=provider, model=model, dimension=dimension)


def collection_name_for(identity: EmbeddingIdentity, version: int = 1) -> str:
    """Name a collection after what is actually inside it.

    The previous scheme was f"litreview_papers_{provider}_v3", taking the
    provider from settings. When the code fell back to a different provider, the
    name kept claiming the configured one -- so the name could not be trusted to
    describe the contents.
    """
    return f"index_v{version}_{identity.collection_slug}"


def chroma_metadata_for(identity: EmbeddingIdentity, version: int = 1) -> dict:
    """Identity written into Chroma itself, so the store can describe itself.

    Postgres remains the control plane, but a collection that carries its own
    identity can be checked against the registry instead of being trusted.
    """
    return {
        "embedding_provider": identity.provider,
        "embedding_model": identity.model,
        "embedding_dimension": identity.dimension,
        "embedding_version": version,
    }


def identity_from_metadata(metadata: dict | None) -> EmbeddingIdentity | None:
    """Read an identity back out of Chroma collection metadata.

    Returns None for collections created before identities were recorded, which
    the caller must treat as "unknown", never as "matches".
    """
    if not metadata:
        return None
    provider = metadata.get("embedding_provider")
    model = metadata.get("embedding_model")
    dimension = metadata.get("embedding_dimension")
    if not provider or not model or not dimension:
        return None
    return EmbeddingIdentity(provider=str(provider), model=str(model), dimension=int(dimension))


def verify_identity_match(
    *,
    collection_name: str,
    expected: EmbeddingIdentity,
    actual: EmbeddingIdentity,
) -> None:
    """Raise unless the two identities are the same. No partial credit.

    Matching dimensionality is not enough: OpenAI's text-embedding-3-small and
    Gemini's gemini-embedding-001 differ in provider and produce unrelated
    spaces, and two 1536-dimension OpenAI models are still two different spaces.
    """
    if expected != actual:
        raise EmbeddingIndexMismatchError(
            collection_name=collection_name, expected=expected, actual=actual
        )


def build_embeddings_for(identity: EmbeddingIdentity, settings):
    """Construct the backend for exactly this identity, or raise.

    Takes the identity as an argument rather than reading configuration, so a
    caller repairing historical vectors can pass the identity recorded for that
    index and be certain the runtime configuration cannot override it.
    """
    from src.services.vector_store import build_embeddings

    # build_embeddings reads provider and model off a settings-like object.
    # A small shim keeps a single construction path while letting the identity,
    # not the ambient configuration, decide what gets built.
    class _PinnedSettings:
        def __init__(self, base, ident: EmbeddingIdentity):
            self._base = base
            self.embedding_provider = ident.provider
            if ident.provider == "local":
                self.local_embedding_model = ident.model
                self.embedding_model = getattr(base, "embedding_model", ident.model)
            else:
                self.embedding_model = ident.model
                self.local_embedding_model = getattr(base, "local_embedding_model", "")

        def __getattr__(self, name):
            return getattr(self._base, name)

    return build_embeddings(_PinnedSettings(settings, identity))
