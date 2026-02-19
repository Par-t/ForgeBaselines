"""FastAPI integration tests for the orchestrator service."""

import io
import csv
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_iris_csv(n_per_class: int = 10) -> bytes:
    """Return bytes of a 30-row Iris-style CSV with an Id surrogate key."""
    rows = []
    idx = 1
    for species in ["Iris-setosa", "Iris-versicolor", "Iris-virginica"]:
        for i in range(n_per_class):
            rows.append([
                idx,
                round(5.0 + i * 0.1, 2),
                round(3.0 + i * 0.05, 2),
                round(1.5 + i * 0.2, 2),
                round(0.2 + i * 0.05, 2),
                species,
            ])
            idx += 1
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Id", "SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm", "Species"])
    writer.writerows(rows)
    return buf.getvalue().encode()


@pytest.fixture(scope="module")
def uploaded_dataset_id():
    """Upload a 30-row Iris CSV once for the whole module; return dataset_id."""
    csv_bytes = _make_iris_csv()
    response = client.post(
        "/datasets/upload",
        files={"file": ("iris.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert response.status_code == 200, response.text
    return response.json()["dataset_id"]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Dataset upload
# ---------------------------------------------------------------------------

def test_upload_valid_csv():
    csv_bytes = _make_iris_csv()
    response = client.post(
        "/datasets/upload",
        files={"file": ("iris.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "dataset_id" in data
    assert data["rows"] == 30
    assert data["cols"] == 6


def test_upload_non_csv_rejected():
    response = client.post(
        "/datasets/upload",
        files={"file": ("data.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Dataset profile
# ---------------------------------------------------------------------------

def test_profile_valid_dataset(uploaded_dataset_id):
    response = client.get(f"/datasets/{uploaded_dataset_id}/profile")
    assert response.status_code == 200
    profile = response.json()["profile"]
    for key in ("n_rows", "n_cols", "column_names", "column_types", "missing_values", "cardinality"):
        assert key in profile, f"Missing key: {key}"
    assert profile["n_rows"] == 30


def test_profile_bad_id_returns_404():
    response = client.get("/datasets/nonexistent-id-000/profile")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Suggest columns
# ---------------------------------------------------------------------------

def test_suggest_columns_detects_id(uploaded_dataset_id):
    response = client.get(
        f"/datasets/{uploaded_dataset_id}/suggest-columns",
        params={"target_column": "Species"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "column_config" in data
    assert "Id" in data["column_config"]["ignore_columns"]


def test_suggest_columns_bad_target(uploaded_dataset_id):
    response = client.get(
        f"/datasets/{uploaded_dataset_id}/suggest-columns",
        params={"target_column": "NonExistent"},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Runtime estimate
# ---------------------------------------------------------------------------

def test_estimate_runtime(uploaded_dataset_id):
    response = client.post(
        "/experiments/estimate",
        json={
            "dataset_id": uploaded_dataset_id,
            "model_names": ["logistic_regression", "random_forest"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "overall_estimate" in data
    assert "per_model" in data


# ---------------------------------------------------------------------------
# Experiment run
# ---------------------------------------------------------------------------

def _mock_httpx_client():
    """Return a mock httpx.AsyncClient that succeeds without real HTTP."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


def test_run_experiment_returns_experiment_id(uploaded_dataset_id):
    with patch("app.routers.experiments.httpx.AsyncClient", return_value=_mock_httpx_client()):
        response = client.post(
            "/experiments/run",
            json={
                "dataset_id": uploaded_dataset_id,
                "target_column": "Species",
                "model_names": ["logistic_regression"],
                "test_size": 0.2,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "experiment_id" in data
    assert data["column_config_used"] is None


def test_run_experiment_bad_target_column(uploaded_dataset_id):
    with patch("app.routers.experiments.httpx.AsyncClient", return_value=_mock_httpx_client()):
        response = client.post(
            "/experiments/run",
            json={
                "dataset_id": uploaded_dataset_id,
                "target_column": "DoesNotExist",
                "model_names": ["logistic_regression"],
                "test_size": 0.2,
            },
        )
    assert response.status_code == 400


def test_run_experiment_with_column_config(uploaded_dataset_id):
    with patch("app.routers.experiments.httpx.AsyncClient", return_value=_mock_httpx_client()):
        response = client.post(
            "/experiments/run",
            json={
                "dataset_id": uploaded_dataset_id,
                "target_column": "Species",
                "model_names": ["logistic_regression"],
                "test_size": 0.2,
                "column_config": {
                    "ignore_columns": ["Id"],
                    "feature_columns": [],
                    "source": "user",
                },
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["column_config_used"] is not None
    assert "Id" in data["column_config_used"]["ignore_columns"]
