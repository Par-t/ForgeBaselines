"""Classification service FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.routers import health, train
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    print(f"Starting classification service in {settings.env} mode")
    print(f"MLflow tracking URI: {settings.mlflow_tracking_uri}")
    yield
    # Shutdown
    print("Shutting down classification service")


app = FastAPI(
    title="ForgeBaselines Classification",
    description="ML classification training service",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(health.router)
app.include_router(train.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "ForgeBaselines Classification",
        "version": "1.0.0",
        "status": "running"
    }