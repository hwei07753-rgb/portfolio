"""
API 集成测试模块

使用 httpx + pytest-asyncio 测试所有 API 端点。
测试覆盖：
1. 认证流程（注册、登录、Token 刷新）
2. 简历流程（上传、列表、详情、更新、删除）
3. 优化流程（Mock LLM、点数扣减、知识库提取）
4. 支付流程（创建订单、确认支付、点数增加、流水查询）
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

# 使用内存 SQLite 数据库进行测试
TEST_DATABASE_URL = "sqlite:///./test_api.db"

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


# 应用数据库覆盖
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

    技能
    - 熟练掌握 React、Vue、TypeScript
    - 了解 Node.js、Webpack
    - 良好的英语读写能力
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
    """注册并登录用户，返回 Token 和用户信息

    Args:
        client: 异步 HTTP 客户端
        user_data: 用户数据

    Returns:
        (access_token, user_info) 元组
    """
    # 注册
    register_response = await client.post(
        "/api/auth/register",
        json=user_data,
    )
    assert register_response.status_code == 201
    register_data = register_response.json()

    return register_data["access_token"], register_data["user"]


def get_auth_headers(token: str) -> dict:
    """获取认证请求头

    Args:
        token: JWT Token

    Returns:
        包含 Authorization 的请求头
    """
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. 认证流程测试
# ===========================================================================


class TestAuthFlow:
    """认证流程测试"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient, test_user_data):
        """测试用户注册成功"""
        response = await client.post(
            "/api/auth/register",
            json=test_user_data,
        )

        assert response.status_code == 201
        data = response.json()

        # 验证响应结构
        assert "access_token" in data
        assert "token_type" in data
        assert "user" in data
        assert data["token_type"] == "bearer"

        # 验证用户信息
        user = data["user"]
        assert user["username"] == test_user_data["username"]
        assert user["email"] == test_user_data["email"]
        assert "id" in user
        assert "created_at" in user

    @pytest.mark.asyncio
    async def test_register_duplicate_username(
        self, client: AsyncClient, test_user_data
    ):
        """测试重复用户名注册"""
        # 第一次注册
        await client.post("/api/auth/register", json=test_user_data)

        # 第二次注册（相同用户名）
        duplicate_data = test_user_data.copy()
        duplicate_data["email"] = "another@example.com"
        response = await client.post("/api/auth/register", json=duplicate_data)

        assert response.status_code == 409
        assert "用户名已被注册" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, client: AsyncClient, test_user_data
    ):
        """测试重复邮箱注册"""
        # 第一次注册
        await client.post("/api/auth/register", json=test_user_data)

        # 第二次注册（相同邮箱）
        duplicate_data = test_user_data.copy()
        duplicate_data["username"] = "anotheruser"
        response = await client.post("/api/auth/register", json=duplicate_data)

        assert response.status_code == 409
        assert "邮箱已被注册" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_invalid_data(self, client: AsyncClient):
        """测试无效注册数据"""
        # 用户名太短（1个字符，最小2个）
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "a",
                "email": "test@example.com",
                "password": "TestPass123!",
            },
        )
        assert response.status_code == 422

        # 无效邮箱
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "invalid-email",
                "password": "TestPass123!",
            },
        )
        assert response.status_code == 422

        # 密码太短（5个字符，最小6个）
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "short",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user_data):
        """测试用户登录成功"""
        # 先注册
        await client.post("/api/auth/register", json=test_user_data)

        # 登录
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        }
        response = await client.post("/api/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user_data["email"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self, client: AsyncClient, test_user_data
    ):
        """测试错误密码登录"""
        # 先注册
        await client.post("/api/auth/register", json=test_user_data)

        # 使用错误密码登录
        login_data = {
            "email": test_user_data["email"],
            "password": "WrongPassword123!",
        }
        response = await client.post("/api/auth/login", json=login_data)

        assert response.status_code == 401
        assert "邮箱或密码错误" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """测试不存在的用户登录"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "TestPass123!",
        }
        response = await client.post("/api/auth/login", json=login_data)

        assert response.status_code == 401
        assert "邮箱或密码错误" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_me(self, client: AsyncClient, test_user_data):
        """测试获取当前用户信息"""
        # 注册并登录
        token, user_info = await register_and_login(client, test_user_data)

        # 获取用户信息
        response = await client.get(
            "/api/auth/me",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == user_info["id"]
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]

    @pytest.mark.asyncio
    async def test_get_me_no_token(self, client: AsyncClient):
        """测试无 Token 访问受保护端点"""
        response = await client.get("/api/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_invalid_token(self, client: AsyncClient):
        """测试无效 Token"""
        response = await client.get(
            "/api/auth/me",
            headers=get_auth_headers("invalid-token"),
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_me(self, client: AsyncClient, test_user_data):
        """测试更新用户信息"""
        # 注册并登录
        token, user_info = await register_and_login(client, test_user_data)

        # 更新用户名
        update_data = {"username": "newusername"}
        response = await client.put(
            "/api/auth/me",
            json=update_data,
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newusername"
        assert data["email"] == test_user_data["email"]

    @pytest.mark.asyncio
    async def test_update_me_duplicate_username(
        self,
        client: AsyncClient,
        test_user_data,
        test_user_data_2,
    ):
        """测试更新为重复用户名"""
        # 注册两个用户
        token1, _ = await register_and_login(client, test_user_data)
        await register_and_login(client, test_user_data_2)

        # 尝试将用户1的用户名改为用户2的用户名
        response = await client.put(
            "/api/auth/me",
            json={"username": test_user_data_2["username"]},
            headers=get_auth_headers(token1),
        )

        assert response.status_code == 409
        assert "用户名已被注册" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, test_user_data):
        """测试 Token 刷新"""
        # 注册并登录
        token, user_info = await register_and_login(client, test_user_data)

        # 刷新 Token
        response = await client.post(
            "/api/auth/refresh",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        # Token 可能相同（如果在同一秒内生成），但应该有效
        assert data["token_type"] == "bearer"
        assert data["user"]["id"] == user_info["id"]

    @pytest.mark.asyncio
    async def test_full_auth_flow(self, client: AsyncClient, test_user_data):
        """测试完整认证流程：注册 → 获取信息 → 更新 → 刷新"""
        # 1. 注册
        register_response = await client.post(
            "/api/auth/register",
            json=test_user_data,
        )
        assert register_response.status_code == 201
        token = register_response.json()["access_token"]

        # 2. 获取用户信息
        me_response = await client.get(
            "/api/auth/me",
            headers=get_auth_headers(token),
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == test_user_data["username"]

        # 3. 更新用户信息
        update_response = await client.put(
            "/api/auth/me",
            json={"username": "updated_user"},
            headers=get_auth_headers(token),
        )
        assert update_response.status_code == 200
        assert update_response.json()["username"] == "updated_user"

        # 4. 刷新 Token
        refresh_response = await client.post(
            "/api/auth/refresh",
            headers=get_auth_headers(token),
        )
        assert refresh_response.status_code == 200
        new_token = refresh_response.json()["access_token"]

        # 5. 使用新 Token 访问
        final_me_response = await client.get(
            "/api/auth/me",
            headers=get_auth_headers(new_token),
        )
        assert final_me_response.status_code == 200
        assert final_me_response.json()["username"] == "updated_user"


# ===========================================================================
# 2. 简历流程测试
# ===========================================================================


class TestResumeFlow:
    """简历流程测试"""

    @pytest.mark.asyncio
    async def test_upload_resume_text(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
    ):
        """测试上传文本简历"""
        token, _ = await register_and_login(client, test_user_data)

        # 上传简历
        response = await client.post(
            "/api/resume/upload",
            data={
                "title": "张三_前端工程师",
                "original_text": sample_resume_text,
                "target_city": "北京",
                "target_salary": "25k-35k",
            },
            headers=get_auth_headers(token),
        )

        assert response.status_code == 201
        data = response.json()

        assert data["title"] == "张三_前端工程师"
        assert data["original_text"] == sample_resume_text
        assert data["target_city"] == "北京"
        assert data["target_salary"] == "25k-35k"
        assert data["status"] == "pending"
        assert data["version"] == 1

    @pytest.mark.asyncio
    async def test_upload_resume_no_title(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
    ):
        """测试上传简历缺少标题"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/resume/upload",
            data={"original_text": sample_resume_text},
            headers=get_auth_headers(token),
        )

        assert response.status_code == 400
        assert "请提供简历标题" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_resume_no_content(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试上传简历缺少内容"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/resume/upload",
            data={"title": "测试简历"},
            headers=get_auth_headers(token),
        )

        assert response.status_code == 400
        assert "请提供简历文本或上传图片文件" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_resumes_empty(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试获取空简历列表"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/resume/list",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_resumes_with_data(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
    ):
        """测试获取简历列表（有数据）"""
        token, _ = await register_and_login(client, test_user_data)

        # 上传 3 份简历
        for i in range(3):
            await client.post(
                "/api/resume/upload",
                data={
                    "title": f"简历_{i+1}",
                    "original_text": sample_resume_text,
                },
                headers=get_auth_headers(token),
            )

        # 获取列表
        response = await client.get(
            "/api/resume/list",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3
        assert len(data["items"]) == 3
        # 验证按创建时间倒序（最新创建的在前面）
        # 注意：如果创建时间在同一秒内，顺序可能不确定
        titles = [item["title"] for item in data["items"]]
        assert "简历_1" in titles
        assert "简历_2" in titles
        assert "简历_3" in titles

    @pytest.mark.asyncio
    async def test_list_resumes_pagination(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
    ):
        """测试简历列表分页"""
        token, _ = await register_and_login(client, test_user_data)

        # 上传 5 份简历
        for i in range(5):
            await client.post(
                "/api/resume/upload",
                data={
                    "title": f"简历_{i+1}",
                    "original_text": sample_resume_text,
                },
                headers=get_auth_headers(token),
            )

        # 第一页（2条）
        response = await client.get(
            "/api/resume/list?page=1&page_size=2",
            headers=get_auth_headers(token),
        )
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2

        # 第二页（2条）
        response = await client.get(
            "/api/resume/list?page=2&page_size=2",
            headers=get_auth_headers(token),
        )
        data = response.json()
        assert len(data["items"]) == 2

        # 第三页（1条）
        response = await client.get(
            "/api/resume/list?page=3&page_size=2",
            headers=get_auth_headers(token),
        )
        data = response.json()
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_resume_detail(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
    ):
        """测试获取简历详情"""
        token, _ = await register_and_login(client, test_user_data)

        # 上传简历
        upload_response = await client.post(
            "/api/resume/upload",
            data={
                "title": "测试简历",
                "original_text": sample_resume_text,
                "target_city": "上海",
            },
            headers=get_auth_headers(token),
        )
        resume_id = upload_response.json()["id"]

        # 获取详情
        response = await client.get(
            f"/api/resume/{resume_id}",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == resume_id
        assert data["title"] == "测试简历"
        assert data["original_text"] == sample_resume_text
        assert data["target_city"] == "上海"

    @pytest.mark.asyncio
    async def test_get_resume_not_found(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试获取不存在的简历"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/resume/999",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_resume_other_user(
        self,
        client: AsyncClient,
        test_user_data,
        test_user_data_2,
        sample_resume_text,
    ):
        """测试访问其他用户的简历"""
        # 用户1上传简历
        token1, _ = await register_and_login(client, test_user_data)
        upload_response = await client.post(
            "/api/resume/upload",
            data={
                "title": "用户1的简历",
                "original_text": sample_resume_text,
            },
            headers=get_auth_headers(token1),
        )
        resume_id = upload_response.json()["id"]

        # 用户2尝试访问
        token2, _ = await register_and_login(client, test_user_data_2)
        response = await client.get(
            f"/api/resume/{resume_id}",
            headers=get_auth_headers(token2),
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_resume(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
    ):
        """测试更新简历"""
        token, _ = await register_and_login(client, test_user_data)

        # 上传简历
        upload_response = await client.post(
            "/api/resume/upload",
            data={
                "title": "原始标题",
                "original_text": sample_resume_text,
            },
            headers=get_auth_headers(token),
        )
        resume_id = upload_response.json()["id"]

        # 更新简历
        update_data = {
            "title": "新标题",
            "target_city": "深圳",
            "target_salary": "30k-40k",
        }
        response = await client.put(
            f"/api/resume/{resume_id}",
            json=update_data,
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        assert data["title"] == "新标题"
        assert data["target_city"] == "深圳"
        assert data["target_salary"] == "30k-40k"
        assert data["original_text"] == sample_resume_text  # 未更新的字段保持不变

    @pytest.mark.asyncio
    async def test_delete_resume(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
    ):
        """测试删除简历"""
        token, _ = await register_and_login(client, test_user_data)

        # 上传简历
        upload_response = await client.post(
            "/api/resume/upload",
            data={
                "title": "待删除简历",
                "original_text": sample_resume_text,
            },
            headers=get_auth_headers(token),
        )
        resume_id = upload_response.json()["id"]

        # 删除简历
        delete_response = await client.delete(
            f"/api/resume/{resume_id}",
            headers=get_auth_headers(token),
        )
        assert delete_response.status_code == 204

        # 验证已删除
        get_response = await client.get(
            f"/api/resume/{resume_id}",
            headers=get_auth_headers(token),
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_resume_versions(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
    ):
        """测试获取简历版本历史"""
        token, _ = await register_and_login(client, test_user_data)

        # 上传原始简历
        upload_response = await client.post(
            "/api/resume/upload",
            data={
                "title": "版本测试简历",
                "original_text": sample_resume_text,
            },
            headers=get_auth_headers(token),
        )
        resume_id = upload_response.json()["id"]

        # 获取版本历史
        response = await client.get(
            f"/api/resume/{resume_id}/versions",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        # 初始版本应该只有1个
        assert len(data) == 1
        assert data[0]["id"] == resume_id
        assert data[0]["version"] == 1

    @pytest.mark.asyncio
    async def test_create_feedback(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
    ):
        """测试提交简历反馈"""
        token, _ = await register_and_login(client, test_user_data)

        # 上传简历
        upload_response = await client.post(
            "/api/resume/upload",
            data={
                "title": "反馈测试简历",
                "original_text": sample_resume_text,
            },
            headers=get_auth_headers(token),
        )
        resume_id = upload_response.json()["id"]

        # 提交反馈
        feedback_data = {
            "rating": 4,
            "comment": "优化效果不错，但可以更详细",
        }
        response = await client.post(
            f"/api/resume/{resume_id}/feedback",
            json=feedback_data,
            headers=get_auth_headers(token),
        )

        assert response.status_code == 201
        data = response.json()

        assert data["rating"] == 4
        assert data["comment"] == feedback_data["comment"]
        assert data["resume_id"] == resume_id

    @pytest.mark.asyncio
    async def test_create_duplicate_feedback(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
    ):
        """测试重复提交反馈"""
        token, _ = await register_and_login(client, test_user_data)

        # 上传简历
        upload_response = await client.post(
            "/api/resume/upload",
            data={
                "title": "反馈测试简历",
                "original_text": sample_resume_text,
            },
            headers=get_auth_headers(token),
        )
        resume_id = upload_response.json()["id"]

        # 第一次反馈
        await client.post(
            f"/api/resume/{resume_id}/feedback",
            json={"rating": 4, "comment": "不错"},
            headers=get_auth_headers(token),
        )

        # 第二次反馈（应该失败）
        response = await client.post(
            f"/api/resume/{resume_id}/feedback",
            json={"rating": 5, "comment": "非常好"},
            headers=get_auth_headers(token),
        )

        assert response.status_code == 409
        assert "已对该简历提交过反馈" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_feedback_invalid_rating(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
    ):
        """测试无效评分"""
        token, _ = await register_and_login(client, test_user_data)

        # 上传简历
        upload_response = await client.post(
            "/api/resume/upload",
            data={
                "title": "反馈测试简历",
                "original_text": sample_resume_text,
            },
            headers=get_auth_headers(token),
        )
        resume_id = upload_response.json()["id"]

        # 评分超出范围
        response = await client.post(
            f"/api/resume/{resume_id}/feedback",
            json={"rating": 6, "comment": "测试"},
            headers=get_auth_headers(token),
        )
        assert response.status_code == 422

        # 评分为0
        response = await client.post(
            f"/api/resume/{resume_id}/feedback",
            json={"rating": 0, "comment": "测试"},
            headers=get_auth_headers(token),
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_full_resume_flow(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
        sample_jd,
    ):
        """测试完整简历流程：上传 → 列表 → 详情 → 更新 → 反馈 → 删除"""
        token, _ = await register_and_login(client, test_user_data)

        # 1. 上传简历
        upload_response = await client.post(
            "/api/resume/upload",
            data={
                "title": "完整流程测试",
                "original_text": sample_resume_text,
                "target_city": "北京",
                "target_jd": sample_jd,
            },
            headers=get_auth_headers(token),
        )
        assert upload_response.status_code == 201
        resume_id = upload_response.json()["id"]

        # 2. 获取列表
        list_response = await client.get(
            "/api/resume/list",
            headers=get_auth_headers(token),
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1

        # 3. 获取详情
        detail_response = await client.get(
            f"/api/resume/{resume_id}",
            headers=get_auth_headers(token),
        )
        assert detail_response.status_code == 200
        assert detail_response.json()["title"] == "完整流程测试"

        # 4. 更新简历
        update_response = await client.put(
            f"/api/resume/{resume_id}",
            json={"title": "更新后的标题", "target_salary": "30k+"},
            headers=get_auth_headers(token),
        )
        assert update_response.status_code == 200
        assert update_response.json()["title"] == "更新后的标题"

        # 5. 提交反馈
        feedback_response = await client.post(
            f"/api/resume/{resume_id}/feedback",
            json={"rating": 5, "comment": "非常满意"},
            headers=get_auth_headers(token),
        )
        assert feedback_response.status_code == 201

        # 6. 删除简历
        delete_response = await client.delete(
            f"/api/resume/{resume_id}",
            headers=get_auth_headers(token),
        )
        assert delete_response.status_code == 204

        # 验证已删除
        get_response = await client.get(
            f"/api/resume/{resume_id}",
            headers=get_auth_headers(token),
        )
        assert get_response.status_code == 404


# ===========================================================================
# 3. 优化流程测试（Mock LLM）
# ===========================================================================


class TestOptimizeFlow:
    """优化流程测试"""

    @pytest.mark.asyncio
    async def test_optimize_success(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
        sample_jd,
        db_session,
    ):
        """测试简历优化成功（Mock LLM）"""
        token, user_info = await register_and_login(client, test_user_data)

        # 用户注册时已赠送 3 点，查询并更新余额
        wallet = db_session.query(UserWallet).filter(
            UserWallet.user_id == user_info["id"]
        ).first()
        wallet.balance = 10
        wallet.total_recharged = 10
        db_session.commit()

        # Mock LLM 服务
        mock_optimized_html = """
        <html>
        <body>
            <h1>张三</h1>
            <h2>高级前端工程师</h2>
            <p>优化后的简历内容...</p>
        </body>
        </html>
        """

        mock_knowledge_data = {
            "patterns": [
                {
                    "type": "star_rewrite",
                    "title": "STAR 原则重写示例",
                    "content": "将工作经历按 STAR 原则重写",
                    "tags": ["前端", "STAR"],
                }
            ],
            "jd_keywords": ["React", "TypeScript", "性能优化"],
            "industry": "互联网",
            "job_level": "senior",
        }

        mock_optimize_result = {
            "optimized_html": mock_optimized_html,
            "optimization_score": 85.0,
            "changes_summary": ["使用 STAR 原则重写了工作经历", "补充了量化数据", "匹配了 JD 关键词"],
            "pros": ["STAR 原则应用到位", "量化数据充分"],
            "cons": ["部分关键词可进一步补充"],
            "star_rewrites": 3,
            "quantifications": 5,
            "keywords_matched": 8,
        }

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            # 配置 Mock
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = mock_optimize_result
            mock_llm.extract_knowledge.return_value = mock_knowledge_data
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            # 执行优化
            response = await client.post(
                "/api/optimize",
                data={
                    "text": sample_resume_text,
                    "city": "北京",
                    "salary": "30k-40k",
                    "jd": sample_jd,
                },
                headers=get_auth_headers(token),
            )

        assert response.status_code == 200
        data = response.json()

        assert "resume_id" in data
        assert "optimized_html" in data
        assert "changes_summary" in data
        assert "knowledge_extracted" in data
        assert data["knowledge_extracted"] == 2  # 1 pattern + 1 jd_keyword

        # 验证点数已扣减
        wallet = db_session.query(UserWallet).filter(
            UserWallet.user_id == user_info["id"]
        ).first()
        assert wallet.balance == 9
        assert wallet.total_consumed == 1

    @pytest.mark.asyncio
    async def test_optimize_insufficient_points(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
        db_session,
    ):
        """测试点数不足时优化失败"""
        token, user_info = await register_and_login(client, test_user_data)

        # 用户注册时已赠送 3 点，将余额设为 0
        wallet = db_session.query(UserWallet).filter(
            UserWallet.user_id == user_info["id"]
        ).first()
        wallet.balance = 0
        db_session.commit()

        response = await client.post(
            "/api/optimize",
            data={"text": sample_resume_text},
            headers=get_auth_headers(token),
        )

        assert response.status_code == 402
        assert "点数不足" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_optimize_no_content(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试优化时没有提供简历内容"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/optimize",
            data={},
            headers=get_auth_headers(token),
        )

        assert response.status_code == 400
        assert "请提供简历文本或上传图片文件" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_optimize_llm_failure(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
        db_session,
    ):
        """测试 LLM 服务失败时的处理"""
        token, user_info = await register_and_login(client, test_user_data)

        # 用户注册时已赠送 3 点，查询并更新余额
        wallet = db_session.query(UserWallet).filter(
            UserWallet.user_id == user_info["id"]
        ).first()
        wallet.balance = 10
        wallet.total_recharged = 10
        db_session.commit()

        # Mock LLM 服务抛出异常
        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.side_effect = Exception("LLM 服务不可用")
            mock_get_llm.return_value = mock_llm

            response = await client.post(
                "/api/optimize",
                data={"text": sample_resume_text},
                headers=get_auth_headers(token),
            )

        # 应该返回 502 或 500
        assert response.status_code in [500, 502]

        # 验证点数已回滚
        wallet = db_session.query(UserWallet).filter(
            UserWallet.user_id == user_info["id"]
        ).first()
        assert wallet.balance == 10  # 点数应该回滚

    @pytest.mark.asyncio
    async def test_check_info_success(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试 AI 预检成功"""
        token, _ = await register_and_login(client, test_user_data)

        # Mock LLM 服务（AI 预检在 routers/optimize.py 中调用）
        with patch("backend.routers.optimize.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat_conversation.return_value = "薪资建议：根据市场行情，建议调整为 25k-35k"
            mock_get_llm.return_value = mock_llm

            response = await client.post(
                "/api/optimize/check",
                data={
                    "city": "北京",
                    "salary": "50k-60k",
                    "jd": "高级前端工程师",
                },
                headers=get_auth_headers(token),
            )

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "薪资建议" in data["suggestions"]

    @pytest.mark.asyncio
    async def test_check_info_no_data(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试 AI 预检没有提供数据"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/optimize/check",
            data={},
            headers=get_auth_headers(token),
        )

        assert response.status_code == 400
        assert "请至少提供一项求职信息进行检查" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_optimize_knowledge_extraction(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
        sample_jd,
        db_session,
    ):
        """测试优化后知识库提取"""
        token, user_info = await register_and_login(client, test_user_data)

        # 用户注册时已赠送 3 点，查询并更新余额
        wallet = db_session.query(UserWallet).filter(
            UserWallet.user_id == user_info["id"]
        ).first()
        wallet.balance = 5
        wallet.total_recharged = 5
        db_session.commit()

        # Mock LLM 服务
        mock_knowledge_data = {
            "patterns": [
                {
                    "type": "quantification",
                    "title": "量化数据示例",
                    "content": "将'负责前端开发'改为'负责核心模块前端开发，提升性能 40%'",
                    "before_example": "负责前端开发",
                    "after_example": "负责核心模块前端开发，提升性能 40%",
                    "tags": ["量化", "性能优化"],
                },
                {
                    "type": "keyword_match",
                    "title": "关键词匹配",
                    "content": "在简历中自然融入 JD 关键词",
                    "tags": ["关键词", "ATS"],
                },
            ],
            "jd_keywords": ["React", "TypeScript", "性能优化", "架构设计"],
            "industry": "互联网",
            "job_level": "senior",
        }

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = {
                "optimized_html": "<html><body>优化后简历</body></html>",
                "optimization_score": 80.0,
                "changes_summary": ["使用 STAR 原则重写", "补充了量化数据"],
                "pros": ["结构清晰"],
                "cons": ["可进一步优化"],
                "star_rewrites": 2,
                "quantifications": 3,
                "keywords_matched": 5,
            }
            mock_llm.extract_knowledge.return_value = mock_knowledge_data
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            response = await client.post(
                "/api/optimize",
                data={
                    "text": sample_resume_text,
                    "jd": sample_jd,
                },
                headers=get_auth_headers(token),
            )

        assert response.status_code == 200
        data = response.json()

        # 验证知识提取数量
        assert data["knowledge_extracted"] == 3  # 2 patterns + 1 jd_keyword

        # 验证知识库中有新条目
        knowledge_entries = db_session.query(KnowledgeEntry).filter(
            KnowledgeEntry.resume_id == data["resume_id"]
        ).all()

        assert len(knowledge_entries) == 3

        # 验证知识条目内容
        categories = [e.category for e in knowledge_entries]
        assert "optimization_case" in categories
        assert "jd_keyword" in categories

    @pytest.mark.asyncio
    async def test_optimize_points_refund_on_failure(
        self,
        client: AsyncClient,
        test_user_data,
        sample_resume_text,
        db_session,
    ):
        """测试优化失败时点数回滚"""
        token, user_info = await register_and_login(client, test_user_data)

        # 用户注册时已赠送 3 点，查询并更新余额
        wallet = db_session.query(UserWallet).filter(
            UserWallet.user_id == user_info["id"]
        ).first()
        wallet.balance = 5
        wallet.total_recharged = 5
        db_session.commit()

        # Mock LLM 服务失败
        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.side_effect = Exception("LLM 超时")
            mock_get_llm.return_value = mock_llm

            response = await client.post(
                "/api/optimize",
                data={"text": sample_resume_text},
                headers=get_auth_headers(token),
            )

        # 请求失败
        assert response.status_code in [500, 502]

        # 验证点数未扣减（事务回滚）
        wallet = db_session.query(UserWallet).filter(
            UserWallet.user_id == user_info["id"]
        ).first()
        assert wallet.balance == 5


# ===========================================================================
# 4. 支付流程测试
# ===========================================================================


class TestPaymentFlow:
    """支付流程测试"""

    @pytest.mark.asyncio
    async def test_get_wallet_info(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """测试获取钱包信息"""
        token, user_info = await register_and_login(client, test_user_data)

        # 用户注册时已赠送 3 点，查询并更新余额
        wallet = db_session.query(UserWallet).filter(
            UserWallet.user_id == user_info["id"]
        ).first()
        wallet.balance = 10
        wallet.total_recharged = 10
        wallet.total_consumed = 0
        db_session.commit()

        response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        assert data["balance"] == 10
        assert data["total_recharged"] == 10
        assert data["total_consumed"] == 0

    @pytest.mark.asyncio
    async def test_get_wallet_auto_create(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试获取钱包信息（注册时自动创建）"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        # 新用户注册时赠送 3 点
        assert data["balance"] == 3
        assert data["total_recharged"] == 3
        assert data["total_consumed"] == 0

    @pytest.mark.asyncio
    async def test_get_packages(self, client: AsyncClient):
        """测试获取充值套餐"""
        response = await client.get("/api/payment/packages")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 3

        # 验证套餐内容
        package_ids = [p["package_id"] for p in data]
        assert "small" in package_ids
        assert "medium" in package_ids
        assert "large" in package_ids

        # 验证套餐详情
        small_package = next(p for p in data if p["package_id"] == "small")
        assert small_package["points"] == 10
        assert small_package["price_cents"] == 990
        assert small_package["price_display"] == "¥9.9"

    @pytest.mark.asyncio
    async def test_create_order_success(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试创建充值订单成功"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/payment/create",
            json={"package_id": "medium"},
            headers=get_auth_headers(token),
        )

        assert response.status_code == 201
        data = response.json()

        assert "order_no" in data
        assert data["amount_cents"] == 3990
        assert data["points"] == 50
        assert data["status"] == "pending"
        assert "expire_at" in data

    @pytest.mark.asyncio
    async def test_create_order_invalid_package(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试创建无效套餐订单"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/payment/create",
            json={"package_id": "invalid"},
            headers=get_auth_headers(token),
        )

        assert response.status_code == 400
        assert "无效的充值套餐" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_confirm_payment_success(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """测试确认支付成功"""
        token, user_info = await register_and_login(client, test_user_data)

        # 创建订单
        create_response = await client.post(
            "/api/payment/create",
            json={"package_id": "small"},
            headers=get_auth_headers(token),
        )
        order_no = create_response.json()["order_no"]

        # 确认支付
        confirm_response = await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )

        assert confirm_response.status_code == 200
        data = confirm_response.json()

        assert data["status"] == "paid"

        # 验证点数已增加（注册赠送 3 点 + 充值 10 点 = 13 点）
        wallet = db_session.query(UserWallet).filter(
            UserWallet.user_id == user_info["id"]
        ).first()
        assert wallet.balance == 13
        assert wallet.total_recharged == 13

    @pytest.mark.asyncio
    async def test_confirm_payment_already_paid(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试重复确认支付"""
        token, _ = await register_and_login(client, test_user_data)

        # 创建订单
        create_response = await client.post(
            "/api/payment/create",
            json={"package_id": "small"},
            headers=get_auth_headers(token),
        )
        order_no = create_response.json()["order_no"]

        # 第一次确认
        await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )

        # 第二次确认（应该失败）
        response = await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 409
        assert "订单已支付" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_confirm_payment_expired_order(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """测试确认过期订单"""
        token, user_info = await register_and_login(client, test_user_data)

        # 创建订单
        create_response = await client.post(
            "/api/payment/create",
            json={"package_id": "small"},
            headers=get_auth_headers(token),
        )
        order_no = create_response.json()["order_no"]

        # 手动将订单设为过期
        order = db_session.query(PaymentOrder).filter(
            PaymentOrder.order_no == order_no
        ).first()
        order.expire_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db_session.commit()

        # 尝试确认支付
        response = await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 410
        assert "订单已过期" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cancel_order_success(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试取消订单成功"""
        token, _ = await register_and_login(client, test_user_data)

        # 创建订单
        create_response = await client.post(
            "/api/payment/create",
            json={"package_id": "medium"},
            headers=get_auth_headers(token),
        )
        order_no = create_response.json()["order_no"]

        # 取消订单
        cancel_response = await client.post(
            f"/api/payment/{order_no}/cancel",
            headers=get_auth_headers(token),
        )

        assert cancel_response.status_code == 200
        data = cancel_response.json()

        assert data["status"] == "expired"

    @pytest.mark.asyncio
    async def test_get_order_list(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试获取订单列表"""
        token, _ = await register_and_login(client, test_user_data)

        # 创建多个订单
        for package in ["small", "medium", "large"]:
            await client.post(
                "/api/payment/create",
                json={"package_id": package},
                headers=get_auth_headers(token),
            )

        # 获取订单列表
        response = await client.get(
            "/api/payment/orders",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_get_wallet_transactions(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """测试获取点数流水记录"""
        token, user_info = await register_and_login(client, test_user_data)

        # 创建订单并确认支付
        create_response = await client.post(
            "/api/payment/create",
            json={"package_id": "small"},
            headers=get_auth_headers(token),
        )
        order_no = create_response.json()["order_no"]

        await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )

        # 获取流水记录
        response = await client.get(
            "/api/wallet/transactions",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        # 注册时赠送 1 条 + 充值 1 条 = 2 条
        assert data["total"] == 2
        assert len(data["items"]) == 2
        # 按时间倒序，最新的在前面
        # 如果在同一秒内创建，顺序可能不确定，所以检查类型存在即可
        types = [item["type"] for item in data["items"]]
        assert "gift" in types
        assert "recharge" in types

    @pytest.mark.asyncio
    async def test_confirm_other_user_order(
        self,
        client: AsyncClient,
        test_user_data,
        test_user_data_2,
    ):
        """测试确认其他用户的订单"""
        # 用户1创建订单
        token1, _ = await register_and_login(client, test_user_data)
        create_response = await client.post(
            "/api/payment/create",
            json={"package_id": "small"},
            headers=get_auth_headers(token1),
        )
        order_no = create_response.json()["order_no"]

        # 用户2尝试确认
        token2, _ = await register_and_login(client, test_user_data_2)
        response = await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token2),
        )

        assert response.status_code == 403
        assert "无权操作此订单" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_full_payment_flow(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """测试完整支付流程：查看套餐 → 创建订单 → 确认支付 → 验证余额 → 查看流水"""
        token, user_info = await register_and_login(client, test_user_data)

        # 1. 查看充值套餐
        packages_response = await client.get("/api/payment/packages")
        assert packages_response.status_code == 200
        packages = packages_response.json()
        assert len(packages) == 3

        # 2. 创建充值订单（选择 medium 套餐）
        create_response = await client.post(
            "/api/payment/create",
            json={"package_id": "medium"},
            headers=get_auth_headers(token),
        )
        assert create_response.status_code == 201
        order_no = create_response.json()["order_no"]
        assert create_response.json()["points"] == 50

        # 3. 查看钱包（注册赠送 3 点）
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        assert wallet_response.json()["balance"] == 3

        # 4. 确认支付
        confirm_response = await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )
        assert confirm_response.status_code == 200
        assert confirm_response.json()["status"] == "paid"

        # 5. 验证点数已增加（3 + 50 = 53）
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        assert wallet_response.json()["balance"] == 53
        assert wallet_response.json()["total_recharged"] == 53

        # 6. 查看流水记录
        transactions_response = await client.get(
            "/api/wallet/transactions",
            headers=get_auth_headers(token),
        )
        assert transactions_response.status_code == 200
        transactions = transactions_response.json()
        # 注册赠送 1 条 + 充值 1 条 = 2 条
        assert transactions["total"] == 2
        # 检查两种类型的流水都存在
        types = [item["type"] for item in transactions["items"]]
        assert "gift" in types
        assert "recharge" in types

        # 7. 查看订单列表
        orders_response = await client.get(
            "/api/payment/orders",
            headers=get_auth_headers(token),
        )
        assert orders_response.status_code == 200
        orders = orders_response.json()
        assert orders["total"] == 1
        assert orders["items"][0]["status"] == "paid"


# ===========================================================================
# 5. 知识库测试
# ===========================================================================


class TestKnowledgeFlow:
    """知识库流程测试"""

    @pytest.mark.asyncio
    async def test_list_knowledge_empty(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试获取空知识库列表"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/knowledge/list",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_knowledge_with_data(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """测试获取知识库列表（有数据）"""
        token, user_info = await register_and_login(client, test_user_data)

        # 添加知识条目
        entries = [
            KnowledgeEntry(
                category="industry_practice",
                title="技术岗简历规范",
                content="使用 STAR 原则描述项目经历",
                source="system",
                status="active",
            ),
            KnowledgeEntry(
                category="jd_keyword",
                title="前端关键词",
                content="React, Vue, TypeScript",
                source="system",
                status="active",
                tags=json.dumps(["React", "Vue", "TypeScript"]),
            ),
            KnowledgeEntry(
                category="optimization_case",
                title="优化案例1",
                content="将'负责开发'改为'负责核心模块开发，提升性能 30%'",
                source="auto_extract",
                status="review_needed",
            ),
        ]

        for entry in entries:
            db_session.add(entry)
        db_session.commit()

        # 获取列表
        response = await client.get(
            "/api/knowledge/list",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_list_knowledge_filter_by_category(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """测试按分类筛选知识库"""
        token, _ = await register_and_login(client, test_user_data)

        # 添加不同分类的知识条目
        entries = [
            KnowledgeEntry(
                category="industry_practice",
                title="技术岗规范",
                content="内容1",
                source="system",
                status="active",
            ),
            KnowledgeEntry(
                category="jd_keyword",
                title="关键词",
                content="内容2",
                source="system",
                status="active",
            ),
        ]

        for entry in entries:
            db_session.add(entry)
        db_session.commit()

        # 按分类筛选
        response = await client.get(
            "/api/knowledge/list?category=industry_practice",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["items"][0]["category"] == "industry_practice"

    @pytest.mark.asyncio
    async def test_get_knowledge_detail(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """测试获取知识条目详情"""
        token, _ = await register_and_login(client, test_user_data)

        # 添加知识条目
        entry = KnowledgeEntry(
            category="industry_practice",
            title="技术岗简历规范",
            content="使用 STAR 原则描述项目经历",
            source="system",
            status="active",
            tags=json.dumps(["技术", "STAR"]),
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        # 获取详情
        response = await client.get(
            f"/api/knowledge/{entry.id}",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == entry.id
        assert data["title"] == "技术岗简历规范"
        assert data["category"] == "industry_practice"
        # tags 可能已经是 list 类型（Pydantic 自动解析）或字符串
        tags = data["tags"]
        if isinstance(tags, str):
            tags = json.loads(tags)
        assert tags == ["技术", "STAR"]

    @pytest.mark.asyncio
    async def test_create_knowledge(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试手动创建知识条目"""
        token, _ = await register_and_login(client, test_user_data)

        knowledge_data = {
            "category": "industry_practice",
            "title": "金融岗简历规范",
            "content": "突出量化业绩，如管理资产规模、收益率等",
            "industry": "金融",
            "tags": json.dumps(["金融", "量化"]),
        }

        response = await client.post(
            "/api/knowledge",
            json=knowledge_data,
            headers=get_auth_headers(token),
        )

        assert response.status_code == 201
        data = response.json()

        assert data["title"] == "金融岗简历规范"
        assert data["category"] == "industry_practice"
        assert data["source"] == "manual"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_update_knowledge(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """测试更新知识条目"""
        token, _ = await register_and_login(client, test_user_data)

        # 创建知识条目
        entry = KnowledgeEntry(
            category="industry_practice",
            title="原始标题",
            content="原始内容",
            source="system",
            status="active",
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        # 更新
        update_data = {
            "title": "更新后的标题",
            "content": "更新后的内容",
        }

        response = await client.put(
            f"/api/knowledge/{entry.id}",
            json=update_data,
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        assert data["title"] == "更新后的标题"
        assert data["content"] == "更新后的内容"
        assert data["category"] == "industry_practice"  # 未更新字段保持不变

    @pytest.mark.asyncio
    async def test_delete_knowledge(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """测试删除知识条目"""
        token, _ = await register_and_login(client, test_user_data)

        # 创建知识条目
        entry = KnowledgeEntry(
            category="industry_practice",
            title="待删除条目",
            content="内容",
            source="system",
            status="active",
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        # 删除
        response = await client.delete(
            f"/api/knowledge/{entry.id}",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 204

        # 验证已删除
        get_response = await client.get(
            f"/api/knowledge/{entry.id}",
            headers=get_auth_headers(token),
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_knowledge_stats(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """测试获取知识库统计"""
        token, _ = await register_and_login(client, test_user_data)

        # 添加不同分类的知识条目
        entries = [
            KnowledgeEntry(
                category="industry_practice",
                title="规范1",
                content="内容",
                source="system",
                status="active",
            ),
            KnowledgeEntry(
                category="industry_practice",
                title="规范2",
                content="内容",
                source="system",
                status="active",
            ),
            KnowledgeEntry(
                category="jd_keyword",
                title="关键词",
                content="内容",
                source="system",
                status="active",
            ),
            KnowledgeEntry(
                category="optimization_case",
                title="案例",
                content="内容",
                source="auto_extract",
                status="review_needed",
            ),
        ]

        for entry in entries:
            db_session.add(entry)
        db_session.commit()

        # 获取统计
        response = await client.get(
            "/api/knowledge/stats",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 4
        assert data["by_category"]["industry_practice"] == 2
        assert data["by_category"]["jd_keyword"] == 1
        assert data["by_category"]["optimization_case"] == 1


# ===========================================================================
# 6. 边界情况和错误处理测试
# ===========================================================================


class TestEdgeCases:
    """边界情况和错误处理测试"""

    @pytest.mark.asyncio
    async def test_concurrent_registrations(
        self,
        client: AsyncClient,
    ):
        """测试并发注册相同用户名"""
        import asyncio

        user_data = {
            "username": "concurrent_user",
            "email": "concurrent@example.com",
            "password": "TestPass123!",
        }

        # 并发注册
        tasks = [
            client.post("/api/auth/register", json=user_data)
            for _ in range(5)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 只有一个应该成功
        success_count = sum(
            1 for r in responses
            if not isinstance(r, Exception) and r.status_code == 201
        )
        assert success_count == 1

    @pytest.mark.asyncio
    async def test_large_resume_text(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试大文本简历"""
        token, _ = await register_and_login(client, test_user_data)

        # 创建大文本（约 100KB）
        large_text = "这是一段测试文本。" * 10000

        response = await client.post(
            "/api/resume/upload",
            data={
                "title": "大文本简历",
                "original_text": large_text,
            },
            headers=get_auth_headers(token),
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_special_characters_in_resume(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试简历中的特殊字符"""
        token, _ = await register_and_login(client, test_user_data)

        special_text = """
        张三's Resume
        Skills: C++, C#, .NET
        Email: test@example.com
        Phone: +86-138-0013-8000
        HTML: <div class="test">Hello</div>
        Unicode: 你好世界 🌍
        """

        response = await client.post(
            "/api/resume/upload",
            data={
                "title": "特殊字符简历",
                "original_text": special_text,
            },
            headers=get_auth_headers(token),
        )

        assert response.status_code == 201

        # 验证内容正确保存
        resume_id = response.json()["id"]
        get_response = await client.get(
            f"/api/resume/{resume_id}",
            headers=get_auth_headers(token),
        )
        assert get_response.status_code == 200
        assert get_response.json()["original_text"] == special_text

    @pytest.mark.asyncio
    async def test_rapid_api_calls(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试快速连续 API 调用"""
        token, _ = await register_and_login(client, test_user_data)

        # 快速连续调用
        responses = []
        for i in range(20):
            response = await client.get(
                "/api/auth/me",
                headers=get_auth_headers(token),
            )
            responses.append(response)

        # 所有请求都应该成功
        assert all(r.status_code == 200 for r in responses)

    @pytest.mark.asyncio
    async def test_malformed_json(
        self,
        client: AsyncClient,
    ):
        """测试畸形 JSON 请求"""
        response = await client.post(
            "/api/auth/register",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_fields(
        self,
        client: AsyncClient,
    ):
        """测试缺少必填字段"""
        # 缺少 password
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_string_fields(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试空字符串字段"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/resume/upload",
            data={
                "title": "",  # 空标题
                "original_text": "测试内容",
            },
            headers=get_auth_headers(token),
        )

        # 应该失败，标题不能为空
        assert response.status_code == 400


# ===========================================================================
# 7. 健康检查测试
# ===========================================================================


class TestHealthCheck:
    """健康检查测试"""

    @pytest.mark.asyncio
    async def test_root(self, client: AsyncClient):
        """测试根路径"""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "version" in data
        assert data["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """测试健康检查端点"""
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data["service"] == "ai-resume-optimizer"
        assert data["version"] == "1.0.0"


class TestJobSearchFlow:
    """岗位搜索流程测试"""

    @pytest.mark.asyncio
    async def test_search_requires_auth(self, client: AsyncClient):
        """未认证搜索应返回 401"""
        response = await client.get("/api/jobs/search", params={"query": "前端"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_search_returns_results(self, client: AsyncClient, test_user_data: dict):
        """关键词搜索应返回匹配的岗位列表"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/jobs/search",
            params={"query": "前端"},
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert data["total"] > 0
        assert len(data["items"]) > 0

        # 验证字段结构
        item = data["items"][0]
        assert "title" in item
        assert "company" in item
        assert "location" in item
        assert "salary" in item
        assert "description" in item

    @pytest.mark.asyncio
    async def test_search_frontend_jobs(self, client: AsyncClient, test_user_data: dict):
        """搜索 '前端' 应返回前端相关岗位"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/jobs/search",
            params={"query": "前端"},
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        titles = [j["title"] for j in data["items"]]

        # 至少应包含"前端"相关岗位
        assert any("前端" in t for t in titles)

    @pytest.mark.asyncio
    async def test_search_python_jobs(self, client: AsyncClient, test_user_data: dict):
        """搜索 'Python' 应返回 Python 相关岗位"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/jobs/search",
            params={"query": "Python"},
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0

        # 描述或标题中应包含 Python 相关内容
        all_text = " ".join(j["title"] + j["description"] for j in data["items"])
        assert "python" in all_text.lower() or "Python" in all_text

    @pytest.mark.asyncio
    async def test_search_no_match(self, client: AsyncClient, test_user_data: dict):
        """搜索不存在的关键词应返回空列表"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/jobs/search",
            params={"query": "xyznonexistent12345"},
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_search_limit_param(self, client: AsyncClient, test_user_data: dict):
        """limit 参数应限制返回条数"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/jobs/search",
            params={"query": "工程师", "limit": 3},
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 3

    @pytest.mark.asyncio
    async def test_search_query_required(self, client: AsyncClient, test_user_data: dict):
        """缺少 query 参数应返回 422"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/jobs/search",
            headers=get_auth_headers(token),
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_job_description_not_empty(self, client: AsyncClient, test_user_data: dict):
        """返回的岗位描述不应为空"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.get(
            "/api/jobs/search",
            params={"query": "算法"},
            headers=get_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert item["description"], f"岗位 '{item['title']}' 的描述为空"
            assert item["title"], "岗位标题为空"


# ===========================================================================
# 运行入口
# ===========================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
