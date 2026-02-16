"""Shared dependencies for FastAPI routes."""


def get_user_id() -> str:
    """
    Get the current user ID.

    In V1, this returns a hardcoded default user.
    In V1.2, this will be replaced with Firebase Auth middleware
    that extracts the user_id from the JWT token.
    """
    return "default_user"
