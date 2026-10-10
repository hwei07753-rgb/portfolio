"""
知识库路由模块

提供知识库条目的 CRUD、统计、批量导入与导出等 RESTful API 端点。
"""

import io
import json
import logging
import zipfile
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.user import User
from backend.schemas.knowledge import KnowledgeCreate, KnowledgeResponse, KnowledgeUpdate
from backend.services.knowledge_service import (
    KnowledgeServiceError,
    EntryNotFoundError,
    create_entry,
    delete_entry,
    get_entry,
    get_stats,
    list_entries,
    update_entry,
)
from backend.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


# ---------------------------------------------------------------------------
# 查询端点
# ---------------------------------------------------------------------------


@router.get(
    "/list",
    summary="知识库条目列表",
    description="分页获取知识库条目，支持按分类、行业、状态和关键词筛选。",
)
async def get_knowledge_list(
    category: str | None = Query(None, description="分类筛选：industry_practice/resume_template/optimization_case/jd_keyword"),
    industry: str | None = Query(None, description="行业筛选"),
    entry_status: str | None = Query(None, description="状态筛选：active/review_needed/archived"),
    keyword: str | None = Query(None, description="关键词搜索（标题和内容）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """GET /api/knowledge/list

    请求头:
        Authorization: Bearer <token>

    查询参数:
        - category: 分类筛选（可选）
        - industry: 行业筛选（可选）
        - entry_status: 状态筛选（可选）
        - keyword: 关键词搜索（可选）
        - page: 页码，默认 1
        - page_size: 每页数量，默认 20

    响应 (200):
        {total, page, page_size, items: [KnowledgeResponse]}
    """
    result = list_entries(
        db,
        category=category,
        industry=industry,
        status=entry_status,
        keyword=keyword,
        page=page,
        size=page_size,
    )
    # 将 ORM 对象转换为响应模型
    result["items"] = [KnowledgeResponse.model_validate(item) for item in result["items"]]
    return result


@router.get(
    "/stats",
    summary="知识库统计",
    description="获取知识库的统计信息：总条数、按分类/状态计数、最常用条目。",
)
async def get_knowledge_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """GET /api/knowledge/stats

    请求头:
        Authorization: Bearer <token>

    响应 (200):
        {total, by_category, by_status, top_used}
    """
    return get_stats(db)


# ---------------------------------------------------------------------------
# 批量导入 / 导出（必须在 /{entry_id} 之前定义，否则路径冲突）
# ---------------------------------------------------------------------------


@router.post(
    "/import",
    summary="批量导入知识条目",
    description="上传 JSON 文件批量导入知识库条目。JSON 文件内容为数组，每个元素包含 category、title、content、tags 字段。",
)
async def import_knowledge(
    file: UploadFile = File(..., description="JSON 文件"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """POST /api/knowledge/import

    请求头:
        Authorization: Bearer <token>

    请求体:
        multipart/form-data，file 字段为 JSON 文件

    JSON 文件格式:
        [
            {"category": "jd_keyword", "title": "React 关键词", "content": "...", "tags": ["前端"]},
            ...
        ]

    响应 (200):
        {imported: 成功数, failed: 失败数, errors: [错误信息]}
    """
    # 校验文件类型
    if not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 JSON 文件格式",
        )

    try:
        content = await file.read()
        entries_data = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"JSON 文件解析失败: {str(e)}",
        )

    if not isinstance(entries_data, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JSON 文件内容应为数组",
        )

    imported = 0
    errors = []

    for idx, item in enumerate(entries_data):
        try:
            entry_data = KnowledgeCreate(**item)
            create_entry(db, entry_data, source="manual")
            imported += 1
        except Exception as e:
            errors.append(f"第 {idx + 1} 条: {str(e)}")

    logger.info(f"批量导入知识条目: 成功 {imported}, 失败 {len(errors)}")
    return {
        "imported": imported,
        "failed": len(errors),
        "errors": errors,
    }


@router.get(
    "/export",
    summary="导出知识库",
    description="将全部知识库条目导出为 JSON 文件（ZIP 压缩包）。",
)
async def export_knowledge(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """GET /api/knowledge/export

    请求头:
        Authorization: Bearer <token>

    响应:
        application/zip，包含 knowledge_export.json
    """
    # 查询全部条目
    from backend.models.knowledge import KnowledgeEntry

    entries = db.query(KnowledgeEntry).order_by(KnowledgeEntry.category, KnowledgeEntry.id).all()

    # 构建导出数据
    export_data = []
    for entry in entries:
        tags = None
        if entry.tags:
            try:
                tags = json.loads(entry.tags)
            except json.JSONDecodeError:
                tags = None

        export_data.append({
            "id": entry.id,
            "category": entry.category,
            "title": entry.title,
            "content": entry.content,
            "source": entry.source,
            "industry": entry.industry,
            "job_title": entry.job_title,
            "tags": tags,
            "status": entry.status,
            "usage_count": entry.usage_count,
            "effectiveness": entry.effectiveness,
        })

    # 生成 ZIP 文件（内存中）
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "knowledge_export.json",
            json.dumps(export_data, ensure_ascii=False, indent=2),
        )
    zip_buffer.seek(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"knowledge_export_{timestamp}.zip"

    logger.info(f"导出知识库: {len(export_data)} 条")
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# 单条操作（/{entry_id} 路由放在最后，避免与 /import、/export 冲突）
# ---------------------------------------------------------------------------


@router.get(
    "/{entry_id}",
    response_model=KnowledgeResponse,
    summary="知识条目详情",
    description="获取单条知识库条目的完整信息。",
)
async def get_knowledge_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeResponse:
    """GET /api/knowledge/{id}

    请求头:
        Authorization: Bearer <token>

    响应 (200):
        KnowledgeResponse

    错误码:
        - 404: 知识条目不存在
    """
    try:
        entry = get_entry(db, entry_id)
        return KnowledgeResponse.model_validate(entry)
    except EntryNotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# ---------------------------------------------------------------------------
# 写入端点
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=KnowledgeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="添加知识条目",
    description="手动添加一条知识库条目。",
)
async def create_knowledge_entry(
    entry_data: KnowledgeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeResponse:
    """POST /api/knowledge

    请求头:
        Authorization: Bearer <token>

    请求体 (JSON):
        - category: 分类
        - title: 标题
        - content: 内容（Markdown）
        - tags: 标签列表（可选）

    响应 (201):
        KnowledgeResponse
    """
    entry = create_entry(db, entry_data, source="manual")
    return KnowledgeResponse.model_validate(entry)


@router.put(
    "/{entry_id}",
    response_model=KnowledgeResponse,
    summary="更新知识条目",
    description="部分更新知识库条目（所有字段可选）。",
)
async def update_knowledge_entry(
    entry_id: int,
    entry_data: KnowledgeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeResponse:
    """PUT /api/knowledge/{id}

    请求头:
        Authorization: Bearer <token>

    请求体 (JSON，所有字段可选):
        - category, title, content, tags, industry, job_title, status

    响应 (200):
        KnowledgeResponse

    错误码:
        - 404: 知识条目不存在
    """
    try:
        entry = update_entry(
            db,
            entry_id,
            title=entry_data.title,
            content=entry_data.content,
            category=entry_data.category,
            industry=entry_data.industry,
            job_title=entry_data.job_title,
            tags=entry_data.tags,
            status=entry_data.status,
        )
        return KnowledgeResponse.model_validate(entry)
    except EntryNotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除知识条目",
    description="删除指定的知识库条目。",
)
async def delete_knowledge_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """DELETE /api/knowledge/{id}

    请求头:
        Authorization: Bearer <token>

    响应:
        204 No Content

    错误码:
        - 404: 知识条目不存在
    """
    try:
        delete_entry(db, entry_id)
    except EntryNotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
