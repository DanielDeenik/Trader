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
    """Initialize DB schema (idempotent) and seed default user."""
    init_db(config.db_path)
    _seed_default_user(config.db_path)


def _seed_default_user(db_path: str):
    """Create default admin user if no users exist."""
    from social_arb.db.schema import get_connection
    from social_arb.auth.models import hash_password

    with get_connection(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
        if row and dict(row)["cnt"] == 0:
            pw_hash = hash_password("socialarb")
            conn.execute(
                "INSERT INTO users (email, password_hash, display_name) VALUES (?, ?, ?)",
                ("deenikdaniel@gmail.com", pw_hash, "Dan"),
            )
            conn.commit()


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
