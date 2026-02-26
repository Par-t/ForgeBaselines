"""Orchestrator FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, datasets, experiments
from app.config import settings
from app.firebase import init_firebase


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    print(f"Starting orchestrator service in {settings.env} mode")
    print(f"MLflow tracking URI: {settings.mlflow_tracking_uri}")
    print(f"Storage backend: {settings.storage_backend}")
    init_firebase()
    yield
    # Shutdown
    print("Shutting down orchestrator service")


app = FastAPI(
    title="ForgeBaselines Orchestrator",
    description="ML baseline orchestration service",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
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