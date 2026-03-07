"""IR experiment endpoints: run BM25 baselines, fetch results."""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

logger = logging.getLogger(__name__)
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.dependencies import get_user_id
from app.schemas.ir_plan import (
    IRExperimentListResponse,
    IRExperimentListItem,
    IRExperimentRunRequest,
    IRExperimentRunResponse,
    IRMetrics,
    IRResultsResponse,
)
from app.config import settings
from app.services.storage import storage
from app.preprocessing.ir_pipeline import preprocess_ir_datasets

router = APIRouter(prefix="/experiments/ir", tags=["ir-experiments"])


def _write_progress(exp_dir: Path, stage: str, pct: int, status: str, message: str) -> None:
    """Atomically write progress.json so readers never see a partial file."""
    data = json.dumps({"stage": stage, "pct": pct, "status": status, "message": message})
    tmp = exp_dir / "progress.json.tmp"
    tmp.write_text(data)
    os.replace(tmp, exp_dir / "progress.json")


async def _run_ir_background(
    corpus_df: pd.DataFrame,
    queries_df: pd.DataFrame,
    exp_dir: Path,
    request: IRExperimentRunRequest,
    user_id: str,
    experiment_id: str,
) -> None:
    """Background task: preprocess, call IR service, persist results."""
    logger.info("[IR %s] Background task started", experiment_id)
    t0 = time.monotonic()
    try:
        _write_progress(exp_dir, "preprocessing", 10, "running", "Preprocessing text...")
        logger.info("[IR %s] Preprocessing datasets", experiment_id)
        corpus_df, queries_df = preprocess_ir_datasets(
            corpus_df, queries_df, "text", request.preprocessing_config
        )
        logger.info("[IR %s] Preprocessing done. corpus=%d rows, queries=%d rows",
                    experiment_id, len(corpus_df), len(queries_df))

        corpus_df.to_csv(exp_dir / "corpus.csv", index=False)
        queries_df.to_csv(exp_dir / "queries.csv", index=False)

        meta = {
            "task_type": "ir",
            "corpus_dataset_id": request.corpus_dataset_id,
            "queries_dataset_id": request.queries_dataset_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (exp_dir / "meta.json").write_text(json.dumps(meta))

        _write_progress(exp_dir, "retrieving", 30, "running", "Calling IR service...")
        logger.info("[IR %s] Calling IR service at %s", experiment_id, settings.ir_service_url)
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{settings.ir_service_url}/retrieve",
                json={
                    "corpus_path": str(exp_dir / "corpus.csv"),
                    "queries_path": str(exp_dir / "queries.csv"),
                    "text_column": "text",
                    "k_values": request.k_values,
                    "experiment_id": experiment_id,
                    "user_id": user_id,
                },
            )
            response.raise_for_status()

        logger.info("[IR %s] IR service responded in %.1fs", experiment_id, time.monotonic() - t0)
        data = response.json()
        results = {
            "metrics": data["metrics"],
            "n_docs": data["n_docs"],
            "n_queries": data["n_queries"],
        }
        (exp_dir / "results.json").write_text(json.dumps(results))
        _write_progress(exp_dir, "done", 100, "completed", "Completed")
        logger.info("[IR %s] Completed in %.1fs. metrics=%s", experiment_id, time.monotonic() - t0, data["metrics"])

    except Exception as e:
        logger.exception("[IR %s] Failed after %.1fs: %s", experiment_id, time.monotonic() - t0, e)
        _write_progress(exp_dir, "error", 0, "failed", f"Error: {str(e)}")


