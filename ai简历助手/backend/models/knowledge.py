"""
知识库模型

定义知识库条目表结构，用于存储简历优化过程中积累的可复用知识点。
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class KnowledgeEntry(Base):
    """知识库条目模型

    存储从简历优化中提取的可复用知识，包括行业最佳实践、
    JD 关键词、优化模式和量化描述案例等。

    Attributes:
        id: 条目唯一标识
        category: 分类（industry_practice/resume_template/optimization_case/jd_keyword）
        title: 知识标题
        content: 知识内容（Markdown 格式）
        source: 来源（system/manual/auto_extract）
        resume_id: 关联的简历 ID（auto_extract 时有值）
        industry: 行业标签
        job_title: 岗位标签
        tags: 额外标签（JSON 数组字符串）
        status: 状态（active/review_needed/archived）
        usage_count: 被引用次数
        effectiveness: 效果评分（基于用户反馈）
        created_at: 创建时间
        updated_at: 最后更新时间（自动刷新）
    """

    __tablename__ = "knowledge_entries"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="条目唯一标识",
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="分类：industry_practice/resume_template/optimization_case/jd_keyword",
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="知识标题",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="知识内容（Markdown 格式）",
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="system",
        server_default="system",
        comment="来源：system/manual/auto_extract",
    )

    resume_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("resumes.id"),
        nullable=True,
        default=None,
        comment="关联的简历 ID（auto_extract 时有值）",
    )

    industry: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        comment="行业标签",
    )

    job_title: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        comment="岗位标签",
    )

    tags: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="额外标签（JSON 数组字符串）",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
        comment="状态：active/review_needed/archived",
    )

    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="被引用次数",
    )

    effectiveness: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0.0",
        comment="效果评分（基于用户反馈）",
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

    resume: Mapped["Resume | None"] = relationship(
        "Resume",
        back_populates="knowledge_entries",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<KnowledgeEntry(id={self.id}, category='{self.category}', "
            f"title='{self.title}', status='{self.status}')>"
        )

    # 数据库索引：提升查询性能
    __table_args__ = (
        Index("idx_knowledge_category", "category"),  # 按分类筛选
        Index("idx_knowledge_status", "status"),  # 按状态筛选
        Index("idx_knowledge_industry", "industry"),  # 按行业筛选
        Index("idx_knowledge_resume_id", "resume_id"),  # 按关联简历查询
    )
