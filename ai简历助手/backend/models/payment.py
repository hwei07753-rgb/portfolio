"""
支付与点数模型

定义用户钱包、点数流水和充值订单的表结构。
"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class UserWallet(Base):
    """用户钱包模型

    存储用户的点数余额及累计消费统计。
    每个用户仅有一个钱包记录。

    Attributes:
        id: 钱包唯一标识
        user_id: 所属用户 ID（唯一）
        balance: 当前点数余额
        total_recharged: 累计充值点数
        total_consumed: 累计消费点数
        created_at: 创建时间
        updated_at: 最后更新时间
    """

    __tablename__ = "user_wallets"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="钱包唯一标识",
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
        comment="所属用户 ID",
    )

    balance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="当前点数余额",
    )

    total_recharged: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="累计充值点数",
    )

    total_consumed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="累计消费点数",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="最后更新时间",
    )

    # ---- 关系映射 ----

    user: Mapped["User"] = relationship(
        "User",
        back_populates="wallet",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<UserWallet(id={self.id}, user_id={self.user_id}, "
            f"balance={self.balance})>"
        )


class PointTransaction(Base):
    """点数流水模型

    记录用户点数的每一笔变动，包括赠送、充值、消费和退款。

    Attributes:
        id: 流水唯一标识
        user_id: 所属用户 ID
        amount: 变动数量（正数=收入，负数=支出）
        balance_after: 变动后余额
        type: 类型（gift/recharge/consume/refund）
        description: 变动描述
        reference_id: 关联订单号或简历 ID
        created_at: 创建时间
    """

    __tablename__ = "point_transactions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="流水唯一标识",
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="所属用户 ID",
    )

    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="变动数量（正数=收入，负数=支出）",
    )

    balance_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="变动后余额",
    )

    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="类型：gift/recharge/consume/refund",
    )

    description: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        default=None,
        comment="变动描述",
    )

    reference_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        comment="关联订单号或简历 ID",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )

    # ---- 关系映射 ----

    user: Mapped["User"] = relationship(
        "User",
        back_populates="point_transactions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<PointTransaction(id={self.id}, user_id={self.user_id}, "
            f"amount={self.amount}, type='{self.type}')>"
        )


class PaymentOrder(Base):
    """充值订单模型

    存储用户的充值订单信息，支持订单过期与状态流转。

    Attributes:
        id: 订单唯一标识
        order_no: 订单号（唯一）
        user_id: 所属用户 ID
        amount_cents: 支付金额（分）
        points: 获得点数
        status: 订单状态（pending/paid/expired/refunded）
        paid_at: 支付时间
        expire_at: 过期时间（15 分钟）
        created_at: 创建时间
    """

    __tablename__ = "payment_orders"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="订单唯一标识",
    )

    order_no: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="订单号",
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="所属用户 ID",
    )

    amount_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="支付金额（分）",
    )

    points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="获得点数",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        comment="订单状态：pending/paid/expired/refunded",
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        comment="支付时间",
    )

    expire_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="过期时间",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )

    # ---- 关系映射 ----

    user: Mapped["User"] = relationship(
        "User",
        back_populates="payment_orders",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<PaymentOrder(id={self.id}, order_no='{self.order_no}', "
            f"status='{self.status}')>"
        )
