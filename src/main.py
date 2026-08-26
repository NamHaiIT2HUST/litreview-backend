import logging
import os

from dotenv import load_dotenv

from src.config import ENV_FILE

load_dotenv(ENV_FILE)
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import router as root_router
from src.api.project_routes import router as project_router
from src.api.screening_routes import router as screening_router
from src.api.export_routes import router as export_router
from src.api.slr_swarm_routes import router as slr_swarm_router
from src.api.auth_routes import router as auth_router
from src.config import get_settings, validate_security_settings
from src.database import create_all_tables, ensure_local_schema_compatibility
from src.services.embedding_manager import (
    EmbeddingConfigurationError,
    EmbeddingIndexMismatchError,
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Raises SecurityConfigurationError and aborts startup rather than running
    # with a publicly-known signing key or seeded admin credentials.
    validate_security_settings(settings)
    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    await create_all_tables()  # Ensure all tables exist (idempotent)
    await ensure_local_schema_compatibility()
    print("Database tables ready.")
    
    # Seed the default project so synthesis & direct-upload always work
    await _ensure_default_project()
    print("Default project seeded.")
    await _ensure_default_admin()
    import asyncio
    # Fast v2 (EXPERIMENTAL): warm local evidence models in background task
    # to allow the HTTP port to bind immediately and avoid startup timeouts
    if settings.fast_v2_enabled:
        async def _safe_warm_fast_v2():
            try:
                from src.synthesis.fast_v2.runtime import warm_fast_v2
                warmup_timings = await warm_fast_v2()
                print(f"Fast v2 warmup complete: {warmup_timings}")
            except Exception as e:
                print(f"Warning: Fast v2 warmup failed: {e}")
        asyncio.create_task(_safe_warm_fast_v2())

    # Run minimal Scopus seeding in the background to prevent blocking server port binding
    asyncio.create_task(_ensure_minimal_scopus_sources())
    print("Background tasks scheduled. Server ready.")
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

async def _ensure_default_admin():
    """Seed an admin account, but only when explicitly configured to.

    This used to unconditionally create ``admin123`` with the password ``123``
    on every startup in every environment, including production. Seeding is now
    opt-in, development-only, and takes the password from configuration;
    ``validate_security_settings`` enforces both conditions.
    """
    settings = get_settings()
    if not settings.seed_default_admin:
        return

    from sqlalchemy import select as _select
    from src.database import AsyncSessionLocal
    from src.models.db_models import User, Role
    from src.api.auth_routes import hash_password

    async with AsyncSessionLocal() as session:
        try:
            exists = await session.execute(
                _select(User).where(User.username == settings.seed_admin_username)
            )
            if exists.scalars().first() is None:
                admin_user = User(
                    username=settings.seed_admin_username,
                    hashed_password=hash_password(settings.seed_admin_password),
                    role=Role.admin
                )
                session.add(admin_user)
                await session.commit()
                print(f"Development admin account seeded ({settings.seed_admin_username}).")
        except Exception as e:
            await session.rollback()
            print(f"Warning: could not seed default admin: {e}")


app = FastAPI(
    title="AI20K Agent",
    description="AI Agent built with LangGraph",
    version="1.0.5",
    lifespan=lifespan,
)

settings = get_settings()
# CORS_ORIGINS was documented in .env.example but never read: the middleware
# was pinned to "*", so the setting had no effect at all.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(EmbeddingIndexMismatchError)
async def _embedding_index_mismatch_handler(request, exc: EmbeddingIndexMismatchError):
    """Fail hard in the logic layer, but hand the UI something it can act on.

    409 Conflict, not 500: the request is well-formed and the server is healthy;
    the stored index and the current configuration simply disagree. The payload
    names the required action so the frontend can offer a re-index instead of
    showing a stack trace -- and, critically, so it never shows an empty result
    list, which would be indistinguishable from "this document says nothing".
    """
    logger.error("Embedding index mismatch on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=exc.to_error_payload())


@app.exception_handler(EmbeddingConfigurationError)
async def _embedding_configuration_handler(request, exc: EmbeddingConfigurationError):
    """A misconfigured embedding provider is an operator problem, not a result."""
    logger.error("Embedding configuration error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error_code": "EMBEDDING_NOT_CONFIGURED",
            "message": str(exc),
            "required_action": "FIX_CONFIGURATION",
        },
    )


app.include_router(project_router, prefix="/api/v1")
app.include_router(root_router, prefix="/api/v1")
app.include_router(screening_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(slr_swarm_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


@app.get("/")
@app.head("/")
async def root_health():
    return {"status": "ok", "app": "LitReview Agent", "version": "1.0.5"}


@app.get("/health")
async def health():
    # Deliberately does not echo API key prefixes. This endpoint is
    # unauthenticated and publicly reachable; key prefixes identify the
    # provider and key format and are not safe to publish.
    return {
        "status": "ok",
        "env": settings.app_env,
        "version": app.version,
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", settings.app_port))
    uvicorn.run("src.main:app", host=settings.app_host, port=port, reload=False)

