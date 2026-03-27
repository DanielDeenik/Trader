"""FastAPI dependency injection."""

from typing import Optional, Dict
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from social_arb.config import config
from social_arb.db.schema import init_db
from social_arb.auth.jwt_handler import verify_token


def get_db_path() -> str:
    """Return configured database path. `config` is the module-level singleton instance from social_arb.config."""
    return config.db_path


def get_config():
    """Return app config."""
    return config


def ensure_db():
    """Initialize DB schema (idempotent)."""
    init_db(config.db_path)


# Auth dependency
security = HTTPBearer(auto_error=False)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict]:
    """Optional auth dependency. Returns user dict if authenticated, None if no token.

    Allows gradual migration: existing routes work without auth,
    protected routes check if user is not None.
    """
    if not credentials:
        return None

    token = credentials.credentials
    user = verify_token(token)
    return user
