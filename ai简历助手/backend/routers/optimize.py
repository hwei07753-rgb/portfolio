"""
简历优化路由模块

提供简历优化、AI 预检、对话微调等 API 端点。
"""

import json as _json
import logging
import re as _re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.resume import Resume
from backend.models.user import User
from backend.schemas.resume import ResumeCreate
from backend.services.llm_service import LLMServiceError, get_llm_service
from backend.services.ocr_service import get_ocr_service, OCRError
from backend.services.optimize_service import OptimizeServiceError, optimize
from backend.services.payment_service import InsufficientPointsError
from backend.utils.security import get_current_user
from backend.utils.text_cleaner import sanitize_html

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/optimize", tags=["优化"])

# 允许的图片类型
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# 对话微调限制
MAX_CHAT_ROUNDS = 10
CHAT_VALIDITY_HOURS = 24


# ---------------------------------------------------------------------------
# 请求/响应 Schema
# ---------------------------------------------------------------------------


class OptimizeResponse(BaseModel):
    """简历优化响应模型"""

    resume_id: int
    optimized_html: str
    optimization_score: float | None = None
    changes_summary: list[str]
    pros: list[str] = []
    cons: list[str] = []
    star_rewrites: int = 0
    quantifications: int = 0
    keywords_matched: int = 0
    knowledge_extracted: int


class ChatMessage(BaseModel):
    """对话消息"""

    role: str = Field(..., pattern=r"^(user|assistant)$", description="角色")
    content: str = Field(..., description="消息内容")


class CheckRequest(BaseModel):
    """AI 预检请求模型"""

    model_config = ConfigDict(str_strip_whitespace=True)

    city: str | None = Field(None, max_length=50, description="目标城市")
    salary: str | None = Field(None, max_length=50, description="期望薪资")
    jd: str | None = Field(None, description="目标岗位 JD")
    details: str | None = Field(None, description="补充信息")
    resume_text: str | None = Field(None, description="简历文本（用于上下文）")
    message: str | None = Field(None, max_length=2000, description="用户消息（多轮对话）")
    history: list[ChatMessage] = Field(default_factory=list, description="对话历史")


class CheckResponse(BaseModel):
    """AI 预检响应模型"""

    suggestions: str


class ChatRequest(BaseModel):
    """对话微调请求模型"""

    model_config = ConfigDict(str_strip_whitespace=True)

    resume_id: int = Field(..., description="简历 ID")
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    history: list[ChatMessage] = Field(default_factory=list, description="对话历史")


class ChatResponse(BaseModel):
    """对话微调响应模型"""

    reply: str
    rounds_used: int
    rounds_remaining: int
    optimized_text: str | None = None


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=OptimizeResponse,
    status_code=status.HTTP_200_OK,
    summary="简历优化",
    description="提交简历进行 AI 优化，消耗 1 点。",
)
async def optimize_resume(
    # 表单字段
    text: str | None = Form(None, description="简历文本"),
    city: str | None = Form(None, description="目标城市"),
    salary: str | None = Form(None, description="期望薪资"),
    jd: str | None = Form(None, description="目标岗位 JD"),
    details: str | None = Form(None, description="补充信息"),
    strength: int | None = Form(None, ge=1, le=5, description="优化强度 (1-5)"),
    # 图片文件
    file: UploadFile | None = File(None, description="简历图片（JPG/PNG）"),
    # 认证
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OptimizeResponse:
    """POST /api/optimize

    提交简历进行 AI 优化。支持文本或图片输入，消耗 1 点。

    请求头:
        Authorization: Bearer <token>
        Content-Type: multipart/form-data

    表单字段:
        - text: 简历文本（与 file 二选一）
        - city: 目标城市（选填）
        - salary: 期望薪资（选填）
        - jd: 目标岗位 JD（选填）
        - details: 补充信息（选填）
        - file: 简历图片文件（与 text 二选一）

    响应 (200):
        OptimizeResponse: 优化结果

    错误码:
        - 400: 缺少必要参数
        - 401: Token 无效
        - 402: 点数不足
        - 413: 文件过大
        - 500: 优化失败
    """
    logger.info(
        f"收到优化请求: user_id={current_user.id}, "
        f"has_text={bool(text)}, has_file={bool(file)}, "
        f"city={city}, strength={strength}"
    )

    # 验证至少提供了一种简历内容来源
    if not file and not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供简历文本或上传图片文件",
        )

    resume_text = text or ""

    # 处理图片上传
    if file:
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="仅支持 JPG 和 PNG 格式的图片",
            )

        file_content = await file.read()

        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="文件大小不能超过 10MB",
            )

        # 调用 OCR 服务识别图片文字
        logger.info(
            f"收到图片文件: {file.filename}, "
            f"类型: {file.content_type}, 大小: {len(file_content)} bytes"
        )

        try:
            ocr_service = get_ocr_service()
            ocr_text = await ocr_service.recognize_text(
                image_data=file_content,
                content_type=file.content_type,
            )
            logger.info(f"OCR 识别成功，识别文字长度: {len(ocr_text)} 字符")
            resume_text = ocr_text
        except OCRError as e:
            logger.error(f"OCR 识别失败: {e.message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"图片识别失败: {e.message}",
            )

    # 生成简历标题
    now_str = datetime.now().strftime("%Y%m%d%H%M%S")
    title = f"{current_user.username}_{now_str}"

    # 构造简历创建数据
    resume_data = ResumeCreate(
        title=title,
        original_text=resume_text,
        target_city=city,
        target_salary=salary,
        target_jd=jd,
        extra_details=details,
    )

    try:
        result = await optimize(
            db=db,
            user_id=current_user.id,
            resume_data=resume_data,
            strength=strength or 3,
        )
        return OptimizeResponse(**result)

    except InsufficientPointsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"点数不足，当前余额: {e.balance}。请先充值后再试。",
        )

    except OptimizeServiceError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )

    except LLMServiceError as e:
        logger.error(f"LLM 服务异常: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI 服务暂时不可用，请稍后重试: {e.message}",
        )


