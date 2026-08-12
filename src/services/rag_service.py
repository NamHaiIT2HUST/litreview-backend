import json
import os
from typing import List
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

from src.config import get_settings

class RAGService:
    def __init__(self):
        settings = get_settings()
        self._settings = settings
        self._llm = None

        # Prompt template for RAG
        prompt_template = """
Bạn là một trợ lý nghiên cứu học thuật. Hãy trả lời câu hỏi sau một cách chi tiết và chính xác, CHỈ dựa trên ngữ cảnh được cung cấp.
Nếu thông tin trong ngữ cảnh không đủ để trả lời câu hỏi, hãy thành thật trả lời là "Tôi không tìm thấy thông tin này trong bài báo".

Ngữ cảnh:
{context}

Câu hỏi: {question}

Câu trả lời:
"""
        self.prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )

    @property
    def llm(self):
        if self._llm is None:
            gemini_key = self._settings.gemini_api_key or self._settings.google_api_key
            if not gemini_key:
                raise RuntimeError(
                    "Gemini API key is required. Set GEMINI_API_KEY or GOOGLE_API_KEY in .env."
                )
            self._llm = ChatGoogleGenerativeAI(
                model=(
                    self._settings.model_name
                    if self._settings.model_name.startswith("gemini-")
                    else "gemini-1.5-flash"
                ),
                google_api_key=gemini_key,
                temperature=self._settings.llm_temperature,
            )
        return self._llm

    def _build_chain(self):
        return self.prompt | self.llm | StrOutputParser()

    def _format_docs(self, docs: List[Document]) -> str:
        return "\n\n".join(doc.page_content for doc in docs)

    @staticmethod
    def make_chunk_id(doc: Document, index: int) -> str:
        """Tạo id tạm cho 1 chunk dựa trên metadata (source + page).

        MVP: chưa có char_start/char_end thật trong metadata (xem
        document_processor.py), nên id này chỉ đủ để trỏ về 1 trang PDF,
        chưa trỏ được tới đoạn ký tự cụ thể. Nâng cấp sau ở bước Ingestion.
        """
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")
        return f"{os.path.basename(str(source))}::p{page}::{index}"

    async def generate_structured_answer(self, query: str, chunks: List[Document]) -> list[dict]:
        """
        Sinh câu trả lời dạng list các câu, MỖI câu bắt buộc gắn chunk_id
        làm bằng chứng. Câu nào không truy vết được nguồn thì không sinh ra.

        Trả về: [{"sentence": ..., "chunk_id": ..., "source": ...}, ...]
        """
        if not chunks:
            return []

        # Đánh id cho từng chunk để LLM có thể trỏ lại đúng ô nào
        indexed_context = []
        id_map = {}
        for i, doc in enumerate(chunks):
            cid = self.make_chunk_id(doc, i)
            id_map[cid] = doc.metadata.get("source", "unknown")
            indexed_context.append(f"[{cid}]\n{doc.page_content}")

        context_str = "\n\n".join(indexed_context)

        structured_prompt = PromptTemplate(
            template="""Bạn là trợ lý nghiên cứu học thuật. Dựa CHỈ trên các đoạn văn bản
được đánh dấu [chunk_id] dưới đây, hãy trả lời câu hỏi.

QUY TẮC BẮT BUỘC:
- Chia câu trả lời thành từng câu riêng biệt.
- MỖI câu phải trỏ đúng 1 chunk_id làm bằng chứng cho câu đó.
- Nếu không có đoạn nào đủ để trả lời, trả về mảng rỗng [].
- CHỈ trả về JSON, không thêm chữ nào khác, không dùng markdown code fence.

Định dạng JSON bắt buộc:
[{{"sentence": "...", "chunk_id": "..."}}, ...]

Các đoạn văn bản:
{context}

Câu hỏi: {question}

JSON:""",
            input_variables=["context", "question"],
        )
        chain = structured_prompt | self.llm | StrOutputParser()
        raw = await chain.ainvoke({"context": context_str, "question": query})

        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return []

        results = []
        for item in parsed:
            cid = item.get("chunk_id", "")
            if cid not in id_map:
                continue  # loại câu trỏ vào chunk_id bịa ra
            results.append({
                "sentence": item.get("sentence", ""),
                "chunk_id": cid,
                "source": id_map[cid],
            })
        return results

    async def generate_answer(self, query: str, chunks: List[Document]) -> str:
        """
        Tạo câu trả lời dựa trên câu hỏi và danh sách tài liệu context.
        """
        if not chunks:
            return "Tôi không tìm thấy ngữ cảnh nào phù hợp trong tài liệu để trả lời câu hỏi này."
            
        context_str = self._format_docs(chunks)
        
        response = await self._build_chain().ainvoke({
            "context": context_str,
            "question": query
        })
        
        return response

rag_service = RAGService()
