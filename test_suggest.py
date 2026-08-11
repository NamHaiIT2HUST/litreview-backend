import asyncio
from src.services.rag_service import rag_service

async def main():
    prompt = '''You are an expert academic librarian. Based on the following research project:
    Topic: Tác động của sinh viên kiệt sức
    Field: Giáo dục học
    Question: Sinh viên kiệt sức ảnh hưởng thế nào đến kết quả học tập?

    Suggest 5-7 highly effective search keywords or phrases for querying databases like Google Scholar or Scopus.
    Return ONLY a JSON array of strings. Do not include markdown formatting or explanations.
    Example: ["machine learning", "deep learning", "healthcare AI"]'''
    try:
        response = await rag_service.llm.ainvoke(prompt)
        content = response.content.strip()
        print('RAW CONTENT:', repr(content))
        if content.startswith('```json'):
            content = content.replace('```json', '').replace('```', '').strip()
        elif content.startswith('```'):
            content = content.replace('```', '').strip()
        import json
        keywords = json.loads(content)
        print('PARSED:', keywords)
    except Exception as e:
        print('EXCEPTION:', e)

asyncio.run(main())
