import importlib
import sys
import threading
import types
from types import SimpleNamespace

import pytest


class FakeChroma:
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.search_thread_id = None

    def similarity_search(self, query, **kwargs):
        self.search_thread_id = threading.get_ident()
        return [SimpleNamespace(page_content="ok", metadata={})]

    def get(self, **kwargs):
        return {"ids": []}

    def add_documents(self, **kwargs):
        return []

    def delete(self, **kwargs):
        return None


class FakeEmbeddings:
    def __init__(self, *args, **kwargs):
        pass


def _load_vector_store_module(monkeypatch):
    lc_chroma = types.ModuleType("langchain_chroma")
    lc_chroma.Chroma = FakeChroma
    monkeypatch.setitem(sys.modules, "langchain_chroma", lc_chroma)

    lc_core = types.ModuleType("langchain_core")
    lc_docs = types.ModuleType("langchain_core.documents")
    lc_docs.Document = object
    monkeypatch.setitem(sys.modules, "langchain_core", lc_core)
    monkeypatch.setitem(sys.modules, "langchain_core.documents", lc_docs)

    lc_hf = types.ModuleType("langchain_huggingface")
    lc_hf.HuggingFaceEmbeddings = FakeEmbeddings
    monkeypatch.setitem(sys.modules, "langchain_huggingface", lc_hf)

    lc_openai = types.ModuleType("langchain_openai")
    lc_openai.OpenAIEmbeddings = FakeEmbeddings
    monkeypatch.setitem(sys.modules, "langchain_openai", lc_openai)

    config = types.ModuleType("src.config")
    config.get_settings = lambda: SimpleNamespace(
        embedding_provider="local",
        local_embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        openai_api_key="",
        get_api_base="",
        embedding_model="text-embedding-3-small",
        chroma_host="",
        chroma_port=8000,
        chroma_ssl=False,
        chroma_persist_dir="./data/chroma",
    )
    monkeypatch.setitem(sys.modules, "src.config", config)

    sys.modules.pop("src.services.vector_store", None)
    return importlib.import_module("src.services.vector_store")


@pytest.mark.asyncio
async def test_similarity_search_runs_sync_chroma_call_off_event_loop(monkeypatch):
    module = _load_vector_store_module(monkeypatch)
    service = module.vector_store_service
    event_loop_thread_id = threading.get_ident()

    docs = await service.search_similar_documents("query", top_k=2)

    assert docs[0].page_content == "ok"
    assert service.vector_store.search_thread_id != event_loop_thread_id

@pytest.mark.asyncio
async def test_stage_documents_returns_old_ids_without_deleting_them(monkeypatch):
    module = _load_vector_store_module(monkeypatch)
    service = module.vector_store_service
    service.vector_store.get = lambda **kwargs: {"ids": ["old-1", "old-2"]}
    deleted = []
    service.vector_store.delete = lambda **kwargs: deleted.extend(kwargs.get("ids", []))

    old_ids = await service.stage_documents_for_paper("paper-1", [object()])

    assert old_ids == ["old-1", "old-2"]
    assert deleted == []


@pytest.mark.asyncio
async def test_delete_document_ids_is_explicit_cleanup_step(monkeypatch):
    module = _load_vector_store_module(monkeypatch)
    service = module.vector_store_service
    deleted = []
    service.vector_store.delete = lambda **kwargs: deleted.extend(kwargs.get("ids", []))

    count = await service.delete_document_ids(["old-1", "old-2"])

    assert count == 2
    assert deleted == ["old-1", "old-2"]