@router.post("/run", response_model=IRExperimentRunResponse)
async def run_ir_experiment(
    request: IRExperimentRunRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    """Start a BM25 IR experiment. Returns immediately; poll /status for progress."""
    # Load and validate synchronously so bad input gets an immediate error response
    try:
        corpus_path = storage.get_dataset_path(request.corpus_dataset_id, user_id)
        corpus_df = pd.read_csv(corpus_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Corpus dataset not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading corpus: {str(e)}")

    try:
        queries_path = storage.get_dataset_path(request.queries_dataset_id, user_id)
        queries_df = pd.read_csv(queries_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Queries dataset not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading queries: {str(e)}")

    corpus_user_cols = {request.corpus_doc_id_col, request.text_column}
    missing_corpus = corpus_user_cols - set(corpus_df.columns)
    if missing_corpus:
        raise HTTPException(status_code=400, detail=f"Corpus missing columns: {sorted(missing_corpus)}")

    corpus_df = corpus_df.rename(columns={
        request.corpus_doc_id_col: "doc_id",
        request.text_column: "text",
    })

    queries_required_cols = {request.queries_query_col, request.queries_doc_id_col}
    if request.queries_query_id_col:
        queries_required_cols.add(request.queries_query_id_col)
    if request.queries_relevance_col:
        queries_required_cols.add(request.queries_relevance_col)

    missing_queries = queries_required_cols - set(queries_df.columns)
    if missing_queries:
        raise HTTPException(status_code=400, detail=f"Queries missing columns: {sorted(missing_queries)}")

    queries_rename = {
        request.queries_query_col: "query",
        request.queries_doc_id_col: "doc_id",
    }
    if request.queries_query_id_col:
        queries_rename[request.queries_query_id_col] = "query_id"
    if request.queries_relevance_col:
        queries_rename[request.queries_relevance_col] = "relevance"

    queries_df = queries_df.rename(columns=queries_rename)

    if "query_id" not in queries_df.columns:
        queries_df["query_id"] = queries_df["query"]

    # Create dir + write initial progress, then return immediately
    experiment_id = str(uuid.uuid4())
    exp_dir = Path(settings.data_path) / user_id / "ir" / experiment_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    _write_progress(exp_dir, "queued", 0, "running", "Starting experiment...")

    background_tasks.add_task(
        _run_ir_background, corpus_df, queries_df, exp_dir, request, user_id, experiment_id
    )

    return IRExperimentRunResponse(
        experiment_id=experiment_id,
        corpus_dataset_id=request.corpus_dataset_id,
        queries_dataset_id=request.queries_dataset_id,
        status="running",
    )


@router.get("/{experiment_id}/status")
async def get_ir_experiment_status(
    experiment_id: str,
    user_id: str = Depends(get_user_id),
):
    """Return the current progress of an IR experiment."""
    exp_dir = Path(settings.data_path) / user_id / "ir" / experiment_id
    if not exp_dir.exists():
        raise HTTPException(status_code=404, detail="IR experiment not found")
    if (exp_dir / "results.json").exists():
        return {"stage": "done", "pct": 100, "status": "completed", "message": "Completed"}
    progress_path = exp_dir / "progress.json"
    if not progress_path.exists():
        raise HTTPException(status_code=404, detail="IR experiment not found")
    return json.loads(progress_path.read_text())


@router.get("/{experiment_id}/results", response_model=IRResultsResponse)
async def get_ir_results(
    experiment_id: str,
    user_id: str = Depends(get_user_id),
):
    """Get IR experiment results."""
    results_path = Path(settings.data_path) / user_id / "ir" / experiment_id / "results.json"
    if not results_path.exists():
        raise HTTPException(status_code=404, detail="IR experiment not found")

    data = json.loads(results_path.read_text())
    return IRResultsResponse(
        experiment_id=experiment_id,
        user_id=user_id,
        status="completed",
        metrics=IRMetrics(**data["metrics"]),
        n_docs=data["n_docs"],
        n_queries=data["n_queries"],
    )


@router.get("", response_model=IRExperimentListResponse)
async def list_ir_experiments(user_id: str = Depends(get_user_id)):
    """List all IR experiments for the current user."""
    ir_dir = Path(settings.data_path) / user_id / "ir"
    experiments = []

    if not ir_dir.exists():
        return IRExperimentListResponse(experiments=[])

    for exp_dir in ir_dir.iterdir():
        if not exp_dir.is_dir():
            continue

        meta_path = exp_dir / "meta.json"
        if not meta_path.exists():
            continue

        meta = json.loads(meta_path.read_text())
        mtime = exp_dir.stat().st_mtime
        created_at = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()

        experiments.append(
            IRExperimentListItem(
                experiment_id=exp_dir.name,
                corpus_dataset_id=meta.get("corpus_dataset_id", ""),
                queries_dataset_id=meta.get("queries_dataset_id", ""),
                status="completed",
                created_at=created_at,
            )
        )

    experiments.sort(key=lambda e: e.created_at, reverse=True)
    return IRExperimentListResponse(experiments=experiments)
