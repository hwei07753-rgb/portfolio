"""
简历优化服务模块

处理简历优化的核心业务流程，包括：
- 读取相关知识库
- 调用 LLM 优化简历
- 保存简历记录
- 提取并保存知识点
- 扣减用户点数
"""

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.resume import Resume
from backend.models.knowledge import KnowledgeEntry
from backend.schemas.resume import ResumeCreate
from backend.services.llm_service import get_llm_service, LLMServiceError
from backend.services.payment_service import consume_points, refund_points, InsufficientPointsError
from backend.utils.text_cleaner import sanitize_html

logger = logging.getLogger(__name__)

# 每次优化消耗点数
OPTIMIZE_COST = 1


class OptimizeServiceError(Exception):
    """优化服务异常基类"""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def _get_knowledge_context(db: Session, jd: Optional[str] = None, resume_text: str = "") -> str:
    """获取相关知识库上下文

    根据 JD 和简历内容，从知识库中检索相关的最佳实践和关键词。

    Args:
        db: 数据库会话
        jd: 目标岗位 JD
        resume_text: 简历文本

    Returns:
        知识库上下文字符串
    """
    knowledge_parts = []

    # 查询行业最佳实践
    practices = (
        db.query(KnowledgeEntry)
        .filter(
            KnowledgeEntry.category == "industry_practice",
            KnowledgeEntry.status == "active",
        )
        .order_by(KnowledgeEntry.effectiveness.desc())
        .limit(3)
        .all()
    )

    if practices:
        knowledge_parts.append("## 行业最佳实践")
        for p in practices:
            knowledge_parts.append(f"### {p.title}\n{p.content[:500]}")

    # 查询 JD 关键词（如果有 JD）
    if jd:
        keywords = (
            db.query(KnowledgeEntry)
            .filter(
                KnowledgeEntry.category == "jd_keyword",
                KnowledgeEntry.status == "active",
            )
            .order_by(KnowledgeEntry.usage_count.desc())
            .limit(5)
            .all()
        )

        if keywords:
            knowledge_parts.append("\n## 常见 JD 关键词")
            for k in keywords:
                try:
                    tags = json.loads(k.tags) if k.tags else []
                except json.JSONDecodeError:
                    tags = []
                if tags:
                    knowledge_parts.append(f"- {k.title}: {', '.join(tags[:5])}")

    # 查询优化案例
    cases = (
        db.query(KnowledgeEntry)
        .filter(
            KnowledgeEntry.category == "optimization_case",
            KnowledgeEntry.status == "active",
        )
        .order_by(KnowledgeEntry.effectiveness.desc())
        .limit(2)
        .all()
    )

    if cases:
        knowledge_parts.append("\n## 优化案例参考")
        for c in cases:
            knowledge_parts.append(f"### {c.title}\n{c.content[:300]}")

    return "\n".join(knowledge_parts) if knowledge_parts else ""


async def _extract_and_save_knowledge(
    db: Session,
    resume: Resume,
    llm_service,
) -> int:
    """提取并保存知识点

    在简历优化完成后，调用 LLM 提取可复用的知识点并存入知识库。

    Args:
        db: 数据库会话
        resume: 优化完成的简历记录
        llm_service: LLM 服务实例

    Returns:
        提取的知识点数量
    """
    try:
        # 调用 LLM 提取知识点
        knowledge_data = await llm_service.extract_knowledge(
            original=resume.original_text,
            optimized=resume.optimized_text or "",
            jd=resume.target_jd or "",
        )

        saved_count = 0

        # 保存优化模式
        for pattern in knowledge_data.get("patterns", []):
            entry = KnowledgeEntry(
                category="optimization_case",
                title=pattern.get("title", "优化案例"),
                content=pattern.get("content", ""),
                source="auto_extract",
                resume_id=resume.id,
                industry=knowledge_data.get("industry"),
                job_title=knowledge_data.get("job_level"),
                tags=json.dumps(pattern.get("tags", []), ensure_ascii=False),
                status="review_needed",  # 自动提取的知识需要审核
            )
            db.add(entry)
            saved_count += 1

        # 保存 JD 关键词
        jd_keywords = knowledge_data.get("jd_keywords", [])
        if jd_keywords:
            entry = KnowledgeEntry(
                category="jd_keyword",
                title=f"JD关键词-{resume.title}",
                content=f"从简历优化中提取的 JD 关键词: {', '.join(jd_keywords)}",
                source="auto_extract",
                resume_id=resume.id,
                industry=knowledge_data.get("industry"),
                tags=json.dumps(jd_keywords, ensure_ascii=False),
                status="review_needed",
            )
            db.add(entry)
            saved_count += 1

        db.flush()
        logger.info(f"从简历 {resume.id} 提取了 {saved_count} 条知识点")
        return saved_count

    except Exception as e:
        logger.error(f"知识点提取失败: {e}")
        return 0


