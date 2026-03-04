import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import User, get_db

try:
    from jose import jwt, JWTError
    import bcrypt as _bcrypt
    _crypto_available = True
except ImportError:
    _crypto_available = False

try:
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
    _google_available = True
except ImportError:
    _google_available = False


def _hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return _bcrypt.checkpw(password.encode(), hashed.encode())

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY", "amlkr-dev-secret-change-in-production")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_DAYS = 30


# ─── Schemas ─────────────────────────────────────────────────────────────────

class RegisterBody(BaseModel):
    name:     str
    email:    str
    password: str

class LoginBody(BaseModel):
    email:    str
    password: str

class UserOut(BaseModel):
    id:    str
    name:  str
    email: Optional[str]
    role:  str

class AuthResponse(BaseModel):
    token: str
    user:  UserOut


class GoogleLoginBody(BaseModel):
    id_token: str


# ─── Helpers ─────────────────────────────────────────────────────────────────

def create_token(user_id: str, email: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_id, "email": email, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterBody, db: AsyncSession = Depends(get_db)):
    if not _crypto_available:
        raise HTTPException(status_code=503, detail="Auth dependencies not installed")

    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = _hash_password(body.password)
    user   = User(
        id            = uuid.uuid4(),
        name          = body.name,
        email         = body.email,
        password_hash = hashed,
        role          = "student",
    )
    db.add(user)
    await db.flush()

    token = create_token(str(user.id), user.email, user.role)
    return AuthResponse(
        token = token,
        user  = UserOut(id=str(user.id), name=user.name, email=user.email, role=user.role),
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginBody, db: AsyncSession = Depends(get_db)):
    if not _crypto_available:
        raise HTTPException(status_code=503, detail="Auth dependencies not installed")

    result = await db.execute(select(User).where(User.email == body.email))
    user   = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not _verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(str(user.id), user.email, user.role)
    return AuthResponse(
        token = token,
        user  = UserOut(id=str(user.id), name=user.name, email=user.email, role=user.role),
    )


@router.post("/google", response_model=AuthResponse)
async def login_google(body: GoogleLoginBody, db: AsyncSession = Depends(get_db)):
    if not _google_available:
        raise HTTPException(status_code=503, detail="Google auth dependencies not installed")

    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not google_client_id:
        raise HTTPException(status_code=503, detail="GOOGLE_CLIENT_ID not configured")
    try:
        request = google_requests.Request()
        payload = google_id_token.verify_oauth2_token(
            body.id_token,
            request,
            google_client_id,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    email = payload.get("email")
    email_verified = payload.get("email_verified", False)
    if not email or not email_verified:
        raise HTTPException(status_code=401, detail="Google account email not verified")

    name = payload.get("name") or email.split("@")[0]
    picture = payload.get("picture")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=uuid.uuid4(),
            name=name,
            email=email,
            password_hash=None,
            role="student",
            avatar_url=picture,
        )
        db.add(user)
        await db.flush()
    else:
        dirty = False
        if name and user.name != name:
            user.name = name
            dirty = True
        if picture and user.avatar_url != picture:
            user.avatar_url = picture
            dirty = True
        if dirty:
            await db.flush()

    token = create_token(str(user.id), user.email or email, user.role)
    return AuthResponse(
        token=token,
        user=UserOut(id=str(user.id), name=user.name, email=user.email, role=user.role),
    )
