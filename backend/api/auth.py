"""
Overcut.ai — Auth Router
Handles user registration, login, token refresh, and profile retrieval.

Environment variables required:
  OVERCUT_MONGO_URI   – MongoDB connection string (e.g. mongodb://localhost:27017)
  OVERCUT_JWT_SECRET  – Secret key for signing JWT tokens (min 32 chars)
  OVERCUT_JWT_EXPIRE  – Token lifetime in minutes (default: 10080 = 7 days)

If OVERCUT_MONGO_URI is not set, the router is mounted but all endpoints return
503 so the frontend can degrade gracefully while the backend is not configured.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field

from backend.core import config

logger = logging.getLogger(__name__)

# ── Optional dependencies (graceful degradation if not installed) ──
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from passlib.context import CryptContext
    from jose import JWTError, jwt
    _AUTH_DEPS_AVAILABLE = True
except ImportError:
    _AUTH_DEPS_AVAILABLE = False
    logger.warning("Auth dependencies (motor/passlib/jose) not installed — auth endpoints will return 503.")

# ── Config ─────────────────────────────────────────────────────────
MONGO_URI   = config.MONGO_URI
JWT_SECRET  = config.JWT_SECRET
JWT_ALGO    = config.JWT_ALGO
JWT_EXPIRE  = config.JWT_EXPIRE_MINUTES
DB_NAME     = "overcut"
USERS_COLL  = "users"

# ── Crypto setup ───────────────────────────────────────────────────
if _AUTH_DEPS_AVAILABLE:
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
else:
    pwd_ctx = None

# ── MongoDB client (lazy — only created if URI is set) ─────────────
_mongo_client: Optional[object] = None
_db = None

def get_db():
    global _mongo_client, _db
    if not _AUTH_DEPS_AVAILABLE:
        raise HTTPException(503, "Auth dependencies not installed on server.")
    if not MONGO_URI:
        raise HTTPException(503, "OVERCUT_MONGO_URI environment variable not configured.")
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(MONGO_URI)
        _db = _mongo_client[DB_NAME]
    return _db

# ── Pydantic schemas ───────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name:  str             = Field(..., min_length=2, max_length=80)
    email: EmailStr
    # bcrypt only considers the first 72 bytes; cap input instead of silently truncating.
    password: str          = Field(..., min_length=8, max_length=72)
    role:  str             = Field(default="Telemetry Engineer", max_length=80)
    team:  str             = Field(default="Formula 1 Racing Team", max_length=80)

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str = Field(..., min_length=1, max_length=72)

class AuthResponse(BaseModel):
    token:   str
    user_id: str
    name:    str
    email:   str
    role:    str
    team:    str
    avatar:  str
    accent_color: str = "#00D4FF"

class ProfileResponse(BaseModel):
    user_id: str
    name:    str
    email:   str
    role:    str
    team:    str
    avatar:  str
    accent_color: str
    created_at: str

# ── Helpers ────────────────────────────────────────────────────────
def _hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)

def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def _create_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE)
    return jwt.encode(
        {"sub": user_id, "email": email, "exp": expire},
        JWT_SECRET,
        algorithm=JWT_ALGO,
    )

def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

def _initials(name: str) -> str:
    parts = name.strip().split()
    return "".join(p[0].upper() for p in parts if p)[:2] or "OE"

# Team → accent colour mapping
_TEAM_COLORS = {
    "ferrari": "#E80020",
    "red bull": "#3671C6",
    "mclaren": "#FF8000",
    "mercedes": "#27F4D2",
    "aston martin": "#229971",
    "alpine": "#0093CC",
    "williams": "#00A0DE",
    "haas": "#B6BABD",
    "kick sauber": "#52E252",
    "racing bulls": "#6692FF",
    "nasa": "#00D4FF",
    "ev fleet": "#00FF88",
}

def _team_color(team: str) -> str:
    t = team.lower()
    for key, color in _TEAM_COLORS.items():
        if key in t:
            return color
    return "#00D4FF"

# ── Bearer auth dependency ─────────────────────────────────────────
_bearer = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db=Depends(get_db),
):
    if not credentials:
        raise HTTPException(401, "No auth token provided.")
    payload = _decode_token(credentials.credentials)
    user_id = payload.get("sub")
    user = await db[USERS_COLL].find_one({"_id": user_id})
    if not user:
        raise HTTPException(401, "User not found.")
    return user

# ── Router ─────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(body: RegisterRequest, db=Depends(get_db)):
    """Create a new user account."""
    existing = await db[USERS_COLL].find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user_id = f"usr_{os.urandom(8).hex()}"
    avatar  = _initials(body.name)
    color   = _team_color(body.team)

    doc = {
        "_id":          user_id,
        "name":         body.name,
        "email":        body.email.lower(),
        "password_hash": _hash_password(body.password),
        "role":         body.role,
        "team":         body.team,
        "avatar":       avatar,
        "accent_color": color,
        "created_at":   datetime.now(timezone.utc).isoformat(),
    }
    await db[USERS_COLL].insert_one(doc)
    token = _create_token(user_id, body.email.lower())
    return AuthResponse(
        token=token, user_id=user_id, name=body.name, email=body.email.lower(),
        role=body.role, team=body.team, avatar=avatar, accent_color=color,
    )

@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db=Depends(get_db)):
    """Authenticate an existing user and return a JWT."""
    user = await db[USERS_COLL].find_one({"email": body.email.lower()})
    if not user or not _verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = _create_token(user["_id"], user["email"])
    return AuthResponse(
        token=token,
        user_id=user["_id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        team=user["team"],
        avatar=user["avatar"],
        accent_color=user.get("accent_color", "#00D4FF"),
    )

@router.get("/me", response_model=ProfileResponse)
async def get_profile(user=Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return ProfileResponse(
        user_id=user["_id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        team=user["team"],
        avatar=user["avatar"],
        accent_color=user.get("accent_color", "#00D4FF"),
        created_at=user.get("created_at", ""),
    )

@router.post("/logout")
async def logout():
    """
    Logout is handled client-side by deleting the stored JWT.
    This endpoint exists for completeness and future token-blocklist support.
    """
    return {"status": "ok", "message": "Token discarded client-side."}
