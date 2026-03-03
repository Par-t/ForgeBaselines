"""IR experiment endpoints: run BM25 baselines, fetch results."""

import json
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

_REQUIRED_CORPUS_COLS = {"doc_id"}
_REQUIRED_QUERIES_COLS = {"query_id", "query", "doc_id", "relevance"}


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

    # Validate required columns
    missing_corpus = _REQUIRED_CORPUS_COLS - set(corpus_df.columns)
    if request.text_column not in corpus_df.columns:
        missing_corpus.add(request.text_column)
    if missing_corpus:
        raise HTTPException(
            status_code=400,
            detail=f"Corpus missing required columns: {sorted(missing_corpus)}"
        )

    missing_queries = _REQUIRED_QUERIES_COLS - set(queries_df.columns)
    if missing_queries:
        raise HTTPException(
            status_code=400,
            detail=f"Queries CSV missing required columns: {sorted(missing_queries)}"
        )

    # Preprocess text
    corpus_df, queries_df = preprocess_ir_datasets(
        corpus_df, queries_df, request.text_column, request.preprocessing_config
    )

    # Save preprocessed files
    experiment_id = str(uuid.uuid4())
    exp_dir = Path(settings.data_path) / user_id / "ir" / experiment_id
    exp_dir.mkdir(parents=True, exist_ok=True)

    corpus_df.to_csv(exp_dir / "corpus.csv", index=False)
    queries_df.to_csv(exp_dir / "queries.csv", index=False)

    # Save metadata for list endpoint
    meta = {
        "corpus_dataset_id": request.corpus_dataset_id,
        "queries_dataset_id": request.queries_dataset_id,
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
                    "text_column": request.text_column,
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

    return IRExperimentRunResponse(
        experiment_id=experiment_id,
        corpus_dataset_id=request.corpus_dataset_id,
        queries_dataset_id=request.queries_dataset_id,
        status="completed",
    )


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
