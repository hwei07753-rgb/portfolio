"""
简历路由模块

提供简历上传、查询、更新、删除、版本历史、用户反馈等 RESTful API 端点。
"""

import json
import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fastapi.responses import StreamingResponse

from backend.database import get_db
from backend.models.feedback import UserFeedback
from backend.models.resume import Resume
from backend.models.user import User
from backend.schemas.resume import (
    FeedbackCreate,
    FeedbackResponse,
    ResumeListResponse,
    ResumeResponse,
    ResumeUpdate,
)
from backend.services.docx_service import html_to_docx
from backend.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resume", tags=["简历"])

# 允许的图片类型
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _get_resume_or_404(
    resume_id: int,
    user_id: int,
    db: Session,
) -> Resume:
    """获取简历并验证所有权

    Args:
        resume_id: 简历 ID
        user_id: 当前用户 ID
        db: 数据库会话

    Returns:
        Resume ORM 对象

    Raises:
        HTTPException: 简历不存在或无权访问时抛出 404
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if resume is None or resume.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="简历不存在或无权访问",
        )
    return resume


# ---------------------------------------------------------------------------
# 简历端点
# ---------------------------------------------------------------------------


@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传简历",
    description="上传简历内容，支持 JSON 文本或图片文件（OCR 识别）。",
)
async def upload_resume(
    # JSON 文本模式参数
    title: Optional[str] = Form(None, max_length=100, description="简历标题"),
    original_text: Optional[str] = Form(None, description="原始简历文本"),
    target_city: Optional[str] = Form(None, max_length=50, description="目标城市"),
    target_salary: Optional[str] = Form(None, max_length=50, description="期望薪资"),
    target_jd: Optional[str] = Form(None, description="目标岗位 JD"),
    extra_details: Optional[str] = Form(None, description="补充细节"),
    tags: Optional[str] = Form(None, description="标签（JSON 数组字符串）"),
    # 图片文件
    file: Optional[UploadFile] = File(None, description="简历图片（JPG/PNG）"),
    # 认证
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeResponse:
    """POST /api/resume/upload

    支持两种上传方式：
    1. **multipart/form-data**：上传图片文件，系统自动 OCR 识别文字
    2. **表单字段**：直接提交简历文本

    请求头:
        Authorization: Bearer <token>
        Content-Type: multipart/form-data

    表单字段:
        - title: 简历标题（必填）
        - original_text: 简历文本（与 file 二选一）
        - target_city: 目标城市（选填）
        - target_salary: 期望薪资（选填）
        - target_jd: 目标岗位 JD（选填）
        - extra_details: 补充细节（选填）
        - file: 简历图片文件（与 original_text 二选一）

    响应 (201):
        ResumeResponse: 创建的简历详情

    错误码:
        - 400: 缺少必要参数或文件类型不支持
        - 401: Token 无效
        - 413: 文件过大（>10MB）
    """
    # 验证至少提供了一种简历内容来源
    if not file and not original_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供简历文本或上传图片文件",
        )

    # 验证标题
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供简历标题",
        )

    resume_text = original_text

    # 处理图片上传
    if file:
        # 验证文件类型
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="仅支持 JPG 和 PNG 格式的图片",
            )

        # 读取文件内容
        file_content = await file.read()

        # 验证文件大小
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="文件大小不能超过 10MB",
            )

        # TODO: 调用 OCR 服务识别文字
        # 目前先返回占位文本，待 OCR 服务实现后替换
        logger.info(f"收到图片文件: {file.filename}, 类型: {file.content_type}, 大小: {len(file_content)} bytes")
        resume_text = original_text or "[图片 OCR 识别结果将在此显示]"

    # 解析标签
    tags_json = None
    if tags:
        try:
            tags_list = json.loads(tags)
            if isinstance(tags_list, list):
                tags_json = json.dumps(tags_list, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            pass

    # 创建简历记录
    resume = Resume(
        user_id=current_user.id,
        title=title,
        original_text=resume_text,
        target_city=target_city,
        target_salary=target_salary,
        target_jd=target_jd,
        extra_details=extra_details,
        tags=tags_json,
        status="pending",
        version=1,
    )

    db.add(resume)

    try:
        db.commit()
        db.refresh(resume)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"创建简历失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建简历失败，请稍后重试",
        )

    logger.info(f"用户 {current_user.id} 上传简历: id={resume.id}, title='{title}'")
    return resume


@router.get(
    "/list",
    response_model=ResumeListResponse,
    summary="获取简历列表",
    description="分页获取当前用户的简历列表，按创建时间倒序排列。",
)
async def list_resumes(
    page: int = 1,
    page_size: int = 10,
    tag: Optional[str] = Query(None, description="按标签筛选"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeListResponse:
    """GET /api/resume/list

    获取当前用户的简历列表，支持分页。

    请求头:
        Authorization: Bearer <token>

    查询参数:
        - page: 页码（默认 1，最小 1）
        - page_size: 每页数量（默认 10，范围 1-200）

    响应 (200):
        ResumeListResponse: total, page, page_size, items

    错误码:
        - 400: 分页参数无效
        - 401: Token 无效
    """
    # 验证分页参数范围
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="页码必须大于 0",
        )
    if page_size < 1 or page_size > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="每页数量必须在 1-200 之间",
        )

    # 计算偏移量
    offset = (page - 1) * page_size

    # 构建基础查询
    query = db.query(Resume).filter(Resume.user_id == current_user.id)

    # 标签过滤
    if tag:
        query = query.filter(Resume.tags.like(f'%"{tag}"%'))

    # 查询总数
    total = query.count()

    # 查询分页数据（按创建时间倒序）
    resumes = (
        query
        .order_by(desc(Resume.created_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return ResumeListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=resumes,
    )


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    summary="获取简历详情",
    description="获取指定简历的详细信息。",
)
async def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeResponse:
    """GET /api/resume/{id}

    获取单个简历的详细信息。

    请求头:
        Authorization: Bearer <token>

    路径参数:
        - id: 简历 ID

    响应 (200):
        ResumeResponse: 简历详情

    错误码:
        - 401: Token 无效
        - 404: 简历不存在或无权访问
    """
    resume = _get_resume_or_404(resume_id, current_user.id, db)
    return resume


@router.put(
    "/{resume_id}",
    response_model=ResumeResponse,
    summary="更新简历",
    description="部分更新简历内容（标题、目标信息等）。",
)
async def update_resume(
    resume_id: int,
    resume_data: ResumeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeResponse:
    """PUT /api/resume/{id}

    部分更新简历内容。仅更新提供的字段，未提供的字段保持不变。

    请求头:
        Authorization: Bearer <token>

    路径参数:
        - id: 简历 ID

    请求体 (JSON，所有字段可选):
        - title: 简历标题
        - original_text: 原始简历文本
        - target_city: 目标城市
        - target_salary: 期望薪资
        - target_jd: 目标岗位 JD
        - extra_details: 补充细节

    响应 (200):
        ResumeResponse: 更新后的简历详情

    错误码:
        - 401: Token 无效
        - 404: 简历不存在或无权访问
    """
    resume = _get_resume_or_404(resume_id, current_user.id, db)

    # 更新提供的字段
    update_data = resume_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "tags" and value is not None:
            # 将标签列表转换为 JSON 字符串存储
            setattr(resume, field, json.dumps(value, ensure_ascii=False))
        else:
            setattr(resume, field, value)

    try:
        db.commit()
        db.refresh(resume)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"更新简历失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新简历失败，请稍后重试",
        )

    logger.info(f"用户 {current_user.id} 更新简历: id={resume_id}, fields={list(update_data.keys())}")
    return resume


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除简历",
    description="删除指定简历及其关联的反馈数据。",
)
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """DELETE /api/resume/{id}

    删除指定简历。如果删除的是原始简历，会同时删除所有关联的子版本。

    请求头:
        Authorization: Bearer <token>

    路径参数:
        - id: 简历 ID

    响应:
        204 No Content

    错误码:
        - 401: Token 无效
        - 404: 简历不存在或无权访问
    """
    resume = _get_resume_or_404(resume_id, current_user.id, db)

    # 收集需要删除的所有简历 ID（包括子版本）
    resume_ids_to_delete = [resume_id]

    # 如果是原始简历，查找所有子版本
    if resume.parent_id is None:
        child_ids = [
            r.id for r in db.query(Resume.id)
            .filter(Resume.parent_id == resume_id)
            .all()
        ]
        resume_ids_to_delete.extend(child_ids)

    try:
        # 删除关联的反馈记录
        db.query(UserFeedback).filter(
            UserFeedback.resume_id.in_(resume_ids_to_delete)
        ).delete(synchronize_session=False)

        # 删除所有关联简历
        db.query(Resume).filter(
            Resume.id.in_(resume_ids_to_delete)
        ).delete(synchronize_session=False)

        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"删除简历失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除简历失败，请稍后重试",
        )

    logger.info(
        f"用户 {current_user.id} 删除简历: id={resume_id}, "
        f"关联删除 {len(resume_ids_to_delete) - 1} 个子版本"
    )


@router.get(
    "/{resume_id}/versions",
    response_model=list[ResumeResponse],
    summary="获取简历版本历史",
    description="获取指定简历的所有版本记录。",
)
async def get_resume_versions(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ResumeResponse]:
    """GET /api/resume/{id}/versions

    获取简历的版本历史。返回同一 parent_id 下的所有版本，
    包括原始版本（parent_id 为 NULL 的初始简历）。

    请求头:
        Authorization: Bearer <token>

    路径参数:
        - id: 简历 ID

    响应 (200):
        ResumeResponse[]: 版本列表，按版本号升序排列

    错误码:
        - 401: Token 无效
        - 404: 简历不存在或无权访问
    """
    # 验证简历存在且属于当前用户
    resume = _get_resume_or_404(resume_id, current_user.id, db)

    # 确定原始简历 ID
    # 如果当前简历有 parent_id，则原始简历是 parent
    # 如果当前简历没有 parent_id，则当前简历就是原始简历
    original_id = resume.parent_id if resume.parent_id else resume.id

    # 查询所有版本（包括原始版本）
    versions = (
        db.query(Resume)
        .filter(
            (Resume.id == original_id) | (Resume.parent_id == original_id),
            Resume.user_id == current_user.id,
        )
        .order_by(Resume.version)
        .all()
    )

    return versions


@router.get(
    "/{resume_id}/export/docx",
    summary="导出 Word 文档",
    description="将优化后的简历导出为 .docx 格式。",
)
async def export_resume_docx(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """GET /api/resume/{id}/export/docx

    将优化后的简历导出为 Word (.docx) 文档。

    请求头:
        Authorization: Bearer <token>

    路径参数:
        - id: 简历 ID

    响应:
        application/vnd.openxmlformats-officedocument.wordprocessingml.document

    错误码:
        - 401: Token 无效
        - 404: 简历不存在或无权访问
        - 400: 简历尚未完成优化
    """
    resume = _get_resume_or_404(resume_id, current_user.id, db)

    if not resume.optimized_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="简历尚未完成优化，无法导出",
        )

    # 生成 DOCX
    docx_buffer = html_to_docx(resume.optimized_text, resume.title)

    # 文件名：简历标题.docx
    from urllib.parse import quote
    safe_title = re.sub(r'[^\w\s\u4e00-\u9fa5\-_.]', '_', resume.title or f"resume_{resume.id}")
    encoded_filename = quote(f"{safe_title}.docx")
    safe_ascii = f"resume_{resume.id}.docx"

    return StreamingResponse(
        docx_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_ascii}"; filename*=UTF-8\'\'{encoded_filename}',
        },
    )


@router.post(
    "/{resume_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="提交优化反馈",
    description="对简历优化结果提交评分和文字反馈。",
)
async def create_feedback(
    resume_id: int,
    feedback_data: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    """POST /api/resume/{id}/feedback

    对简历优化结果提交反馈。每个用户对同一简历只能提交一次反馈。

    请求头:
        Authorization: Bearer <token>

    路径参数:
        - id: 简历 ID

    请求体 (JSON):
        - rating: 评分（1-5 星，必填）
        - comment: 文字反馈（选填，最多 1000 字）

    响应 (201):
        FeedbackResponse: 创建的反馈记录

    错误码:
        - 401: Token 无效
        - 404: 简历不存在或无权访问
        - 409: 已提交过反馈
    """
    # 验证简历存在且属于当前用户
    resume = _get_resume_or_404(resume_id, current_user.id, db)

    # 检查是否已提交过反馈
    existing_feedback = (
        db.query(UserFeedback)
        .filter(
            UserFeedback.user_id == current_user.id,
            UserFeedback.resume_id == resume_id,
        )
        .first()
    )

    if existing_feedback:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="您已对该简历提交过反馈",
        )

    # 创建反馈记录
    feedback = UserFeedback(
        user_id=current_user.id,
        resume_id=resume_id,
        rating=feedback_data.rating,
        comment=feedback_data.comment,
    )

    db.add(feedback)

    try:
        db.commit()
        db.refresh(feedback)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"创建反馈失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="提交反馈失败，请稍后重试",
        )

    logger.info(
        f"用户 {current_user.id} 对简历 {resume_id} 提交反馈: "
        f"rating={feedback_data.rating}"
    )
    return feedback
