"""Auth dependencies for FastAPI route injection."""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request

from src.auth.jwt import verify_token
from src.db.client import get_supabase


@dataclass
class CurrentUser:
    id: str
    email: str


def _extract_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:]
    return None


def _extract_api_key(request: Request) -> str | None:
    return request.headers.get("X-API-Key")


async def get_current_user(request: Request) -> CurrentUser:
    """FastAPI dependency: authenticate via Bearer JWT or X-API-Key."""

    # Try JWT first
    token = _extract_bearer_token(request)
    if token:
        try:
            payload = verify_token(token)
            if payload.get("type") != "access":
                raise HTTPException(status_code=401, detail="Invalid token type")
            return CurrentUser(id=payload["sub"], email=payload.get("email", ""))
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Try API key
    api_key = _extract_api_key(request)
    if api_key:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        db = get_supabase()
        result = db.table("api_keys").select("user_id, is_active, expires_at, scopes").eq("key_hash", key_hash).execute()

        if not result.data:
            raise HTTPException(status_code=401, detail="Invalid API key")

        key_row = result.data[0]
        if not key_row["is_active"]:
            raise HTTPException(status_code=401, detail="API key is inactive")
        if key_row["expires_at"]:
            expires = datetime.fromisoformat(key_row["expires_at"])
            if expires < datetime.now(timezone.utc):
                raise HTTPException(status_code=401, detail="API key has expired")

        # Update last_used_at
        db.table("api_keys").update({"last_used_at": datetime.now(timezone.utc).isoformat()}).eq("key_hash", key_hash).execute()

        # Fetch user email
        user_result = db.table("users").select("email").eq("id", key_row["user_id"]).execute()
        email = user_result.data[0]["email"] if user_result.data else ""

        return CurrentUser(id=key_row["user_id"], email=email)

    raise HTTPException(status_code=401, detail="Missing authentication credentials")
