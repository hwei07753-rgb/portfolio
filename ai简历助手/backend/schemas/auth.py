"""
认证相关 Schema

定义用户注册、登录、信息响应的请求/响应模型。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """用户注册请求模型"""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class UserLogin(BaseModel):
    """用户登录请求模型"""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=1, description="密码")


class UserUpdate(BaseModel):
    """用户信息更新请求模型（所有字段可选）"""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str | None = Field(None, min_length=2, max_length=50, description="用户名")
    email: EmailStr | None = Field(None, description="邮箱地址")
    avatar_url: str | None = Field(None, max_length=255, description="头像 URL")


class PasswordChange(BaseModel):
    """密码修改请求模型"""

    model_config = ConfigDict(str_strip_whitespace=True)

    current_password: str = Field(..., min_length=1, description="当前密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")


class UserResponse(BaseModel):
    """用户信息响应模型（支持从 SQLAlchemy ORM 自动转换）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    avatar_url: str | None = None
    created_at: datetime
    resume_count: int = 0
    knowledge_count: int = 0


class TokenResponse(BaseModel):
    """登录成功响应模型（含 JWT Token）"""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
