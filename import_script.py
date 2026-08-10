import asyncio
import os
from src.database import AsyncSessionLocal
from src.services.scopus_matcher import import_scopus_excel

async def run():
    print("Starting import...")
    file_path = os.path.join("data", "ext_list_Jun_2026.xlsx")
    
    async with AsyncSessionLocal() as db:
        try:
            count = await import_scopus_excel(db, file_path)
            await db.commit()
            print(f"Successfully imported {count} records into scopus_sources.")
        except Exception as e:
            await db.rollback()
            print(f"Error during import: {e}")

if __name__ == "__main__":
    asyncio.run(run())
