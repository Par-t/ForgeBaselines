"""Experiment execution and results endpoints."""

import csv
import io
import json
import logging
import os
import time
import uuid
import numpy as np
import pandas as pd
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies import get_user_id
from app.schemas.experiment import (
    RuntimeEstimateRequest, RuntimeEstimateResponse,
    ExperimentListItem, ExperimentListResponse,
    UnifiedExperimentListItem, UnifiedExperimentListResponse,
)
from app.schemas.classification import ExperimentRunRequest, ExperimentRunResponse
from app.schemas.ir import IRExperimentRunRequest, IRExperimentRunResponse
from app.schemas.dataset import DeleteResponse
from app.config import settings
from app.services.storage import storage
from app.services.profiler import profile_dataset
from app.services.runtime_estimator import estimate_runtime
from app.preprocessing.classification_pipeline import preprocess_dataset
from app.preprocessing.ir_pipeline import preprocess_ir_datasets

router = APIRouter(prefix="/experiments", tags=["experiments"])


def _write_progress(exp_dir: Path, stage: str, pct: int, status: str, message: str) -> None:
    """Atomically write progress.json so readers never see a partial file."""
    data = json.dumps({"stage": stage, "pct": pct, "status": status, "message": message})
    tmp = exp_dir / "progress.json.tmp"
    tmp.write_text(data)
    os.replace(tmp, exp_dir / "progress.json")


async def _run_classification_background(
    df: pd.DataFrame,
    request,
    exp_dir: Path,
    experiment_id: str,
    user_id: str,
) -> None:
    """Background task: preprocess data, call classification service, write progress."""
    try:
        _write_progress(exp_dir, "preprocessing", 10, "running", "Preprocessing data...")
        try:
            X_train, X_test, y_train, y_test, preprocessor, label_classes = preprocess_dataset(
                df, request.target_column, request.test_size,
                column_config=request.column_config,
                preprocessing_config=request.preprocessing_config,
            )
        except Exception as e:
            _write_progress(exp_dir, "error", 0, "failed", f"Preprocessing failed: {str(e)}")
            return

        np.save(exp_dir / "X_train.npy", X_train)
        np.save(exp_dir / "X_test.npy", X_test)
        np.save(exp_dir / "y_train.npy", y_train)
        np.save(exp_dir / "y_test.npy", y_test)

        n_models = len(request.model_names)
        _write_progress(exp_dir, "training", 20, "running", f"Training {n_models} model(s)...")

        classification_url = os.getenv("CLASSIFICATION_SERVICE_URL", "http://classification:8001")
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{classification_url}/train",
                json={
                    "X_train_path": str(exp_dir / "X_train.npy"),
                    "X_test_path": str(exp_dir / "X_test.npy"),
                    "y_train_path": str(exp_dir / "y_train.npy"),
                    "y_test_path": str(exp_dir / "y_test.npy"),
                    "model_names": request.model_names,
                    "label_classes": label_classes,
                    "user_id": user_id,
                    "experiment_id": experiment_id,
                    "use_class_weight": (
                        request.preprocessing_config is not None
                        and request.preprocessing_config.class_balancing == "class_weight"
                    ),
                }
            )
            response.raise_for_status()

        _write_progress(exp_dir, "done", 100, "completed", "Completed")

    except Exception as e:
        _write_progress(exp_dir, "error", 0, "failed", f"Training failed: {str(e)}")


@router.post("/estimate", response_model=RuntimeEstimateResponse)
async def estimate_experiment_runtime(
    request: RuntimeEstimateRequest,
    user_id: str = Depends(get_user_id)
):
    """Estimate runtime for an experiment based on dataset profile."""
    try:
        file_path = storage.get_dataset_path(request.dataset_id, user_id)
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading dataset: {str(e)}")

    profile = profile_dataset(df)
    estimate = estimate_runtime(profile, request.model_names)

    return RuntimeEstimateResponse(
        dataset_id=request.dataset_id,
        overall_estimate=estimate["overall_estimate"],
        per_model=estimate["per_model"],
        complexity_factors=estimate["complexity_factors"]
    )


