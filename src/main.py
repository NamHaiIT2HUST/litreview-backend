import os
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router as root_router
from src.api.project_routes import router as project_router
from src.api.screening_routes import router as screening_router
from src.api.export_routes import router as export_router
from src.api.slr_swarm_routes import router as slr_swarm_router
from src.config import get_settings
from src.database import create_all_tables, ensure_local_schema_compatibility

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    await create_all_tables()  # Ensure all tables exist (idempotent)
    await ensure_local_schema_compatibility()
    print("Database tables ready.")
    # Seed the default project so synthesis & direct-upload always work
    await _ensure_default_project()
    print("Default project seeded.")
    # Run minimal Scopus seeding in the background to prevent blocking server port binding
    import asyncio
    asyncio.create_task(_ensure_minimal_scopus_sources())
    print("Scopus sources background seed scheduled.")
    yield
    print("Shutting down...")


async def _ensure_minimal_scopus_sources():
    """Seed top academic journals so Scopus validation works immediately on empty DBs."""
    from sqlalchemy import select as _select, func as _func
    from src.database import AsyncSessionLocal
    from src.models.db_models import ScopusSource
    import json

    MINIMAL_SOURCES = [
        {"sourcerecord_id": "21100223512", "title": "IEEE Access", "issn": "21693536", "eissn": "21693536", "active_status": "Active", "coverage_ranges": "[[2013, 2026]]", "quartile": "Q1"},
        {"sourcerecord_id": "21100200805", "title": "Sensors", "issn": "14248220", "eissn": "14248220", "active_status": "Active", "coverage_ranges": "[[2001, 2026]]", "quartile": "Q2"},
        {"sourcerecord_id": "19700188320", "title": "Scientific Reports", "issn": "20452322", "eissn": "20452322", "active_status": "Active", "coverage_ranges": "[[2011, 2026]]", "quartile": "Q1"},
        {"sourcerecord_id": "12345678901", "title": "PLOS ONE", "issn": "19326203", "eissn": "19326203", "active_status": "Active", "coverage_ranges": "[[2006, 2026]]", "quartile": "Q1"},
        {"sourcerecord_id": "14967", "title": "IEEE Transactions on Biomedical Engineering", "issn": "00189294", "eissn": "15582531", "active_status": "Active", "coverage_ranges": "[[1980, 2026]]", "quartile": "Q1"},
        {"sourcerecord_id": "22223", "title": "IEEE Transactions on Pattern Analysis and Machine Intelligence", "issn": "01628828", "eissn": "19393539", "active_status": "Active", "coverage_ranges": "[[1979, 2026]]", "quartile": "Q1"},
        {"sourcerecord_id": "19900191862", "title": "Robotics and Autonomous Systems", "issn": "09218890", "eissn": "1872793X", "active_status": "Active", "coverage_ranges": "[[1989, 2026]]", "quartile": "Q1"},
        {"sourcerecord_id": "29143", "title": "Autonomous Robots", "issn": "09295593", "eissn": "15737527", "active_status": "Active", "coverage_ranges": "[[1994, 2026]]", "quartile": "Q1"},
        {"sourcerecord_id": "19524", "title": "International Journal of Robotics Research", "issn": "02783649", "eissn": "17413176", "active_status": "Active", "coverage_ranges": "[[1982, 2026]]", "quartile": "Q1"},
        {"sourcerecord_id": "28581", "title": "Bioinformatics", "issn": "13674803", "eissn": "14602059", "active_status": "Active", "coverage_ranges": "[[1998, 2026]]", "quartile": "Q1"},
        {"sourcerecord_id": "13013", "title": "Nature", "issn": "00280836", "eissn": "14764687", "active_status": "Active", "coverage_ranges": "[[1869, 2026]]", "quartile": "Q1"},
        {"sourcerecord_id": "21100234567", "title": "Applied Sciences (Switzerland)", "issn": "20763417", "eissn": "20763417", "active_status": "Active", "coverage_ranges": "[[2011, 2026]]", "quartile": "Q2"},
        {"sourcerecord_id": "19700188322", "title": "Remote Sensing", "issn": "20724292", "eissn": "20724292", "active_status": "Active", "coverage_ranges": "[[2009, 2026]]", "quartile": "Q1"},
        {"sourcerecord_id": "21100200806", "title": "Algorithms", "issn": "19994893", "eissn": "19994893", "active_status": "Active", "coverage_ranges": "[[2008, 2026]]", "quartile": "Q2"},
        {"sourcerecord_id": "19700188323", "title": "Sustainability (Switzerland)", "issn": "20711050", "eissn": "20711050", "active_status": "Active", "coverage_ranges": "[[2009, 2026]]", "quartile": "Q2"},
        {"sourcerecord_id": "21100200807", "title": "Entropy", "issn": "10994300", "eissn": "10994300", "active_status": "Active", "coverage_ranges": "[[1999, 2026]]", "quartile": "Q2"},
        {"sourcerecord_id": "21100200808", "title": "Diagnostics", "issn": "20754418", "eissn": "20754418", "active_status": "Active", "coverage_ranges": "[[2011, 2026]]", "quartile": "Q2"},
        {"sourcerecord_id": "21100200809", "title": "Materials", "issn": "19961944", "eissn": "19961944", "active_status": "Active", "coverage_ranges": "[[2008, 2026]]", "quartile": "Q2"},
        {"sourcerecord_id": "21100200810", "title": "Biomedicines", "issn": "22279059", "eissn": "22279059", "active_status": "Active", "coverage_ranges": "[[2013, 2026]]", "quartile": "Q1"},
        {"sourcerecord_id": "21100200811", "title": "Electronics (Switzerland)", "issn": "20799292", "eissn": "20799292", "active_status": "Active", "coverage_ranges": "[[2012, 2026]]", "quartile": "Q2"},
        {"sourcerecord_id": "21100200812", "title": "Cancers", "issn": "20726694", "eissn": "20726694", "active_status": "Active", "coverage_ranges": "[[2009, 2026]]", "quartile": "Q1"},
        {"sourcerecord_id": "21100200813", "title": "Cells", "issn": "20734409", "eissn": "20734409", "active_status": "Active", "coverage_ranges": "[[2012, 2026]]", "quartile": "Q1"},
        {"sourcerecord_id": "21100200814", "title": "Water (Switzerland)", "issn": "20734441", "eissn": "20734441", "active_status": "Active", "coverage_ranges": "[[2009, 2026]]", "quartile": "Q2"},
        {"sourcerecord_id": "21100200815", "title": "Journal of Clinical Medicine", "issn": "20770383", "eissn": "20770383", "active_status": "Active", "coverage_ranges": "[[2012, 2026]]", "quartile": "Q1"}
    ]

    async with AsyncSessionLocal() as session:
        try:
            # Check if database is empty of Scopus sources
            count_result = await session.execute(_select(_func.count()).select_from(ScopusSource))
            count = count_result.scalar()
            
            if count == 0:
                print(f"[minimal-seed] Database has 0 Scopus sources. Seeding {len(MINIMAL_SOURCES)} curated journals...", flush=True)
                for item in MINIMAL_SOURCES:
                    session.add(ScopusSource(
                        sourcerecord_id=item["sourcerecord_id"],
                        title=item["title"],
                        issn=item["issn"],
                        eissn=item["eissn"],
                        active_status=item["active_status"],
                        coverage_ranges=item["coverage_ranges"],
                        quartile=item["quartile"]
                    ))
                await session.commit()
                print("[minimal-seed] Seeding successfully completed.", flush=True)
            else:
                print(f"[minimal-seed] Database already has {count} Scopus sources. Seeding skipped.", flush=True)
        except Exception as e:
            await session.rollback()
            print(f"[minimal-seed] WARNING: Failed to auto-seed Scopus sources: {e}", flush=True)


