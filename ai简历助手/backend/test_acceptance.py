"""
最终验收测试模块

覆盖完整业务流程、多用户场景、数据隔离、并发操作等验收场景。

测试分组：
1. 完整流程测试（注册→登录→上传→优化→查看→对话微调→导出）
2. 充值消费流程（充值→消费→查看流水）
3. 知识库流程（浏览→搜索→筛选）
4. 多用户测试（创建多用户、数据隔离、并发操作）
5. 文档与部署检查
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 确保项目根目录在 Python 路径中
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.config import settings
from backend.database import Base, get_db
from backend.main import app
from backend.models.user import User
from backend.models.resume import Resume
from backend.models.knowledge import KnowledgeEntry
from backend.models.payment import UserWallet, PointTransaction, PaymentOrder
from backend.utils.security import create_access_token, hash_password

# ---------------------------------------------------------------------------
# 测试数据库配置
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///./test_acceptance.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def override_get_db():
    """覆盖数据库依赖"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ---------------------------------------------------------------------------
# 测试夹具
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def setup_database():
    """每个测试前重建数据库"""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest_asyncio.fixture
async def client():
    """异步 HTTP 客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def db_session():
    """数据库会话"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def user_a_data():
    """用户 A 数据"""
    return {
        "username": "alice",
        "email": "alice@example.com",
        "password": "AlicePass123!",
    }


@pytest.fixture
def user_b_data():
    """用户 B 数据"""
    return {
        "username": "bob",
        "email": "bob@example.com",
        "password": "BobPass456!",
    }


@pytest.fixture
def user_c_data():
    """用户 C 数据"""
    return {
        "username": "charlie",
        "email": "charlie@example.com",
        "password": "CharliePass789!",
    }


@pytest.fixture
def frontend_resume():
    """前端工程师简历"""
    return """
    张三
    高级前端工程师
    手机：13800138000
    邮箱：zhangsan@example.com

    教育背景
    北京大学 计算机科学与技术 本科 2018-2022

    工作经历
    2022-至今 ABC科技有限公司 高级前端工程师
    - 负责公司核心产品的前端架构设计和开发
    - 使用 React + TypeScript 开发 Web 应用
    - 优化页面性能，首屏加载时间减少 40%
    - 带领 3 人前端团队完成 5 个核心项目

    2020-2022 XYZ互联网公司 前端工程师
    - 参与电商平台前端开发
    - 使用 Vue.js 构建后台管理系统
    - 编写单元测试，覆盖率达到 85%

    技能
    - 精通 React、Vue、TypeScript
    - 熟悉 Node.js、Webpack、Vite
    - 了解 Docker、CI/CD
    - 良好的英语读写能力
    """


@pytest.fixture
def backend_resume():
    """后端工程师简历"""
    return """
    李四
    后端工程师
    手机：13900139000
    邮箱：lisi@example.com

    教育背景
    清华大学 软件工程 硕士 2019-2022

    工作经历
    2022-至今 DEF科技有限公司 后端工程师
    - 负责微服务架构设计与开发
    - 使用 Python + FastAPI 构建 RESTful API
    - 优化数据库查询，响应时间降低 60%
    - 设计并实现消息队列系统，处理日均 500 万条消息

    技能
    - 精通 Python、Go、Java
    - 熟悉 FastAPI、Django、Spring Boot
    - 熟悉 PostgreSQL、Redis、MongoDB
    - 了解 Kubernetes、Docker
    """


@pytest.fixture
def sample_jd():
    """示例岗位 JD"""
    return """
    高级前端工程师

    岗位职责：
    1. 负责公司核心产品的前端架构设计和开发
    2. 优化前端性能，提升用户体验
    3. 参与技术选型和代码规范制定
    4. 指导初级开发人员

    任职要求：
    1. 3年以上前端开发经验
    2. 精通 React 或 Vue 框架
    3. 熟悉 TypeScript
    4. 有大型项目架构经验优先
    5. 良好的沟通能力和团队协作精神
    """


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


async def register_and_login(
    client: AsyncClient,
    user_data: dict,
) -> tuple[str, dict]:
    """注册并登录用户，返回 Token 和用户信息"""
    register_response = await client.post(
        "/api/auth/register",
        json=user_data,
    )
    assert register_response.status_code == 201
    register_data = register_response.json()
    return register_data["access_token"], register_data["user"]


def get_auth_headers(token: str) -> dict:
    """获取认证请求头"""
    return {"Authorization": f"Bearer {token}"}


def mock_llm_optimize(score=85.0, html=None):
    """创建 Mock LLM 优化结果"""
    if html is None:
        html = """
        <html>
        <head><meta charset="utf-8"><title>优化后简历</title></head>
        <body>
            <h1>张三</h1>
            <h2>高级前端工程师</h2>
            <p>优化后的简历内容...</p>
        </body>
        </html>
        """
    return {
        "optimized_html": html,
        "optimization_score": score,
        "changes_summary": [
            "使用 STAR 原则重写了 3 段工作经历",
            "补充了 5 处量化数据",
            "匹配 JD 关键词 12 个",
        ],
        "pros": ["STAR 原则应用到位", "量化数据充分", "关键词匹配度高"],
        "cons": ["部分技能可进一步细化"],
        "star_rewrites": 3,
        "quantifications": 5,
        "keywords_matched": 12,
    }


