"""Reset a user's password in the local Social Arb database."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from social_arb.auth.models import hash_password
from social_arb.db.schema import get_connection
from social_arb.config import config
from social_arb.api.deps import ensure_db

ensure_db()

email = sys.argv[1] if len(sys.argv) > 1 else "deenikdaniel@gmail.com"
password = sys.argv[2] if len(sys.argv) > 2 else "socialarb"

pw_hash = hash_password(password)
with get_connection(config.db_path) as conn:
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if row:
        conn.execute("UPDATE users SET password_hash = ? WHERE email = ?", (pw_hash, email))
        conn.commit()
        print(f"Password reset for {email}")
    else:
        conn.execute(
            "INSERT INTO users (email, password_hash, display_name) VALUES (?, ?, ?)",
            (email, pw_hash, email.split("@")[0]),
        )
        conn.commit()
        print(f"Created user {email}")