async def optimize(
    db: Session,
    user_id: int,
    resume_data: ResumeCreate,
    strength: int = 3,
) -> dict:
    """简历优化主流程

    完整流程：
    1. 扣减用户点数
    2. 创建简历记录
    3. 读取相关知识库
    4. 调用 LLM 优化简历
    5. 保存优化结果
    6. 提取并保存知识点
    7. 返回优化结果

    Args:
        db: 数据库会话
        user_id: 用户 ID
        resume_data: 简历创建请求数据

    Returns:
        dict 包含:
        - resume_id: 简历 ID
        - optimized_html: 优化后的 HTML
        - optimization_score: 优化分数
        - changes_summary: 修改摘要
        - knowledge_extracted: 提取的知识点数量

    Raises:
        InsufficientPointsError: 点数不足
        OptimizeServiceError: 优化过程异常
    """
    llm_service = get_llm_service()

    try:
        logger.info(f"开始优化流程: user_id={user_id}, title={resume_data.title}")

        # 1. 扣减用户点数（flush 不 commit，保持事务开放）
        consume_points(
            db=db,
            user_id=user_id,
            amount=OPTIMIZE_COST,
            desc=f"简历优化: {resume_data.title}",
        )

        # 2. 创建简历记录
        resume = Resume(
            user_id=user_id,
            title=resume_data.title,
            original_text=resume_data.original_text,
            target_city=resume_data.target_city,
            target_salary=resume_data.target_salary,
            target_jd=resume_data.target_jd,
            extra_details=resume_data.extra_details,
            status="processing",
        )
        db.add(resume)
        db.flush()

        # 3. 读取相关知识库
        knowledge_context = _get_knowledge_context(
            db=db,
            jd=resume_data.target_jd,
            resume_text=resume_data.original_text,
        )

        # 4. 调用 LLM 优化简历（返回结构化数据）
        logger.info("正在调用 LLM API 优化简历...")
        llm_result = await llm_service.optimize_resume(
            original_text=resume_data.original_text,
            jd=resume_data.target_jd or "",
            city=resume_data.target_city,
            salary=resume_data.target_salary,
            details=resume_data.extra_details,
            knowledge_context=knowledge_context,
            strength=strength,
        )

        optimized_html = llm_result.get("optimized_html", "")
        logger.info(f"LLM API 调用完成，优化分数: {llm_result.get('optimization_score')}")

        # 4.1 消毒 AI 输出的 HTML（防止存储型 XSS）
        optimized_html = sanitize_html(optimized_html)

        # 5. 保存优化结果
        resume.optimized_text = optimized_html
        resume.optimization_score = llm_result.get("optimization_score")
        resume.star_rewrites = llm_result.get("star_rewrites", 0)
        resume.quantifications = llm_result.get("quantifications", 0)
        resume.keywords_matched = llm_result.get("keywords_matched", 0)
        resume.status = "completed"
        resume.model_used = llm_service.default_model

        # 6. 提取并保存知识点
        knowledge_extracted = await _extract_and_save_knowledge(
            db=db,
            resume=resume,
            llm_service=llm_service,
        )

        # 7. 全部成功，统一提交事务
        db.commit()
        db.refresh(resume)

        logger.info(
            f"简历优化完成: ID={resume.id}, "
            f"分数={resume.optimization_score}, "
            f"知识点提取={knowledge_extracted}"
        )

        return {
            "resume_id": resume.id,
            "optimized_html": optimized_html,
            "optimization_score": llm_result.get("optimization_score"),
            "changes_summary": llm_result.get("changes_summary", []),
            "pros": llm_result.get("pros", []),
            "cons": llm_result.get("cons", []),
            "star_rewrites": llm_result.get("star_rewrites", 0),
            "quantifications": llm_result.get("quantifications", 0),
            "keywords_matched": llm_result.get("keywords_matched", 0),
            "knowledge_extracted": knowledge_extracted,
        }

    except InsufficientPointsError:
        # 点数不足，直接抛出，无需回滚
        raise

    except Exception as e:
        # 任何异常都回滚整个事务（包括点数扣减和简历记录）
        logger.error(f"优化过程异常，回滚事务: {e}")
        db.rollback()

        raise OptimizeServiceError(f"简历优化失败: {str(e)}")