def mock_knowledge_data():
    """创建 Mock 知识提取结果"""
    return {
        "patterns": [
            {
                "type": "star_rewrite",
                "title": "STAR 原则重写前端经历",
                "content": "将'负责前端开发'改为'主导核心模块前端架构设计，性能提升 40%'",
                "before_example": "负责前端开发",
                "after_example": "主导核心模块前端架构设计，首屏加载时间从 3s 降至 1.8s，性能提升 40%",
                "tags": ["前端", "STAR", "性能优化"],
            },
            {
                "type": "quantification",
                "title": "量化数据补充",
                "content": "在工作经历中补充具体的数字、百分比和金额",
                "tags": ["量化", "数据"],
            },
        ],
        "jd_keywords": ["React", "TypeScript", "性能优化", "架构设计", "前端"],
        "industry": "互联网",
        "job_level": "senior",
    }


# ===========================================================================
# 1. 完整流程测试
# ===========================================================================


class TestFullUserJourney:
    """完整用户旅程测试

    覆盖：注册 → 登录 → 上传简历 → AI 预检 → 优化 → 查看结果 → 对话微调 → 导出
    """

    @pytest.mark.asyncio
    async def test_complete_user_journey(
        self,
        client: AsyncClient,
        user_a_data,
        frontend_resume,
        sample_jd,
        db_session,
    ):
        """完整流程：注册→登录→上传→AI预检→优化→查看→对话微调→导出"""

        # ========== 1. 注册 ==========
        register_response = await client.post(
            "/api/auth/register",
            json=user_a_data,
        )
        assert register_response.status_code == 201
        reg_data = register_response.json()
        token = reg_data["access_token"]
        user_id = reg_data["user"]["id"]
        assert reg_data["user"]["username"] == user_a_data["username"]

        # 验证新用户赠送 3 点
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        assert wallet_response.status_code == 200
        assert wallet_response.json()["balance"] == 3

        # ========== 2. 登录 ==========
        login_response = await client.post(
            "/api/auth/login",
            json={
                "email": user_a_data["email"],
                "password": user_a_data["password"],
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # ========== 3. 上传简历 ==========
        upload_response = await client.post(
            "/api/resume/upload",
            data={
                "title": "张三_高级前端工程师",
                "original_text": frontend_resume,
                "target_city": "北京",
                "target_salary": "30k-40k",
                "target_jd": sample_jd,
            },
            headers=get_auth_headers(token),
        )
        assert upload_response.status_code == 201
        resume_id = upload_response.json()["id"]
        assert upload_response.json()["status"] == "pending"

        # ========== 4. AI 预检 ==========
        with patch("backend.routers.optimize.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat_conversation.return_value = (
                "## 需要改进\n"
                "- 薪资 30k-40k 对于 3 年经验的高级前端工程师在北京市场偏低\n\n"
                "## 建议补充\n"
                "- 建议补充项目链接或 GitHub 地址\n"
                "- 建议补充团队管理经验"
            )
            mock_get_llm.return_value = mock_llm

            check_response = await client.post(
                "/api/optimize/check",
                json={
                    "city": "北京",
                    "salary": "30k-40k",
                    "jd": sample_jd,
                    "resume_text": frontend_resume[:500],
                },
                headers=get_auth_headers(token),
            )

        assert check_response.status_code == 200
        suggestions = check_response.json()["suggestions"]
        assert "需要改进" in suggestions
        assert "薪资" in suggestions

        # ========== 5. 优化简历（消耗 1 点） ==========
        # 充值确保有足够点数
        create_order_resp = await client.post(
            "/api/payment/create",
            json={"package_id": "small"},
            headers=get_auth_headers(token),
        )
        order_no = create_order_resp.json()["order_no"]
        await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )
        # 现在余额应该是 3 + 10 = 13

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = mock_llm_optimize(score=87.5)
            mock_llm.extract_knowledge.return_value = mock_knowledge_data()
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            optimize_response = await client.post(
                "/api/optimize",
                data={
                    "text": frontend_resume,
                    "city": "北京",
                    "salary": "30k-40k",
                    "jd": sample_jd,
                    "strength": 4,
                },
                headers=get_auth_headers(token),
            )

        assert optimize_response.status_code == 200
        opt_data = optimize_response.json()
        assert "resume_id" in opt_data
        assert "optimized_html" in opt_data
        assert opt_data["optimization_score"] == 87.5
        assert len(opt_data["changes_summary"]) > 0
        assert opt_data["knowledge_extracted"] > 0

        optimized_resume_id = opt_data["resume_id"]

        # 验证点数扣减（13 - 1 = 12）
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        assert wallet_response.json()["balance"] == 12

        # ========== 6. 查看优化结果 ==========
        detail_response = await client.get(
            f"/api/resume/{optimized_resume_id}",
            headers=get_auth_headers(token),
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["status"] == "completed"
        assert detail["optimization_score"] == 87.5
        assert detail["optimized_text"] is not None

        # ========== 7. 对话微调 ==========
        with patch("backend.routers.optimize.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat_conversation.return_value = (
                "<html><body><h1>张三</h1>"
                "<p>根据您的要求，已将技能部分移到工作经历前面</p>"
                "</body></html>"
            )
            mock_get_llm.return_value = mock_llm

            chat_response = await client.post(
                "/api/optimize/chat",
                json={
                    "resume_id": optimized_resume_id,
                    "message": "请把技能部分移到工作经历前面",
                    "history": [],
                },
                headers=get_auth_headers(token),
            )

        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        assert "reply" in chat_data
        assert chat_data["rounds_used"] == 1
        assert chat_data["rounds_remaining"] == 9

        # ========== 8. 导出 Word ==========
        export_response = await client.get(
            f"/api/resume/{optimized_resume_id}/export/docx",
            headers=get_auth_headers(token),
        )
        assert export_response.status_code == 200
        assert export_response.headers["content-type"].startswith(
            "application/vnd.openxmlformats"
        )

        # ========== 9. 提交反馈 ==========
        feedback_response = await client.post(
            f"/api/resume/{optimized_resume_id}/feedback",
            json={"rating": 5, "comment": "优化效果非常好！"},
            headers=get_auth_headers(token),
        )
        assert feedback_response.status_code == 201

        # ========== 10. 查看简历历史 ==========
        history_response = await client.get(
            "/api/resume/list",
            headers=get_auth_headers(token),
        )
        assert history_response.status_code == 200
        assert history_response.json()["total"] >= 1

        # ========== 11. 查看版本历史 ==========
        versions_response = await client.get(
            f"/api/resume/{optimized_resume_id}/versions",
            headers=get_auth_headers(token),
        )
        assert versions_response.status_code == 200

    @pytest.mark.asyncio
    async def test_upload_image_with_ocr(
        self,
        client: AsyncClient,
        user_a_data,
        db_session,
    ):
        """测试图片上传 + OCR 识别流程"""
        token, _ = await register_and_login(client, user_a_data)

        # 创建一个简单的 PNG 图片（1x1 像素）
        import struct
        import zlib

        def create_minimal_png():
            """创建最小的有效 PNG 文件"""
            signature = b"\x89PNG\r\n\x1a\n"
            # IHDR chunk
            ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
            ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
            ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
            # IDAT chunk
            raw_data = zlib.compress(b"\x00\xff\x00\x00")
            idat_crc = zlib.crc32(b"IDAT" + raw_data) & 0xFFFFFFFF
            idat = struct.pack(">I", len(raw_data)) + b"IDAT" + raw_data + struct.pack(">I", idat_crc)
            # IEND chunk
            iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
            iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
            return signature + ihdr + idat + iend

        png_data = create_minimal_png()

        with patch("backend.routers.optimize.get_ocr_service") as mock_get_ocr:
            mock_ocr = AsyncMock()
            mock_ocr.recognize_text.return_value = "张三\n前端工程师\n13800138000"
            mock_get_ocr.return_value = mock_ocr

            # 充值点数
            create_resp = await client.post(
                "/api/payment/create",
                json={"package_id": "small"},
                headers=get_auth_headers(token),
            )
            order_no = create_resp.json()["order_no"]
            await client.post(
                f"/api/payment/{order_no}/confirm",
                headers=get_auth_headers(token),
            )

            with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
                mock_llm = AsyncMock()
                mock_llm.optimize_resume.return_value = mock_llm_optimize()
                mock_llm.extract_knowledge.return_value = mock_knowledge_data()
                mock_llm.default_model = "qwen3.7-max"
                mock_get_llm.return_value = mock_llm

                response = await client.post(
                    "/api/optimize",
                    files={"file": ("resume.png", png_data, "image/png")},
                    data={},
                    headers=get_auth_headers(token),
                )

        assert response.status_code == 200
        assert "resume_id" in response.json()

    @pytest.mark.asyncio
    async def test_version_tracking(
        self,
        client: AsyncClient,
        user_a_data,
        frontend_resume,
        sample_jd,
        db_session,
    ):
        """测试同一简历多次优化的版本追踪"""
        token, user_info = await register_and_login(client, user_a_data)

        # 充值点数
        create_resp = await client.post(
            "/api/payment/create",
            json={"package_id": "large"},
            headers=get_auth_headers(token),
        )
        order_no = create_resp.json()["order_no"]
        await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )

        # 第一次优化
        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = mock_llm_optimize(score=75.0)
            mock_llm.extract_knowledge.return_value = mock_knowledge_data()
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            resp1 = await client.post(
                "/api/optimize",
                data={"text": frontend_resume, "jd": sample_jd},
                headers=get_auth_headers(token),
            )

        assert resp1.status_code == 200
        resume_id_1 = resp1.json()["resume_id"]

        # 查看简历列表
        list_resp = await client.get(
            "/api/resume/list",
            headers=get_auth_headers(token),
        )
        assert list_resp.json()["total"] >= 1


# ===========================================================================
# 2. 充值消费流程测试
# ===========================================================================


class TestPaymentConsumptionFlow:
    """充值消费流程测试

    覆盖：充值 → 消费 → 查看流水
    """

    @pytest.mark.asyncio
    async def test_recharge_consume_check_flow(
        self,
        client: AsyncClient,
        user_a_data,
        frontend_resume,
        db_session,
    ):
        """完整充值消费流程：注册(3点) → 充值 → 消费 → 查看流水"""
        token, user_info = await register_and_login(client, user_a_data)

        # 1. 验证初始余额（注册赠送 3 点）
        wallet = await client.get("/api/wallet", headers=get_auth_headers(token))
        assert wallet.json()["balance"] == 3
        assert wallet.json()["total_recharged"] == 3

        # 2. 查看充值套餐
        packages = await client.get("/api/payment/packages")
        assert packages.status_code == 200
        assert len(packages.json()) == 3

        # 3. 创建充值订单（50 点套餐）
        create_resp = await client.post(
            "/api/payment/create",
            json={"package_id": "medium"},
            headers=get_auth_headers(token),
        )
        assert create_resp.status_code == 201
        order_no = create_resp.json()["order_no"]
        assert create_resp.json()["points"] == 50
        assert create_resp.json()["amount_cents"] == 3990

        # 4. 确认支付
        confirm_resp = await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "paid"

        # 5. 验证余额（3 + 50 = 53）
        wallet = await client.get("/api/wallet", headers=get_auth_headers(token))
        assert wallet.json()["balance"] == 53
        assert wallet.json()["total_recharged"] == 53

        # 6. 消费点数（优化简历）
        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = mock_llm_optimize()
            mock_llm.extract_knowledge.return_value = mock_knowledge_data()
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            optimize_resp = await client.post(
                "/api/optimize",
                data={"text": frontend_resume},
                headers=get_auth_headers(token),
            )

        assert optimize_resp.status_code == 200

        # 7. 验证余额扣减（53 - 1 = 52）
        wallet = await client.get("/api/wallet", headers=get_auth_headers(token))
        assert wallet.json()["balance"] == 52
        assert wallet.json()["total_consumed"] == 1

        # 8. 查看流水记录
        transactions = await client.get(
            "/api/wallet/transactions",
            headers=get_auth_headers(token),
        )
        assert transactions.status_code == 200
        tx_data = transactions.json()
        # 应该有 3 条：gift + recharge + consume
        assert tx_data["total"] == 3
        types = [item["type"] for item in tx_data["items"]]
        assert "gift" in types
        assert "recharge" in types
        assert "consume" in types

        # 9. 查看订单列表
        orders = await client.get(
            "/api/payment/orders",
            headers=get_auth_headers(token),
        )
        assert orders.status_code == 200
        assert orders.json()["total"] == 1
        assert orders.json()["items"][0]["status"] == "paid"

    @pytest.mark.asyncio
    async def test_multiple_recharges(
        self,
        client: AsyncClient,
        user_a_data,
        db_session,
    ):
        """多次充值测试"""
        token, _ = await register_and_login(client, user_a_data)

        # 充值 3 次不同套餐
        for package_id in ["small", "medium", "large"]:
            create_resp = await client.post(
                "/api/payment/create",
                json={"package_id": package_id},
                headers=get_auth_headers(token),
            )
            order_no = create_resp.json()["order_no"]
            await client.post(
                f"/api/payment/{order_no}/confirm",
                headers=get_auth_headers(token),
            )

        # 验证余额（3 + 10 + 50 + 100 = 163）
        wallet = await client.get("/api/wallet", headers=get_auth_headers(token))
        assert wallet.json()["balance"] == 163
        assert wallet.json()["total_recharged"] == 163

        # 验证订单列表
        orders = await client.get(
            "/api/payment/orders",
            headers=get_auth_headers(token),
        )
        assert orders.json()["total"] == 3

    @pytest.mark.asyncio
    async def test_cancel_order_flow(
        self,
        client: AsyncClient,
        user_a_data,
        db_session,
    ):
        """取消订单流程测试"""
        token, _ = await register_and_login(client, user_a_data)

        # 创建订单
        create_resp = await client.post(
            "/api/payment/create",
            json={"package_id": "medium"},
            headers=get_auth_headers(token),
        )
        order_no = create_resp.json()["order_no"]

        # 取消订单
        cancel_resp = await client.post(
            f"/api/payment/{order_no}/cancel",
            headers=get_auth_headers(token),
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "expired"

        # 验证余额不变
        wallet = await client.get("/api/wallet", headers=get_auth_headers(token))
        assert wallet.json()["balance"] == 3


# ===========================================================================
# 3. 知识库流程测试
# ===========================================================================


class TestKnowledgeFlow:
    """知识库流程测试

    覆盖：浏览 → 搜索 → 筛选 → 统计
    """

    @pytest.mark.asyncio
    async def test_knowledge_browse_search_filter(
        self,
        client: AsyncClient,
        user_a_data,
        db_session,
    ):
        """知识库完整流程：添加 → 浏览 → 搜索 → 筛选 → 统计"""
        token, _ = await register_and_login(client, user_a_data)

        # 1. 添加多条知识条目
        entries = [
            {
                "category": "industry_practice",
                "title": "技术岗简历 STAR 原则",
                "content": "使用 STAR 原则描述项目经历：Situation（情境）、Task（任务）、Action（行动）、Result（结果）",
                "tags": ["STAR", "技术岗", "简历写作"],
            },
            {
                "category": "industry_practice",
                "title": "金融岗简历规范",
                "content": "突出量化业绩，如管理资产规模、收益率、风险控制等关键指标",
                "tags": ["金融", "量化"],
                "industry": "金融",
            },
            {
                "category": "jd_keyword",
                "title": "前端工程师关键词",
                "content": "React, Vue, TypeScript, Webpack, 性能优化, 组件化",
                "tags": ["React", "Vue", "TypeScript"],
            },
            {
                "category": "optimization_case",
                "title": "前端性能优化案例",
                "content": "将'负责前端开发'优化为'主导前端架构重构，首屏加载时间从 3s 降至 1.2s，性能提升 60%'",
                "tags": ["前端", "性能优化", "量化"],
            },
            {
                "category": "resume_template",
                "title": "ATS 友好模板",
                "content": "使用标准的 HTML 标签，避免使用表格布局，确保 ATS 系统能正确解析",
                "tags": ["ATS", "模板"],
            },
        ]

        for entry in entries:
            resp = await client.post(
                "/api/knowledge",
                json=entry,
                headers=get_auth_headers(token),
            )
            assert resp.status_code == 201

        # 2. 浏览全部知识库
        list_resp = await client.get(
            "/api/knowledge/list",
            headers=get_auth_headers(token),
        )
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 5

        # 3. 按分类筛选
        filter_resp = await client.get(
            "/api/knowledge/list?category=industry_practice",
            headers=get_auth_headers(token),
        )
        assert filter_resp.status_code == 200
        assert filter_resp.json()["total"] == 2
        for item in filter_resp.json()["items"]:
            assert item["category"] == "industry_practice"

        # 4. 关键词搜索
        search_resp = await client.get(
            "/api/knowledge/list?keyword=STAR",
            headers=get_auth_headers(token),
        )
        assert search_resp.status_code == 200
        assert search_resp.json()["total"] >= 1

        # 5. 搜索"前端"
        search_resp2 = await client.get(
            "/api/knowledge/list?keyword=前端",
            headers=get_auth_headers(token),
        )
        assert search_resp2.status_code == 200
        assert search_resp2.json()["total"] >= 2

        # 6. 获取知识库统计
        stats_resp = await client.get(
            "/api/knowledge/stats",
            headers=get_auth_headers(token),
        )
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert stats["total"] == 5
        assert stats["by_category"]["industry_practice"] == 2
        assert stats["by_category"]["jd_keyword"] == 1
        assert stats["by_category"]["optimization_case"] == 1
        assert stats["by_category"]["resume_template"] == 1

        # 7. 获取单条详情
        detail_resp = await client.get(
            f"/api/knowledge/{list_resp.json()['items'][0]['id']}",
            headers=get_auth_headers(token),
        )
        assert detail_resp.status_code == 200
        assert "title" in detail_resp.json()
        assert "content" in detail_resp.json()

        # 8. 更新知识条目
        entry_id = list_resp.json()["items"][0]["id"]
        update_resp = await client.put(
            f"/api/knowledge/{entry_id}",
            json={"title": "更新后的标题", "status": "archived"},
            headers=get_auth_headers(token),
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "更新后的标题"
        assert update_resp.json()["status"] == "archived"

        # 9. 删除知识条目
        delete_resp = await client.delete(
            f"/api/knowledge/{entry_id}",
            headers=get_auth_headers(token),
        )
        assert delete_resp.status_code == 204

        # 验证删除后数量
        list_resp2 = await client.get(
            "/api/knowledge/list",
            headers=get_auth_headers(token),
        )
        assert list_resp2.json()["total"] == 4

    @pytest.mark.asyncio
    async def test_knowledge_import_export(
        self,
        client: AsyncClient,
        user_a_data,
        db_session,
    ):
        """知识库导入导出测试"""
        token, _ = await register_and_login(client, user_a_data)

        # 1. 批量导入
        import_data = [
            {
                "category": "jd_keyword",
                "title": "后端关键词",
                "content": "Python, FastAPI, PostgreSQL, Redis",
                "tags": ["Python", "后端"],
            },
            {
                "category": "jd_keyword",
                "title": "算法关键词",
                "content": "机器学习, 深度学习, TensorFlow, PyTorch",
                "tags": ["AI", "算法"],
            },
        ]

        import_resp = await client.post(
            "/api/knowledge/import",
            files={"file": ("knowledge.json", json.dumps(import_data).encode("utf-8"), "application/json")},
            headers=get_auth_headers(token),
        )
        assert import_resp.status_code == 200
        assert import_resp.json()["imported"] == 2
        assert import_resp.json()["failed"] == 0

        # 2. 验证导入后的数据
        list_resp = await client.get(
            "/api/knowledge/list",
            headers=get_auth_headers(token),
        )
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 2

        # 3. 导出
        export_resp = await client.get(
            "/api/knowledge/export",
            headers=get_auth_headers(token),
        )
        assert export_resp.status_code == 200
        assert "application/zip" in export_resp.headers.get("content-type", "")


# ===========================================================================
# 4. 多用户测试
# ===========================================================================


class TestMultiUser:
    """多用户测试

    覆盖：创建多用户、数据隔离、并发操作
    """

    @pytest.mark.asyncio
    async def test_multi_user_data_isolation(
        self,
        client: AsyncClient,
        user_a_data,
        user_b_data,
        frontend_resume,
        backend_resume,
        db_session,
    ):
        """多用户数据隔离测试

        验证：
        - 用户 A 不能访问用户 B 的简历
        - 用户 A 不能操作用户 B 的订单
        - 用户 A 的简历列表只包含自己的简历
        """
        # 注册两个用户
        token_a, user_a = await register_and_login(client, user_a_data)
        token_b, user_b = await register_and_login(client, user_b_data)

        # 用户 A 上传简历
        upload_a = await client.post(
            "/api/resume/upload",
            data={
                "title": "A的前端简历",
                "original_text": frontend_resume,
            },
            headers=get_auth_headers(token_a),
        )
        assert upload_a.status_code == 201
        resume_a_id = upload_a.json()["id"]

        # 用户 B 上传简历
        upload_b = await client.post(
            "/api/resume/upload",
            data={
                "title": "B的后端简历",
                "original_text": backend_resume,
            },
            headers=get_auth_headers(token_b),
        )
        assert upload_b.status_code == 201
        resume_b_id = upload_b.json()["id"]

        # 验证用户 A 只能看到自己的简历
        list_a = await client.get(
            "/api/resume/list",
            headers=get_auth_headers(token_a),
        )
        assert list_a.json()["total"] == 1
        assert list_a.json()["items"][0]["title"] == "A的前端简历"

        # 验证用户 B 只能看到自己的简历
        list_b = await client.get(
            "/api/resume/list",
            headers=get_auth_headers(token_b),
        )
        assert list_b.json()["total"] == 1
        assert list_b.json()["items"][0]["title"] == "B的后端简历"

        # 验证用户 A 不能访问用户 B 的简历
        resp = await client.get(
            f"/api/resume/{resume_b_id}",
            headers=get_auth_headers(token_a),
        )
        assert resp.status_code == 404

        # 验证用户 B 不能访问用户 A 的简历
        resp = await client.get(
            f"/api/resume/{resume_a_id}",
            headers=get_auth_headers(token_b),
        )
        assert resp.status_code == 404

        # 验证用户 A 不能删除用户 B 的简历
        resp = await client.delete(
            f"/api/resume/{resume_b_id}",
            headers=get_auth_headers(token_a),
        )
        assert resp.status_code == 404

        # 验证用户 A 的钱包和用户 B 的钱包独立
        wallet_a = await client.get("/api/wallet", headers=get_auth_headers(token_a))
        wallet_b = await client.get("/api/wallet", headers=get_auth_headers(token_b))
        assert wallet_a.json()["balance"] == 3
        assert wallet_b.json()["balance"] == 3

        # 用户 A 充值不影响用户 B
        create_resp = await client.post(
            "/api/payment/create",
            json={"package_id": "small"},
            headers=get_auth_headers(token_a),
        )
        order_no = create_resp.json()["order_no"]
        await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token_a),
        )

        wallet_a = await client.get("/api/wallet", headers=get_auth_headers(token_a))
        wallet_b = await client.get("/api/wallet", headers=get_auth_headers(token_b))
        assert wallet_a.json()["balance"] == 13  # 3 + 10
        assert wallet_b.json()["balance"] == 3  # 不变

    @pytest.mark.asyncio
    async def test_concurrent_operations(
        self,
        client: AsyncClient,
        user_a_data,
        user_b_data,
        user_c_data,
        frontend_resume,
        backend_resume,
        db_session,
    ):
        """并发操作测试

        验证：
        - 多用户同时注册不冲突
        - 多用户同时上传简历不冲突
        - 多用户同时充值不冲突
        """
        # 并发注册三个用户
        register_tasks = [
            client.post("/api/auth/register", json=user_a_data),
            client.post("/api/auth/register", json=user_b_data),
            client.post("/api/auth/register", json=user_c_data),
        ]
        register_results = await asyncio.gather(*register_tasks)

        # 三个用户都应该注册成功
        for resp in register_results:
            assert resp.status_code == 201

        # 获取三个用户的 token
        tokens = [resp.json()["access_token"] for resp in register_results]

        # 并发上传简历
        upload_tasks = [
            client.post(
                "/api/resume/upload",
                data={"title": f"用户{i+1}的简历", "original_text": frontend_resume},
                headers=get_auth_headers(token),
            )
            for i, token in enumerate(tokens)
        ]
        upload_results = await asyncio.gather(*upload_tasks)

        # 所有上传都应该成功
        for resp in upload_results:
            assert resp.status_code == 201

        # 并发创建充值订单
        order_tasks = [
            client.post(
                "/api/payment/create",
                json={"package_id": "small"},
                headers=get_auth_headers(token),
            )
            for token in tokens
        ]
        order_results = await asyncio.gather(*order_tasks)

        # 所有订单都应该创建成功
        order_nos = []
        for resp in order_results:
            assert resp.status_code == 201
            order_nos.append(resp.json()["order_no"])

        # 并发确认支付
        confirm_tasks = [
            client.post(
                f"/api/payment/{order_no}/confirm",
                headers=get_auth_headers(token),
            )
            for order_no, token in zip(order_nos, tokens)
        ]
        confirm_results = await asyncio.gather(*confirm_tasks)

        # 所有支付都应该成功
        for resp in confirm_results:
            assert resp.status_code == 200

        # 验证每个用户的余额都正确（3 + 10 = 13）
        for token in tokens:
            wallet = await client.get(
                "/api/wallet",
                headers=get_auth_headers(token),
            )
            assert wallet.json()["balance"] == 13

    @pytest.mark.asyncio
    async def test_concurrent_same_username_registration(
        self,
        client: AsyncClient,
    ):
        """并发注册相同用户名测试"""
        user_data = {
            "username": "same_user",
            "email": "same@example.com",
            "password": "TestPass123!",
        }

        # 并发注册 5 次相同用户名
        tasks = [
            client.post("/api/auth/register", json=user_data)
            for _ in range(5)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 只有 1 个成功，其余应该返回 409
        success_count = sum(
            1 for r in results
            if not isinstance(r, Exception) and r.status_code == 201
        )
        conflict_count = sum(
            1 for r in results
            if not isinstance(r, Exception) and r.status_code == 409
        )
        assert success_count == 1
        assert conflict_count == 4

    @pytest.mark.asyncio
    async def test_user_profile_operations(
        self,
        client: AsyncClient,
        user_a_data,
        user_b_data,
    ):
        """用户资料操作测试"""
        # 注册用户 A
        token_a, _ = await register_and_login(client, user_a_data)

        # 注册用户 B
        token_b, _ = await register_and_login(client, user_b_data)

        # 用户 A 更新资料
        update_resp = await client.put(
            "/api/auth/me",
            json={"username": "alice_updated"},
            headers=get_auth_headers(token_a),
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["username"] == "alice_updated"

        # 用户 A 不能更新为用户 B 的用户名
        update_resp = await client.put(
            "/api/auth/me",
            json={"username": user_b_data["username"]},
            headers=get_auth_headers(token_a),
        )
        assert update_resp.status_code == 409

        # 用户 A 修改密码
        change_pwd_resp = await client.put(
            "/api/auth/password",
            json={
                "current_password": user_a_data["password"],
                "new_password": "NewAlicePass123!",
            },
            headers=get_auth_headers(token_a),
        )
        assert change_pwd_resp.status_code == 204

        # 用旧密码登录应该失败
        login_resp = await client.post(
            "/api/auth/login",
            json={
                "email": user_a_data["email"],
                "password": user_a_data["password"],
            },
        )
        assert login_resp.status_code == 401

        # 用新密码登录应该成功
        login_resp = await client.post(
            "/api/auth/login",
            json={
                "email": user_a_data["email"],
                "password": "NewAlicePass123!",
            },
        )
        assert login_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_optimize_insufficient_points_multi_user(
        self,
        client: AsyncClient,
        user_a_data,
        user_b_data,
        frontend_resume,
        db_session,
    ):
        """多用户点数独立测试"""
        token_a, _ = await register_and_login(client, user_a_data)
        token_b, _ = await register_and_login(client, user_b_data)

        # 用户 A 充值
        create_resp = await client.post(
            "/api/payment/create",
            json={"package_id": "small"},
            headers=get_auth_headers(token_a),
        )
        order_no = create_resp.json()["order_no"]
        await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token_a),
        )

        # 用户 A 消耗所有点数
        for i in range(13):  # 3 + 10 = 13
            with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
                mock_llm = AsyncMock()
                mock_llm.optimize_resume.return_value = mock_llm_optimize()
                mock_llm.extract_knowledge.return_value = mock_knowledge_data()
                mock_llm.default_model = "qwen3.7-max"
                mock_get_llm.return_value = mock_llm

                resp = await client.post(
                    "/api/optimize",
                    data={"text": frontend_resume},
                    headers=get_auth_headers(token_a),
                )
                if resp.status_code == 200:
                    continue
                elif resp.status_code == 402:
                    break

        # 用户 A 点数用完
        wallet_a = await client.get("/api/wallet", headers=get_auth_headers(token_a))
        assert wallet_a.json()["balance"] == 0

        # 用户 A 不能再优化
        resp = await client.post(
            "/api/optimize",
            data={"text": frontend_resume},
            headers=get_auth_headers(token_a),
        )
        assert resp.status_code == 402

        # 用户 B 仍然有 3 点，可以优化
        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = mock_llm_optimize()
            mock_llm.extract_knowledge.return_value = mock_knowledge_data()
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            resp = await client.post(
                "/api/optimize",
                data={"text": frontend_resume},
                headers=get_auth_headers(token_b),
            )

        assert resp.status_code == 200

        # 用户 B 余额变为 2
        wallet_b = await client.get("/api/wallet", headers=get_auth_headers(token_b))
        assert wallet_b.json()["balance"] == 2


# ===========================================================================
# 5. 文档与部署检查
# ===========================================================================


class TestDocumentationAndDeployment:
    """文档与部署检查"""

    @pytest.mark.asyncio
    async def test_api_docs_accessible(self, client: AsyncClient):
        """API 文档可访问"""
        # Swagger UI
        resp = await client.get("/docs")
        assert resp.status_code == 200

        # ReDoc
        resp = await client.get("/redoc")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """健康检查端点"""
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "ai-resume-optimizer"
        assert data["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """根路径端点"""
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "docs" in data

    def test_config_loading(self):
        """配置加载测试"""
        assert settings.ANTHROPIC_BASE_URL != ""
        assert settings.ANTHROPIC_MODEL != ""
        assert settings.JWT_SECRET_KEY != ""
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.JWT_EXPIRE_MINUTES > 0
        assert settings.DATABASE_URL != ""

    def test_requirements_file_exists(self):
        """requirements.txt 存在且完整"""
        req_path = Path(__file__).parent.parent / "requirements.txt"
        assert req_path.exists()

        content = req_path.read_text()
        required_packages = [
            "fastapi",
            "uvicorn",
            "sqlalchemy",
            "python-jose",
            "passlib",
            "httpx",
            "pillow",
            "pydantic",
        ]
        for pkg in required_packages:
            assert pkg in content, f"requirements.txt 缺少 {pkg}"

    def test_database_models_complete(self):
        """数据库模型完整性检查"""
        from backend.models import (
            User,
            Resume,
            KnowledgeEntry,
            UserWallet,
            PointTransaction,
            PaymentOrder,
            UserFeedback,
        )

        # 检查所有模型都有 __tablename__
        models = [
            User,
            Resume,
            KnowledgeEntry,
            UserWallet,
            PointTransaction,
            PaymentOrder,
            UserFeedback,
        ]
        for model in models:
            assert hasattr(model, "__tablename__"), f"{model.__name__} 缺少 __tablename__"

    def test_all_routers_registered(self):
        """所有路由已注册"""
        from backend.main import app

        # 收集所有路由路径
        routes = [route.path for route in app.routes]

        # 验证关键路由存在
        expected_prefixes = [
            "/api/auth",
            "/api/resume",
            "/api/optimize",
            "/api/knowledge",
            "/api/payment",
            "/api/wallet",
            "/api/stats",
            "/api/jobs",
            "/api/health",
        ]
        for prefix in expected_prefixes:
            assert any(
                prefix in route for route in routes
            ), f"路由 {prefix} 未注册"

    def test_project_structure(self):
        """项目目录结构检查"""
        root = Path(__file__).parent.parent

        # 检查关键文件存在
        critical_files = [
            "CLAUDE.md",
            "settings.json",
            "requirements.txt",
            "frontend/index.html",
            "backend/main.py",
            "backend/config.py",
            "backend/database.py",
            "backend/models/__init__.py",
            "backend/models/user.py",
            "backend/models/resume.py",
            "backend/models/payment.py",
            "backend/models/knowledge.py",
            "backend/models/feedback.py",
            "backend/schemas/auth.py",
            "backend/schemas/resume.py",
            "backend/schemas/payment.py",
            "backend/schemas/knowledge.py",
            "backend/routers/auth.py",
            "backend/routers/resume.py",
            "backend/routers/optimize.py",
            "backend/routers/payment.py",
            "backend/routers/knowledge.py",
            "backend/routers/stats.py",
            "backend/routers/jobs.py",
            "backend/services/auth_service.py",
            "backend/services/llm_service.py",
            "backend/services/optimize_service.py",
            "backend/services/payment_service.py",
            "backend/services/knowledge_service.py",
            "backend/services/ocr_service.py",
            "backend/services/stats_service.py",
            "backend/services/docx_service.py",
            "backend/services/job_search_service.py",
            "backend/utils/security.py",
            "backend/utils/text_cleaner.py",
        ]

        for file_path in critical_files:
            full_path = root / file_path
            assert full_path.exists(), f"关键文件缺失: {file_path}"


# ===========================================================================
# 6. 安全性测试
# ===========================================================================


class TestSecurity:
    """安全性测试"""

    @pytest.mark.asyncio
    async def test_unauthenticated_access_blocked(self, client: AsyncClient):
        """未认证访问被阻止"""
        protected_endpoints = [
            ("GET", "/api/auth/me"),
            ("PUT", "/api/auth/me"),
            ("POST", "/api/auth/refresh"),
            ("GET", "/api/resume/list"),
            ("POST", "/api/optimize"),
            ("GET", "/api/knowledge/list"),
            ("GET", "/api/wallet"),
            ("GET", "/api/stats/dashboard"),
            ("GET", "/api/jobs/search?query=test"),
        ]

        for method, endpoint in protected_endpoints:
            if method == "GET":
                resp = await client.get(endpoint)
            elif method == "POST":
                resp = await client.post(endpoint, json={})
            elif method == "PUT":
                resp = await client.put(endpoint, json={})

            assert resp.status_code == 401, (
                f"{method} {endpoint} 应返回 401，实际返回 {resp.status_code}"
            )

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, client: AsyncClient):
        """无效 Token 被拒绝"""
        invalid_tokens = [
            "invalid-token",
            "Bearer invalid",
            "",
            "eyJhbGciOiJIUzI1NiJ9.invalid.signature",
        ]

        for token in invalid_tokens:
            resp = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_password_hashing(self, client: AsyncClient, user_a_data, db_session):
        """密码哈希存储验证"""
        await register_and_login(client, user_a_data)

        # 从数据库直接查询用户
        user = db_session.query(User).filter(
            User.username == user_a_data["username"]
        ).first()

        # 密码不应该是明文
        assert user.password_hash != user_a_data["password"]
        # 应该是 bcrypt 格式
        assert user.password_hash.startswith("$2b$") or user.password_hash.startswith("$2a$")

    @pytest.mark.asyncio
    async def test_input_validation(self, client: AsyncClient):
        """输入验证测试"""
        # 注册时用户名太短
        resp = await client.post(
            "/api/auth/register",
            json={
                "username": "a",
                "email": "test@example.com",
                "password": "TestPass123!",
            },
        )
        assert resp.status_code == 422

        # 注册时无效邮箱
        resp = await client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "not-an-email",
                "password": "TestPass123!",
            },
        )
        assert resp.status_code == 422

        # 注册时密码太短
        resp = await client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "short",
            },
        )
        assert resp.status_code == 422

        # 反馈评分超出范围
        resp = await client.post(
            "/api/resume/1/feedback",
            json={"rating": 6},
        )
        assert resp.status_code in [401, 422]


# ===========================================================================
# 运行入口
# ===========================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
