import asyncio
from src.services.vector_store import vector_store_service
import os

async def check():
    collection = vector_store_service.vector_store._collection
    count = collection.count()
    print(f"Collection count: {count}")
    if count > 0:
        docs = collection.peek(5)
        for i, meta in enumerate(docs['metadatas']):
            print(f"Doc {i} metadata: {meta}")
    else:
        print("Collection is empty!")

if __name__ == "__main__":
    asyncio.run(check())
