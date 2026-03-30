"""Authentication endpoints — register, login, user settings, watchlist."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Optional
import json
import secrets

from social_arb.api.deps import get_db_path, get_current_user
from social_arb.auth.jwt_handler import create_token, verify_token
from social_arb.auth.models import hash_password, verify_password, User, Watchlist
from social_arb.db.schema import get_connection

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: Dict


class GoogleAuthRequest(BaseModel):
    credential: str  # Google ID token


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    created_at: Optional[str] = None


class SettingsUpdate(BaseModel):
    display_name: Optional[str] = None
    settings_json: Optional[Dict] = None


class WatchlistItem(BaseModel):
    symbol: str


class WatchlistResponse(BaseModel):
    symbol: str
    added_at: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────────────────

@router.post("/auth/register", response_model=LoginResponse)
def register(req: RegisterRequest):
    """Register a new user."""
    db_path = get_db_path()

    # Validate input
    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="Invalid email")
    if not req.password or len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not req.display_name:
        raise HTTPException(status_code=400, detail="Display name required")

    # Check if user exists
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", (req.email,)
        ).fetchone()
        if row:
            raise HTTPException(status_code=409, detail="Email already registered")

    # Hash password
    password_hash = hash_password(req.password)

    # Create user
    with get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO users (email, password_hash, display_name, settings_json)
               VALUES (?, ?, ?, ?)""",
            (req.email, password_hash, req.display_name, "{}"),
        )
        conn.commit()
        user_id = c.lastrowid

    # Create token
    token = create_token(user_id, req.email)
    return LoginResponse(
        token=token,
        user={"id": user_id, "email": req.email, "display_name": req.display_name},
    )


@router.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """Login and get JWT token."""
    db_path = get_db_path()

    # Validate input
    if not req.email or not req.password:
        raise HTTPException(status_code=400, detail="Email and password required")

    # Find user
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, password_hash, display_name FROM users WHERE email = ?",
            (req.email,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = dict(row).get("id")
    password_hash = dict(row).get("password_hash")
    display_name = dict(row).get("display_name")

    # Verify password
    if not verify_password(req.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create token
    token = create_token(user_id, req.email)
    return LoginResponse(
        token=token,
        user={"id": user_id, "email": req.email, "display_name": display_name},
    )


@router.post("/auth/google", response_model=LoginResponse)
def google_login(req: GoogleAuthRequest):
    """Login with Google Sign-In credential."""
    import httpx

    # Verify the Google ID token
    try:
        resp = httpx.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={req.credential}",
            timeout=10,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Google token")

        payload = resp.json()
        email = payload.get("email")
        name = payload.get("name", email.split("@")[0] if email else "User")

        if not email:
            raise HTTPException(status_code=401, detail="No email in Google token")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Failed to verify Google token")

    db_path = get_db_path()

    # Find or create user
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, display_name FROM users WHERE email = ?", (email,)
        ).fetchone()

    if row:
        user_id = row["id"]
        display_name = row["display_name"]
    else:
        # Auto-register Google users
        password_hash = hash_password(secrets.token_hex(32))  # random password
        with get_connection(db_path) as conn:
            c = conn.cursor()
            c.execute(
                """INSERT INTO users (email, password_hash, display_name, settings_json)
                   VALUES (?, ?, ?, ?)""",
                (email, password_hash, name, "{}"),
            )
            conn.commit()
            user_id = c.lastrowid
        display_name = name

    token = create_token(user_id, email)
    return LoginResponse(
        token=token,
        user={"id": user_id, "email": email, "display_name": display_name},
    )


@router.get("/auth/me", response_model=UserResponse)
def get_current_user_info(user: Dict = Depends(get_current_user)):
    """Get current authenticated user."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_path = get_db_path()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, email, display_name, created_at FROM users WHERE id = ?",
            (user["user_id"],),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(**dict(row))


@router.put("/auth/settings")
def update_settings(
    updates: SettingsUpdate,
    user: Dict = Depends(get_current_user)
):
    """Update user settings."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_path = get_db_path()

    # Get current user
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT settings_json FROM users WHERE id = ?",
            (user["user_id"],),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    # Merge settings
    current_settings = json.loads(dict(row).get("settings_json") or "{}")
    if updates.settings_json:
        current_settings.update(updates.settings_json)

    # Update user
    with get_connection(db_path) as conn:
        c = conn.cursor()
        query_parts = []
        params = []

        if updates.display_name:
            query_parts.append("display_name = ?")
            params.append(updates.display_name)

        query_parts.append("settings_json = ?")
        params.append(json.dumps(current_settings))

        params.append(user["user_id"])

        query = f"UPDATE users SET {', '.join(query_parts)} WHERE id = ?"
        c.execute(query, params)
        conn.commit()

    return {"success": True}


@router.get("/auth/watchlist", response_model=List[WatchlistResponse])
def get_watchlist(user: Dict = Depends(get_current_user)):
    """Get user's watchlist."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_path = get_db_path()
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT symbol, added_at FROM watchlists WHERE user_id = ? ORDER BY added_at DESC",
            (user["user_id"],),
        ).fetchall()

    return [WatchlistResponse(symbol=dict(row).get("symbol"), added_at=dict(row).get("added_at")) for row in rows]


@router.post("/auth/watchlist")
def add_to_watchlist(
    item: WatchlistItem,
    user: Dict = Depends(get_current_user)
):
    """Add symbol to watchlist."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not item.symbol:
        raise HTTPException(status_code=400, detail="Symbol required")

    db_path = get_db_path()

    # Check if already in watchlist
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM watchlists WHERE user_id = ? AND symbol = ?",
            (user["user_id"], item.symbol),
        ).fetchone()

    if row:
        raise HTTPException(status_code=409, detail="Already in watchlist")

    # Add to watchlist
    with get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO watchlists (user_id, symbol) VALUES (?, ?)",
            (user["user_id"], item.symbol),
        )
        conn.commit()

    return {"success": True, "symbol": item.symbol}


@router.delete("/auth/watchlist/{symbol}")
def remove_from_watchlist(
    symbol: str,
    user: Dict = Depends(get_current_user)
):
    """Remove symbol from watchlist."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_path = get_db_path()

    with get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute(
            "DELETE FROM watchlists WHERE user_id = ? AND symbol = ?",
            (user["user_id"], symbol),
        )
        conn.commit()

    return {"success": True}
