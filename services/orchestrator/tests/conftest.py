"""Shared test fixtures — override Firebase auth with a mock user."""

import pytest
from app.main import app
from app.dependencies import get_user_id


def _mock_get_user_id() -> str:
    """Return a deterministic test user ID instead of validating a real JWT."""
    return "test_user"


@pytest.fixture(autouse=True, scope="session")
def override_auth():
    """Replace Firebase auth dependency with a mock for all tests.

    scope="session" is required because test_api.py has scope="module"
    fixtures that call the API — the override must be active before those
    module-scoped fixtures run.
    """
    app.dependency_overrides[get_user_id] = _mock_get_user_id
    yield
    app.dependency_overrides.clear()
