"""
知识库服务模块

处理知识库条目的 CRUD 操作和查询逻辑。
"""

import json
import logging
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.models.knowledge import KnowledgeEntry
from backend.schemas.knowledge import KnowledgeCreate, KnowledgeResponse

logger = logging.getLogger(__name__)


class KnowledgeServiceError(Exception):
    """知识库服务异常基类"""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class EntryNotFoundError(KnowledgeServiceError):
    """知识条目不存在"""

    def __init__(self):
        super().__init__("知识条目不存在", status_code=404)


def list_entries(
    db: Session,
    category: Optional[str] = None,
    industry: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    size: int = 20,
) -> dict:
    """分页查询知识库条目

    Args:
        db: 数据库会话
        category: 分类筛选
        industry: 行业筛选
        status: 状态筛选
        keyword: 关键词搜索（标题和内容）
        page: 页码（从 1 开始）
        size: 每页数量

    Returns:
        dict 包含:
        - total: 总数
        - page: 当前页码
        - page_size: 每页数量
        - items: 条目列表
    """
    query = db.query(KnowledgeEntry)

    # 应用筛选条件
    if category:
        query = query.filter(KnowledgeEntry.category == category)

    if industry:
        query = query.filter(KnowledgeEntry.industry == industry)

    if status:
        query = query.filter(KnowledgeEntry.status == status)

    if keyword:
        search_pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                KnowledgeEntry.title.ilike(search_pattern),
                KnowledgeEntry.content.ilike(search_pattern),
            )
        )

    # 获取总数
    total = query.count()

    # 分页查询
    items = (
        query.order_by(KnowledgeEntry.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": size,
        "items": items,
    }


def get_entry(db: Session, entry_id: int) -> KnowledgeEntry:
    """获取单条知识库条目

    Args:
        db: 数据库会话
        entry_id: 条目 ID

    Returns:
        KnowledgeEntry ORM 对象

    Raises:
        EntryNotFoundError: 条目不存在
    """
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise EntryNotFoundError()
    return entry


def create_entry(
    db: Session,
    entry_data: KnowledgeCreate,
    source: str = "manual",
    auto_commit: bool = True,
) -> KnowledgeEntry:
    """创建知识库条目

    Args:
        db: 数据库会话
        entry_data: 创建请求数据
        source: 来源（manual/system/auto_extract）
        auto_commit: 是否自动提交事务（默认 True）
            - 独立调用时使用 True（如 API 路由）
            - 作为大事务的一部分时使用 False（如 optimize 流程）

    Returns:
        创建的 KnowledgeEntry 对象
    """
    # 处理 tags 字段
    tags_json = None
    if entry_data.tags:
        tags_json = json.dumps(entry_data.tags, ensure_ascii=False)

    entry = KnowledgeEntry(
        category=entry_data.category,
        title=entry_data.title,
        content=entry_data.content,
        tags=tags_json,
        source=source,
        status="active",
    )
    db.add(entry)

    if auto_commit:
        db.commit()
    else:
        db.flush()  # 只 flush 获取 ID，不提交，由外层事务统一提交

    db.refresh(entry)

    logger.info(f"创建知识条目: ID={entry.id}, 标题={entry.title}")
    return entry


def update_entry(
    db: Session,
    entry_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    category: Optional[str] = None,
    industry: Optional[str] = None,
    job_title: Optional[str] = None,
    tags: Optional[list[str]] = None,
    status: Optional[str] = None,
    auto_commit: bool = True,
) -> KnowledgeEntry:
    """更新知识库条目

    Args:
        db: 数据库会话
        entry_id: 条目 ID
        title: 新标题
        content: 新内容
        category: 新分类
        industry: 新行业
        job_title: 新岗位
        tags: 新标签列表
        status: 新状态
        auto_commit: 是否自动提交事务（默认 True）

    Returns:
        更新后的 KnowledgeEntry 对象
    """
    entry = get_entry(db, entry_id)

    if title is not None:
        entry.title = title
    if content is not None:
        entry.content = content
    if category is not None:
        entry.category = category
    if industry is not None:
        entry.industry = industry
    if job_title is not None:
        entry.job_title = job_title
    if tags is not None:
        entry.tags = json.dumps(tags, ensure_ascii=False)
    if status is not None:
        entry.status = status

    if auto_commit:
        db.commit()
    else:
        db.flush()

    db.refresh(entry)

    logger.info(f"更新知识条目: ID={entry.id}")
    return entry


def delete_entry(db: Session, entry_id: int, auto_commit: bool = True) -> None:
    """删除知识库条目

    Args:
        db: 数据库会话
        entry_id: 条目 ID
        auto_commit: 是否自动提交事务（默认 True）
    """
    entry = get_entry(db, entry_id)
    db.delete(entry)

    if auto_commit:
        db.commit()
    else:
        db.flush()

    logger.info(f"删除知识条目: ID={entry_id}")


def update_usage_count(db: Session, entry_id: int, auto_commit: bool = True) -> None:
    """更新知识条目使用次数

    在知识条目被引用时调用，增加使用计数。

    Args:
        db: 数据库会话
        entry_id: 条目 ID
        auto_commit: 是否自动提交事务（默认 True）
    """
    entry = get_entry(db, entry_id)
    entry.usage_count += 1

    if auto_commit:
        db.commit()
    else:
        db.flush()

    logger.debug(f"更新知识条目使用次数: ID={entry_id}, count={entry.usage_count}")


def get_stats(db: Session) -> dict:
    """获取知识库统计信息

    Args:
        db: 数据库会话

    Returns:
        dict 包含:
        - total: 总条目数
        - by_category: 按分类统计
        - by_status: 按状态统计
        - top_used: 使用最多的条目
    """
    total = db.query(KnowledgeEntry).count()

    # 按分类统计
    category_stats = {}
    for category in ["industry_practice", "resume_template", "optimization_case", "jd_keyword"]:
        count = (
            db.query(KnowledgeEntry)
            .filter(KnowledgeEntry.category == category)
            .count()
        )
        category_stats[category] = count

    # 按状态统计
    status_stats = {}
    for status_val in ["active", "review_needed", "archived"]:
        count = (
            db.query(KnowledgeEntry)
            .filter(KnowledgeEntry.status == status_val)
            .count()
        )
        status_stats[status_val] = count

    # 使用最多的条目
    top_used = (
        db.query(KnowledgeEntry)
        .filter(KnowledgeEntry.status == "active")
        .order_by(KnowledgeEntry.usage_count.desc())
        .limit(5)
        .all()
    )

    return {
        "total": total,
        "by_category": category_stats,
        "by_status": status_stats,
        "top_used": [
            {"id": e.id, "title": e.title, "usage_count": e.usage_count}
            for e in top_used
        ],
    }
