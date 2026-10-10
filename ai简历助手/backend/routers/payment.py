"""
支付与点数路由模块

提供用户钱包、点数流水、充值套餐、订单管理等 RESTful API 端点。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.payment import PaymentOrder
from backend.models.user import User
from backend.schemas.payment import OrderResponse, TransactionResponse, WalletResponse
from backend.services.payment_service import (
    InvalidPackageError,
    OrderAlreadyPaidError,
    OrderExpiredError,
    OrderNotFoundError,
    PaymentServiceError,
    cancel_order,
    confirm_order,
    create_order,
    get_orders,
    get_packages,
    get_transactions,
    get_wallet,
)
from backend.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["支付"])


def _get_order_or_404(db: Session, order_no: str, user_id: int) -> PaymentOrder:
    """获取订单并验证归属

    Args:
        db: 数据库会话
        order_no: 订单号
        user_id: 当前用户 ID

    Returns:
        PaymentOrder ORM 对象

    Raises:
        HTTPException: 订单不存在或不属于当前用户
    """
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == order_no).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权操作此订单")
    return order


# ---------------------------------------------------------------------------
# 请求体模型
# ---------------------------------------------------------------------------


class CreateOrderRequest(BaseModel):
    """创建充值订单请求体"""

    package_id: str = Field(..., description="套餐 ID：small/medium/large")


# ---------------------------------------------------------------------------
# 钱包端点
# ---------------------------------------------------------------------------


@router.get(
    "/api/wallet",
    response_model=WalletResponse,
    summary="获取钱包信息",
    description="获取当前用户的点数余额和累计收支信息。",
)
async def get_wallet_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WalletResponse:
    """GET /api/wallet

    请求头:
        Authorization: Bearer <token>

    响应 (200):
        WalletResponse: balance, total_recharged, total_consumed
    """
    wallet = get_wallet(db, current_user.id)
    return WalletResponse.model_validate(wallet)


@router.get(
    "/api/wallet/transactions",
    summary="点数流水记录",
    description="分页获取当前用户的点数变动流水。",
)
async def get_wallet_transactions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """GET /api/wallet/transactions

    请求头:
        Authorization: Bearer <token>

    查询参数:
        - page: 页码，默认 1
        - page_size: 每页数量，默认 20

    响应 (200):
        {total, page, page_size, items: [TransactionResponse]}
    """
    result = get_transactions(db, current_user.id, page=page, size=page_size)
    result["items"] = [TransactionResponse.model_validate(item) for item in result["items"]]
    return result


# ---------------------------------------------------------------------------
# 充值套餐端点
# ---------------------------------------------------------------------------


@router.get(
    "/api/payment/packages",
    summary="获取充值套餐",
    description="获取可用的充值套餐列表（10/50/100 点三档）。",
)
async def get_recharge_packages() -> list[dict]:
    """GET /api/payment/packages

    响应 (200):
        [
            {"package_id": "small", "points": 10, "price_cents": 990, "price_display": "¥9.9"},
            {"package_id": "medium", "points": 50, "price_cents": 3990, "price_display": "¥39.9"},
            {"package_id": "large", "points": 100, "price_cents": 6990, "price_display": "¥69.9"}
        ]
    """
    return get_packages()


# ---------------------------------------------------------------------------
# 订单端点
# ---------------------------------------------------------------------------


@router.post(
    "/api/payment/create",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建充值订单",
    description="根据套餐 ID 创建充值订单，订单 15 分钟内有效。",
)
async def create_payment_order(
    request: CreateOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    """POST /api/payment/create

    请求头:
        Authorization: Bearer <token>

    请求体 (JSON):
        - package_id: 套餐 ID（small/medium/large）

    响应 (201):
        OrderResponse: order_no, amount_cents, points, status, created_at, expire_at

    错误码:
        - 400: 无效的套餐 ID
    """
    try:
        order = create_order(db, current_user.id, request.package_id)
        return OrderResponse.model_validate(order)
    except InvalidPackageError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get(
    "/api/payment/orders",
    summary="订单列表",
    description="分页获取当前用户的充值订单列表。",
)
async def get_payment_orders(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """GET /api/payment/orders

    请求头:
        Authorization: Bearer <token>

    查询参数:
        - page: 页码，默认 1
        - page_size: 每页数量，默认 20

    响应 (200):
        {total, page, page_size, items: [OrderResponse]}
    """
    result = get_orders(db, current_user.id, page=page, size=page_size)
    result["items"] = [OrderResponse.model_validate(item) for item in result["items"]]
    return result


@router.post(
    "/api/payment/{order_no}/confirm",
    response_model=OrderResponse,
    summary="确认支付",
    description="模拟支付确认，为用户充值点数。订单 15 分钟内有效。",
)
async def confirm_payment(
    order_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    """POST /api/payment/{order_no}/confirm

    请求头:
        Authorization: Bearer <token>

    响应 (200):
        OrderResponse: 支付成功后的订单信息

    错误码:
        - 403: 无权操作此订单
        - 404: 订单不存在
        - 409: 订单已支付
        - 410: 订单已过期
    """
    # 先校验订单归属
    _get_order_or_404(db, order_no, current_user.id)
    try:
        order = confirm_order(db, order_no)
        return OrderResponse.model_validate(order)
    except OrderNotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except OrderAlreadyPaidError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except OrderExpiredError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/api/payment/{order_no}/cancel",
    response_model=OrderResponse,
    summary="取消订单",
    description="取消未支付的充值订单。",
)
async def cancel_payment(
    order_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    """POST /api/payment/{order_no}/cancel

    请求头:
        Authorization: Bearer <token>

    响应 (200):
        OrderResponse: 取消后的订单信息

    错误码:
        - 403: 无权操作此订单
        - 404: 订单不存在
    """
    # 先校验订单归属
    _get_order_or_404(db, order_no, current_user.id)
    try:
        order = cancel_order(db, order_no)
        return OrderResponse.model_validate(order)
    except OrderNotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
