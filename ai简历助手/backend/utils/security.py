"""
安全工具模块

提供密码哈希、JWT Token 和用户认证相关的工具函数。
"""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db

# 密码哈希上下文（bcrypt，salt rounds >= 12）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 Bearer Token 提取方案
# tokenUrl 指向登录接口，FastAPI 自动在 /docs 中生成授权按钮
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希

    Args:
        password: 明文密码

    Returns:
        bcrypt 哈希后的密码字符串
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希密码是否匹配

    Args:
        plain_password: 用户输入的明文密码
        hashed_password: 数据库中存储的哈希密码

    Returns:
        密码匹配返回 True，否则返回 False
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """创建 JWT Access Token

    Args:
        data: 要编码到 Token 中的数据（至少包含 "sub" 字段）
        expires_delta: 过期时间增量，默认使用配置中的 JWT_EXPIRE_MINUTES

    Returns:
        编码后的 JWT Token 字符串
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """解码并验证 JWT Token

    Args:
        token: JWT Token 字符串

    Returns:
        解码后的数据字典，验证失败返回 None
    """
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> "User":
    """FastAPI 依赖注入：验证 Token 并返回当前登录用户

    从请求 Header 中提取 Bearer Token，解码后查询数据库获取用户。
    验证失败时返回 401 Unauthorized。

    Args:
        token: OAuth2 Bearer Token（由 FastAPI 自动从 Header 提取）
        db: 数据库会话（由 FastAPI 依赖注入）

    Returns:
        当前登录的 User ORM 对象

    Raises:
        HTTPException: Token 无效、用户不存在或账号已停用时抛出 401

    Example:
        ```python
        @app.get("/api/auth/me")
        def get_me(current_user: User = Depends(get_current_user)):
            return current_user
        ```
    """
    # 延迟导入，避免循环依赖（User -> relationship -> Resume -> ...）
    from backend.models.user import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 解码 Token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # 从 payload 中提取用户标识（"sub" 字段存储用户 ID）
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # 查询数据库
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    # 检查账号是否激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已停用，请联系管理员",
        )

    return user
