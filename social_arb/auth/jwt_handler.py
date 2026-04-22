"""JWT token creation and verification."""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional

try:
    import jwt
except ImportError:
    jwt = None

# Secret key from env or default for dev
JWT_SECRET = os.getenv("SA_JWT_SECRET", "social-arb-dev-secret-key-not-for-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


def create_token(user_id: int, email: str) -> str:
    """Create a JWT token for a user.

    Args:
        user_id: User ID
        email: User email

    Returns:
        JWT token string
    """
    if not jwt:
        raise RuntimeError("PyJWT not installed. Install with: pip install PyJWT")

    payload = {
        "user_id": user_id,
        "email": email,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> Optional[Dict]:
    """Verify a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token dict with user_id and email, or None if invalid
    """
    if not jwt:
        raise RuntimeError("PyJWT not installed. Install with: pip install PyJWT")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
        }
    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
        return None
