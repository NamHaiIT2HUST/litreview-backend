"""Test URL normalization without importing async DB drivers in this sandbox."""
import ast
from pathlib import Path


def _load_normalizer():
    tree = ast.parse(Path("src/database.py").read_text(encoding="utf-8"))
    fn = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_normalize_async_database_url"
    )
    namespace = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "src/database.py", "exec"), namespace)
    return namespace["_normalize_async_database_url"]


_normalize_async_database_url = _load_normalizer()


def test_normalize_postgres_url_to_asyncpg():
    assert (
        _normalize_async_database_url("postgresql://u:p@db:5432/litreview")
        == "postgresql+asyncpg://u:p@db:5432/litreview"
    )


def test_normalize_sqlite_url_to_aiosqlite():
    assert (
        _normalize_async_database_url("sqlite:///./data/app.db")
        == "sqlite+aiosqlite:///./data/app.db"
    )
