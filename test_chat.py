import asyncio
import os
from src.services.rag_service import rag_service
from src.services.vector_store import vector_store_service

async def test():
    print('Searching chunks...')
    try:
        chunks = await vector_store_service.search_similar_documents('Ai là người tạo ra facebook?', 4)
        print(f'Found {len(chunks)} chunks.')
        print('Generating answer...')
        ans = await rag_service.generate_answer('Ai là người tạo ra facebook?', chunks)
        print("Answer:")
        print(ans)
    except Exception as e:
        print(f"Error: {type(e).__name__} - {e}")

if __name__ == "__main__":
    asyncio.run(test())
