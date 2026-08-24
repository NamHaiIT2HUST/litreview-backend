"""Rebuild the Fast v2 semantic collection for the Xu2010/Xu2018 benchmark corpus only."""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

PAPER_IDS = [
    uuid.UUID("52c06c26-1dd1-486a-8c4f-202779ed5c7f"),  # Xu2010
    uuid.UUID("0373c7b5-3a9e-437d-a59a-a1baa9a708cc"),  # Xu2018
]


async def main():
    from src.database import session_scope
    from src.synthesis.fast_v2.evidence.indexing_service import FastV2IndexingService
    from src.synthesis.fast_v2.evidence.semantic_index import FastV2SemanticIndex

    index = FastV2SemanticIndex()
    service = FastV2IndexingService(session_scope, index)

    print(f"Indexing into collection: {index.collection_name}")
    stats_list = await service.rebuild_collection(PAPER_IDS)
    for stats in stats_list:
        print(f"  paper={stats.paper_id} seen={stats.chunks_seen} indexed={stats.chunks_indexed} "
              f"skipped_empty={stats.chunks_skipped_empty}")

    info = index.collection_info()
    print(f"\ncollection_info: {info}")


if __name__ == "__main__":
    asyncio.run(main())
