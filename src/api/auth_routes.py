from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database import get_db
from src.models.db_models import User, Role
import hashlib
import os
import base64
import jwt
from datetime import datetime, timedelta, UTC

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = "SUPER_SECRET_KEY_LITREVIEW" # Should be in env, but keeping simple for now
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

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

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"

class UserLogin(BaseModel):
    username: str
    password: str

@router.post("/register")
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Simple validation inside the route
    if len(user_data.password) < 8:
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 8 ký tự.")
    if not any(char in "!@#$%^&*()_+-=[]{}|;':,.<>?/" for char in user_data.password):
        raise HTTPException(status_code=400, detail="Mật khẩu phải chứa ít nhất 1 ký tự đặc biệt.")
    
    # Check if username exists
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
    from sqlalchemy import func, desc

    # Total counts
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    project_count = (await db.execute(select(func.count()).select_from(Project))).scalar() or 0
    query_count = (await db.execute(select(func.count()).select_from(SearchQuery))).scalar() or 0
    paper_count = (await db.execute(select(func.count()).select_from(Paper))).scalar() or 0

    # Recent queries
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

    # Users list with project count
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

