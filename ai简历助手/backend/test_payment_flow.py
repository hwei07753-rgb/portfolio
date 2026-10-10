"""
支付流程联调测试

测试覆盖：
1. 新用户赠送点数
2. 消费点数（简历优化）
3. 充值流程（创建订单 → 确认支付 → 验证余额）
4. 边界情况（点数不足、订单过期、重复确认）
"""

import asyncio
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

from backend.database import Base, get_db
from backend.main import app
from backend.models.payment import UserWallet, PointTransaction, PaymentOrder
from backend.utils.security import create_access_token

# ---------------------------------------------------------------------------
# 测试数据库配置
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///./test_payment_flow.db"

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
        "username": "payment_test_user",
        "email": "payment_test@example.com",
        "password": "TestPass123!",
    }


@pytest.fixture
def test_user_data_2():
    """第二个测试用户数据"""
    return {
        "username": "payment_test_user2",
        "email": "payment_test2@example.com",
        "password": "TestPass456!",
    }


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


async def register_and_login(client: AsyncClient, user_data: dict) -> tuple[str, dict]:
    """注册并登录用户，返回 (token, user_info)"""
    register_response = await client.post("/api/auth/register", json=user_data)
    assert register_response.status_code in [200, 201], f"注册失败: {register_response.text}"
    data = register_response.json()
    return data["access_token"], data["user"]


def get_auth_headers(token: str) -> dict:
    """获取认证头"""
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. 新用户赠送点数测试
# ===========================================================================


