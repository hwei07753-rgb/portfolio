"""
用户模型

定义用户表结构，用于存储注册用户信息。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class User(Base):
    """用户模型

    存储用户注册信息、认证状态和个人设置。

    Attributes:
        id: 用户唯一标识
        username: 用户名（唯一）
        email: 邮箱地址（唯一）
        password_hash: bcrypt 加密后的密码
        avatar_url: 头像 URL（可选）
        created_at: 注册时间
        updated_at: 最后更新时间（自动刷新）
        last_login: 最后登录时间
        is_active: 账号是否激活
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="用户唯一标识",
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="用户名",
    )

    email: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="邮箱地址",
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="加密后的密码",
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
        comment="头像 URL",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="注册时间",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="最后更新时间",
    )

    last_login: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        comment="最后登录时间",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="账号是否激活",
    )

    # ---- 关系映射 ----

    resumes: Mapped[list["Resume"]] = relationship(
        "Resume",
        back_populates="user",
        lazy="selectin",
    )

    feedbacks: Mapped[list["UserFeedback"]] = relationship(
        "UserFeedback",
        back_populates="user",
        lazy="selectin",
    )

    wallet: Mapped["UserWallet | None"] = relationship(
        "UserWallet",
        back_populates="user",
        uselist=False,
        lazy="selectin",
    )

    point_transactions: Mapped[list["PointTransaction"]] = relationship(
        "PointTransaction",
        back_populates="user",
        lazy="selectin",
    )

    payment_orders: Mapped[list["PaymentOrder"]] = relationship(
        "PaymentOrder",
        back_populates="user",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

    # 数据库索引：提升查询性能
    __table_args__ = (
        Index("idx_user_email", "email"),  # 登录查询
        Index("idx_user_username", "username"),  # 用户名查询
    )
