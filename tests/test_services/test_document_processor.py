import importlib
import sys
import types
from dataclasses import dataclass, field


def _load_document_processor_with_langchain_stubs(monkeypatch):
    community = types.ModuleType("langchain_community")
    loaders = types.ModuleType("langchain_community.document_loaders")
    splitters = types.ModuleType("langchain_text_splitters")

    class FakeLoader:
        def __init__(self, file_path):
            self.file_path = file_path

        def load(self):
            return []

    class FakeSplitter:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def split_documents(self, pages):
            return []

    loaders.PyPDFLoader = FakeLoader
    splitters.RecursiveCharacterTextSplitter = FakeSplitter
    community.document_loaders = loaders

    monkeypatch.setitem(sys.modules, "langchain_community", community)
    monkeypatch.setitem(sys.modules, "langchain_community.document_loaders", loaders)
    monkeypatch.setitem(sys.modules, "langchain_text_splitters", splitters)
    sys.modules.pop("src.services.document_processor", None)
    return importlib.import_module("src.services.document_processor")


@dataclass
class FakeDocument:
    page_content: str
    metadata: dict = field(default_factory=dict)


def test_splitter_enables_start_index(monkeypatch, tmp_path):
    module = _load_document_processor_with_langchain_stubs(monkeypatch)
    monkeypatch.setattr(module, "UPLOAD_DIR", str(tmp_path))

    processor = module.DocumentProcessor()

    assert processor.text_splitter.kwargs["add_start_index"] is True


def test_chunk_metadata_reconstructs_exact_page_span(monkeypatch, tmp_path):
    module = _load_document_processor_with_langchain_stubs(monkeypatch)
    monkeypatch.setattr(module, "UPLOAD_DIR", str(tmp_path))
    processor = module.DocumentProcessor()

    page_text = "Alpha beta gamma. Delta epsilon zeta."
    pages = [FakeDocument(page_content=page_text, metadata={"page": 0})]
    chunks = [
        FakeDocument("Alpha beta gamma.", {"page": 0, "start_index": 0}),
        FakeDocument("Delta epsilon zeta.", {"page": 0, "start_index": 18}),
    ]

    processor._attach_chunk_metadata(pages, chunks)

    assert chunks[0].metadata["chunk_index"] == 0
    assert chunks[1].metadata["chunk_index"] == 1
    for chunk in chunks:
        start = chunk.metadata["page_char_start"]
        end = chunk.metadata["page_char_end"]
        assert 0 <= start < end <= len(page_text)
        assert page_text[start:end] == chunk.page_content


def test_chunk_metadata_rejects_invalid_start_index(monkeypatch, tmp_path):
    module = _load_document_processor_with_langchain_stubs(monkeypatch)
    monkeypatch.setattr(module, "UPLOAD_DIR", str(tmp_path))
    processor = module.DocumentProcessor()

    pages = [FakeDocument(page_content="short page", metadata={"page": 0})]
    chunks = [FakeDocument("not present", {"page": 0, "start_index": 99})]

    try:
        processor._attach_chunk_metadata(pages, chunks)
    except ValueError as exc:
        assert "offset" in str(exc).lower()
    else:
        raise AssertionError("Expected invalid chunk offsets to raise ValueError")
