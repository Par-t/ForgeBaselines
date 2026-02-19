"""FastAPI integration tests for the classification service."""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def iris_npy_paths(tmp_path):
    """Write small Iris-style .npy arrays and return their paths as strings."""
    rng = np.random.default_rng(42)
    n_train, n_test, n_features = 120, 30, 4

    X_train = rng.standard_normal((n_train, n_features)).astype(np.float64)
    X_test = rng.standard_normal((n_test, n_features)).astype(np.float64)
    # 3-class integer labels
    y_train = np.tile(np.arange(3), n_train // 3).astype(np.int64)
    y_test = np.tile(np.arange(3), n_test // 3).astype(np.int64)

    paths = {
        "X_train": str(tmp_path / "X_train.npy"),
        "X_test": str(tmp_path / "X_test.npy"),
        "y_train": str(tmp_path / "y_train.npy"),
        "y_test": str(tmp_path / "y_test.npy"),
    }
    np.save(paths["X_train"], X_train)
    np.save(paths["X_test"], X_test)
    np.save(paths["y_train"], y_train)
    np.save(paths["y_test"], y_test)
    return paths


def _mock_mlflow():
    """Return a context manager mock that stubs all mlflow calls used in runner.py."""
    mock_run_ctx = MagicMock()
    mock_run_ctx.__enter__ = MagicMock(return_value=MagicMock())
    mock_run_ctx.__exit__ = MagicMock(return_value=False)

    mock_mlflow = MagicMock()
    mock_mlflow.start_run.return_value = mock_run_ctx
    mock_mlflow.set_tracking_uri = MagicMock()
    mock_mlflow.set_experiment = MagicMock()
    mock_mlflow.log_param = MagicMock()
    mock_mlflow.log_metric = MagicMock()
    mock_mlflow.sklearn = MagicMock()
    mock_mlflow.sklearn.log_model = MagicMock()
    return mock_mlflow


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Train endpoint
# ---------------------------------------------------------------------------

def test_train_valid_request(iris_npy_paths):
    with patch("app.training.runner.mlflow", _mock_mlflow()):
        response = client.post(
            "/train",
            json={
                "X_train_path": iris_npy_paths["X_train"],
                "X_test_path": iris_npy_paths["X_test"],
                "y_train_path": iris_npy_paths["y_train"],
                "y_test_path": iris_npy_paths["y_test"],
                "model_names": ["logistic_regression"],
                "label_classes": ["Iris-setosa", "Iris-versicolor", "Iris-virginica"],
                "user_id": "test_user",
                "experiment_id": "test-exp-api",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert len(data["results"]) == 1
    result = data["results"][0]
    assert result["model_name"] == "logistic_regression"
    assert "accuracy" in result
    assert "f1" in result
    assert 0.0 <= result["accuracy"] <= 1.0


def test_train_multiple_models(iris_npy_paths):
    with patch("app.training.runner.mlflow", _mock_mlflow()):
        response = client.post(
            "/train",
            json={
                "X_train_path": iris_npy_paths["X_train"],
                "X_test_path": iris_npy_paths["X_test"],
                "y_train_path": iris_npy_paths["y_train"],
                "y_test_path": iris_npy_paths["y_test"],
                "model_names": ["logistic_regression", "random_forest"],
                "label_classes": ["Iris-setosa", "Iris-versicolor", "Iris-virginica"],
                "user_id": "test_user",
                "experiment_id": "test-exp-multi",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2


def test_train_missing_required_field():
    # Omit X_train_path — should get 422 Unprocessable Entity
    response = client.post(
        "/train",
        json={
            "X_test_path": "/some/path",
            "y_train_path": "/some/path",
            "y_test_path": "/some/path",
            "model_names": ["logistic_regression"],
            "label_classes": ["a", "b"],
            "user_id": "u",
            "experiment_id": "e",
        },
    )
    assert response.status_code == 422


def test_train_nonexistent_file_paths():
    with patch("app.training.runner.mlflow", _mock_mlflow()):
        response = client.post(
            "/train",
            json={
                "X_train_path": "/nonexistent/X_train.npy",
                "X_test_path": "/nonexistent/X_test.npy",
                "y_train_path": "/nonexistent/y_train.npy",
                "y_test_path": "/nonexistent/y_test.npy",
                "model_names": ["logistic_regression"],
                "label_classes": ["a", "b"],
                "user_id": "u",
                "experiment_id": "missing-files",
            },
        )
    assert response.status_code == 404
