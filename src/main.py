from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from src.api.admin import router as admin_router
from src.api.digests import router as digests_router
from src.api.feedback import router as feedback_router
from src.config.settings import Settings

logger = structlog.get_logger()

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
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
