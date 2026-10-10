"""
简历模型

定义简历表结构，用于存储用户上传的简历及优化结果。
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Resume(Base):
    """简历模型

    存储用户简历的原始内容、优化结果及元信息。
    支持版本追踪（parent_id 关联原始简历）。

    Attributes:
        id: 简历唯一标识
        user_id: 所属用户 ID
        title: 简历标题，如"张三_前端工程师_20260528"
        original_text: 原始简历文本
        optimized_text: 优化后的 HTML
        target_city: 目标城市
        target_salary: 期望薪资
        target_jd: 目标岗位 JD
        extra_details: 补充细节
        model_used: 使用的模型名称
        status: 处理状态（pending/processing/completed/failed）
        version: 版本号，同一简历多次优化递增
        parent_id: 关联原始简历 ID（用于版本追踪）
        optimization_score: AI 评估的优化分数 (0-100)
        created_at: 创建时间
    """

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="简历唯一标识",
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="所属用户 ID",
    )

    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="简历标题",
    )

    original_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="原始简历文本",
    )

    optimized_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="优化后的 HTML",
    )

    target_city: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        comment="目标城市",
    )

    target_salary: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        comment="期望薪资",
    )

    target_jd: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="目标岗位 JD",
    )

    extra_details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="补充细节",
    )

    model_used: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        comment="使用的模型",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="处理状态：pending/processing/completed/failed",
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="版本号",
    )

    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("resumes.id"),
        nullable=True,
        default=None,
        comment="关联原始简历 ID（版本追踪）",
    )

    tags: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="标签（JSON 数组字符串）",
    )

    optimization_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        default=None,
        comment="AI 优化分数 (0-100)",
    )

    star_rewrites: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="STAR 原则重写段落数",
    )

    quantifications: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="补充的量化数据个数",
    )

    keywords_matched: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="匹配的 JD 关键词数量",
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
        back_populates="resumes",
        lazy="selectin",
    )

    parent: Mapped["Resume | None"] = relationship(
        "Resume",
        remote_side="Resume.id",
        back_populates="children",
        lazy="selectin",
    )

    children: Mapped[list["Resume"]] = relationship(
        "Resume",
        back_populates="parent",
        lazy="selectin",
    )

    knowledge_entries: Mapped[list["KnowledgeEntry"]] = relationship(
        "KnowledgeEntry",
        back_populates="resume",
        lazy="selectin",
    )

    feedbacks: Mapped[list["UserFeedback"]] = relationship(
        "UserFeedback",
        back_populates="resume",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Resume(id={self.id}, title='{self.title}', "
            f"status='{self.status}', version={self.version})>"
        )

    # 数据库索引：提升查询性能
    __table_args__ = (
        Index("idx_resume_user_id", "user_id"),  # 按用户查询简历
        Index("idx_resume_status", "status"),  # 按状态筛选
        Index("idx_resume_created_at", "created_at"),  # 按时间排序
    )
