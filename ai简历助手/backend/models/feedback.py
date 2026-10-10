"""
用户反馈模型

定义用户反馈表结构，用于存储用户对优化结果的评分与评论。
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class UserFeedback(Base):
    """用户反馈模型

    存储用户对简历优化结果的评分和文字反馈。

    Attributes:
        id: 反馈唯一标识
        user_id: 提交反馈的用户 ID
        resume_id: 关联的简历 ID
        rating: 评分（1-5 星）
        comment: 文字反馈（可选）
        created_at: 提交时间
    """

    __tablename__ = "user_feedback"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_user_feedback_rating"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="反馈唯一标识",
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="提交反馈的用户 ID",
    )

    resume_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("resumes.id"),
        nullable=False,
        comment="关联的简历 ID",
    )

    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="评分（1-5 星）",
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="文字反馈",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="提交时间",
    )

    # ---- 关系映射 ----

    user: Mapped["User"] = relationship(
        "User",
        back_populates="feedbacks",
        lazy="selectin",
    )

    resume: Mapped["Resume"] = relationship(
        "Resume",
        back_populates="feedbacks",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<UserFeedback(id={self.id}, user_id={self.user_id}, "
            f"resume_id={self.resume_id}, rating={self.rating})>"
        )
