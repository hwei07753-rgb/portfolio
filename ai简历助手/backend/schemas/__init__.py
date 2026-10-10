"""
Pydantic 请求/响应模型

集中导出所有 Schema，方便路由层直接 from backend.schemas import xxx。
"""

from .auth import UserCreate, UserLogin, UserResponse, TokenResponse
from .resume import (
    FeedbackCreate,
    FeedbackResponse,
    ResumeCreate,
    ResumeListResponse,
    ResumeResponse,
    ResumeUpdate,
)
from .knowledge import KnowledgeCreate, KnowledgeResponse, KnowledgeUpdate
from .payment import WalletResponse, TransactionResponse, OrderResponse

__all__ = [
    # Auth
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    # Resume
    "ResumeCreate",
    "ResumeUpdate",
    "ResumeResponse",
    "ResumeListResponse",
    "FeedbackCreate",
    "FeedbackResponse",
    # Knowledge
    "KnowledgeCreate",
    "KnowledgeResponse",
    "KnowledgeUpdate",
    # Payment
    "WalletResponse",
    "TransactionResponse",
    "OrderResponse",
]
