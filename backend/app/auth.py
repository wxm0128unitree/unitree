"""
认证模块：密码哈希、JWT 签发与验证、当前用户依赖注入
"""
import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

# JWT 配置（生产环境应该用环境变量）
JWT_SECRET = os.environ.get("JWT_SECRET", "yushu-inventory-default-secret-CHANGE-ME")
JWT_ALG = "HS256"
TOKEN_EXPIRE_HOURS = 24 * 30  # 30 天

# OAuth2 password flow 仅为 OpenAPI 文档；实际请求传 Header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(plain: str) -> str:
    """bcrypt 哈希"""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """bcrypt 校验"""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user: models.User) -> str:
    """签发 JWT"""
    payload = {
        "uid": user.id,
        "phone": user.phone,
        "name": user.name,
        "is_admin": user.is_admin,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> dict:
    """解码 JWT，无效则抛 401"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的登录凭证")


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """依赖注入：从 Authorization header 获取当前用户"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    user = db.query(models.User).filter(models.User.id == payload["uid"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[models.User]:
    """可选鉴权：有 token 就返回用户，没 token 返回 None（用于读接口）"""
    if not token:
        return None
    try:
        payload = decode_token(token)
    except HTTPException:
        return None
    return db.query(models.User).filter(models.User.id == payload["uid"]).first()