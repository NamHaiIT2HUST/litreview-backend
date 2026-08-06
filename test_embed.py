import asyncio
from src.services.vector_store import vector_store_service
from langchain_core.documents import Document

async def test():
    print('Testing add_documents')
    try:
        await vector_store_service.add_documents([Document(page_content='hello world')])
        print('Done')
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