@router.post("/run", response_model=ExperimentRunResponse)
async def run_experiment(
    request: ExperimentRunRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id)
):
    """Start a classification experiment. Returns immediately; poll /status for progress."""
    # Create the experiment directory and write initial progress immediately
    # so the frontend can redirect before the (potentially slow) CSV read.
    experiment_id = request.experiment_id or str(uuid.uuid4())
    exp_dir = Path(f"{settings.data_path}/{user_id}/{request.dataset_id}/preprocessed/{experiment_id}")
    exp_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "task_type": "classification",
        "dataset_id": request.dataset_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (exp_dir / "meta.json").write_text(json.dumps(meta))
    _write_progress(exp_dir, "queued", 0, "running", "Starting experiment...")

    try:
        file_path = storage.get_dataset_path(request.dataset_id, user_id)
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        _write_progress(exp_dir, "error", 0, "failed", "Dataset not found")
        raise HTTPException(status_code=404, detail="Dataset not found")
    except Exception as e:
        _write_progress(exp_dir, "error", 0, "failed", f"Error reading dataset: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error reading dataset: {str(e)}")

    if request.target_column not in df.columns:
        _write_progress(exp_dir, "error", 0, "failed", f"Target column '{request.target_column}' not found")
        raise HTTPException(
            status_code=400,
            detail=f"Target column '{request.target_column}' not found in dataset. Available columns: {df.columns.tolist()}"
        )

    if request.column_config is not None:
        all_cols = set(df.columns)
        bad_ignore = set(request.column_config.ignore_columns) - all_cols - {request.target_column}
        bad_features = set(request.column_config.feature_columns) - all_cols - {request.target_column}
        if bad_ignore or bad_features:
            _write_progress(exp_dir, "error", 0, "failed", "Invalid column config")
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "column_config references columns not found in dataset",
                    "unknown_ignore_columns": sorted(bad_ignore),
                    "unknown_feature_columns": sorted(bad_features),
                    "available_columns": df.columns.tolist()
                }
            )

    profile = profile_dataset(df)
    runtime_estimate = estimate_runtime(profile, request.model_names)

    background_tasks.add_task(
        _run_classification_background, df, request, exp_dir, experiment_id, user_id
    )

    return ExperimentRunResponse(
        experiment_id=experiment_id,
        dataset_id=request.dataset_id,
        status="running",
        estimated_runtime=runtime_estimate["overall_estimate"],
        models=request.model_names,
        column_config_used=request.column_config,
        preprocessing_config_used=request.preprocessing_config,
    )


@router.get("/{experiment_id}/status")
async def get_experiment_status(experiment_id: str, user_id: str = Depends(get_user_id)):
    """Return the current progress of an experiment (classification or IR)."""
    location = _find_experiment_location(experiment_id, user_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    task_type, exp_dir = location
    # results.json written = experiment completed; guard against stale progress.json
    if task_type == "ir" and (exp_dir / "results.json").exists():
        return {"stage": "done", "pct": 100, "status": "completed", "message": "Completed"}
    progress_path = exp_dir / "progress.json"
    if not progress_path.exists():
        # Pre-async experiments have no progress.json — treat as completed
        return {"stage": "done", "pct": 100, "status": "completed", "message": "Completed"}
    return json.loads(progress_path.read_text())


@router.get("/{experiment_id}/results")
async def get_experiment_results(experiment_id: str, user_id: str = Depends(get_user_id)):
    """Get experiment results (classification or IR)."""
    location = _find_experiment_location(experiment_id, user_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    task_type, exp_dir = location

    if task_type == "ir":
        results_path = exp_dir / "results.json"
        if not results_path.exists():
            raise HTTPException(status_code=404, detail="IR results not ready yet")
        data = json.loads(results_path.read_text())
        return {
            "experiment_id": experiment_id,
            "task_type": "ir",
            "metrics": data["metrics"],
            "n_docs": data["n_docs"],
            "n_queries": data["n_queries"],
        }

    # Classification — fetch from MLflow
    mlflow_url = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    leaderboard, label_mapping = await _fetch_mlflow_results(mlflow_url, experiment_id)
    return {
        "experiment_id": experiment_id,
        "task_type": "classification",
        "label_mapping": label_mapping,
        "leaderboard": leaderboard,
    }


@router.get("/{experiment_id}/results/download")
async def download_experiment_results(experiment_id: str, user_id: str = Depends(get_user_id)):
    """Download experiment leaderboard as a CSV file."""
    dataset_id = _find_dataset_id_for_experiment(experiment_id, user_id)
    if dataset_id is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    mlflow_url = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    leaderboard, _ = await _fetch_mlflow_results(mlflow_url, experiment_id)

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["model_name", "accuracy", "precision", "recall", "f1", "training_time"],
    )
    writer.writeheader()
    for row in leaderboard:
        writer.writerow(row)

    buf.seek(0)
    filename = f"results_{experiment_id[:8]}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{experiment_id}", response_model=DeleteResponse)
