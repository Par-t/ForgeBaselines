"""Orchestrator FastAPI application."""

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, datasets, experiments
from app.config import settings
from app.firebase import init_firebase

logger = logging.getLogger(__name__)


def _recover_orphaned_experiments() -> None:
    """On startup, mark any 'running' experiments as failed.

    Background tasks die with the process. Any experiment still marked
    'running' at startup was orphaned by a previous crash/restart.
    """
    data_dir = Path(settings.data_path)
    if not data_dir.exists():
        return

    recovered = 0
    failed_msg = json.dumps({
        "stage": "error", "pct": 0, "status": "failed",
        "message": "Experiment was interrupted (service restart). Please re-run.",
    })

    for user_dir in data_dir.iterdir():
        if not user_dir.is_dir():
            continue

        # Classification experiments: {user}/{dataset}/preprocessed/{exp_id}/
        for dataset_dir in user_dir.iterdir():
            if dataset_dir.name == "ir" or not dataset_dir.is_dir():
                continue
            preprocessed = dataset_dir / "preprocessed"
            if not preprocessed.exists():
                continue
            for exp_dir in preprocessed.iterdir():
                progress_path = exp_dir / "progress.json"
                if not progress_path.exists():
                    continue
                try:
                    p = json.loads(progress_path.read_text())
                    if p.get("status") == "running":
                        progress_path.write_text(failed_msg)
                        recovered += 1
                        logger.warning("Recovered orphaned classification experiment: %s", exp_dir.name)
                except Exception:
                    pass

        # IR experiments: {user}/ir/{exp_id}/
        ir_dir = user_dir / "ir"
        if not ir_dir.exists():
            continue
        for exp_dir in ir_dir.iterdir():
            if not exp_dir.is_dir():
                continue
            # Skip if results already written — experiment actually completed
            if (exp_dir / "results.json").exists():
                continue
            progress_path = exp_dir / "progress.json"
            if not progress_path.exists():
                continue
            try:
                p = json.loads(progress_path.read_text())
                if p.get("status") == "running":
                    progress_path.write_text(failed_msg)
                    recovered += 1
                    logger.warning("Recovered orphaned IR experiment: %s", exp_dir.name)
            except Exception:
                pass

    if recovered:
        logger.info("Startup recovery: marked %d orphaned experiment(s) as failed", recovered)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting orchestrator service in %s mode", settings.env)
    logger.info("MLflow tracking URI: %s", settings.mlflow_tracking_uri)
    logger.info("Storage backend: %s", settings.storage_backend)
    init_firebase()
    _recover_orphaned_experiments()
    yield
    # Shutdown
    logger.info("Shutting down orchestrator service")


app = FastAPI(
    title="ForgeBaselines Orchestrator",
    description="ML baseline orchestration service",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware — set FRONTEND_URL env var to your Vercel domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(datasets.router)
app.include_router(experiments.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "ForgeBaselines Orchestrator",
        "version": "1.0.0",
        "status": "running"
    }