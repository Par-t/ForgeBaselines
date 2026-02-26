"""Auth behavior tests — verifies real 401 responses when auth override is removed.

These tests temporarily remove the session-scoped auth override to exercise
the actual JWT validation path. Discard after V1.2.1 is confirmed working.
"""

import pytest
from starlette.testclient import TestClient
from app.main import app
from app.dependencies import get_user_id


@pytest.fixture()
def unauthed_client():
    """TestClient with NO auth override — endpoints require real tokens."""
    # Temporarily remove the session override
    original = app.dependency_overrides.pop(get_user_id, None)
    client = TestClient(app)
    yield client
    # Restore
    if original is not None:
        app.dependency_overrides[get_user_id] = original


def test_health_no_auth_required(unauthed_client):
    """GET /health should work without any token."""
    resp = unauthed_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_requires_auth(unauthed_client):
    """POST /datasets/upload without token → 401."""
    resp = unauthed_client.post(
        "/datasets/upload",
        files={"file": ("test.csv", b"a,b\n1,2", "text/csv")},
    )
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]


def test_profile_requires_auth(unauthed_client):
    """GET /datasets/{id}/profile without token → 401."""
    resp = unauthed_client.get("/datasets/fake-id/profile")
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]


def test_experiments_require_auth(unauthed_client):
    """POST /experiments/run without token → 401."""
    resp = unauthed_client.post(
        "/experiments/run",
        json={
            "dataset_id": "x",
            "target_column": "y",
            "model_names": ["logistic_regression"],
            "test_size": 0.2,
        },
    )
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]


def test_invalid_token_rejected(unauthed_client):
    """A garbage Bearer token → 401 invalid/expired."""
    resp = unauthed_client.get(
        "/datasets/fake-id/profile",
        headers={"Authorization": "Bearer this-is-not-a-real-firebase-token"},
    )
    assert resp.status_code == 401
    assert "Invalid or expired" in resp.json()["detail"]
