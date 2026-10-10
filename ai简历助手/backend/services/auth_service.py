"""
认证服务模块

处理用户注册、登录、信息查询等认证相关业务逻辑。
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models.user import User
from backend.models.payment import UserWallet, PointTransaction
from backend.schemas.auth import UserCreate, UserLogin, UserUpdate, PasswordChange, TokenResponse, UserResponse
from backend.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
)

logger = logging.getLogger(__name__)

# 新用户注册赠送点数
GIFT_POINTS = 3


class AuthServiceError(Exception):
    """认证服务异常基类"""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class DuplicateUsernameError(AuthServiceError):
    """用户名已存在"""

    def __init__(self):
        super().__init__("用户名已被注册", status_code=409)


class DuplicateEmailError(AuthServiceError):
    """邮箱已存在"""

    def __init__(self):
        super().__init__("邮箱已被注册", status_code=409)


class InvalidCredentialsError(AuthServiceError):
    """登录凭证无效"""

    def __init__(self):
        super().__init__(message="邮箱或密码错误", status_code=401)


class UserNotFoundError(AuthServiceError):
    """用户不存在"""

    def __init__(self):
        super().__init__("用户不存在", status_code=404)


class WrongPasswordError(AuthServiceError):
    """当前密码错误"""

    def __init__(self):
        super().__init__("当前密码不正确", status_code=400)


def register(db: Session, user_data: UserCreate) -> TokenResponse:
    """用户注册

    流程：
    1. 检查用户名唯一性
    2. 检查邮箱唯一性
    3. 创建用户记录（密码 bcrypt 哈希）
    4. 创建用户钱包并赠送初始点数
    5. 生成 JWT Token 返回

    Args:
        db: 数据库会话
        user_data: 注册请求数据

    Returns:
        TokenResponse 包含 JWT Token 和用户信息

    Raises:
        DuplicateUsernameError: 用户名已被注册
        DuplicateEmailError: 邮箱已被注册
    """
    # 检查用户名唯一性
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise DuplicateUsernameError()

    # 检查邮箱唯一性
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise DuplicateEmailError()

    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
    )
    db.add(user)
    db.flush()  # 获取 user.id

    # 创建钱包并赠送初始点数
    wallet = UserWallet(user_id=user.id, balance=GIFT_POINTS, total_recharged=GIFT_POINTS)
    db.add(wallet)

    # 记录赠送流水
    transaction = PointTransaction(
        user_id=user.id,
        amount=GIFT_POINTS,
        balance_after=GIFT_POINTS,
        type="gift",
        description="新用户注册赠送",
    )
    db.add(transaction)

    db.commit()
    db.refresh(user)

    logger.info(f"用户注册成功: {user.username} (ID: {user.id}), 赠送 {GIFT_POINTS} 点")

    # 生成 Token
    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
        ),
    )


def login(db: Session, login_data: UserLogin) -> TokenResponse:
    """用户登录

    流程：
    1. 根据邮箱查找用户
    2. 验证密码
    3. 更新最后登录时间
    4. 生成 JWT Token 返回

    Args:
        db: 数据库会话
        login_data: 登录请求数据

    Returns:
        TokenResponse 包含 JWT Token 和用户信息

    Raises:
        InvalidCredentialsError: 邮箱或密码错误
    """
    # 查找用户
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        raise InvalidCredentialsError()

    # 验证密码
    if not verify_password(login_data.password, user.password_hash):
        raise InvalidCredentialsError()

    # 检查账号状态
    if not user.is_active:
        raise AuthServiceError("账号已停用，请联系管理员", status_code=403)

    # 更新最后登录时间
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    logger.info(f"用户登录成功: {user.username} (ID: {user.id})")

    # 生成 Token
    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
        ),
    )


def get_user(db: Session, user_id: int) -> User:
    """获取用户信息

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        User ORM 对象

    Raises:
        UserNotFoundError: 用户不存在
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundError()
    return user


def get_user_response(db: Session, user_id: int) -> UserResponse:
    """获取用户信息（响应格式）

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        UserResponse 对象
    """
    user = get_user(db, user_id)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
    )


def update_user(db: Session, user_id: int, user_data: UserUpdate) -> UserResponse:
    """更新用户信息

    只更新请求中明确传入的字段（非 None 字段）。
    更新用户名或邮箱时会检查唯一性。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        user_data: 更新请求数据（部分字段可选）

    Returns:
        更新后的 UserResponse 对象

    Raises:
        UserNotFoundError: 用户不存在
        DuplicateUsernameError: 用户名已被注册
        DuplicateEmailError: 邮箱已被注册
    """
    user = get_user(db, user_id)

    # 更新用户名（检查唯一性）
    if user_data.username is not None and user_data.username != user.username:
        existing = db.query(User).filter(User.username == user_data.username).first()
        if existing:
            raise DuplicateUsernameError()
        user.username = user_data.username

    # 更新邮箱（检查唯一性）
    if user_data.email is not None and user_data.email != user.email:
        existing = db.query(User).filter(User.email == user_data.email).first()
        if existing:
            raise DuplicateEmailError()
        user.email = user_data.email

    # 更新头像
    if user_data.avatar_url is not None:
        user.avatar_url = user_data.avatar_url

    db.commit()
    db.refresh(user)

    logger.info(f"用户信息已更新: {user.username} (ID: {user.id})")

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
    )


def change_password(db: Session, user_id: int, data: PasswordChange) -> None:
    """修改用户密码

    验证当前密码后更新为新密码。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        data: 密码修改请求数据（当前密码 + 新密码）

    Raises:
        UserNotFoundError: 用户不存在
        WrongPasswordError: 当前密码不正确
    """
    user = get_user(db, user_id)

    # 验证当前密码
    if not verify_password(data.current_password, user.password_hash):
        raise WrongPasswordError()

    # 更新为新密码
    user.password_hash = hash_password(data.new_password)
    db.commit()

    logger.info(f"用户密码已修改: {user.username} (ID: {user.id})")
