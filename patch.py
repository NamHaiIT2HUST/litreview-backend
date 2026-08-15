import sys
import re

with open('src/api/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix UUID
content = content.replace('project_result = await db.execute(select(Project).where(Project.id == request.project_id))', '''try:
        project_uuid = uuid.UUID(str(request.project_id))
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid project_id format: {request.project_id}")
    project_result = await db.execute(select(Project).where(Project.id == project_uuid))''')

content = content.replace('paper_ids = list(dict.fromkeys(request.paper_ids))', 'raw_paper_ids = list(dict.fromkeys(request.paper_ids))')
content = content.replace('if len(paper_ids) > max_papers:', 'if len(raw_paper_ids) > max_papers:')
content = content.replace('paper_result = await db.execute(select(Paper).where(Paper.id.in_(paper_ids)))', '''parsed_paper_ids = [uuid.UUID(str(pid)) for pid in raw_paper_ids]
    paper_result = await db.execute(select(Paper).where(Paper.id.in_(parsed_paper_ids)))''')
content = content.replace('missing = [paper_id for paper_id in paper_ids if paper_id not in by_id]', 'missing = [pid for pid in parsed_paper_ids if pid not in by_id]')
content = content.replace('paper.id for paper in papers if paper.project_id != request.project_id', 'paper.id for paper in papers if paper.project_id != project_uuid')
content = content.replace('project_id=request.project_id,\n        paper_ids=paper_ids,', 'project_id=project_uuid,\n        paper_ids=[str(pid) for pid in parsed_paper_ids],')

# Fix Celery
celery_block = '''    try:
        from src.tasks.synthesis_tasks import run_synthesis_session
        run_synthesis_session.delay(str(session.id))
    except Exception as enqueue_exc:'''
fallback_block = '''    try:
        import asyncio
        from src.tasks.synthesis_tasks import run_synthesis_session
        asyncio.create_task(run_synthesis_session(str(session.id)))
    except Exception as enqueue_exc:'''
content = content.replace(celery_block, fallback_block)

# Add PDF route
pdf_route = '''
@router.get("/workspace/uploads/papers/{filename}")
async def get_pdf_file(filename: str):
    \"\"\"Serve uploaded PDF files.\"\"\"
    from fastapi.responses import FileResponse
    import os
    file_path = os.path.join("uploads", "papers", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/pdf")
'''
if 'get_pdf_file' not in content:
    content += pdf_route

with open('src/api/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
