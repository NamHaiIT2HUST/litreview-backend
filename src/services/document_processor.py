import os
import shutil
import uuid
from fastapi import UploadFile

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

UPLOAD_DIR = "uploads/papers"

class DocumentProcessor:
    def __init__(self):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

    async def save_upload_file(self, upload_file: UploadFile) -> str:
        """Lưu file từ request xuống thư mục vật lý."""
        file_id = str(uuid.uuid4())
        # Tạo tên file an toàn để tránh ghi đè
        safe_filename = f"{file_id}_{upload_file.filename}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
            
        return file_path

    def extract_and_chunk(self, file_path: str):
        """Đọc PDF và cắt thành các chunk nhỏ."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Bước 1: Load toàn bộ trang PDF
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        
        # Bước 2: Cắt nhỏ nội dung
        chunks = self.text_splitter.split_documents(pages)
        
        return pages, chunks
