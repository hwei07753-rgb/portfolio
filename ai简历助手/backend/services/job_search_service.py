"""
岗位搜索服务模块

提供基于关键词的岗位 JD 搜索功能。
当前为 Mock 实现，内置常见岗位样本数据；后续可替换为真实招聘平台 API。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass
class JobItem:
    """单条岗位信息"""

    title: str
    company: str
    location: str
    salary: str
    description: str
    keywords: list[str]


# ---------------------------------------------------------------------------
# Mock 岗位数据
# ---------------------------------------------------------------------------

_MOCK_JOBS: list[JobItem] = [
    # ── 前端 ──
    JobItem(
        title="高级前端工程师",
        company="字节跳动",
        location="北京",
        salary="30-50K·15薪",
        description=(
            "负责公司核心产品的前端架构设计与开发，优化页面性能和用户体验。\n"
            "要求：本科及以上学历，3年以上前端开发经验；精通 React/Vue 框架，"
            "熟悉 TypeScript；具备良好的工程化思维，熟悉 Webpack/Vite 等构建工具；"
            "有大型 SPA 项目经验优先。"
        ),
        keywords=["前端", "React", "Vue", "TypeScript", "性能优化", "架构"],
    ),
    JobItem(
        title="前端开发工程师",
        company="阿里巴巴",
        location="杭州",
        salary="25-40K·16薪",
        description=(
            "参与电商平台前端业务开发，负责商品详情、购物车等核心模块。\n"
            "要求：本科及以上，2年以上前端经验；熟练使用 React，了解 Node.js；"
            "具备跨端开发经验（H5/小程序）优先；良好的沟通协作能力。"
        ),
        keywords=["前端", "React", "Node.js", "H5", "小程序", "电商"],
    ),
    JobItem(
        title="Web 前端负责人",
        company="腾讯",
        location="深圳",
        salary="40-65K·16薪",
        description=(
            "带领前端团队负责社交产品 Web 端的架构设计和技术演进。\n"
            "要求：5年以上前端经验，2年以上团队管理经验；精通 React 生态，"
            "深入理解浏览器原理和前端性能优化；有微前端、Monorepo 等实践经验优先。"
        ),
        keywords=["前端", "React", "微前端", "Monorepo", "团队管理", "性能优化"],
    ),
    # ── 后端 ──
    JobItem(
        title="高级后端工程师",
        company="美团",
        location="北京",
        salary="35-55K·15薪",
        description=(
            "负责外卖配送系统核心服务的设计与开发，保障高并发场景下的稳定性。\n"
            "要求：本科及以上，3年以上 Java/Go 后端开发经验；熟悉 Spring Boot、"
            "微服务架构；了解 MySQL、Redis、Kafka 等中间件；有分布式系统经验优先。"
        ),
        keywords=["后端", "Java", "Go", "微服务", "Spring Boot", "分布式", "高并发"],
    ),
    JobItem(
        title="Python 后端开发工程师",
        company="小红书",
        location="上海",
        salary="25-45K·14薪",
        description=(
            "负责社区内容推荐服务的后端开发与优化。\n"
            "要求：2年以上 Python 后端经验；熟悉 FastAPI/Django 框架；"
            "了解推荐系统基本原理；熟悉 Redis、Elasticsearch；有 NLP 或机器学习经验优先。"
        ),
        keywords=["后端", "Python", "FastAPI", "Django", "推荐系统", "NLP", "Redis"],
    ),
    # ── 全栈 ──
    JobItem(
        title="全栈开发工程师",
        company="PingCAP",
        location="北京/上海/杭州",
        salary="30-50K·15薪",
        description=(
            "参与分布式数据库管理平台的全栈开发，覆盖前端可视化与后端 API。\n"
            "要求：3年以上全栈开发经验；前端精通 React + TypeScript，后端熟悉 Go/Rust；"
            "了解数据库原理和分布式系统；有开源项目贡献经验优先。"
        ),
        keywords=["全栈", "React", "TypeScript", "Go", "Rust", "分布式", "数据库"],
    ),
    # ── 产品 ──
    JobItem(
        title="高级产品经理",
        company="京东",
        location="北京",
        salary="30-50K·14薪",
        description=(
            "负责电商搜索推荐产品方向，提升用户转化率和购物体验。\n"
            "要求：3年以上电商产品经理经验；具备优秀的数据分析能力，熟练使用 SQL；"
            "有搜索或推荐产品经验优先；良好的跨部门沟通协调能力。"
        ),
        keywords=["产品经理", "电商", "搜索", "推荐", "数据分析", "SQL"],
    ),
    JobItem(
        title="B端产品经理",
        company="飞书",
        location="北京/深圳",
        salary="25-45K·15薪",
        description=(
            "负责企业协作工具的产品规划与需求分析，推动产品迭代。\n"
            "要求：2年以上 B 端产品经验；具备企业服务 SaaS 领域知识；"
            "擅长需求文档撰写和原型设计；有 ToB 销售或客户成功经验优先。"
        ),
        keywords=["产品经理", "B端", "SaaS", "企业服务", "需求分析", "飞书"],
    ),
    # ── 设计 ──
    JobItem(
        title="高级UI设计师",
        company="蚂蚁集团",
        location="杭州",
        salary="25-40K·16薪",
        description=(
            "负责支付宝及蚂蚁生态产品的视觉设计与设计规范建设。\n"
            "要求：3年以上移动端 UI 设计经验；精通 Figma/Sketch；"
            "具备 Design System 建设经验；有金融或支付领域设计经验优先。"
        ),
        keywords=["UI设计", "Figma", "Sketch", "Design System", "移动端", "金融"],
    ),
    JobItem(
        title="UX设计师",
        company="网易",
        location="杭州/广州",
        salary="20-35K·14薪",
        description=(
            "负责游戏平台用户体验设计，包括用户研究、交互设计和可用性测试。\n"
            "要求：2年以上 UX 设计经验；熟练使用 Figma、Axure；"
            "具备用户研究和数据分析能力；有游戏行业经验优先。"
        ),
        keywords=["UX设计", "用户体验", "交互设计", "Figma", "用户研究", "游戏"],
    ),
    # ── 数据/AI ──
    JobItem(
        title="数据分析师",
        company="拼多多",
        location="上海",
        salary="20-35K·16薪",
        description=(
            "负责电商业务数据分析，输出数据报告，驱动业务决策。\n"
            "要求：本科及以上统计学/计算机相关专业；熟练使用 SQL、Python；"
            "掌握 Tableau/Power BI 等可视化工具；有电商数据分析经验优先。"
        ),
        keywords=["数据分析", "SQL", "Python", "Tableau", "电商", "数据可视化"],
    ),
    JobItem(
        title="算法工程师",
        company="百度",
        location="北京/深圳",
        salary="35-60K·14薪",
        description=(
            "负责搜索广告排序算法的研发与优化，提升广告收入和用户体验。\n"
            "要求：硕士及以上学历，计算机/人工智能相关专业；3年以上推荐/广告/搜索算法经验；"
            "精通 Python，熟悉 TensorFlow/PyTorch；有顶会论文优先。"
        ),
        keywords=["算法", "机器学习", "深度学习", "TensorFlow", "PyTorch", "推荐", "广告"],
    ),
    JobItem(
        title="AI 大模型应用工程师",
        company="智谱AI",
        location="北京",
        salary="40-70K·15薪",
        description=(
            "负责大语言模型的应用开发，包括 RAG、Agent、Prompt Engineering 等方向。\n"
            "要求：2年以上 LLM 应用开发经验；熟悉 LangChain/LlamaIndex 等框架；"
            "了解向量数据库（Milvus/Pinecone）；有 Agent 或 Multi-Agent 系统经验优先。"
        ),
        keywords=["大模型", "LLM", "RAG", "Agent", "LangChain", "向量数据库", "Prompt"],
    ),
    # ── 测试 ──
    JobItem(
        title="测试开发工程师",
        company="华为",
        location="深圳/南京",
        salary="20-35K·14薪",
        description=(
            "负责通信产品自动化测试框架搭建与测试工具开发。\n"
            "要求：2年以上测试开发经验；熟悉 Python/Java；掌握 Selenium/Appium；"
            "了解 CI/CD 流程；有通信行业经验优先。"
        ),
        keywords=["测试", "自动化测试", "Python", "Selenium", "CI/CD", "Appium"],
    ),
    # ── 运维/DevOps ──
    JobItem(
        title="DevOps 工程师",
        company="滴滴",
        location="北京",
        salary="30-50K·15薪",
        description=(
            "负责 CI/CD 平台建设、容器化部署和监控告警体系。\n"
            "要求：3年以上运维或 DevOps 经验；精通 Docker/Kubernetes；"
            "熟悉 Jenkins/GitLab CI；了解 Terraform/Ansible 等 IaC 工具。"
        ),
        keywords=["DevOps", "Docker", "Kubernetes", "CI/CD", "Jenkins", "Terraform"],
    ),
    # ── 项目经理 ──
    JobItem(
        title="项目经理",
        company="中兴通讯",
        location="南京/深圳",
        salary="25-40K·13薪",
        description=(
            "负责通信设备研发项目的全生命周期管理，协调跨部门资源。\n"
            "要求：3年以上项目管理经验；持有 PMP 认证；熟悉敏捷开发流程；"
            "有通信或硬件研发项目管理经验优先。"
        ),
        keywords=["项目管理", "PMP", "敏捷", "Scrum", "通信", "研发管理"],
    ),
    # ── 运营 ──
    JobItem(
        title="内容运营",
        company="B站",
        location="上海",
        salary="15-25K·14薪",
        description=(
            "负责视频社区内容策划与创作者运营，提升内容质量和用户活跃度。\n"
            "要求：1年以上内容运营经验；具备优秀的文案撰写能力；"
            "熟悉短视频行业趋势；有创作者运营或社区运营经验优先。"
        ),
        keywords=["内容运营", "短视频", "创作者运营", "社区运营", "文案", "B站"],
    ),
    JobItem(
        title="用户增长运营",
        company="快手",
        location="北京",
        salary="20-35K·16薪",
        description=(
            "负责用户增长策略制定与执行，通过活动运营和渠道投放提升 DAU。\n"
            "要求：2年以上增长运营经验；具备数据分析能力，熟练使用 SQL；"
            "有裂变营销或渠道投放经验优先。"
        ),
        keywords=["增长运营", "用户增长", "数据分析", "活动运营", "裂变", "DAU"],
    ),
    # ── 人力资源 ──
    JobItem(
        title="HRBP",
        company="小米",
        location="北京",
        salary="20-35K·14薪",
        description=(
            "对接业务部门，提供人力资源全方位支持，推动组织发展和人才梯队建设。\n"
            "要求：3年以上 HRBP 经验；熟悉互联网行业人力资源管理；"
            "具备招聘、绩效、员工关系等模块实操经验；有 COE 经验优先。"
        ),
        keywords=["HRBP", "人力资源", "招聘", "绩效", "组织发展", "人才梯队"],
    ),
    # ── 财务 ──
    JobItem(
        title="财务分析师",
        company="腾讯",
        location="深圳",
        salary="20-35K·16薪",
        description=(
            "负责业务线财务分析与预算管理，输出经营分析报告。\n"
            "要求：本科及以上财务/会计相关专业；3年以上财务分析经验；"
            "熟练使用 Excel 和 SQL；持有 CPA/CMA 证书优先。"
        ),
        keywords=["财务分析", "预算管理", "Excel", "SQL", "CPA", "经营分析"],
    ),
    # ── 销售 ──
    JobItem(
        title="大客户销售",
        company="华为云",
        location="北京/上海/深圳",
        salary="25-40K·12薪+提成",
        description=(
            "负责云计算产品的大客户开拓与关系维护，完成销售目标。\n"
            "要求：3年以上 ToB 销售经验；有云计算或 IT 基础设施销售经验；"
            "具备优秀的商务谈判和客户关系管理能力。"
        ),
        keywords=["销售", "大客户", "云计算", "ToB", "商务谈判", "客户管理"],
    ),
    # ── 安全 ──
    JobItem(
        title="安全工程师",
        company="蚂蚁集团",
        location="杭州/成都",
        salary="30-50K·16薪",
        description=(
            "负责金融级安全攻防体系的建设，包括漏洞挖掘、安全审计和应急响应。\n"
            "要求：3年以上安全工程经验；熟悉 Web 安全、移动端安全；"
            "掌握渗透测试工具和方法论；有 CTF 竞赛经验优先。"
        ),
        keywords=["安全", "渗透测试", "Web安全", "漏洞挖掘", "CTF", "应急响应"],
    ),
    # ── 嵌入式/IoT ──
    JobItem(
        title="嵌入式软件工程师",
        company="大疆",
        location="深圳",
        salary="25-40K·14薪",
        description=(
            "负责无人机飞控系统嵌入式软件的开发与调试。\n"
            "要求：本科及以上电子/自动化/计算机相关专业；精通 C/C++；"
            "熟悉 RTOS 或 Linux 内核驱动开发；有飞控或机器人开发经验优先。"
        ),
        keywords=["嵌入式", "C/C++", "RTOS", "Linux", "飞控", "无人机"],
    ),
]


# ---------------------------------------------------------------------------
# 搜索函数
# ---------------------------------------------------------------------------


def search_jobs(query: str, limit: int = 20) -> list[dict]:
    """根据关键词搜索岗位列表。

    在标题、公司、地点、描述和关键词中做模糊匹配（不区分大小写），
    按匹配关键词数量降序返回结果。

    Args:
        query: 搜索关键词（如 "前端工程师"、"Python"）。
        limit: 最大返回条数，默认 20。

    Returns:
        岗位字典列表，包含 title / company / location / salary / description 字段。
    """
    if not query or not query.strip():
        # 无关键词时返回全部（按原序）
        return [_to_dict(j) for j in _MOCK_JOBS[:limit]]

    q = query.strip().lower()
    results: list[tuple[int, JobItem]] = []

    for job in _MOCK_JOBS:
        # 统计匹配的关键词数量作为相关性分数
        score = 0
        searchable = f"{job.title} {job.company} {job.location} {job.description}".lower()
        if q in searchable:
            score += 10
        for kw in job.keywords:
            if q in kw.lower() or kw.lower() in q:
                score += 1
        if score > 0:
            results.append((score, job))

    # 按分数降序排列
    results.sort(key=lambda x: x[0], reverse=True)
    return [_to_dict(j) for _, j in results[:limit]]


def _to_dict(job: JobItem) -> dict:
    """将 JobItem 转换为 API 响应字典。"""
    return {
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "salary": job.salary,
        "description": job.description,
    }