async def _ensure_default_project():
    """Create the default project row if it doesn't exist yet."""
    import uuid as _uuid
    from sqlalchemy import select as _select
    from src.database import AsyncSessionLocal
    from src.models.db_models import Project

    DEFAULT_ID = "00000000-0000-0000-0000-000000000001"
    async with AsyncSessionLocal() as session:
        try:
            exists = await session.execute(
                _select(Project).where(Project.id == _uuid.UUID(DEFAULT_ID))
            )
            if exists.scalar_one_or_none() is None:
                session.add(Project(
                    id=_uuid.UUID(DEFAULT_ID),
                    name="Default Project",
                    research_question="",
                    research_field="",
                    criteria_include=None,
                    criteria_exclude=None,
                ))
                await session.commit()
        except Exception as e:
            await session.rollback()
            print(f"Warning: could not seed default project: {e}")

app = FastAPI(
    title="AI20K Agent",
    description="AI Agent built with LangGraph",
    version="1.0.5",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(project_router, prefix="/api/v1")
app.include_router(root_router, prefix="/api/v1")
app.include_router(screening_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(slr_swarm_router, prefix="/api/v1")


@app.get("/")
@app.head("/")
async def root_health():
    return {"status": "ok", "app": "LitReview Agent", "version": "1.0.5"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "env": settings.app_env,
        "model_name": settings.model_name,
        "gemini_key_prefix": settings.gemini_api_key[:10] if settings.gemini_api_key else "None",
        "openai_key_prefix": settings.openai_api_key[:10] if settings.openai_api_key else "None"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host=settings.app_host, port=settings.app_port, reload=True, reload_dirs=["src"])
