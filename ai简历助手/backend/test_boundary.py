"""
Phase 6: 边界情况测试模块

覆盖以下边界场景：
1. 输入验证边界（空表单、超长文本、特殊字符、非法文件类型、超大文件）
2. 认证边界（Token 过期、无效 Token、并发登录）
3. 业务边界（点数为 0、重复提交、并发操作、删除正在优化的简历）
4. 网络/错误边界（LLM 超时、LLM 错误、服务器错误处理）
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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

TEST_DATABASE_URL = "sqlite:///./test_boundary.db"

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
def test_user_data():
    """测试用户数据"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!",
    }


@pytest.fixture
def test_user_data_2():
    """第二个测试用户数据"""
    return {
        "username": "testuser2",
        "email": "test2@example.com",
        "password": "TestPass456!",
    }


@pytest.fixture
def sample_resume_text():
    """示例简历文本"""
    return """
    张三
    前端工程师
    手机：13800138000
    邮箱：zhangsan@example.com

    教育背景
    北京大学 计算机科学与技术 本科 2018-2022

    工作经历
    2022-至今 ABC科技有限公司 前端工程师
    - 负责公司核心产品的前端开发
    - 使用 React + TypeScript 开发 Web 应用
    - 优化页面性能，首屏加载时间减少 40%
    """


