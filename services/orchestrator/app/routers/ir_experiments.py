"""IR experiment endpoints: run BM25 baselines, fetch results."""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

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


@router.post("/run", response_model=IRExperimentRunResponse)
async def run_ir_experiment(
    request: IRExperimentRunRequest,
    user_id: str = Depends(get_user_id),
):
    """Run a BM25 IR experiment end-to-end."""
    # Load corpus
    try:
        corpus_path = storage.get_dataset_path(request.corpus_dataset_id, user_id)
        corpus_df = pd.read_csv(corpus_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Corpus dataset not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading corpus: {str(e)}")

    # Load queries
    try:
        queries_path = storage.get_dataset_path(request.queries_dataset_id, user_id)
        queries_df = pd.read_csv(queries_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Queries dataset not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading queries: {str(e)}")

    # Validate user-specified column names exist, then rename to standard schema
    corpus_user_cols = {request.corpus_doc_id_col, request.text_column}
    missing_corpus = corpus_user_cols - set(corpus_df.columns)
    if missing_corpus:
        raise HTTPException(status_code=400, detail=f"Corpus missing columns: {sorted(missing_corpus)}")

    corpus_df = corpus_df.rename(columns={
        request.corpus_doc_id_col: "doc_id",
        request.text_column: "text",
    })

    # Required query columns; query_id and relevance are optional
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

    # Synthesize query_id from query text if not provided (groups identical queries correctly)
    if "query_id" not in queries_df.columns:
        queries_df["query_id"] = queries_df["query"]

    # Create experiment directory early so progress.json is always reachable
    experiment_id = str(uuid.uuid4())
    exp_dir = Path(settings.data_path) / user_id / "ir" / experiment_id
    exp_dir.mkdir(parents=True, exist_ok=True)

    _write_progress(exp_dir, "queued", 0, "running", "Starting experiment...")

    # Preprocess text (columns are now normalized to standard names)
    corpus_df, queries_df = preprocess_ir_datasets(
        corpus_df, queries_df, "text", request.preprocessing_config
    )

    _write_progress(exp_dir, "preprocessing", 10, "running", "Preprocessing text...")

    # Save preprocessed files
    corpus_df.to_csv(exp_dir / "corpus.csv", index=False)
    queries_df.to_csv(exp_dir / "queries.csv", index=False)

    # Save metadata for list endpoint
    meta = {
        "task_type": "ir",
        "corpus_dataset_id": request.corpus_dataset_id,
        "queries_dataset_id": request.queries_dataset_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (exp_dir / "meta.json").write_text(json.dumps(meta))

    # Call IR service
    ir_url = settings.ir_service_url

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(
                f"{ir_url}/retrieve",
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
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"IR service error: {str(e)}")

    data = response.json()
    metrics_data = data["metrics"]

    # Persist results
    results = {
        "metrics": metrics_data,
        "n_docs": data["n_docs"],
        "n_queries": data["n_queries"],
    }
    (exp_dir / "results.json").write_text(json.dumps(results))

    _write_progress(exp_dir, "done", 100, "completed", "Completed")

    return IRExperimentRunResponse(
        experiment_id=experiment_id,
        corpus_dataset_id=request.corpus_dataset_id,
        queries_dataset_id=request.queries_dataset_id,
        status="completed",
    )


@router.get("/{experiment_id}/status")
async def get_ir_experiment_status(
    experiment_id: str,
    user_id: str = Depends(get_user_id),
):
    """Return the current progress of an IR experiment."""
    progress_path = Path(settings.data_path) / user_id / "ir" / experiment_id / "progress.json"
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
