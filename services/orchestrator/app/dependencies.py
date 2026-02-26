"""Shared dependencies for FastAPI routes."""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.firebase import verify_id_token

security = HTTPBearer(auto_error=False)


def get_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Extract and validate Firebase ID token from Authorization header.

    Returns the Firebase UID as the user_id.
    In V1.2, this replaces the hardcoded 'default_user'.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        decoded_token = verify_id_token(credentials.credentials)
        return decoded_token["uid"]
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
        )
