from types import SimpleNamespace

from src.services.vector_store_config import build_chroma_connection_kwargs


def test_server_mode_uses_host_port_and_not_persist_directory():
    settings = SimpleNamespace(
        chroma_host="chroma",
        chroma_port=8000,
        chroma_ssl=False,
        chroma_persist_dir="./data/chroma",
    )

    kwargs = build_chroma_connection_kwargs(settings)

    assert kwargs == {
        "host": "chroma",
        "port": 8000,
        "ssl": False,
    }
    assert "persist_directory" not in kwargs


def test_embedded_mode_uses_persist_directory_when_host_is_empty():
    settings = SimpleNamespace(
        chroma_host="",
        chroma_port=8000,
        chroma_ssl=False,
        chroma_persist_dir="./data/chroma",
    )

    kwargs = build_chroma_connection_kwargs(settings)

    assert kwargs == {"persist_directory": "./data/chroma"}