@router.post(
    "/check",
    response_model=CheckResponse,
    summary="AI 预检",
    description="检查求职信息的合理性，返回优化建议。支持图片上传（自动 OCR 识别）。",
)
async def check_info(
    # 表单字段
    city: str | None = Form(None, description="目标城市"),
    salary: str | None = Form(None, description="期望薪资"),
    jd: str | None = Form(None, description="目标岗位 JD"),
    details: str | None = Form(None, description="补充信息"),
    resume_text: str | None = Form(None, description="简历文本"),
    message: str | None = Form(None, description="用户消息（多轮对话）"),
    history: str | None = Form(None, description="对话历史（JSON 字符串）"),
    # 图片文件
    file: UploadFile | None = File(None, description="简历图片（JPG/PNG）"),
    # 认证
    current_user: User = Depends(get_current_user),
) -> CheckResponse:
    """POST /api/optimize/check

    AI 预检：检查用户填写的求职信息是否合理，返回优化建议。
    支持图片上传，自动 OCR 识别简历内容。

    请求头:
        Authorization: Bearer <token>

    请求体 (multipart/form-data):
        - city: 目标城市（选填）
        - salary: 期望薪资（选填）
        - jd: 目标岗位 JD（选填）
        - details: 补充信息（选填）
        - resume_text: 简历文本（选填）
        - file: 简历图片（选填，与 resume_text 二选一）
        - message: 用户消息（选填，多轮对话用）
        - history: 对话历史 JSON（选填）

    响应 (200):
        CheckResponse: AI 预检建议

    错误码:
        - 401: Token 无效
        - 500: AI 服务异常
    """
    # 解析对话历史
    parsed_history: list[ChatMessage] = []
    if history:
        try:
            history_list = _json.loads(history)
            parsed_history = [ChatMessage(**msg) for msg in history_list]
        except Exception:
            pass  # 忽略解析错误

    # 如果有上传图片但没有文本，先做 OCR
    ocr_text = resume_text or ""
    ocr_failed = False
    ocr_error_msg = ""
    if file and not ocr_text:
        try:
            ocr_service = get_ocr_service()
            image_data = await file.read()
            content_type = file.content_type or "image/jpeg"
            ocr_text = await ocr_service.recognize_text(image_data, content_type)
            logger.info(f"预检 OCR 识别完成，提取 {len(ocr_text)} 字符")
        except OCRError as e:
            logger.warning(f"预检 OCR 失败: {e.message}")
            ocr_failed = True
            ocr_error_msg = e.message
            # OCR 失败不阻断预检，继续用其他信息

    # 构建预检提示词
    parts = []
    if city:
        parts.append(f"目标城市：{city}")
    if salary:
        parts.append(f"期望薪资：{salary}")
    if jd:
        parts.append(f"目标岗位 JD：{jd}")
    if details:
        parts.append(f"补充信息：{details}")
    if ocr_text:
        parts.append(f"简历内容：{ocr_text[:2000]}")
    elif ocr_failed:
        # OCR 失败时，告知 AI 用户上传了图片但识别失败
        parts.append(f"[系统提示：用户上传了简历图片，但图片文字识别失败（{ocr_error_msg}）。请告知用户图片识别失败，建议用户直接粘贴简历文本内容。]")

    # 如果没有任何上下文信息且没有用户消息，才报错
    if not parts and not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请至少提供一项求职信息进行检查",
        )

    context_info = "\n".join(parts)

    system_prompt = """你是一位资深职业顾问，擅长分析简历和求职信息的合理性。

根据用户提供的信息，从以下维度进行分析（仅分析有信息的维度，跳过无数据的维度）：

1. **简历内容分析**（有简历内容时）：
   - 简历结构是否完整（个人信息、教育背景、工作/项目经历、技能）
   - 工作/项目经历描述是否使用 STAR 原则
   - 是否有量化数据（数字、百分比、金额）
   - 技能描述是否清晰具体
   - 排版和格式是否规范

2. **薪资合理性**（有薪资和城市/行业信息时）：结合城市、行业、经验水平，判断期望薪资是否合理
3. **城市匹配**（有城市和岗位信息时）：目标城市是否有足够的该岗位机会
4. **岗位匹配**（有 JD 和简历时）：JD 与用户描述的经验/技能是否匹配
5. **信息完整性**：是否缺少关键信息（如联系方式、教育背景、工作经历等）
6. **经验匹配**（有 JD 和工作年限时）：工作年限与岗位要求是否匹配
7. **学历匹配**（有学历和岗位要求时）：学历是否满足岗位要求

如果用户只上传了简历文件，重点分析简历本身的优缺点，给出具体的改进建议。

请用简洁、专业的语言给出建议，分为"需要改进"和"建议补充"两部分。"""

    try:
        llm_service = get_llm_service()

        # 构建对话历史
        conversation_history = [
            {"role": msg.role, "content": msg.content} for msg in parsed_history
        ]

        # 确定用户消息（始终附加上下文信息）
        if context_info:
            user_message = f"{message or '请检查以下求职信息的合理性'}\n\n以下是用户提供的信息：\n{context_info}"
        else:
            user_message = message or "请检查以下求职信息的合理性"

        reply = await llm_service.chat_conversation(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            user_message=user_message,
            temperature=0.5,
        )
        return CheckResponse(suggestions=reply)

    except LLMServiceError as e:
        logger.error(f"AI 预检失败: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI 服务暂时不可用，请稍后重试: {e.message}",
        )


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="对话微调",
    description="基于简历内容进行对话微调，不额外消耗点数。",
)
async def chat_refine(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """POST /api/optimize/chat

    对话微调：用户对优化结果不满意时，可通过对话进行针对性修改。
    不额外消耗点数，最多 10 轮，生成后 24 小时内有效。

    请求头:
        Authorization: Bearer <token>

    请求体 (JSON):
        - resume_id: 简历 ID（必填）
        - message: 用户消息（必填）
        - history: 对话历史（选填，数组）

    响应 (200):
        ChatResponse: AI 回复

    错误码:
        - 400: 对话轮次超限或超出有效期
        - 401: Token 无效
        - 404: 简历不存在
        - 500: AI 服务异常
    """
    # 验证简历存在且属于当前用户
    resume = db.query(Resume).filter(Resume.id == request.resume_id).first()
    if resume is None or resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="简历不存在或无权访问",
        )

    # 验证简历状态
    if resume.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="简历尚未完成优化，无法进行对话微调",
        )

    # 验证 24 小时有效期
    created_at = resume.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created_at > timedelta(hours=CHAT_VALIDITY_HOURS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"简历已超过 {CHAT_VALIDITY_HOURS} 小时有效期，请重新优化",
        )

    # 验证对话轮次
    current_rounds = len([m for m in request.history if m.role == "user"])
    if current_rounds >= MAX_CHAT_ROUNDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"已达到最大对话轮次（{MAX_CHAT_ROUNDS} 轮），请重新优化",
        )

    # 构建系统提示词（注入简历上下文）
    system_prompt = f"""你是一位资深简历优化顾问，正在帮助用户微调简历。

## 用户原始简历
{resume.original_text[:3000]}

## 优化后简历（HTML）
{resume.optimized_text[:5000] if resume.optimized_text else "暂无"}

## 目标岗位 JD
{resume.target_jd or "未提供"}

## 求职意向
- 目标城市：{resume.target_city or "未指定"}
- 期望薪资：{resume.target_salary or "未指定"}

请根据用户的反馈，对优化后的简历进行针对性修改。
- 直接输出修改后的完整 HTML
- 保持原有风格和结构
- 如果用户的要求不合理，说明原因并给出替代方案"""

    # 构造对话历史
    conversation_history = [
        {"role": msg.role, "content": msg.content} for msg in request.history
    ]

    try:
        llm_service = get_llm_service()
        reply = await llm_service.chat_conversation(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            user_message=request.message,
            temperature=0.7,
        )

        # 更新简历的优化文本（如果回复包含 HTML）
        optimized_text = None
        # 先剥离可能的 markdown 代码块标记
        cleaned_reply = reply.strip()
        if cleaned_reply.startswith("```"):
            m = _re.match(r"^```(?:html|HTML)?\s*\n?(.*?)\n?\s*```$", cleaned_reply, _re.DOTALL)
            if m:
                cleaned_reply = m.group(1).strip()
        if "<html" in cleaned_reply.lower() or "<!doctype" in cleaned_reply.lower():
            resume.optimized_text = sanitize_html(cleaned_reply)
            db.commit()
            optimized_text = resume.optimized_text
            logger.info(f"对话微调更新简历 {resume.id} 的优化文本")

        rounds_used = current_rounds + 1
        rounds_remaining = MAX_CHAT_ROUNDS - rounds_used

        return ChatResponse(
            reply=reply,
            rounds_used=rounds_used,
            rounds_remaining=rounds_remaining,
            optimized_text=optimized_text,
        )

    except LLMServiceError as e:
        logger.error(f"对话微调失败: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI 服务暂时不可用，请稍后重试: {e.message}",
        )
