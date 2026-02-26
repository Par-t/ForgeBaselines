"""Firebase Admin SDK initialization."""

import json
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from app.config import settings


def init_firebase() -> None:
    """Initialize Firebase Admin SDK from JSON env var.

    Skips initialization if the JSON is empty (allows tests/CI to run
    without real Firebase credentials).
    """
    if firebase_admin._apps:
        return  # Already initialized

    service_account_info = json.loads(settings.firebase_service_account_json)
    if not service_account_info:
        return  # No credentials — skip (tests/CI)

    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)


def verify_id_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return the decoded claims."""
    return firebase_auth.verify_id_token(id_token)