@pytest.fixture
def sample_jd():
    """示例岗位 JD"""
    return """
    高级前端工程师

    岗位职责：
    1. 负责公司核心产品的前端架构设计和开发
    2. 优化前端性能，提升用户体验

    任职要求：
    1. 3年以上前端开发经验
    2. 精通 React 或 Vue 框架
    3. 熟悉 TypeScript
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
    """获取认证头"""
    return {"Authorization": f"Bearer {token}"}


def create_expired_token(user_id: int) -> str:
    """创建已过期的 JWT Token"""
    return create_access_token(
        data={"sub": str(user_id)},
        expires_delta=timedelta(seconds=-1),  # 已过期
    )


# ===========================================================================
# 1. 输入验证边界测试
# ===========================================================================


class TestInputValidation:
    """输入验证边界测试"""

    # -----------------------------------------------------------------------
    # 空表单 / 缺少必要字段
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_optimize_no_text_no_file(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """优化接口：既没有 text 也没有 file，应返回 400"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/optimize",
            data={},
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400
        assert "简历文本或上传图片" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_no_text_no_file(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """上传接口：既没有 original_text 也没有 file，应返回 400"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/resume/upload",
            data={"title": "测试简历"},
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400
        assert "简历文本或上传图片" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_empty_title(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """上传接口：空标题，应返回 400"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/resume/upload",
            data={
                "title": "",
                "original_text": "测试内容",
            },
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_no_title(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """上传接口：缺少标题字段，应返回 400"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/resume/upload",
            data={"original_text": "测试内容"},
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_empty_username(
        self,
        client: AsyncClient,
    ):
        """注册接口：空用户名，应返回 422"""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "",
                "email": "test@example.com",
                "password": "TestPass123!",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_password(
        self,
        client: AsyncClient,
    ):
        """注册接口：密码太短（<6字符），应返回 422"""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "12345",  # 5 字符，低于最小值 6
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_email(
        self,
        client: AsyncClient,
    ):
        """注册接口：无效邮箱格式，应返回 422"""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "not-an-email",
                "password": "TestPass123!",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """登录接口：错误密码，应返回 401"""
        await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/auth/login",
            json={
                "email": test_user_data["email"],
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_email(
        self,
        client: AsyncClient,
    ):
        """登录接口：不存在的邮箱，应返回 401"""
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "TestPass123!",
            },
        )
        assert response.status_code == 401

    # -----------------------------------------------------------------------
    # 超长文本输入
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_optimize_very_large_text(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """优化接口：超长简历文本（~1MB），应正常处理或返回明确错误"""
        token, _ = await register_and_login(client, test_user_data)

        # 创建约 1MB 的文本
        large_text = "这是一段测试文本，用于验证超长输入的处理能力。" * 50000

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = {
                "optimized_html": "<html><body>优化后简历</body></html>",
                "optimization_score": 85.0,
                "changes_summary": ["优化了内容"],
                "pros": ["内容丰富"],
                "cons": [],
                "star_rewrites": 1,
                "quantifications": 1,
                "keywords_matched": 2,
            }
            mock_llm.extract_knowledge.return_value = {
                "patterns": [],
                "jd_keywords": [],
                "industry": "互联网",
                "job_level": "mid",
            }
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            response = await client.post(
                "/api/optimize",
                data={"text": large_text},
                headers=get_auth_headers(token),
            )

        # 应该成功或返回明确的业务错误（如点数不足），但不应 500
        assert response.status_code in (200, 400, 402)

    @pytest.mark.asyncio
    async def test_upload_very_long_title(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """上传接口：超长标题（200字符），应返回 422（max_length=100）"""
        token, _ = await register_and_login(client, test_user_data)

        long_title = "A" * 200  # 超过 max_length=100

        response = await client.post(
            "/api/resume/upload",
            data={
                "title": long_title,
                "original_text": "测试内容",
            },
            headers=get_auth_headers(token),
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_long_city_name(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """上传接口：超长城市名（100字符），应返回 422（max_length=50）"""
        token, _ = await register_and_login(client, test_user_data)

        long_city = "城" * 100

        response = await client.post(
            "/api/resume/upload",
            data={
                "title": "测试简历",
                "original_text": "测试内容",
                "target_city": long_city,
            },
            headers=get_auth_headers(token),
        )
        assert response.status_code == 422

    # -----------------------------------------------------------------------
    # 特殊字符输入
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_resume_with_xss_payload(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """简历内容包含 XSS payload，应安全存储"""
        token, _ = await register_and_login(client, test_user_data)

        xss_text = """
        <script>alert('XSS')</script>
        <img onerror="alert(1)" src="x">
        <a href="javascript:void(0)">Click</a>
        正常简历内容
        """

        response = await client.post(
            "/api/resume/upload",
            data={
                "title": "XSS测试简历",
                "original_text": xss_text,
            },
            headers=get_auth_headers(token),
        )
        assert response.status_code == 201

        # 验证内容被安全存储（原样存储，优化时消毒）
        resume_id = response.json()["id"]
        get_response = await client.get(
            f"/api/resume/{resume_id}",
            headers=get_auth_headers(token),
        )
        assert get_response.status_code == 200
        # original_text 应保留（存储原始内容，输出时消毒）
        assert "正常简历内容" in get_response.json()["original_text"]

    @pytest.mark.asyncio
    async def test_resume_with_unicode_emoji(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """简历内容包含 Unicode emoji，应正确处理"""
        token, _ = await register_and_login(client, test_user_data)

        emoji_text = "张三 🚀 前端工程师 💻 熟练掌握 React 🎯"

        response = await client.post(
            "/api/resume/upload",
            data={
                "title": "Emoji简历 📄",
                "original_text": emoji_text,
            },
            headers=get_auth_headers(token),
        )
        assert response.status_code == 201

        # 验证 emoji 正确保留
        resume_id = response.json()["id"]
        get_response = await client.get(
            f"/api/resume/{resume_id}",
            headers=get_auth_headers(token),
        )
        assert get_response.status_code == 200
        assert "🚀" in get_response.json()["original_text"]
        assert "📄" in get_response.json()["title"]

    @pytest.mark.asyncio
    async def test_resume_with_sql_injection_attempt(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """简历内容包含 SQL 注入尝试，应安全处理"""
        token, _ = await register_and_login(client, test_user_data)

        sql_injection = "'; DROP TABLE resumes; --"

        response = await client.post(
            "/api/resume/upload",
            data={
                "title": "SQL注入测试",
                "original_text": sql_injection,
            },
            headers=get_auth_headers(token),
        )
        assert response.status_code == 201

        # 验证数据正常存储，SQL 注入未生效
        resume_id = response.json()["id"]
        get_response = await client.get(
            f"/api/resume/{resume_id}",
            headers=get_auth_headers(token),
        )
        assert get_response.status_code == 200
        assert get_response.json()["original_text"] == sql_injection

        # 验证表仍然存在（SQL 注入未生效）
        list_response = await client.get(
            "/api/resume/list",
            headers=get_auth_headers(token),
        )
        assert list_response.status_code == 200

    @pytest.mark.asyncio
    async def test_resume_with_null_bytes(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """简历内容包含 null 字节，应安全处理"""
        token, _ = await register_and_login(client, test_user_data)

        null_text = "张三\x00前端工程师"

        response = await client.post(
            "/api/resume/upload",
            data={
                "title": "Null字节测试",
                "original_text": null_text,
            },
            headers=get_auth_headers(token),
        )
        # 应成功或返回明确错误，不应 500
        assert response.status_code in (201, 400, 422)

    # -----------------------------------------------------------------------
    # 非法文件类型 / 超大文件
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """上传非法文件类型（PDF），应返回 400"""
        token, _ = await register_and_login(client, test_user_data)

        # 模拟上传 PDF 文件
        files = {
            "file": ("resume.pdf", b"fake pdf content", "application/pdf"),
        }
        response = await client.post(
            "/api/resume/upload",
            data={"title": "PDF简历"},
            files=files,
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400
        assert "仅支持 JPG 和 PNG" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type_text(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """上传非法文件类型（TXT），应返回 400"""
        token, _ = await register_and_login(client, test_user_data)

        files = {
            "file": ("resume.txt", b"plain text content", "text/plain"),
        }
        response = await client.post(
            "/api/resume/upload",
            data={"title": "TXT简历"},
            files=files,
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_oversized_file(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """上传超大文件（>10MB），应返回 413"""
        token, _ = await register_and_login(client, test_user_data)

        # 创建超过 10MB 的文件内容
        oversized_content = b"x" * (10 * 1024 * 1024 + 1)  # 10MB + 1 byte

        files = {
            "file": ("large.jpg", oversized_content, "image/jpeg"),
        }
        response = await client.post(
            "/api/resume/upload",
            data={"title": "超大文件"},
            files=files,
            headers=get_auth_headers(token),
        )
        assert response.status_code == 413

    @pytest.mark.asyncio
    async def test_optimize_invalid_file_type(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """优化接口：上传非法文件类型，应返回 400"""
        token, _ = await register_and_login(client, test_user_data)

        files = {
            "file": ("resume.gif", b"fake gif content", "image/gif"),
        }
        response = await client.post(
            "/api/optimize",
            data={},
            files=files,
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_optimize_oversized_file(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """优化接口：上传超大文件，应返回 413"""
        token, _ = await register_and_login(client, test_user_data)

        oversized_content = b"x" * (10 * 1024 * 1024 + 1)

        files = {
            "file": ("large.jpg", oversized_content, "image/jpeg"),
        }
        response = await client.post(
            "/api/optimize",
            data={},
            files=files,
            headers=get_auth_headers(token),
        )
        assert response.status_code == 413

    # -----------------------------------------------------------------------
    # 分页参数边界
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_resume_list_invalid_page_zero(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """简历列表：page=0，应返回 400"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/resume/list?page=0",
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_resume_list_invalid_page_negative(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """简历列表：page=-1，应返回 400"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/resume/list?page=-1",
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_resume_list_invalid_page_size_zero(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """简历列表：page_size=0，应返回 400"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/resume/list?page_size=0",
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_resume_list_invalid_page_size_too_large(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """简历列表：page_size=100（超过上限50），应返回 400"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/resume/list?page_size=100",
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400

    # -----------------------------------------------------------------------
    # 评分边界
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_feedback_rating_zero(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """反馈接口：rating=0（低于最小值1），应返回 422"""
        token, user_info = await register_and_login(client, test_user_data)

        # 创建一个已完成的简历
        resume = Resume(
            user_id=user_info["id"],
            title="测试简历",
            original_text="内容",
            status="completed",
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)

        response = await client.post(
            f"/api/resume/{resume.id}/feedback",
            json={"rating": 0},
            headers=get_auth_headers(token),
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_feedback_rating_six(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """反馈接口：rating=6（超过最大值5），应返回 422"""
        token, user_info = await register_and_login(client, test_user_data)

        resume = Resume(
            user_id=user_info["id"],
            title="测试简历",
            original_text="内容",
            status="completed",
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)

        response = await client.post(
            f"/api/resume/{resume.id}/feedback",
            json={"rating": 6},
            headers=get_auth_headers(token),
        )
        assert response.status_code == 422

    # -----------------------------------------------------------------------
    # 优化强度边界
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_optimize_strength_zero(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """优化接口：strength=0（低于最小值1），应返回 422"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/optimize",
            data={"text": "测试简历", "strength": 0},
            headers=get_auth_headers(token),
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_optimize_strength_six(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """优化接口：strength=6（超过最大值5），应返回 422"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/optimize",
            data={"text": "测试简历", "strength": 6},
            headers=get_auth_headers(token),
        )
        assert response.status_code == 422


# ===========================================================================
# 2. 认证边界测试
# ===========================================================================


class TestAuthBoundaries:
    """认证边界测试"""

    @pytest.mark.asyncio
    async def test_expired_token(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """已过期的 Token 应返回 401"""
        # 注册用户
        register_response = await client.post(
            "/api/auth/register",
            json=test_user_data,
        )
        assert register_response.status_code == 201
        user_id = register_response.json()["user"]["id"]

        # 创建已过期的 Token
        expired_token = create_expired_token(user_id)

        response = await client.get(
            "/api/auth/me",
            headers=get_auth_headers(expired_token),
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_malformed(
        self,
        client: AsyncClient,
    ):
        """格式错误的 Token 应返回 401"""
        response = await client.get(
            "/api/auth/me",
            headers=get_auth_headers("not.a.valid.jwt.token"),
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_random_string(
        self,
        client: AsyncClient,
    ):
        """随机字符串作为 Token 应返回 401"""
        response = await client.get(
            "/api/auth/me",
            headers=get_auth_headers("random-garbage-string"),
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_bearer_prefix(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """缺少 Bearer 前缀的 Authorization 头应返回 401"""
        token, _ = await register_and_login(client, test_user_data)

        # 直接使用 token，不带 "Bearer " 前缀
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": token},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_authorization_header(
        self,
        client: AsyncClient,
    ):
        """空 Authorization 头应返回 401"""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": ""},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_with_nonexistent_user(
        self,
        client: AsyncClient,
    ):
        """Token 中的用户 ID 不存在，应返回 401"""
        # 创建一个引用不存在用户的 Token
        fake_token = create_access_token(data={"sub": "99999"})

        response = await client.get(
            "/api/auth/me",
            headers=get_auth_headers(fake_token),
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_without_sub_field(
        self,
        client: AsyncClient,
    ):
        """Token 中没有 sub 字段，应返回 401"""
        from jose import jwt

        # 手动创建没有 sub 字段的 Token
        token = jwt.encode(
            {"user_id": 1, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        response = await client.get(
            "/api/auth/me",
            headers=get_auth_headers(token),
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_deactivated_user_token(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """已停用用户的 Token 应返回 403"""
        # 注册用户
        register_response = await client.post(
            "/api/auth/register",
            json=test_user_data,
        )
        assert register_response.status_code == 201
        token = register_response.json()["access_token"]
        user_id = register_response.json()["user"]["id"]

        # 停用用户
        user = db_session.query(User).filter(User.id == user_id).first()
        user.is_active = False
        db_session.commit()

        response = await client.get(
            "/api/auth/me",
            headers=get_auth_headers(token),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_concurrent_login_same_user(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """同一用户并发登录，应都能成功并获得不同 Token"""
        # 先注册
        register_response = await client.post(
            "/api/auth/register",
            json=test_user_data,
        )
        assert register_response.status_code == 201

        # 并发登录
        login_tasks = [
            client.post(
                "/api/auth/login",
                json={
                    "email": test_user_data["email"],
                    "password": test_user_data["password"],
                },
            )
            for _ in range(5)
        ]

        responses = await asyncio.gather(*login_tasks)

        # 所有登录都应成功
        for resp in responses:
            assert resp.status_code == 200
            assert "access_token" in resp.json()

        # 所有 Token 都应该有效
        tokens = [r.json()["access_token"] for r in responses]
        for token in tokens:
            me_response = await client.get(
                "/api/auth/me",
                headers=get_auth_headers(token),
            )
            assert me_response.status_code == 200

    @pytest.mark.asyncio
    async def test_register_duplicate_username(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """重复用户名注册应返回 409"""
        await register_and_login(client, test_user_data)

        # 用相同用户名、不同邮箱再注册
        response = await client.post(
            "/api/auth/register",
            json={
                "username": test_user_data["username"],
                "email": "another@example.com",
                "password": "TestPass789!",
            },
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """重复邮箱注册应返回 409"""
        await register_and_login(client, test_user_data)

        # 用不同用户名、相同邮箱再注册
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "another_user",
                "email": test_user_data["email"],
                "password": "TestPass789!",
            },
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """修改密码时当前密码错误，应返回 400"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.put(
            "/api/auth/password",
            json={
                "current_password": "WrongPassword!",
                "new_password": "NewPass123!",
            },
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_change_password_then_login(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """修改密码后用新密码登录应成功，旧密码应失败"""
        token, _ = await register_and_login(client, test_user_data)

        # 修改密码
        change_response = await client.put(
            "/api/auth/password",
            json={
                "current_password": test_user_data["password"],
                "new_password": "NewPass123!",
            },
            headers=get_auth_headers(token),
        )
        assert change_response.status_code == 204

        # 用旧密码登录应失败
        old_login = await client.post(
            "/api/auth/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )
        assert old_login.status_code == 401

        # 用新密码登录应成功
        new_login = await client.post(
            "/api/auth/login",
            json={
                "email": test_user_data["email"],
                "password": "NewPass123!",
            },
        )
        assert new_login.status_code == 200


# ===========================================================================
# 3. 业务边界测试
# ===========================================================================


class TestBusinessBoundaries:
    """业务逻辑边界测试"""

    # -----------------------------------------------------------------------
    # 点数为 0 时优化
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_optimize_with_zero_points(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """点数为 0 时尝试优化，应返回 402"""
        token, user_info = await register_and_login(client, test_user_data)

        # 将用户点数设为 0
        wallet = db_session.query(UserWallet).filter(
            UserWallet.user_id == user_info["id"]
        ).first()
        wallet.balance = 0
        db_session.commit()

        response = await client.post(
            "/api/optimize",
            data={"text": "测试简历内容"},
            headers=get_auth_headers(token),
        )
        assert response.status_code == 402
        assert "点数不足" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_optimize_exactly_one_point(
        self,
        client: AsyncClient,
        test_user_data,
        sample_jd,
    ):
        """恰好有 1 点时优化应成功，优化后余额为 0"""
        token, user_info = await register_and_login(client, test_user_data)

        # 注册赠送 3 点，先消耗 2 点（做两次优化）
        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = {
                "optimized_html": "<html><body>优化后简历</body></html>",
                "optimization_score": 80.0,
                "changes_summary": ["优化了内容"],
                "pros": [],
                "cons": [],
                "star_rewrites": 0,
                "quantifications": 0,
                "keywords_matched": 0,
            }
            mock_llm.extract_knowledge.return_value = {
                "patterns": [],
                "jd_keywords": [],
                "industry": "互联网",
                "job_level": "mid",
            }
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            # 第一次优化（3 -> 2）
            resp1 = await client.post(
                "/api/optimize",
                data={"text": "简历1"},
                headers=get_auth_headers(token),
            )
            assert resp1.status_code == 200

            # 第二次优化（2 -> 1）
            resp2 = await client.post(
                "/api/optimize",
                data={"text": "简历2"},
                headers=get_auth_headers(token),
            )
            assert resp2.status_code == 200

            # 第三次优化（1 -> 0），应成功
            resp3 = await client.post(
                "/api/optimize",
                data={"text": "简历3"},
                headers=get_auth_headers(token),
            )
            assert resp3.status_code == 200

        # 验证余额为 0
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        assert wallet_response.status_code == 200
        assert wallet_response.json()["balance"] == 0

        # 第四次优化应失败（余额为 0）
        resp4 = await client.post(
            "/api/optimize",
            data={"text": "简历4"},
            headers=get_auth_headers(token),
        )
        assert resp4.status_code == 402

    # -----------------------------------------------------------------------
    # 重复提交优化
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_rapid_optimize_submissions(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """快速连续提交多次优化，应正确扣减点数"""
        token, user_info = await register_and_login(client, test_user_data)

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = {
                "optimized_html": "<html><body>优化</body></html>",
                "optimization_score": 80.0,
                "changes_summary": ["优化"],
                "pros": [],
                "cons": [],
                "star_rewrites": 0,
                "quantifications": 0,
                "keywords_matched": 0,
            }
            mock_llm.extract_knowledge.return_value = {
                "patterns": [],
                "jd_keywords": [],
                "industry": "互联网",
                "job_level": "mid",
            }
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            # 快速连续提交 3 次（刚好用完初始 3 点）
            responses = []
            for i in range(3):
                resp = await client.post(
                    "/api/optimize",
                    data={"text": f"简历{i+1}"},
                    headers=get_auth_headers(token),
                )
                responses.append(resp)

        # 前 3 次应成功
        for resp in responses:
            assert resp.status_code == 200

        # 验证余额为 0
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        assert wallet_response.json()["balance"] == 0

    # -----------------------------------------------------------------------
    # 删除简历边界
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_delete_nonexistent_resume(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """删除不存在的简历，应返回 404"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.delete(
            "/api/resume/99999",
            headers=get_auth_headers(token),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_other_users_resume(
        self,
        client: AsyncClient,
        test_user_data,
        test_user_data_2,
        db_session,
    ):
        """删除其他用户的简历，应返回 404"""
        token1, user1 = await register_and_login(client, test_user_data)
        token2, user2 = await register_and_login(client, test_user_data_2)

        # 用户1创建简历
        resume = Resume(
            user_id=user1["id"],
            title="用户1的简历",
            original_text="内容",
            status="pending",
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)

        # 用户2尝试删除
        response = await client.delete(
            f"/api/resume/{resume.id}",
            headers=get_auth_headers(token2),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_resume_with_children(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """删除有子版本的简历，应级联删除所有子版本"""
        token, user_info = await register_and_login(client, test_user_data)

        # 创建父简历
        parent = Resume(
            user_id=user_info["id"],
            title="原始简历",
            original_text="内容",
            status="completed",
            version=1,
        )
        db_session.add(parent)
        db_session.commit()
        db_session.refresh(parent)

        # 创建子版本
        child = Resume(
            user_id=user_info["id"],
            title="优化版本",
            original_text="内容",
            optimized_text="<html>优化后</html>",
            status="completed",
            version=2,
            parent_id=parent.id,
        )
        db_session.add(child)
        db_session.commit()

        # 删除父简历
        response = await client.delete(
            f"/api/resume/{parent.id}",
            headers=get_auth_headers(token),
        )
        assert response.status_code == 204

        # 验证子版本也被删除
        get_response = await client.get(
            f"/api/resume/{child.id}",
            headers=get_auth_headers(token),
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_resume(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """获取不存在的简历，应返回 404"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/resume/99999",
            headers=get_auth_headers(token),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_nonexistent_resume(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """更新不存在的简历，应返回 404"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.put(
            "/api/resume/99999",
            json={"title": "新标题"},
            headers=get_auth_headers(token),
        )
        assert response.status_code == 404

    # -----------------------------------------------------------------------
    # 跨用户访问
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_access_other_users_resume(
        self,
        client: AsyncClient,
        test_user_data,
        test_user_data_2,
        db_session,
    ):
        """访问其他用户的简历，应返回 404"""
        token1, user1 = await register_and_login(client, test_user_data)
        token2, user2 = await register_and_login(client, test_user_data_2)

        # 用户1创建简历
        resume = Resume(
            user_id=user1["id"],
            title="用户1的简历",
            original_text="内容",
            status="completed",
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)

        # 用户2尝试访问
        response = await client.get(
            f"/api/resume/{resume.id}",
            headers=get_auth_headers(token2),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_other_users_resume(
        self,
        client: AsyncClient,
        test_user_data,
        test_user_data_2,
        db_session,
    ):
        """更新其他用户的简历，应返回 404"""
        token1, user1 = await register_and_login(client, test_user_data)
        token2, user2 = await register_and_login(client, test_user_data_2)

        resume = Resume(
            user_id=user1["id"],
            title="用户1的简历",
            original_text="内容",
            status="completed",
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)

        response = await client.put(
            f"/api/resume/{resume.id}",
            json={"title": "被篡改的标题"},
            headers=get_auth_headers(token2),
        )
        assert response.status_code == 404

    # -----------------------------------------------------------------------
    # 反馈边界
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_duplicate_feedback(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """对同一简历重复提交反馈，第二次应返回 409"""
        token, user_info = await register_and_login(client, test_user_data)

        resume = Resume(
            user_id=user_info["id"],
            title="测试简历",
            original_text="内容",
            status="completed",
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)

        # 第一次反馈
        resp1 = await client.post(
            f"/api/resume/{resume.id}/feedback",
            json={"rating": 4, "comment": "不错"},
            headers=get_auth_headers(token),
        )
        assert resp1.status_code == 201

        # 第二次反馈应失败
        resp2 = await client.post(
            f"/api/resume/{resume.id}/feedback",
            json={"rating": 5, "comment": "很好"},
            headers=get_auth_headers(token),
        )
        assert resp2.status_code == 409

    @pytest.mark.asyncio
    async def test_feedback_on_nonexistent_resume(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """对不存在的简历提交反馈，应返回 404"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/resume/99999/feedback",
            json={"rating": 4},
            headers=get_auth_headers(token),
        )
        assert response.status_code == 404

    # -----------------------------------------------------------------------
    # 对话微调边界
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_chat_nonexistent_resume(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """对不存在的简历进行对话微调，应返回 404"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/optimize/chat",
            json={
                "resume_id": 99999,
                "message": "请修改简历",
            },
            headers=get_auth_headers(token),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_chat_other_users_resume(
        self,
        client: AsyncClient,
        test_user_data,
        test_user_data_2,
        db_session,
    ):
        """对其他用户的简历进行对话微调，应返回 404"""
        token1, user1 = await register_and_login(client, test_user_data)
        token2, user2 = await register_and_login(client, test_user_data_2)

        resume = Resume(
            user_id=user1["id"],
            title="用户1的简历",
            original_text="内容",
            optimized_text="<html>优化后</html>",
            status="completed",
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)

        response = await client.post(
            "/api/optimize/chat",
            json={
                "resume_id": resume.id,
                "message": "请修改简历",
            },
            headers=get_auth_headers(token2),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_chat_on_pending_resume(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """对状态为 pending 的简历进行对话微调，应返回 400"""
        token, user_info = await register_and_login(client, test_user_data)

        resume = Resume(
            user_id=user_info["id"],
            title="待处理简历",
            original_text="内容",
            status="pending",
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)

        response = await client.post(
            "/api/optimize/chat",
            json={
                "resume_id": resume.id,
                "message": "请修改简历",
            },
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400
        assert "尚未完成优化" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_chat_on_processing_resume(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """对状态为 processing 的简历进行对话微调，应返回 400"""
        token, user_info = await register_and_login(client, test_user_data)

        resume = Resume(
            user_id=user_info["id"],
            title="处理中简历",
            original_text="内容",
            status="processing",
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)

        response = await client.post(
            "/api/optimize/chat",
            json={
                "resume_id": resume.id,
                "message": "请修改简历",
            },
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_chat_exceeds_max_rounds(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """对话微调超过 10 轮限制，应返回 400"""
        token, user_info = await register_and_login(client, test_user_data)

        resume = Resume(
            user_id=user_info["id"],
            title="测试简历",
            original_text="内容",
            optimized_text="<html>优化后</html>",
            status="completed",
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)

        # 构造 10 轮对话历史（已有 10 轮 user 消息）
        history = []
        for i in range(10):
            history.append({"role": "user", "content": f"修改需求 {i+1}"})
            history.append({"role": "assistant", "content": f"已修改 {i+1}"})

        response = await client.post(
            "/api/optimize/chat",
            json={
                "resume_id": resume.id,
                "message": "第11轮修改",
                "history": history,
            },
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400
        assert "最大对话轮次" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_chat_on_expired_resume(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """对超过 24 小时的简历进行对话微调，应返回 400"""
        token, user_info = await register_and_login(client, test_user_data)

        # 创建一个 25 小时前的简历
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        resume = Resume(
            user_id=user_info["id"],
            title="过期简历",
            original_text="内容",
            optimized_text="<html>优化后</html>",
            status="completed",
            created_at=old_time,
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)

        response = await client.post(
            "/api/optimize/chat",
            json={
                "resume_id": resume.id,
                "message": "请修改简历",
            },
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400
        assert "有效期" in response.json()["detail"]

    # -----------------------------------------------------------------------
    # 版本历史边界
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_versions_of_nonexistent_resume(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """获取不存在简历的版本历史，应返回 404"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/resume/99999/versions",
            headers=get_auth_headers(token),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_versions_of_other_users_resume(
        self,
        client: AsyncClient,
        test_user_data,
        test_user_data_2,
        db_session,
    ):
        """获取其他用户简历的版本历史，应返回 404"""
        token1, user1 = await register_and_login(client, test_user_data)
        token2, user2 = await register_and_login(client, test_user_data_2)

        resume = Resume(
            user_id=user1["id"],
            title="用户1的简历",
            original_text="内容",
            status="completed",
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)

        response = await client.get(
            f"/api/resume/{resume.id}/versions",
            headers=get_auth_headers(token2),
        )
        assert response.status_code == 404

    # -----------------------------------------------------------------------
    # 知识库边界
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_nonexistent_knowledge(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """获取不存在的知识条目，应返回 404"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/knowledge/99999",
            headers=get_auth_headers(token),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_knowledge(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """删除不存在的知识条目，应返回 404"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.delete(
            "/api/knowledge/99999",
            headers=get_auth_headers(token),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_nonexistent_knowledge(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """更新不存在的知识条目，应返回 404"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.put(
            "/api/knowledge/99999",
            json={"title": "新标题"},
            headers=get_auth_headers(token),
        )
        assert response.status_code == 404

    # -----------------------------------------------------------------------
    # 支付边界
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_create_order_invalid_package(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """创建订单时使用无效套餐 ID，应返回 400"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/payment/create",
            json={"package_id": "invalid_package"},
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_confirm_nonexistent_order(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """确认不存在的订单，应返回 404"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/payment/INVALID_ORDER_NO/confirm",
            headers=get_auth_headers(token),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_order(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """取消不存在的订单，应返回 404"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/payment/INVALID_ORDER_NO/cancel",
            headers=get_auth_headers(token),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_wallet_transactions_pagination(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """点数流水记录分页参数边界"""
        token, _ = await register_and_login(client, test_user_data)

        # 正常请求
        response = await client.get(
            "/api/wallet/transactions?page=1&size=10",
            headers=get_auth_headers(token),
        )
        assert response.status_code == 200

    # -----------------------------------------------------------------------
    # 未认证访问所有受保护端点
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_unauthenticated_access_all_endpoints(
        self,
        client: AsyncClient,
    ):
        """未认证访问所有受保护端点，都应返回 401"""
        protected_endpoints = [
            ("GET", "/api/auth/me"),
            ("PUT", "/api/auth/me"),
            ("PUT", "/api/auth/password"),
            ("POST", "/api/auth/refresh"),
            ("GET", "/api/resume/list"),
            ("GET", "/api/resume/1"),
            ("PUT", "/api/resume/1"),
            ("DELETE", "/api/resume/1"),
            ("GET", "/api/resume/1/versions"),
            ("POST", "/api/resume/1/feedback"),
            ("POST", "/api/optimize"),
            ("POST", "/api/optimize/check"),
            ("POST", "/api/optimize/chat"),
            ("GET", "/api/knowledge/list"),
            ("GET", "/api/knowledge/1"),
            ("POST", "/api/knowledge"),
            ("PUT", "/api/knowledge/1"),
            ("DELETE", "/api/knowledge/1"),
            ("GET", "/api/wallet"),
            ("GET", "/api/wallet/transactions"),
            # 注意：/api/payment/packages 是公开端点，无需认证
            ("POST", "/api/payment/create"),
            ("GET", "/api/payment/orders"),
            ("GET", "/api/jobs/search"),
        ]

        for method, path in protected_endpoints:
            if method == "GET":
                response = await client.get(path)
            elif method == "POST":
                response = await client.post(path, json={})
            elif method == "PUT":
                response = await client.put(path, json={})
            elif method == "DELETE":
                response = await client.delete(path)

            assert response.status_code == 401, (
                f"{method} {path} 应返回 401，实际返回 {response.status_code}"
            )


# ===========================================================================
# 4. 网络/错误边界测试
# ===========================================================================


class TestNetworkBoundaries:
    """网络和错误处理边界测试"""

    @pytest.mark.asyncio
    async def test_llm_service_timeout(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """LLM 服务超时，应返回 502"""
        token, _ = await register_and_login(client, test_user_data)

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.side_effect = Exception("Connection timeout")
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            response = await client.post(
                "/api/optimize",
                data={"text": "测试简历"},
                headers=get_auth_headers(token),
            )

        # 应返回 500 或 502（优化失败会回滚事务）
        assert response.status_code in (500, 502)

    @pytest.mark.asyncio
    async def test_llm_service_error(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """LLM 服务返回错误，应返回 502 并回滚点数"""
        token, user_info = await register_and_login(client, test_user_data)

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.side_effect = Exception("LLM 服务不可用")
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            response = await client.post(
                "/api/optimize",
                data={"text": "测试简历"},
                headers=get_auth_headers(token),
            )

        assert response.status_code in (500, 502)

        # 验证点数已回滚（应仍为 3）
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        assert wallet_response.status_code == 200
        assert wallet_response.json()["balance"] == 3

    @pytest.mark.asyncio
    async def test_llm_returns_invalid_html(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """LLM 返回无效 HTML，应安全处理"""
        token, _ = await register_and_login(client, test_user_data)

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = {
                "optimized_html": "<html><body><script>alert('xss')</script>正常内容</body></html>",
                "optimization_score": 80.0,
                "changes_summary": ["优化了内容"],
                "pros": [],
                "cons": [],
                "star_rewrites": 0,
                "quantifications": 0,
                "keywords_matched": 0,
            }
            mock_llm.extract_knowledge.return_value = {
                "patterns": [],
                "jd_keywords": [],
                "industry": "互联网",
                "job_level": "mid",
            }
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            response = await client.post(
                "/api/optimize",
                data={"text": "测试简历"},
                headers=get_auth_headers(token),
            )

        assert response.status_code == 200
        # 验证 script 标签被消毒
        html = response.json()["optimized_html"]
        assert "<script>" not in html

    @pytest.mark.asyncio
    async def test_llm_returns_empty_html(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """LLM 返回空 HTML，应正常处理"""
        token, _ = await register_and_login(client, test_user_data)

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = {
                "optimized_html": "",
                "optimization_score": 0.0,
                "changes_summary": [],
                "pros": [],
                "cons": [],
                "star_rewrites": 0,
                "quantifications": 0,
                "keywords_matched": 0,
            }
            mock_llm.extract_knowledge.return_value = {
                "patterns": [],
                "jd_keywords": [],
                "industry": None,
                "job_level": None,
            }
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            response = await client.post(
                "/api/optimize",
                data={"text": "测试简历"},
                headers=get_auth_headers(token),
            )

        assert response.status_code == 200
        assert response.json()["optimized_html"] == ""

    @pytest.mark.asyncio
    async def test_knowledge_extraction_failure_does_not_fail_optimization(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """知识提取失败不应影响优化结果"""
        token, _ = await register_and_login(client, test_user_data)

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = {
                "optimized_html": "<html><body>优化后</body></html>",
                "optimization_score": 85.0,
                "changes_summary": ["优化了内容"],
                "pros": [],
                "cons": [],
                "star_rewrites": 0,
                "quantifications": 0,
                "keywords_matched": 0,
            }
            # 知识提取抛出异常
            mock_llm.extract_knowledge.side_effect = Exception("知识提取失败")
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            response = await client.post(
                "/api/optimize",
                data={"text": "测试简历"},
                headers=get_auth_headers(token),
            )

        # 优化应成功（知识提取失败被静默处理）
        assert response.status_code == 200
        assert response.json()["knowledge_extracted"] == 0

    @pytest.mark.asyncio
    async def test_ai_check_llm_error(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """AI 预检时 LLM 出错，应返回 502"""
        from backend.services.llm_service import LLMServiceError

        token, _ = await register_and_login(client, test_user_data)

        mock_llm = AsyncMock()
        mock_llm.chat_conversation.side_effect = LLMServiceError("LLM 服务不可用")

        # patch 两处：源模块 + 路由模块的 import 副本
        with patch("backend.services.llm_service.get_llm_service", return_value=mock_llm), \
             patch("backend.routers.optimize.get_llm_service", return_value=mock_llm):

            response = await client.post(
                "/api/optimize/check",
                json={
                    "city": "北京",
                    "salary": "20k",
                    "jd": "前端工程师",
                },
                headers=get_auth_headers(token),
            )

        assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_ai_check_no_info_provided(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """AI 预检不提供任何信息，应返回 400"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/optimize/check",
            json={},
            headers=get_auth_headers(token),
        )
        assert response.status_code == 400
        assert "至少提供一项" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_chat_llm_error(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """对话微调时 LLM 出错，应返回 502"""
        from backend.services.llm_service import LLMServiceError

        token, user_info = await register_and_login(client, test_user_data)

        resume = Resume(
            user_id=user_info["id"],
            title="测试简历",
            original_text="内容",
            optimized_text="<html>优化后</html>",
            status="completed",
        )
        db_session.add(resume)
        db_session.commit()
        db_session.refresh(resume)

        mock_llm = AsyncMock()
        mock_llm.chat_conversation.side_effect = LLMServiceError("LLM 服务不可用")

        # patch 两处：源模块 + 路由模块的 import 副本
        with patch("backend.services.llm_service.get_llm_service", return_value=mock_llm), \
             patch("backend.routers.optimize.get_llm_service", return_value=mock_llm):

            response = await client.post(
                "/api/optimize/chat",
                json={
                    "resume_id": resume.id,
                    "message": "请修改简历",
                },
                headers=get_auth_headers(token),
            )

        assert response.status_code == 502


# ===========================================================================
# 5. 事务原子性测试
# ===========================================================================


class TestTransactionAtomicity:
    """事务原子性测试 - 验证异常时数据一致性"""

    @pytest.mark.asyncio
    async def test_optimize_failure_rolls_back_point_deduction(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """优化失败时，点数扣减应回滚"""
        token, user_info = await register_and_login(client, test_user_data)

        # 记录初始余额
        wallet_resp = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        initial_balance = wallet_resp.json()["balance"]
        assert initial_balance == 3

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.side_effect = Exception("LLM 崩溃")
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            response = await client.post(
                "/api/optimize",
                data={"text": "测试简历"},
                headers=get_auth_headers(token),
            )

        # 优化应失败
        assert response.status_code in (500, 502)

        # 验证点数未被扣减
        wallet_resp = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        assert wallet_resp.json()["balance"] == initial_balance

    @pytest.mark.asyncio
    async def test_optimize_failure_no_orphan_resume(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """优化失败时，不应留下孤立的简历记录"""
        token, user_info = await register_and_login(client, test_user_data)

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.side_effect = Exception("LLM 崩溃")
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            response = await client.post(
                "/api/optimize",
                data={"text": "测试简历"},
                headers=get_auth_headers(token),
            )

        assert response.status_code in (500, 502)

        # 验证简历列表为空（无孤立记录）
        list_resp = await client.get(
            "/api/resume/list",
            headers=get_auth_headers(token),
        )
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 0


# ===========================================================================
# 运行入口
# ===========================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