async def delete_experiment(experiment_id: str, user_id: str = Depends(get_user_id)):
    """Delete an experiment (preprocessed data + MLflow runs). Leaves dataset intact."""
    dataset_id = _find_dataset_id_for_experiment(experiment_id, user_id)
    if dataset_id is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    mlflow_url = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    async with httpx.AsyncClient() as client:
        from app.routers.datasets import _delete_mlflow_experiment
        await _delete_mlflow_experiment(client, mlflow_url, experiment_id)

    storage.delete_experiment(user_id, dataset_id, experiment_id)

    return DeleteResponse(message=f"Experiment {experiment_id} deleted")


@router.get("/all", response_model=UnifiedExperimentListResponse)
async def list_all_experiments(user_id: str = Depends(get_user_id)):
    """List all experiments (classification + IR) for the current user, sorted newest-first."""
    user_dir = Path(settings.data_path) / user_id
    experiments = []

    if not user_dir.exists():
        return UnifiedExperimentListResponse(experiments=[])

    # --- classification experiments ---
    for dataset_dir in user_dir.iterdir():
        if dataset_dir.name == "ir" or not dataset_dir.is_dir():
            continue
        preprocessed_dir = dataset_dir / "preprocessed"
        if not preprocessed_dir.exists():
            continue
        dataset_id = dataset_dir.name
        for exp_dir in preprocessed_dir.iterdir():
            if not exp_dir.is_dir():
                continue

            meta_path = exp_dir / "meta.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                created_at = meta.get(
                    "created_at",
                    datetime.fromtimestamp(exp_dir.stat().st_mtime, tz=timezone.utc).isoformat(),
                )
            else:
                # Legacy experiment without meta.json — infer from dir structure
                created_at = datetime.fromtimestamp(exp_dir.stat().st_mtime, tz=timezone.utc).isoformat()

            progress_path = exp_dir / "progress.json"
            status = json.loads(progress_path.read_text()).get("status", "completed") if progress_path.exists() else "completed"

            experiments.append(UnifiedExperimentListItem(
                experiment_id=exp_dir.name,
                task_type="classification",
                status=status,
                created_at=created_at,
                dataset_id=dataset_id,
            ))

    # --- IR experiments ---
    ir_dir = user_dir / "ir"
    if ir_dir.exists():
        for exp_dir in ir_dir.iterdir():
            if not exp_dir.is_dir():
                continue

            meta_path = exp_dir / "meta.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                created_at = meta.get(
                    "created_at",
                    datetime.fromtimestamp(exp_dir.stat().st_mtime, tz=timezone.utc).isoformat(),
                )
                corpus_dataset_id = meta.get("corpus_dataset_id")
                queries_dataset_id = meta.get("queries_dataset_id")
            else:
                created_at = datetime.fromtimestamp(exp_dir.stat().st_mtime, tz=timezone.utc).isoformat()
                corpus_dataset_id = None
                queries_dataset_id = None

            progress_path = exp_dir / "progress.json"
            status = json.loads(progress_path.read_text()).get("status", "completed") if progress_path.exists() else "completed"

            experiments.append(UnifiedExperimentListItem(
                experiment_id=exp_dir.name,
                task_type="ir",
                status=status,
                created_at=created_at,
                corpus_dataset_id=corpus_dataset_id,
                queries_dataset_id=queries_dataset_id,
            ))

    experiments.sort(key=lambda e: e.created_at, reverse=True)
    return UnifiedExperimentListResponse(experiments=experiments)