class TestNewUserGiftPoints:
    """新用户赠送点数测试"""

    @pytest.mark.asyncio
    async def test_new_user_gets_gift_points(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试新用户注册后获得赠送点数"""
        # 注册新用户
        token, user_info = await register_and_login(client, test_user_data)

        # 查询钱包余额
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )

        assert wallet_response.status_code == 200
        wallet = wallet_response.json()

        # 验证余额为 3 点
        assert wallet["balance"] == 3, f"期望余额 3，实际 {wallet['balance']}"
        assert wallet["total_recharged"] == 3, f"期望累计充值 3，实际 {wallet['total_recharged']}"
        assert wallet["total_consumed"] == 0, f"期望累计消费 0，实际 {wallet['total_consumed']}"

    @pytest.mark.asyncio
    async def test_gift_points_transaction_recorded(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试赠送点数有对应的流水记录"""
        token, _ = await register_and_login(client, test_user_data)

        # 查询流水记录
        txn_response = await client.get(
            "/api/wallet/transactions",
            headers=get_auth_headers(token),
        )

        assert txn_response.status_code == 200
        txn_data = txn_response.json()

        # 应该有 1 条赠送记录
        assert txn_data["total"] == 1, f"期望 1 条流水，实际 {txn_data['total']}"

        gift_txn = txn_data["items"][0]
        assert gift_txn["type"] == "gift", f"期望类型 gift，实际 {gift_txn['type']}"
        assert gift_txn["amount"] == 3, f"期望金额 3，实际 {gift_txn['amount']}"
        assert gift_txn["balance_after"] == 3, f"期望变动后余额 3，实际 {gift_txn['balance_after']}"
        assert "赠送" in gift_txn["description"], f"描述应包含'赠送'，实际 {gift_txn['description']}"


# ===========================================================================
# 2. 消费点数测试
# ===========================================================================


class TestConsumePoints:
    """消费点数测试"""

    @pytest.mark.asyncio
    async def test_optimize_consume_one_point(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """测试简历优化消耗 1 点"""
        token, _ = await register_and_login(client, test_user_data)

        # Mock LLM 服务
        mock_llm_result = {
            "optimized_html": "<html><body>优化后简历</body></html>",
            "optimization_score": 85,
            "changes_summary": ["STAR 原则重写", "补充量化数据"],
            "pros": ["结构清晰"],
            "cons": ["可进一步优化"],
            "star_rewrites": 3,
            "quantifications": 5,
            "keywords_matched": 8,
        }

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = mock_llm_result
            mock_llm.extract_knowledge.return_value = {
                "patterns": [],
                "jd_keywords": [],
                "industry": "互联网",
                "job_level": "mid",
            }
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            # 执行优化
            optimize_response = await client.post(
                "/api/optimize",
                data={
                    "text": "测试简历内容",
                    "city": "北京",
                    "salary": "15K-20K",
                    "jd": "前端工程师",
                    "strength": 3,
                },
                headers=get_auth_headers(token),
            )

            assert optimize_response.status_code == 200, f"优化失败: {optimize_response.text}"

        # 查询钱包余额
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )

        wallet = wallet_response.json()
        # 初始 3 点 - 消费 1 点 = 2 点
        assert wallet["balance"] == 2, f"期望余额 2，实际 {wallet['balance']}"
        assert wallet["total_consumed"] == 1, f"期望累计消费 1，实际 {wallet['total_consumed']}"

    @pytest.mark.asyncio
    async def test_consume_points_transaction_recorded(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试消费点数有对应的流水记录"""
        token, _ = await register_and_login(client, test_user_data)

        # Mock LLM 并执行优化
        mock_llm_result = {
            "optimized_html": "<html>优化后</html>",
            "optimization_score": 80,
            "changes_summary": ["修改1"],
            "pros": [],
            "cons": [],
            "star_rewrites": 1,
            "quantifications": 2,
            "keywords_matched": 3,
        }

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = mock_llm_result
            mock_llm.extract_knowledge.return_value = {
                "patterns": [],
                "jd_keywords": [],
            }
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            await client.post(
                "/api/optimize",
                data={"text": "测试简历", "strength": 3},
                headers=get_auth_headers(token),
            )

        # 查询流水记录
        txn_response = await client.get(
            "/api/wallet/transactions",
            headers=get_auth_headers(token),
        )

        txn_data = txn_response.json()
        # 应该有 2 条记录：1 条赠送 + 1 条消费
        assert txn_data["total"] == 2, f"期望 2 条流水，实际 {txn_data['total']}"

        types = [item["type"] for item in txn_data["items"]]
        assert "gift" in types, "缺少赠送流水"
        assert "consume" in types, "缺少消费流水"

        # 找到消费记录
        consume_txn = next(item for item in txn_data["items"] if item["type"] == "consume")
        assert consume_txn["amount"] == -1, f"期望消费金额 -1，实际 {consume_txn['amount']}"
        assert consume_txn["balance_after"] == 2, f"期望变动后余额 2，实际 {consume_txn['balance_after']}"


# ===========================================================================
# 3. 充值流程测试
# ===========================================================================


class TestRechargeFlow:
    """充值流程测试"""

    @pytest.mark.asyncio
    async def test_get_recharge_packages(
        self,
        client: AsyncClient,
    ):
        """测试获取充值套餐列表"""
        response = await client.get("/api/payment/packages")

        assert response.status_code == 200
        packages = response.json()

        # 应该有 3 个套餐
        assert len(packages) == 3, f"期望 3 个套餐，实际 {len(packages)}"

        # 验证套餐内容
        package_ids = [p["package_id"] for p in packages]
        assert "small" in package_ids, "缺少 small 套餐"
        assert "medium" in package_ids, "缺少 medium 套餐"
        assert "large" in package_ids, "缺少 large 套餐"

        # 验证 small 套餐
        small = next(p for p in packages if p["package_id"] == "small")
        assert small["points"] == 10
        assert small["price_cents"] == 990
        assert small["price_display"] == "¥9.9"

    @pytest.mark.asyncio
    async def test_create_order(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试创建充值订单"""
        token, _ = await register_and_login(client, test_user_data)

        # 创建订单
        create_response = await client.post(
            "/api/payment/create",
            json={"package_id": "medium"},
            headers=get_auth_headers(token),
        )

        assert create_response.status_code == 201
        order = create_response.json()

        # 验证订单信息
        assert order["points"] == 50
        assert order["amount_cents"] == 3990
        assert order["status"] == "pending"
        assert "order_no" in order
        assert "expire_at" in order

    @pytest.mark.asyncio
    async def test_full_recharge_flow(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试完整充值流程：创建订单 → 确认支付 → 验证余额"""
        token, _ = await register_and_login(client, test_user_data)

        # 1. 初始余额应为 3 点
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        initial_balance = wallet_response.json()["balance"]
        assert initial_balance == 3

        # 2. 创建充值订单（10 点套餐）
        create_response = await client.post(
            "/api/payment/create",
            json={"package_id": "small"},
            headers=get_auth_headers(token),
        )
        assert create_response.status_code == 201
        order_no = create_response.json()["order_no"]

        # 3. 确认支付
        confirm_response = await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )
        assert confirm_response.status_code == 200
        assert confirm_response.json()["status"] == "paid"

        # 4. 验证余额增加（3 + 10 = 13）
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        wallet = wallet_response.json()
        assert wallet["balance"] == 13, f"期望余额 13，实际 {wallet['balance']}"
        assert wallet["total_recharged"] == 13, f"期望累计充值 13，实际 {wallet['total_recharged']}"

    @pytest.mark.asyncio
    async def test_recharge_transaction_recorded(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试充值有对应的流水记录"""
        token, _ = await register_and_login(client, test_user_data)

        # 创建并确认订单
        create_response = await client.post(
            "/api/payment/create",
            json={"package_id": "large"},
            headers=get_auth_headers(token),
        )
        order_no = create_response.json()["order_no"]

        await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )

        # 查询流水记录
        txn_response = await client.get(
            "/api/wallet/transactions",
            headers=get_auth_headers(token),
        )

        txn_data = txn_response.json()
        # 应该有 2 条记录：1 条赠送 + 1 条充值
        assert txn_data["total"] == 2

        types = [item["type"] for item in txn_data["items"]]
        assert "gift" in types
        assert "recharge" in types

        # 找到充值记录
        recharge_txn = next(item for item in txn_data["items"] if item["type"] == "recharge")
        assert recharge_txn["amount"] == 100
        assert recharge_txn["balance_after"] == 103  # 3 + 100

    @pytest.mark.asyncio
    async def test_order_list_after_payment(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试支付后订单列表正确"""
        token, _ = await register_and_login(client, test_user_data)

        # 创建并确认订单
        create_response = await client.post(
            "/api/payment/create",
            json={"package_id": "medium"},
            headers=get_auth_headers(token),
        )
        order_no = create_response.json()["order_no"]

        await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )

        # 查询订单列表
        orders_response = await client.get(
            "/api/payment/orders",
            headers=get_auth_headers(token),
        )

        assert orders_response.status_code == 200
        orders = orders_response.json()

        assert orders["total"] == 1
        assert orders["items"][0]["status"] == "paid"
        assert orders["items"][0]["points"] == 50


# ===========================================================================
# 4. 边界情况测试
# ===========================================================================


class TestEdgeCases:
    """边界情况测试"""

    @pytest.mark.asyncio
    async def test_insufficient_points_optimize_fails(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试点数不足时优化失败"""
        token, _ = await register_and_login(client, test_user_data)

        # 消耗所有点数（3 次优化，每次 1 点）
        mock_llm_result = {
            "optimized_html": "<html>优化后</html>",
            "optimization_score": 80,
            "changes_summary": ["修改"],
            "pros": [],
            "cons": [],
            "star_rewrites": 1,
            "quantifications": 1,
            "keywords_matched": 1,
        }

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = mock_llm_result
            mock_llm.extract_knowledge.return_value = {
                "patterns": [],
                "jd_keywords": [],
            }
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            # 执行 3 次优化，消耗所有点数
            for i in range(3):
                response = await client.post(
                    "/api/optimize",
                    data={"text": f"简历{i}", "strength": 3},
                    headers=get_auth_headers(token),
                )
                assert response.status_code == 200, f"第 {i+1} 次优化失败: {response.text}"

        # 验证余额为 0
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        assert wallet_response.json()["balance"] == 0

        # 第 4 次优化应该失败
        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm

            response = await client.post(
                "/api/optimize",
                data={"text": "第4次简历", "strength": 3},
                headers=get_auth_headers(token),
            )

            # 应该返回 402 Payment Required
            assert response.status_code == 402, f"期望 402，实际 {response.status_code}"
            assert "点数不足" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_expired_order(
        self,
        client: AsyncClient,
        test_user_data,
        db_session,
    ):
        """测试订单过期处理"""
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
        confirm_response = await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )

        # 应该返回 410 Gone
        assert confirm_response.status_code == 410, f"期望 410，实际 {confirm_response.status_code}"
        assert "过期" in confirm_response.json()["detail"]

        # 验证余额未变
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        assert wallet_response.json()["balance"] == 3

    @pytest.mark.asyncio
    async def test_duplicate_confirm_payment(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试重复确认支付处理"""
        token, _ = await register_and_login(client, test_user_data)

        # 创建订单
        create_response = await client.post(
            "/api/payment/create",
            json={"package_id": "small"},
            headers=get_auth_headers(token),
        )
        order_no = create_response.json()["order_no"]

        # 第一次确认支付
        first_confirm = await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )
        assert first_confirm.status_code == 200

        # 第二次确认支付应该失败
        second_confirm = await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )

        # 应该返回 409 Conflict
        assert second_confirm.status_code == 409, f"期望 409，实际 {second_confirm.status_code}"
        assert "已支付" in second_confirm.json()["detail"]

        # 验证余额只增加了一次（3 + 10 = 13）
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        assert wallet_response.json()["balance"] == 13

    @pytest.mark.asyncio
    async def test_invalid_package_id(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试无效的套餐 ID"""
        token, _ = await register_and_login(client, test_user_data)

        response = await client.post(
            "/api/payment/create",
            json={"package_id": "invalid_package"},
            headers=get_auth_headers(token),
        )

        assert response.status_code == 400, f"期望 400，实际 {response.status_code}"
        assert "无效" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cancel_order(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试取消订单"""
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
        assert cancel_response.json()["status"] == "expired"

        # 尝试确认已取消的订单
        confirm_response = await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )

        # 应该返回 409（订单状态不是 pending）
        assert confirm_response.status_code == 409

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_order(
        self,
        client: AsyncClient,
        test_user_data,
        test_user_data_2,
    ):
        """测试用户无法操作其他用户的订单"""
        # 用户 1 创建订单
        token1, _ = await register_and_login(client, test_user_data)
        create_response = await client.post(
            "/api/payment/create",
            json={"package_id": "small"},
            headers=get_auth_headers(token1),
        )
        order_no = create_response.json()["order_no"]

        # 用户 2 尝试确认用户 1 的订单
        token2, _ = await register_and_login(client, test_user_data_2)
        confirm_response = await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token2),
        )

        # 应该返回 403 Forbidden
        assert confirm_response.status_code == 403, f"期望 403，实际 {confirm_response.status_code}"


# ===========================================================================
# 5. 完整业务流程测试
# ===========================================================================


class TestFullBusinessFlow:
    """完整业务流程测试"""

    @pytest.mark.asyncio
    async def test_complete_user_journey(
        self,
        client: AsyncClient,
        test_user_data,
    ):
        """测试完整用户旅程：注册 → 优化 → 充值 → 再次优化"""
        # 1. 注册新用户（获得 3 点）
        token, user_info = await register_and_login(client, test_user_data)

        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        assert wallet_response.json()["balance"] == 3

        # 2. 执行 2 次优化（消耗 2 点，剩余 1 点）
        mock_llm_result = {
            "optimized_html": "<html>优化后简历</html>",
            "optimization_score": 85,
            "changes_summary": ["STAR 原则重写", "补充量化数据"],
            "pros": ["结构清晰"],
            "cons": ["可进一步优化"],
            "star_rewrites": 3,
            "quantifications": 5,
            "keywords_matched": 8,
        }

        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = mock_llm_result
            mock_llm.extract_knowledge.return_value = {
                "patterns": [],
                "jd_keywords": [],
                "industry": "互联网",
                "job_level": "mid",
            }
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            for i in range(2):
                response = await client.post(
                    "/api/optimize",
                    data={"text": f"简历内容 {i+1}", "strength": 3},
                    headers=get_auth_headers(token),
                )
                assert response.status_code == 200

        # 验证余额为 1
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        assert wallet_response.json()["balance"] == 1
        assert wallet_response.json()["total_consumed"] == 2

        # 3. 充值 50 点
        create_response = await client.post(
            "/api/payment/create",
            json={"package_id": "medium"},
            headers=get_auth_headers(token),
        )
        order_no = create_response.json()["order_no"]

        confirm_response = await client.post(
            f"/api/payment/{order_no}/confirm",
            headers=get_auth_headers(token),
        )
        assert confirm_response.status_code == 200

        # 验证余额为 51（1 + 50）
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        assert wallet_response.json()["balance"] == 51
        assert wallet_response.json()["total_recharged"] == 53  # 3 + 50

        # 4. 再次优化
        with patch("backend.services.optimize_service.get_llm_service") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.optimize_resume.return_value = mock_llm_result
            mock_llm.extract_knowledge.return_value = {
                "patterns": [],
                "jd_keywords": [],
            }
            mock_llm.default_model = "qwen3.7-max"
            mock_get_llm.return_value = mock_llm

            response = await client.post(
                "/api/optimize",
                data={"text": "第三次简历", "strength": 3},
                headers=get_auth_headers(token),
            )
            assert response.status_code == 200

        # 验证余额为 50
        wallet_response = await client.get(
            "/api/wallet",
            headers=get_auth_headers(token),
        )
        assert wallet_response.json()["balance"] == 50
        assert wallet_response.json()["total_consumed"] == 3

        # 5. 验证流水记录
        txn_response = await client.get(
            "/api/wallet/transactions",
            headers=get_auth_headers(token),
        )
        txn_data = txn_response.json()

        # 应该有 5 条记录：1 赠送 + 3 消费 + 1 充值
        assert txn_data["total"] == 5

        types = [item["type"] for item in txn_data["items"]]
        assert types.count("gift") == 1
        assert types.count("consume") == 3
        assert types.count("recharge") == 1


# ===========================================================================
# 入口
# ===========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
