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
    yield
    print("Shutting down...")


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
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(project_router, prefix="/api/v1")
app.include_router(root_router, prefix="/api/v1")
app.include_router(screening_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")


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
