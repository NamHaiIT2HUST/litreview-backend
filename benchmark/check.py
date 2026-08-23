import asyncio
import os
import sys
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(override=False)

sys.path.insert(0, os.path.abspath('.'))
from src.services.vector_store import vector_store_service

async def test():
    q = 'According to Proposition 2.2 in Xu (2010), what two properties do both the projection P_K and its complement I - P_K have?'
    retrieval_res = await asyncio.wait_for(vector_store_service.search_similar_documents(q, top_k=10), timeout=20.0)
    for i, doc in enumerate(retrieval_res):
        page = doc.metadata.get("page")
        print(f"\n--- CHUNK {i+1} [Page {page}] ---")
        print(doc.page_content[:600] + '...')

asyncio.run(test())
