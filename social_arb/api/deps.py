"""FastAPI dependency injection."""

from social_arb.config import config
from social_arb.db.schema import init_db


def get_db_path() -> str:
    """Return configured database path. `config` is the module-level singleton instance from social_arb.config."""
    return config.db_path


def get_config():
    """Return app config."""
    return config


def ensure_db():
    """Initialize DB schema (idempotent)."""
    init_db(config.db_path)
