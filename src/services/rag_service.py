import os
from typing import List
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

class RAGService:
    def __init__(self):
        # Tắt LangSmith tracing để tránh lỗi 403 Forbidden nếu user không có LANGCHAIN_API_KEY hợp lệ
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        
        # We assume GEMINI_API_KEY_1 is loaded in environment via python-dotenv
        api_key = os.getenv("GEMINI_API_KEY_1")
        if api_key and not os.getenv("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = api_key
            
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            temperature=0.2,
            max_output_tokens=2048,
            timeout=30
        )
        
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
        
        # Simple LCEL Chain: format dict -> prompt -> llm -> string
        self.chain = self.prompt | self.llm | StrOutputParser()

    def _format_docs(self, docs: List[Document]) -> str:
        return "\n\n".join(doc.page_content for doc in docs)

    async def generate_answer(self, query: str, chunks: List[Document]) -> str:
        """
        Tạo câu trả lời dựa trên câu hỏi và danh sách tài liệu context.
        """
        if not chunks:
            return "Tôi không tìm thấy ngữ cảnh nào phù hợp trong tài liệu để trả lời câu hỏi này."
            
        context_str = self._format_docs(chunks)
        
        response = await self.chain.ainvoke({
            "context": context_str,
            "question": query
        })
        
        return response

rag_service = RAGService()
