"""
岗位搜索路由模块

提供按关键词搜索目标岗位 JD 的 RESTful API 端点。
"""

import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.models.user import User
from backend.services.job_search_service import search_jobs
from backend.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["岗位搜索"])


# ---------------------------------------------------------------------------
# 响应模型
# ---------------------------------------------------------------------------


class JobItemResponse(BaseModel):
    """单条岗位信息"""

    title: str
    company: str
    location: str
    salary: str
    description: str


class JobSearchResponse(BaseModel):
    """岗位搜索响应"""

    items: list[JobItemResponse]
    total: int


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------


@router.get(
    "/search",
    response_model=JobSearchResponse,
    summary="搜索岗位",
    description="根据关键词搜索目标岗位 JD，返回匹配的岗位列表。",
)
async def search(
    query: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=50, description="最大返回条数"),
    current_user: User = Depends(get_current_user),
) -> JobSearchResponse:
    """GET /api/jobs/search?query=前端工程师&limit=20

    在内置岗位库中搜索匹配的岗位，返回标题、公司、地点、薪资和 JD 描述。
    """
    logger.info("用户 %s 搜索岗位: query=%s", current_user.username, query)
    items = search_jobs(query, limit=limit)
    return JobSearchResponse(items=items, total=len(items))
