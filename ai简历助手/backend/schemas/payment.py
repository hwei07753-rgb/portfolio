"""
支付与点数相关 Schema

定义钱包、点数流水、充值订单的响应模型。
字段严格对应 CLAUDE.md 中的接口规范。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WalletResponse(BaseModel):
    """用户钱包信息响应模型"""

    model_config = ConfigDict(from_attributes=True)

    balance: int = 0
    total_recharged: int = 0
    total_consumed: int = 0


class TransactionResponse(BaseModel):
    """点数流水记录响应模型"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: int
    balance_after: int
    type: str
    description: str | None = None
    created_at: datetime


class OrderResponse(BaseModel):
    """充值订单响应模型"""

    model_config = ConfigDict(from_attributes=True)

    order_no: str
    amount_cents: int
    points: int
    status: str = "pending"
    created_at: datetime
    expire_at: datetime
