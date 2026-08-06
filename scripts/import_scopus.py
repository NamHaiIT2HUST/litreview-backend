import asyncio
import sys
import time
from pathlib import Path

# Fix Windows console encoding for print output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import create_all_tables, AsyncSessionLocal
from src.services.scopus_matcher import import_scopus_excel

async def main():
    excel_path = r"C:\Users\Hp\Downloads\ext_list_Jun_2026.xlsx"
    print(f"[import] Bat dau tao DB schema va nap file Scopus Source List:\n  {excel_path}")

    start_time = time.time()
    await create_all_tables()

    async with AsyncSessionLocal() as session:
        count = await import_scopus_excel(session, excel_path)
        await session.commit()

    elapsed = time.time() - start_time
    print(f"[import] SUCCESS: Nap thanh cong {count:,} tap chi Scopus va CSDL!")
    print(f"[import] Thoi gian thuc thi: {elapsed:.2f} giay.")

if __name__ == "__main__":
    asyncio.run(main())
