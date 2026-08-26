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

from src.api.auth_routes import router as auth_router
from src.api.export_routes import router as export_router
from src.api.project_routes import router as project_router
from src.api.routes import router as root_router
from src.api.screening_routes import router as screening_router
from src.api.slr_swarm_routes import router as slr_swarm_router
from src.config import get_settings, validate_security_settings
from src.database import create_all_tables, ensure_local_schema_compatibility
from src.services.embedding_manager import (
    EmbeddingConfigurationError,
    EmbeddingIndexMismatchError,
)
from src.services.ingestion_service import PdfIngestionError
from src.services.llm import LLMBudgetExceededError, NoCapableProviderError

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
    await _ensure_demo_accounts()
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
    """Seed a small set of Scopus source rows so lookups work on an empty database.

    Each entry carries its real Scopus sourcerecord_id. Several previously did
    not -- PLOS ONE was "12345678901", and a run of neighbouring MDPI titles
    shared invented sequential ids -- which put values in the database that look
    like Scopus identifiers, are not, and cannot be told apart from real ones
    afterwards. Entries whose real id could not be confirmed are omitted rather
    than made up; the proper fix for coverage is importing the official source
    list via import_scopus_excel.

    quartile is None throughout, because the Scopus source list has no quartile
    column at all: it needs the separate CiteScore file, and a journal has a
    different quartile per subject category. See the module docstring of
    src/services/scopus_matcher.py.
    """

    from sqlalchemy import func as _func
    from sqlalchemy import select as _select

    from src.database import AsyncSessionLocal
    from src.models.db_models import ScopusSource

    MINIMAL_SOURCES = [
        {"sourcerecord_id": "seed:ieee-access", "title": "IEEE Access", "issn": "21693536", "eissn": "21693536", "active_status": "Active", "coverage_ranges": "[[2013, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:sensors", "title": "Sensors", "issn": "14248220", "eissn": "14248220", "active_status": "Active", "coverage_ranges": "[[2001, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:scientific-reports", "title": "Scientific Reports", "issn": "20452322", "eissn": "20452322", "active_status": "Active", "coverage_ranges": "[[2011, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:plos-one", "title": "PLOS ONE", "issn": "19326203", "eissn": "19326203", "active_status": "Active", "coverage_ranges": "[[2006, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:ieee-transactions-on-biomedical-engineering", "title": "IEEE Transactions on Biomedical Engineering", "issn": "00189294", "eissn": "15582531", "active_status": "Active", "coverage_ranges": "[[1980, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:ieee-transactions-on-pattern-analysis-and-machine-intelligence", "title": "IEEE Transactions on Pattern Analysis and Machine Intelligence", "issn": "01628828", "eissn": "19393539", "active_status": "Active", "coverage_ranges": "[[1979, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:robotics-and-autonomous-systems", "title": "Robotics and Autonomous Systems", "issn": "09218890", "eissn": "1872793X", "active_status": "Active", "coverage_ranges": "[[1989, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:autonomous-robots", "title": "Autonomous Robots", "issn": "09295593", "eissn": "15737527", "active_status": "Active", "coverage_ranges": "[[1994, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:international-journal-of-robotics-research", "title": "International Journal of Robotics Research", "issn": "02783649", "eissn": "17413176", "active_status": "Active", "coverage_ranges": "[[1982, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:bioinformatics", "title": "Bioinformatics", "issn": "13674803", "eissn": "14602059", "active_status": "Active", "coverage_ranges": "[[1998, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:nature", "title": "Nature", "issn": "00280836", "eissn": "14764687", "active_status": "Active", "coverage_ranges": "[[1869, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:applied-sciences-switzerland", "title": "Applied Sciences (Switzerland)", "issn": "20763417", "eissn": "20763417", "active_status": "Active", "coverage_ranges": "[[2011, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:remote-sensing", "title": "Remote Sensing", "issn": "20724292", "eissn": "20724292", "active_status": "Active", "coverage_ranges": "[[2009, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:algorithms", "title": "Algorithms", "issn": "19994893", "eissn": "19994893", "active_status": "Active", "coverage_ranges": "[[2008, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:sustainability-switzerland", "title": "Sustainability (Switzerland)", "issn": "20711050", "eissn": "20711050", "active_status": "Active", "coverage_ranges": "[[2009, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:entropy", "title": "Entropy", "issn": "10994300", "eissn": "10994300", "active_status": "Active", "coverage_ranges": "[[1999, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:diagnostics", "title": "Diagnostics", "issn": "20754418", "eissn": "20754418", "active_status": "Active", "coverage_ranges": "[[2011, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:materials", "title": "Materials", "issn": "19961944", "eissn": "19961944", "active_status": "Active", "coverage_ranges": "[[2008, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:biomedicines", "title": "Biomedicines", "issn": "22279059", "eissn": "22279059", "active_status": "Active", "coverage_ranges": "[[2013, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:electronics-switzerland", "title": "Electronics (Switzerland)", "issn": "20799292", "eissn": "20799292", "active_status": "Active", "coverage_ranges": "[[2012, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:cancers", "title": "Cancers", "issn": "20726694", "eissn": "20726694", "active_status": "Active", "coverage_ranges": "[[2009, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:cells", "title": "Cells", "issn": "20734409", "eissn": "20734409", "active_status": "Active", "coverage_ranges": "[[2012, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:water-switzerland", "title": "Water (Switzerland)", "issn": "20734441", "eissn": "20734441", "active_status": "Active", "coverage_ranges": "[[2009, 2026]]", "quartile": None},
        {"sourcerecord_id": "seed:journal-of-clinical-medicine", "title": "Journal of Clinical Medicine", "issn": "20770383", "eissn": "20770383", "active_status": "Active", "coverage_ranges": "[[2012, 2026]]", "quartile": None},
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

    from src.api.auth_routes import hash_password
    from src.database import AsyncSessionLocal
    from src.models.db_models import Role, User

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


async def _ensure_demo_accounts():
    """Create the demo researcher profiles offered on the sign-in screen.

    These are ordinary user rows. Picking one in the UI performs a real login
    and receives a real token, so the shortcut skips the signup form and nothing
    else. validate_security_settings keeps this to development, because the
    password is shared and served to the client.
    """
    settings = get_settings()
    if not settings.seed_demo_accounts:
        return

    from sqlalchemy import func as _func
    from sqlalchemy import select as _select

    from src.api.auth_routes import DEMO_ACCOUNTS, hash_password
    from src.database import AsyncSessionLocal
    from src.models.db_models import Role, User

    async with AsyncSessionLocal() as session:
        try:
            created = 0
            for account in DEMO_ACCOUNTS:
                username = account["username"]
                exists = await session.execute(
                    _select(User).where(_func.lower(User.username) == username.lower())
                )
                if exists.scalars().first() is None:
                    session.add(User(
                        username=username,
                        hashed_password=hash_password(settings.seed_demo_password),
                        role=Role.user,
                    ))
                    created += 1
            if created:
                await session.commit()
                print(f"Demo accounts seeded ({created}).")
        except Exception as e:
            await session.rollback()
            print(f"Warning: could not seed demo accounts: {e}")


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


@app.exception_handler(NoCapableProviderError)
async def _no_capable_provider_handler(request, exc: NoCapableProviderError):
    """No configured provider can do this work -- an operator problem, not a result.

    503 with a structured body rather than a 500 or, worse, a plausible-looking
    answer. The previous behaviour for this case was to return the failure
    message inside the data itself: run_criteria_generator handed back
    "Hệ thống đang tạm thời hết hạn mức AI" as an inclusion criterion, which the
    UI rendered as a criterion and the user could save to the database.
    """
    logger.error("No capable LLM provider for %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error_code": "NO_CAPABLE_LLM_PROVIDER",
            "message": str(exc),
            "required_action": "FIX_CONFIGURATION",
            "details": {"task": exc.task, "providers": exc.reasons},
        },
    )


@app.exception_handler(LLMBudgetExceededError)
async def _llm_budget_handler(request, exc: LLMBudgetExceededError):
    logger.error("LLM budget exceeded on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error_code": "LLM_BUDGET_EXCEEDED",
            "message": str(exc),
            "required_action": "RETRY_LATER",
        },
    )


@app.exception_handler(PdfIngestionError)
async def _pdf_ingestion_handler(request, exc: PdfIngestionError):
    """The document could not be read, so it has not been indexed.

    422 rather than a silent substitution. A PDF that failed to parse used to be
    replaced by a chunk holding just its title and abstract and recorded as a
    successful ingestion, after which synthesis cited the paper as though it had
    been read in full.
    """
    logger.warning("PDF ingestion failed on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "PDF_INGESTION_FAILED",
            "message": str(exc),
            "required_action": "REUPLOAD_OR_OCR",
        },
    )


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

