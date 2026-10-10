"""
数据统计服务

提供仪表盘所需的聚合统计数据。
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.knowledge import KnowledgeEntry
from backend.models.payment import PointTransaction
from backend.models.resume import Resume

logger = logging.getLogger(__name__)


def get_dashboard_stats(db: Session, user_id: int) -> dict:
    """获取用户仪表盘统计数据

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        包含各项统计数据的字典
    """
    # 简历总数
    total_resumes = (
        db.query(func.count(Resume.id))
        .filter(Resume.user_id == user_id)
        .scalar()
    ) or 0

    # 已完成简历数
    completed_resumes = (
        db.query(func.count(Resume.id))
        .filter(Resume.user_id == user_id, Resume.status == "completed")
        .scalar()
    ) or 0

    # 平均优化分数
    avg_score = (
        db.query(func.avg(Resume.optimization_score))
        .filter(
            Resume.user_id == user_id,
            Resume.optimization_score.isnot(None),
        )
        .scalar()
    )

    # 最高优化分数
    max_score = (
        db.query(func.max(Resume.optimization_score))
        .filter(
            Resume.user_id == user_id,
            Resume.optimization_score.isnot(None),
        )
        .scalar()
    )

    # 知识库贡献数（来源为 auto_extract 且关联用户简历）
    knowledge_contributed = (
        db.query(func.count(KnowledgeEntry.id))
        .join(Resume, KnowledgeEntry.resume_id == Resume.id)
        .filter(Resume.user_id == user_id)
        .scalar()
    ) or 0

    # 最近 7 天优化次数
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_optimizations = (
        db.query(func.count(Resume.id))
        .filter(
            Resume.user_id == user_id,
            Resume.status == "completed",
            Resume.created_at >= seven_days_ago,
        )
        .scalar()
    ) or 0

    # 累计消费点数
    total_consumed = (
        db.query(func.sum(func.abs(PointTransaction.amount)))
        .filter(
            PointTransaction.user_id == user_id,
            PointTransaction.type == "consume",
        )
        .scalar()
    ) or 0

    # 最近 5 份简历（用于趋势展示）
    recent_resumes = (
        db.query(Resume.id, Resume.title, Resume.optimization_score, Resume.created_at)
        .filter(Resume.user_id == user_id, Resume.status == "completed")
        .order_by(Resume.created_at.desc())
        .limit(5)
        .all()
    )

    recent_list = [
        {
            "id": r.id,
            "title": r.title,
            "score": r.optimization_score,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recent_resumes
    ]

    return {
        "total_resumes": total_resumes,
        "completed_resumes": completed_resumes,
        "avg_score": round(avg_score, 1) if avg_score else None,
        "max_score": round(max_score, 1) if max_score else None,
        "knowledge_contributed": knowledge_contributed,
        "recent_optimizations_7d": recent_optimizations,
        "total_points_consumed": total_consumed,
        "recent_resumes": recent_list,
    }
