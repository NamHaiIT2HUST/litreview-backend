import asyncio
import os
import sys
import glob
from dotenv import load_dotenv

# Load env before imports
load_dotenv(override=False)

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.services.document_processor import DocumentProcessor
from src.services.vector_store import vector_store_service
import re

def clean_source_name(source_path):
    source_path = str(source_path).replace("\\", "/")
    basename = os.path.basename(source_path)
    uuid_prefix = re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_(.+)$",
        basename,
        re.IGNORECASE,
    )
    if uuid_prefix:
        return uuid_prefix.group(1)
    return basename

def normalize_filename(name: str) -> str:
    if not name:
        return ""
    base = clean_source_name(name).lower()
    return re.sub(r"[^a-z0-9]", "", base)

async def reindex_all_papers():
    processor = DocumentProcessor()
    
    print("=" * 60)
    print(" [CLEANUP] XOA VECTOR STORE CU DE DAM BAO KHONG BI TRUNG LAP")
    try:
        vector_store_service.vector_store.delete_collection()
        print("    [SUCCESS] Da xoa collection cu thanh cong.")
    except Exception as e:
        print(f"    [WARN] Loi khi xoa collection (co the chua ton tai): {e}")

    # Re-initialize after deletion
    vector_store_service.__init__()

    upload_dir = "uploads/papers"
    pdf_files = glob.glob(f"{upload_dir}/**/*.pdf", recursive=True)
    
    print("=" * 60)
    print(f" [START] BAT DAU RE-INDEX TAT CA FILE PDF VAO CHROMADB")
    print(f" [DIR] Thu muc tim kiem: {upload_dir}")
    print(f" [FILE] So file PDF tim thay: {len(pdf_files)}")
    print("=" * 60)

    target_papers = ["4. byrne2002.pdf", "5. xu2010.pdf", "6. xu2018.pdf"]
    ingested_count = 0
    seen_normalized_names = set()

    for pdf_path in pdf_files:
        norm_name = normalize_filename(pdf_path)
        
        if norm_name in seen_normalized_names:
            continue
            
        is_target = any(normalize_filename(t) in norm_name for t in target_papers)
        
        # We index all target papers or all papers found
        if is_target or len(pdf_files) <= 10:
            seen_normalized_names.add(norm_name)
            print(f" [WAIT] Dang xu ly chunk va tao vector embedding cho: {os.path.basename(pdf_path)}...")
            try:
                pages, chunks = processor.extract_and_chunk(pdf_path)
                # Ensure filename is clean in metadata
                for c in chunks:
                    c.metadata["source"] = pdf_path
                
                await vector_store_service.vector_store.aadd_documents(chunks)
                print(f"    [OK] Thanh cong: {len(chunks)} chunks da duoc nap vao Chroma ({vector_store_service.vector_store._collection.name})")
                ingested_count += 1
            except Exception as e:
                print(f"    [FAIL] Loi khi index {pdf_path}: {e}")

    print("=" * 60)
    print(f" [DONE] HOAN TAT RE-INDEX {ingested_count} FILE PDF!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(reindex_all_papers())
