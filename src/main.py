from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from src.api.admin import router as admin_router
from src.api.digests import router as digests_router
from src.api.feedback import router as feedback_router
from src.config.settings import Settings

logger = structlog.get_logger()

settings = Settings()


def _run_migrations():
    import subprocess
    result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("migration_failed", stderr=result.stderr)
        raise RuntimeError(f"Alembic migration failed: {result.stderr}")
    logger.info("migrations_applied")


async def _seed_if_empty():
    from scripts.seed import seed
    await seed()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _run_migrations()
    await _seed_if_empty()
    from src.jobs.scheduler import create_scheduler
    scheduler = create_scheduler(start=True)
    logger.info("app_startup", version="0.1.0")
    yield
    scheduler.shutdown(wait=False)
    logger.info("app_shutdown")


app = FastAPI(
    title="City Family Events Curator",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

app.include_router(admin_router)
app.include_router(feedback_router)
app.include_router(digests_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
