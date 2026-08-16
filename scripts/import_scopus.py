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
    project_root = Path(__file__).parent.parent
    # Dynamically find any ext_list_*.xlsx file in the data/ directory
    excel_path = project_root / "data" / "ext_list_Jun_2026.xlsx"
    if not excel_path.exists():
        # Fallback to scanning the directory for any ext_list_*.xlsx file
        xlsx_files = list((project_root / "data").glob("ext_list_*.xlsx"))
        if xlsx_files:
            excel_path = xlsx_files[0]
        else:
            excel_path = project_root / "data" / "ext_list_Jul_2026.xlsx"

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
