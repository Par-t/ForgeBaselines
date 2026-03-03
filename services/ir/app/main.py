"""IR service — BM25 retrieval baselines."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.routers import health, retrieve

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("IR service starting up")
    yield
    logger.info("IR service shutting down")


app = FastAPI(
    title="ForgeBaselines IR Service",
    description="BM25 information retrieval baselines",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(retrieve.router)


@app.get("/")
async def root():
    return {"service": "ir", "status": "ok"}
