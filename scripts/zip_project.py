import os
import zipfile
from pathlib import Path

def create_zip():
    repo_dir = Path(".").resolve()
    zip_filename = repo_dir / "P-165_Project_Source.zip"

    exclude_dirs = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".chroma_db",
        "__pycache__",
        ".pytest_cache",
        "dist",
        "build",
        ".gemini",
    }

    exclude_files = {
        "P-165_Project_Source.zip",
        ".env",
        "app.db",
    }

    print(f"Creating zip file at: {zip_filename}")

    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(repo_dir):
            # Exclude directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]

            for file in files:
                if file in exclude_files or file.endswith(".pyc") or file.endswith(".zip"):
                    continue

                file_path = Path(root) / file
                rel_path = file_path.relative_to(repo_dir)
                
                print(f"Adding: {rel_path}")
                zipf.write(file_path, rel_path)

    size_mb = zip_filename.stat().st_size / (1024 * 1024)
    print(f"\nSUCCESS: Zip archive created at '{zip_filename}' ({size_mb:.2f} MB)")

if __name__ == "__main__":
    create_zip()
