"""
认证路由模块

提供用户注册、登录、信息查询与更新、Token 刷新等 RESTful API 端点。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.knowledge import KnowledgeEntry
from backend.models.resume import Resume
from backend.models.user import User
from backend.schemas.auth import (
    PasswordChange,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from backend.services.auth_service import (
    AuthServiceError,
    DuplicateEmailError,
    DuplicateUsernameError,
    InvalidCredentialsError,
    WrongPasswordError,
    change_password as change_password_service,
    login as login_service,
    register as register_service,
    update_user as update_user_service,
)
from backend.utils.security import create_access_token, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ---------------------------------------------------------------------------
# 公开端点（无需认证）
# ---------------------------------------------------------------------------


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="注册新用户并返回 JWT Token。新用户自动获赠 3 点。",
)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """POST /api/auth/register

    请求体 (JSON):
        - username: 用户名（2-50 字符）
        - email: 邮箱地址
        - password: 密码（6-128 字符）

    响应 (201):
        TokenResponse: access_token, token_type, user

    错误码:
        - 409: 用户名或邮箱已被注册
        - 422: 请求体校验失败
    """
    try:
        return register_service(db, user_data)
    except DuplicateUsernameError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except DuplicateEmailError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except AuthServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="用户登录",
    description="验证邮箱和密码，返回 JWT Token。",
)
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """POST /api/auth/login

    请求体 (JSON):
        - email: 邮箱地址
        - password: 密码

    响应 (200):
        TokenResponse: access_token, token_type, user

    错误码:
        - 401: 邮箱或密码错误
        - 403: 账号已停用
    """
    try:
        return login_service(db, login_data)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except AuthServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# ---------------------------------------------------------------------------
# 受保护端点（需要 JWT 认证）
# ---------------------------------------------------------------------------


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
    description="返回当前已认证用户的详细信息。",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """GET /api/auth/me

    请求头:
        Authorization: Bearer <token>

    响应 (200):
        UserResponse: id, username, email, avatar_url, created_at, resume_count, knowledge_count

    错误码:
        - 401: Token 无效或已过期
    """
    # 查询简历数量
    resume_count = db.query(Resume).filter(Resume.user_id == current_user.id).count()

    # 查询知识库贡献数量（来自该用户的优化结果）
    knowledge_count = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.source == "auto_extract"
    ).join(Resume, KnowledgeEntry.resume_id == Resume.id).filter(
        Resume.user_id == current_user.id
    ).count()

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at,
        resume_count=resume_count,
        knowledge_count=knowledge_count,
    )


@router.put(
    "/me",
    response_model=UserResponse,
    summary="更新当前用户信息",
    description="部分更新当前已认证用户的信息（用户名、邮箱、头像）。",
)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """PUT /api/auth/me

    请求头:
        Authorization: Bearer <token>

    请求体 (JSON，所有字段可选):
        - username: 新用户名
        - email: 新邮箱
        - avatar_url: 新头像 URL

    响应 (200):
        UserResponse: 更新后的用户信息

    错误码:
        - 401: Token 无效或已过期
        - 409: 用户名或邮箱已被注册
    """
    try:
        return update_user_service(db, current_user.id, user_data)
    except DuplicateUsernameError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except DuplicateEmailError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except AuthServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.put(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="修改密码",
    description="验证当前密码后修改为新密码。",
)
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """PUT /api/auth/password

    验证当前密码后修改为新密码。

    请求头:
        Authorization: Bearer <token>

    请求体 (JSON):
        - current_password: 当前密码
        - new_password: 新密码（6-128 字符）

    响应 (204): 无内容

    错误码:
        - 400: 当前密码不正确
        - 401: Token 无效或已过期
    """
    try:
        change_password_service(db, current_user.id, data)
    except WrongPasswordError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except AuthServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="刷新 Token",
    description="使用当前有效 Token 换取新 Token（续期）。",
)
async def refresh_token(
    current_user: User = Depends(get_current_user),
) -> TokenResponse:
    """POST /api/auth/refresh

    请求头:
        Authorization: Bearer <token>

    响应 (200):
        TokenResponse: 新的 access_token, token_type, user

    错误码:
        - 401: Token 无效或已过期
    """
    # 生成新 Token
    access_token = create_access_token(data={"sub": str(current_user.id)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            avatar_url=current_user.avatar_url,
            created_at=current_user.created_at,
        ),
    )
