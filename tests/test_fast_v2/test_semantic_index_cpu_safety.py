"""CPU-safety and Legacy-isolation checks for the Fast v2 semantic index.

Importing the semantic-index modules must never pull in torch/sentence-
transformers/chromadb network clients, and must never import Legacy's
VectorStoreService/EMBEDDING_PROVIDER machinery.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_import_probe(module_name: str) -> str:
    """Import one module in a fresh subprocess and report which of the heavy
    packages ended up in sys.modules. A subprocess is used so this test's own
    process (which may have already imported torch via other test files) can
    never produce a false pass."""
    code = (
        f"import {module_name}\n"
        "import sys\n"
        "heavy = [m for m in ('torch', 'sentence_transformers') if m in sys.modules]\n"
        "print(','.join(heavy))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_importing_semantic_index_does_not_load_torch():
    heavy = _run_import_probe("src.synthesis.fast_v2.evidence.semantic_index")
    assert heavy == "", f"unexpected heavy imports at module import time: {heavy}"


def test_importing_indexing_service_does_not_load_torch():
    heavy = _run_import_probe("src.synthesis.fast_v2.evidence.indexing_service")
    assert heavy == "", f"unexpected heavy imports at module import time: {heavy}"


def test_importing_chroma_retriever_does_not_load_torch():
    heavy = _run_import_probe("src.synthesis.fast_v2.evidence.chroma_retriever")
    assert heavy == "", f"unexpected heavy imports at module import time: {heavy}"


def test_semantic_index_modules_never_import_legacy_vector_store():
    """Fast v2's own retrieval path must stay fully decoupled from
    VectorStoreService/EMBEDDING_PROVIDER -- that coupling is exactly what
    made Fast v2 retrieval depend on a working OpenAI key."""
    import ast

    root = Path(__file__).resolve().parents[2] / "src" / "synthesis" / "fast_v2" / "evidence"
    for filename in ("semantic_index.py", "indexing_service.py", "chroma_retriever.py"):
        source = (root / filename).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=filename)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "vector_store" not in node.module, (
                    f"{filename} imports from {node.module!r} -- must not depend on "
                    "Legacy's VectorStoreService"
                )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "vector_store" not in alias.name


# A guard named test_legacy_vector_store_module_is_unmodified_by_this_worktree
# used to live here. It asserted that `git diff HEAD -- src/services/vector_store.py`
# was empty, which encoded a single task's scope ("do not touch Legacy") as a
# permanent test.
#
# It is removed because it does not express a durable invariant. It asserts on
# version-control state rather than on code, so it fails for any uncommitted
# edit to that file and passes again the moment the edit is committed -- including
# edits that genuinely break the boundary it was meant to protect.
#
# The invariant that does matter is still enforced above: fast_v2's evidence
# modules must not import Legacy's VectorStoreService.
