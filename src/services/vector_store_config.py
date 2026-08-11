"""Connection settings for Chroma.

Production uses client/server mode so the API and Celery worker do not share an
embedded persistent store across processes. Local single-process development can
still fall back to the embedded persist directory when CHROMA_HOST is empty.
"""


def build_chroma_connection_kwargs(settings) -> dict:
    host = (getattr(settings, "chroma_host", "") or "").strip()
    if host:
        return {
            "host": host,
            "port": int(getattr(settings, "chroma_port", 8000)),
            "ssl": bool(getattr(settings, "chroma_ssl", False)),
        }

    return {
        "persist_directory": getattr(settings, "chroma_persist_dir", "./data/chroma")
    }
