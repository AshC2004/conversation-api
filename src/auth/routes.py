"""Auth endpoints: register, login, refresh, logout."""

import hashlib
from datetime import datetime, timezone

import bcrypt as _bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from src.auth.dependencies import CurrentUser, get_current_user
from src.auth.jwt import create_access_token, create_refresh_token, verify_token
from src.db.client import get_supabase

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


# --- Request / Response schemas ---

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    status: str = "success"
    data: dict


# --- Helpers ---

def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _epoch_to_iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _token_pair(user_id: str, email: str) -> dict:
    return {
        "access_token": create_access_token(user_id, email),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
    }


# --- Endpoints ---

@router.post("/register", status_code=201, response_model=TokenResponse, summary="Register a new user", description="Create a new user account and return JWT tokens.")
async def register(body: RegisterRequest):
    db = get_supabase()

    # Check existing user
    existing = db.table("users").select("id").eq("email", body.email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create user
    password_hash = _bcrypt.hashpw(body.password.encode(), _bcrypt.gensalt()).decode()
    result = db.table("users").insert({
        "email": body.email,
        "password_hash": password_hash,
    }).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create user")

    user = result.data[0]
    tokens = _token_pair(user["id"], user["email"])

    # Store refresh token hash
    db.table("refresh_tokens").insert({
        "user_id": user["id"],
        "token_hash": _hash_refresh_token(tokens["refresh_token"]),
        "expires_at": _epoch_to_iso(verify_token(tokens["refresh_token"])["exp"]),
    }).execute()

    return TokenResponse(data=tokens)


@router.post("/login", response_model=TokenResponse, summary="Login", description="Authenticate with email and password, returns JWT access and refresh tokens.")
async def login(body: LoginRequest):
    db = get_supabase()

    result = db.table("users").select("id, email, password_hash").eq("email", body.email).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = result.data[0]
    if not _bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    tokens = _token_pair(user["id"], user["email"])

    # Store refresh token hash
    db.table("refresh_tokens").insert({
        "user_id": user["id"],
        "token_hash": _hash_refresh_token(tokens["refresh_token"]),
        "expires_at": _epoch_to_iso(verify_token(tokens["refresh_token"])["exp"]),
    }).execute()

    return TokenResponse(data=tokens)


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token", description="Exchange a valid refresh token for a new token pair. Old refresh token is revoked.")
async def refresh(body: RefreshRequest):
    # Verify the refresh token JWT
    try:
        payload = verify_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    db = get_supabase()
    token_hash = _hash_refresh_token(body.refresh_token)

    # Check refresh token in DB
    stored = db.table("refresh_tokens").select("id, is_revoked").eq("token_hash", token_hash).execute()
    if not stored.data or stored.data[0]["is_revoked"]:
        raise HTTPException(status_code=401, detail="Refresh token revoked or not found")

    # Revoke old refresh token
    db.table("refresh_tokens").update({"is_revoked": True}).eq("id", stored.data[0]["id"]).execute()

    # Fetch user email
    user_id = payload["sub"]
    user_result = db.table("users").select("email").eq("id", user_id).execute()
    email = user_result.data[0]["email"] if user_result.data else ""

    # Issue new token pair
    tokens = _token_pair(user_id, email)

    db.table("refresh_tokens").insert({
        "user_id": user_id,
        "token_hash": _hash_refresh_token(tokens["refresh_token"]),
        "expires_at": _epoch_to_iso(verify_token(tokens["refresh_token"])["exp"]),
    }).execute()

    return TokenResponse(data=tokens)


@router.post("/logout", summary="Logout", description="Revoke the refresh token. Requires a valid access token.")
async def logout(body: RefreshRequest, user: CurrentUser = Depends(get_current_user)):
    db = get_supabase()
    token_hash = _hash_refresh_token(body.refresh_token)

    # Revoke the refresh token
    db.table("refresh_tokens").update({"is_revoked": True}).eq("token_hash", token_hash).eq("user_id", user.id).execute()

    return {"status": "success", "data": {"message": "Logged out successfully"}}
