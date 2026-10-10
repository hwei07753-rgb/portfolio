"""
数据统计路由

提供仪表盘数据聚合 API。
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.user import User
from backend.services.stats_service import get_dashboard_stats
from backend.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stats", tags=["数据统计"])


class RecentResume(BaseModel):
    """最近简历摘要"""

    id: int
    title: str
    score: float | None = None
    created_at: str | None = None


class DashboardResponse(BaseModel):
    """仪表盘统计响应"""

    total_resumes: int
    completed_resumes: int
    avg_score: float | None = None
    max_score: float | None = None
    knowledge_contributed: int
    recent_optimizations_7d: int
    total_points_consumed: int
    recent_resumes: list[RecentResume]


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="获取仪表盘统计",
    description="获取当前用户的简历优化统计数据。",
)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    """GET /api/stats/dashboard

    返回当前用户的仪表盘统计数据，包括：
    - 简历总数 / 已完成数
    - 平均优化分数 / 最高分
    - 知识库贡献数
    - 最近 7 天优化次数
    - 累计消费点数
    - 最近 5 份简历摘要

    请求头:
        Authorization: Bearer <token>

    响应 (200):
        DashboardResponse: 各项统计数据
    """
    stats = get_dashboard_stats(db, current_user.id)
    return DashboardResponse(**stats)
