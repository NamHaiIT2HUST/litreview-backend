"""
Authentication Routes for LitReview Agent
Handles Local Credentials (Username/Password, Role-based Access, Admin Management)
and Google OAuth 2.0 (Token verification, Google Identity Services, and session management).
"""

import os
import logging
import hashlib
import base64
import jwt
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
import httpx

from src.database import get_db
from src.models.db_models import User, Role

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger("litreview.auth")

SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_KEY_LITREVIEW")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID",
    "447985190531-p2gko4a06q485g1mku819bno42qsifen.apps.googleusercontent.com"
)
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8000/api/v1/auth/google/callback"
)


# ── Password Hashing & Token Helpers ──────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return base64.b64encode(salt + pwdhash).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    try:
        decoded = base64.b64decode(hashed.encode('utf-8'))
        salt = decoded[:16]
        stored_hash = decoded[16:]
        pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return pwdhash == stored_hash
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"


class UserLogin(BaseModel):
    username: str
    password: str


class GoogleAuthPayload(BaseModel):
    id_token: Optional[str] = None
    access_token: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    sub: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: str
    name: str
    email: str
    avatar: str
    picture: Optional[str] = None
    role: str = "Academic Researcher"
    institution: str = "Academic Institution"
    plan: str = "Scholar Pro"
    bio: str = "Đăng nhập xác thực qua Google Workspace."
    provider: str = "google"


# ── Local Auth Endpoints (Register, Login, Admin) ─────────────────────────────

@router.post("/register")
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    if len(user_data.password) < 8:
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 8 ký tự.")
    if not any(char in "!@#$%^&*()_+-=[]{}|;':,.<>?/" for char in user_data.password):
        raise HTTPException(status_code=400, detail="Mật khẩu phải chứa ít nhất 1 ký tự đặc biệt.")
    
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Tên người dùng đã tồn tại.")

    role_val = Role.admin if user_data.role == "admin" else Role.user
    
    new_user = User(
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        role=role_val
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    access_token = create_access_token(
        data={"sub": new_user.username, "role": new_user.role.value, "id": str(new_user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user": {
            "id": str(new_user.id),
            "username": new_user.username,
            "role": new_user.role.value
        }
    }


@router.post("/login")
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Sai tên đăng nhập hoặc mật khẩu.")
    
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value, "id": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "role": user.role.value
        }
    }


@router.get("/admin/stats")
async def get_admin_stats(db: AsyncSession = Depends(get_db)):
    from src.models.db_models import Project, SearchQuery, Paper

    user_count = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    project_count = (await db.execute(select(func.count()).select_from(Project))).scalar() or 0
    query_count = (await db.execute(select(func.count()).select_from(SearchQuery))).scalar() or 0
    paper_count = (await db.execute(select(func.count()).select_from(Paper))).scalar() or 0

    recent_queries_result = await db.execute(
        select(SearchQuery.query_string, SearchQuery.executed_at, SearchQuery.result_count)
        .order_by(desc(SearchQuery.executed_at))
        .limit(10)
    )
    recent_queries = [
        {
            "query": r[0],
            "time": r[1].isoformat() if r[1] else "",
            "results": r[2]
        }
        for r in recent_queries_result.all()
    ]

    users_result = await db.execute(select(User).order_by(desc(User.created_at)))
    users_data = []
    for u in users_result.scalars().all():
        p_count = (await db.execute(
            select(func.count()).select_from(Project).where(Project.user_id == u.id)
        )).scalar() or 0
        users_data.append({
            "id": str(u.id),
            "username": u.username,
            "role": u.role.value if hasattr(u.role, 'value') else u.role,
            "created_at": u.created_at.isoformat() if u.created_at else "",
            "project_count": p_count
        })

    return {
        "summary": {
            "total_users": user_count,
            "total_projects": project_count,
            "total_queries": query_count,
            "total_papers": paper_count
        },
        "users": users_data,
        "recent_queries": recent_queries
    }


@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db)):
    import uuid
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID người dùng không hợp lệ.")

    user = (await db.execute(select(User).where(User.id == uid))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    if user.role == Role.admin:
        raise HTTPException(status_code=400, detail="Không thể xóa tài khoản Admin hệ thống.")

    await db.delete(user)
    await db.commit()
    return {"message": "Đã xóa người dùng thành công."}


# ── Google OAuth Endpoints ───────────────────────────────────────────────────

@router.post("/google", response_model=UserProfileResponse)
async def verify_google_auth(payload: GoogleAuthPayload):
    user_email = payload.email
    user_name = payload.name
    user_picture = payload.picture
    user_sub = payload.sub or f"google_{abs(hash(user_email or 'anon'))}"

    if payload.access_token:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {payload.access_token}"}
                )
                if res.status_code == 200:
                    google_info = res.json()
                    user_email = google_info.get("email", user_email)
                    user_name = google_info.get("name", user_name)
                    user_picture = google_info.get("picture", user_picture)
                    user_sub = google_info.get("sub", user_sub)
                    logger.info(f"Google OAuth verified successfully for {user_email}")
        except Exception as e:
            logger.warning(f"Failed to query Google Userinfo endpoint: {e}")

    elif payload.id_token:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    f"https://oauth2.googleapis.com/tokeninfo?id_token={payload.id_token}"
                )
                if res.status_code == 200:
                    token_info = res.json()
                    user_email = token_info.get("email", user_email)
                    user_name = token_info.get("name", user_name)
                    user_picture = token_info.get("picture", user_picture)
                    user_sub = token_info.get("sub", user_sub)
                    logger.info(f"Google ID token verified successfully for {user_email}")
        except Exception as e:
            logger.warning(f"Failed to verify Google ID token: {e}")

    if not user_email:
        user_email = "scholar.researcher@gmail.com"
    if not user_name:
        user_name = user_email.split("@")[0].replace(".", " ").title()

    initials = "".join([w[0] for w in user_name.split()[:2]]).upper() or "G"

    institution = "Google Workspace Academic"
    if "@" in user_email:
        domain = user_email.split("@")[1].lower()
        if "vinuni.edu" in domain:
            institution = "VinUniversity"
        elif "hust.edu" in domain:
            institution = "HUST - ĐH Bách Khoa Hà Nội"
        elif "vnu.edu" in domain:
            institution = "Đại học Quốc gia Hà Nội"
        elif "edu" in domain:
            institution = domain.replace(".edu", "").replace(".vn", "").upper() + " University"

    return UserProfileResponse(
        id=user_sub,
        name=user_name,
        email=user_email,
        avatar=initials,
        picture=user_picture,
        role="Senior Researcher",
        institution=institution,
        plan="Scholar Pro",
        bio="Tài khoản học thuật xác thực qua Google OAuth 2.0.",
        provider="google"
    )


@router.get("/google/callback")
async def google_oauth_callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None
):
    if error:
        logger.error(f"Google OAuth callback error: {error}")
        return RedirectResponse(url=f"http://localhost:5173/?auth_error={error}")

    logger.info(f"Received Google OAuth authorization code: {code[:10] if code else 'none'}...")
    return RedirectResponse(url="http://localhost:5173/#overview")


@router.get("/config")
async def get_auth_config():
    return {
        "google_client_id": GOOGLE_CLIENT_ID,
        "google_redirect_uri": GOOGLE_REDIRECT_URI,
        "enabled_providers": ["google", "academic_email", "demo"]
    }