@router.get("", response_model=ExperimentListResponse)
async def list_experiments(user_id: str = Depends(get_user_id)):
    """List all experiments for the current user."""
    user_dir = Path(settings.data_path) / user_id
    experiments = []

    if not user_dir.exists():
        return ExperimentListResponse(experiments=[])

    for dataset_dir in user_dir.iterdir():
        if not dataset_dir.is_dir():
            continue
        preprocessed_dir = dataset_dir / "preprocessed"
        if not preprocessed_dir.exists():
            continue

        dataset_id = dataset_dir.name
        for exp_dir in preprocessed_dir.iterdir():
            if not exp_dir.is_dir():
                continue

            mtime = exp_dir.stat().st_mtime
            created_at = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()

            experiments.append(
                ExperimentListItem(
                    experiment_id=exp_dir.name,
                    dataset_id=dataset_id,
                    status="completed",
                    run_count=1,
                    created_at=created_at,
                )
            )

    experiments.sort(key=lambda e: e.created_at, reverse=True)
    return ExperimentListResponse(experiments=experiments)


# ------------------------------------------------------------------ helpers

def _find_experiment_location(experiment_id: str, user_id: str) -> Optional[Tuple[str, Path]]:
    """Return ("classification", path) or ("ir", path) or None if not found."""
    user_dir = Path(settings.data_path) / user_id
    if not user_dir.exists():
        return None
    # IR is a flat O(1) check — try it first
    ir_path = user_dir / "ir" / experiment_id
    if ir_path.exists():
        return ("ir", ir_path)
    # Walk classification dataset dirs
    for dataset_dir in user_dir.iterdir():
        if dataset_dir.name == "ir" or not dataset_dir.is_dir():
            continue
        exp_path = dataset_dir / "preprocessed" / experiment_id
        if exp_path.exists():
            return ("classification", exp_path)
    return None


def _find_dataset_id_for_experiment(experiment_id: str, user_id: str):
    """Return the dataset_id that owns this experiment, or None if not found."""
    user_data_dir = Path(settings.data_path) / user_id
    if not user_data_dir.exists():
        return None
    for dataset_dir in user_data_dir.iterdir():
        exp_path = dataset_dir / "preprocessed" / experiment_id
        if exp_path.exists():
            return dataset_dir.name
    return None


async def _fetch_mlflow_results(mlflow_url: str, experiment_id: str):
    """Query MLflow for leaderboard rows. Returns (leaderboard, label_mapping)."""
    async with httpx.AsyncClient() as client:
        try:
            exp_resp = await client.get(
                f"{mlflow_url}/api/2.0/mlflow/experiments/get-by-name",
                params={"experiment_name": experiment_id},
            )
            exp_resp.raise_for_status()
            mlflow_exp_id = exp_resp.json()["experiment"]["experiment_id"]

            runs_resp = await client.post(
                f"{mlflow_url}/api/2.0/mlflow/runs/search",
                json={"experiment_ids": [mlflow_exp_id], "max_results": 100},
            )
            runs_resp.raise_for_status()
            data = runs_resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Experiment not found in MLflow")
            raise HTTPException(status_code=500, detail=f"MLflow query error: {str(e)}")
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"MLflow query error: {str(e)}")

    if "runs" not in data or not data["runs"]:
        raise HTTPException(status_code=404, detail="No results found for this experiment")

    leaderboard = []
    label_classes = None

    for run in data["runs"]:
        metrics_dict = {m["key"]: m["value"] for m in run["data"]["metrics"]}
        params_dict = {p["key"]: p["value"] for p in run["data"]["params"]}

        if label_classes is None and "label_classes" in params_dict:
            label_classes = params_dict["label_classes"].split(",")

        leaderboard.append({
            "model_name": run["info"]["run_name"],
            "accuracy": metrics_dict.get("accuracy", 0.0),
            "precision": metrics_dict.get("precision", 0.0),
            "recall": metrics_dict.get("recall", 0.0),
            "f1": metrics_dict.get("f1", 0.0),
            "training_time": metrics_dict.get("training_time", 0.0),
        })

    leaderboard.sort(key=lambda x: x["f1"], reverse=True)
    label_mapping = (
        {str(i): cls for i, cls in enumerate(label_classes)}
        if label_classes else {}
    )
    return leaderboard, label_mapping


# ------------------------------------------------------------------ IR run

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


@router.post("/ir/run", response_model=IRExperimentRunResponse)
async def run_ir_experiment(
    request: IRExperimentRunRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    """Start a BM25 IR experiment. Returns immediately; poll /status for progress."""
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
