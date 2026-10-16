"""User accounts + Stripe billing for CAD AI Editor."""
import hashlib
import secrets
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = Path(__file__).parent / "app.db"  # flat structure


def _db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    db = _db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL,
            stripe_customer_id TEXT,
            plan TEXT DEFAULT 'free',
            credits INTEGER DEFAULT 3
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS payments (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            stripe_session_id TEXT,
            amount_cents INTEGER,
            plan TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    db.commit()
    db.close()


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 100_000
    ).hex()


def register(email: str, password: str) -> dict:
    """Create a new user. Returns user dict or raises ValueError."""
    import uuid
    db = _db()
    if db.execute(
        "SELECT id FROM users WHERE email = ?", (email.lower(),)
    ).fetchone():
        db.close()
        raise ValueError("Email already registered")

    user_id = uuid.uuid4().hex[:12]
    salt = secrets.token_hex(16)
    db.execute(
        "INSERT INTO users (id, email, password_hash, salt, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, email.lower(), _hash(password, salt), salt,
         datetime.utcnow().isoformat()),
    )
    db.commit()
    db.close()
    return {"id": user_id, "email": email.lower(), "plan": "free", "credits": 3}


def login(email: str, password: str) -> Optional[str]:
    """Verify credentials. Returns session token or None."""
    db = _db()
    user = db.execute(
        "SELECT * FROM users WHERE email = ?", (email.lower(),)
    ).fetchone()
    if not user or _hash(password, user["salt"]) != user["password_hash"]:
        db.close()
        return None

    token = secrets.token_hex(32)
    expires = (datetime.utcnow() + timedelta(days=30)).isoformat()
    db.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user["id"], expires),
    )
    db.commit()
    db.close()
    return token


def get_user_by_token(token: str) -> Optional[dict]:
    """Get user from session token."""
    db = _db()
    row = db.execute(
        "SELECT u.* FROM users u JOIN sessions s ON s.user_id = u.id "
        "WHERE s.token = ? AND s.expires_at > ?",
        (token, datetime.utcnow().isoformat()),
    ).fetchone()
    db.close()
    if not row:
        return None
    return dict(row)


def use_credit(user_id: str) -> bool:
    """Consume one credit. Returns False if none left."""
    db = _db()
    user = db.execute(
        "SELECT credits, plan FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if not user:
        db.close()
        return False
    # Pro/unlimited plans don't use credits
    if user["plan"] in ("pro", "unlimited"):
        db.close()
        return True
    if user["credits"] <= 0:
        db.close()
        return False
    db.execute(
        "UPDATE users SET credits = credits - 1 WHERE id = ?", (user_id,)
    )
    db.commit()
    db.close()
    return True


def upgrade_plan(user_id: str, plan: str, stripe_customer_id: str = None):
    """Upgrade user after successful Stripe payment."""
    db = _db()
    db.execute(
        "UPDATE users SET plan = ?, stripe_customer_id = COALESCE(?, stripe_customer_id) "
        "WHERE id = ?",
        (plan, stripe_customer_id, user_id),
    )
    db.commit()
    db.close()


# Pricing tiers
PLANS = {
    "free": {"credits": 3, "price": 0, "name": "Free Trial"},
    "pay_per": {"credits": 10, "price_cents": 2900, "name": "10 Revisions"},
    "pro": {"credits": -1, "price_cents": 9900, "name": "Pro Monthly",
            "interval": "month"},
}
