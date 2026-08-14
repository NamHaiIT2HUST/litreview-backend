import asyncio, json, os, time, uuid
from collections import defaultdict
from sqlalchemy import select
from src.database import session_scope
from src.models.db_models import LLMCallLog, Paper, SynthesisMetrics, SynthesisSession, SynthesisStatus
from src.synthesis.graph import build_synthesis_graph
from src.services.synthesis_llm_service import synthesis_llm_service

RQ = "How have algorithms for the Split Feasibility Problem evolved in terms of problem assumptions, projection mechanisms, convergence guarantees, and computational requirements?"
async def main():
    async with session_scope() as db:
        papers = list((await db.execute(select(Paper).order_by(Paper.created_at))).scalars())
        papers = papers[:5]
        session = SynthesisSession(id=uuid.uuid4(), project_id=papers[0].project_id, paper_ids=[str(p.id) for p in papers], research_question=RQ, status=SynthesisStatus.processing)
        db.add(session); await db.flush(); sid=session.id
    started=time.perf_counter(); error=None
    try: await build_synthesis_graph().ainvoke({"session_id":str(sid)})
    except Exception as exc: error=f"{type(exc).__name__}: {exc}"
    wall=int((time.perf_counter()-started)*1000)
    async with session_scope() as db:
        logs=list((await db.execute(select(LLMCallLog).where(LLMCallLog.session_id==sid))).scalars())
        metrics=(await db.execute(select(SynthesisMetrics).where(SynthesisMetrics.session_id==sid))).scalar_one_or_none()
    stages=defaultdict(lambda:{"calls":0,"duration_ms":0,"durations_ms":[]})
    for log in logs:
        x=stages[log.step_name]; x["calls"]+=1; x["duration_ms"]+=log.duration_ms or 0; x["durations_ms"].append(log.duration_ms or 0)
    print(json.dumps({"session_id":str(sid),"error":error,"wall_ms":wall,"llm_calls":len(logs),"stages":stages,"metrics":({"final_word_count":metrics.final_word_count,"citation_coverage":metrics.citation_coverage,"grounding_retries":metrics.grounding_retry_count,"section_metrics":metrics.section_metrics} if metrics else None),"concurrency":synthesis_llm_service.concurrency_snapshot()},default=str))
if __name__=="__main__": asyncio.run(main())
