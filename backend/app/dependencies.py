"""Shared auth dependencies — password hashing, token generation/verification, rate limiter."""
import os
import hmac
import hashlib
import base64
import json
import secrets
import time
from typing import Optional

from fastapi import Header
from slowapi import Limiter
from slowapi.util import get_remote_address

# ── Rate limiter (shared across all routers) ──────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── Secret key (loaded from environment via main.py's load_dotenv call) ───────
def _get_secret() -> str:
    key = os.environ.get("JWT_SECRET", "")
    if not key:
        import warnings
        warnings.warn(
            "JWT_SECRET is not set. Using insecure fallback — set it in backend/.env!",
            stacklevel=2,
        )
        return "insecure-fallback-dev-only-do-not-use-in-production"
    return key


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, key_hex = hashed.split("$")
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return hmac.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


def generate_token(user_id: str) -> str:
    secret = _get_secret()
    payload = {"sub": user_id, "exp": int(time.time()) + 86400 * 7}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return f"{payload_b64}.{sig_b64}"


def verify_token(token: str) -> Optional[str]:
    try:
        secret = _get_secret()
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig_b64 = parts

        pad = len(payload_b64) % 4
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + ("=" * (4 - pad) if pad else ""))
        payload = json.loads(payload_bytes.decode())

        if payload.get("exp", 0) < time.time():
            return None

        expected_sig = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")

        if hmac.compare_digest(sig_b64, expected_sig_b64):
            return payload.get("sub")
    except Exception:
        return None
    return None


def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Extracts and validates Bearer token from Authorization header. Returns None if absent/invalid."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return verify_token(authorization.split(" ")[1])
    except Exception:
        return None
