import os
from typing import List
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document

load_dotenv()
CHROMA_PERSIST_DIR = ".chroma_db"

class VectorStoreService:
    def __init__(self):
        # We assume GEMINI_API_KEY_1 is loaded in environment via python-dotenv in main.py
        # Fallback to os.environ mapping if langchain uses GOOGLE_API_KEY specifically
        api_key = os.getenv("GEMINI_API_KEY_1")
        if api_key and not os.getenv("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = api_key
            
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        
        self.vector_store = Chroma(
            collection_name="litreview_papers",
            embedding_function=self.embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )

    async def add_documents(self, documents: List[Document]):
        """
        Nhúng và lưu danh sách các chunk vào ChromaDB.
        """
        if not documents:
            return 0
            
        self.vector_store.add_documents(documents=documents)
        return len(documents)

    async def search_similar_documents(self, query: str, top_k: int = 4) -> List[Document]:
        """
        Tìm kiếm các đoạn văn bản tương đồng với câu hỏi.
        """
        results = self.vector_store.similarity_search(query, k=top_k)
        return results

vector_store_service = VectorStoreService()
