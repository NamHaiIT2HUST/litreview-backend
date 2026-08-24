import asyncio
import os
import sys
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(override=False)

sys.path.insert(0, os.path.abspath('.'))
from src.services.rag_service import rag_service
from src.services.vector_store import vector_store_service

async def test():
    q = 'According to Proposition 2.2 in Xu (2010), what two properties do both the projection P_K and its complement I - P_K have?'
    retrieval_res = await asyncio.wait_for(vector_store_service.search_similar_documents(q, top_k=10), timeout=20.0)
    ans = await rag_service.generate_answer_with_citations(q, retrieval_res)
    print('\n[ANSWER]:', ans['answer'])

asyncio.run(test())
