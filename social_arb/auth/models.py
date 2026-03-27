"""User and watchlist models for authentication."""

import hashlib
import secrets
from typing import Optional, Dict, Any


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2.

    Args:
        password: Plain text password

    Returns:
        Hashed password string in format: salt$hash
    """
    salt = secrets.token_hex(32)
    # Use PBKDF2 with 100k iterations
    hash_obj = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=100000
    )
    hash_hex = hash_obj.hex()
    return f"{salt}${hash_hex}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a hash.

    Args:
        password: Plain text password
        hashed: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    try:
        salt, hash_hex = hashed.split('$')
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations=100000
        )
        return hash_obj.hex() == hash_hex
    except (ValueError, AttributeError):
        return False


class User:
    """User model."""

    def __init__(
        self,
        id: int,
        email: str,
        display_name: str,
        password_hash: str,
        settings_json: Optional[str] = None,
        created_at: Optional[str] = None,
    ):
        self.id = id
        self.email = email
        self.display_name = display_name
        self.password_hash = password_hash
        self.settings_json = settings_json or "{}"
        self.created_at = created_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_row(row: Dict) -> "User":
        """Create User from database row."""
        return User(
            id=row.get("id"),
            email=row.get("email"),
            display_name=row.get("display_name"),
            password_hash=row.get("password_hash"),
            settings_json=row.get("settings_json"),
            created_at=row.get("created_at"),
        )


class Watchlist:
    """Watchlist entry model."""

    def __init__(self, id: int, user_id: int, symbol: str, added_at: Optional[str] = None):
        self.id = id
        self.user_id = user_id
        self.symbol = symbol
        self.added_at = added_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "added_at": self.added_at,
        }

    @staticmethod
    def from_row(row: Dict) -> "Watchlist":
        """Create Watchlist from database row."""
        return Watchlist(
            id=row.get("id"),
            user_id=row.get("user_id"),
            symbol=row.get("symbol"),
            added_at=row.get("added_at"),
        )
