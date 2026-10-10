"""
数据库模型包

导入所有模型以确保它们被注册到 Base.metadata。
"""

from backend.models.feedback import UserFeedback
from backend.models.knowledge import KnowledgeEntry
from backend.models.payment import PaymentOrder, PointTransaction, UserWallet
from backend.models.resume import Resume
from backend.models.user import User

__all__: list[str] = [
    "KnowledgeEntry",
    "PaymentOrder",
    "PointTransaction",
    "Resume",
    "User",
    "UserFeedback",
    "UserWallet",
]
