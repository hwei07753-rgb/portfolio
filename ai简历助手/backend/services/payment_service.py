"""
支付与点数服务模块

处理用户钱包、点数流水、充值订单等支付相关业务逻辑。
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.payment import UserWallet, PointTransaction, PaymentOrder

logger = logging.getLogger(__name__)

# 充值套餐配置
RECHARGE_PACKAGES = {
    "small": {"points": 10, "price_cents": 990},    # 9.9 元
    "medium": {"points": 50, "price_cents": 3990},   # 39.9 元
    "large": {"points": 100, "price_cents": 6990},   # 69.9 元
}

# 订单过期时间（分钟）
ORDER_EXPIRE_MINUTES = 15


class PaymentServiceError(Exception):
    """支付服务异常基类"""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InsufficientPointsError(PaymentServiceError):
    """点数不足"""

    def __init__(self, balance: int):
        self.balance = balance
        super().__init__(f"点数不足，当前余额: {balance}", status_code=402)


class OrderNotFoundError(PaymentServiceError):
    """订单不存在"""

    def __init__(self):
        super().__init__("订单不存在", status_code=404)


class OrderExpiredError(PaymentServiceError):
    """订单已过期"""

    def __init__(self):
        super().__init__("订单已过期，请重新下单", status_code=410)


class OrderAlreadyPaidError(PaymentServiceError):
    """订单已支付"""

    def __init__(self, message: str = "订单已支付"):
        super().__init__(message, status_code=409)


class InvalidPackageError(PaymentServiceError):
    """无效的套餐"""

    def __init__(self):
        super().__init__("无效的充值套餐", status_code=400)


def get_wallet(db: Session, user_id: int) -> UserWallet:
    """获取用户钱包

    如果钱包不存在，自动创建一个新钱包。

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        UserWallet ORM 对象
    """
    wallet = db.query(UserWallet).filter(UserWallet.user_id == user_id).first()
    if not wallet:
        wallet = UserWallet(user_id=user_id, balance=0)
        db.add(wallet)
        db.flush()  # flush 而非 commit，由调用者控制事务
    return wallet


def get_transactions(
    db: Session,
    user_id: int,
    page: int = 1,
    size: int = 20,
) -> dict:
    """获取点数流水记录

    Args:
        db: 数据库会话
        user_id: 用户 ID
        page: 页码
        size: 每页数量

    Returns:
        dict 包含 total, page, page_size, items
    """
    query = db.query(PointTransaction).filter(PointTransaction.user_id == user_id)

    total = query.count()
    items = (
        query.order_by(PointTransaction.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": size,
        "items": items,
    }


def get_packages() -> list[dict]:
    """获取可用充值套餐

    Returns:
        套餐列表，每个包含 package_id, points, price_cents, price_display
    """
    packages = []
    for package_id, config in RECHARGE_PACKAGES.items():
        packages.append({
            "package_id": package_id,
            "points": config["points"],
            "price_cents": config["price_cents"],
            "price_display": f"¥{config['price_cents'] / 100:.1f}",
        })
    return packages


def create_order(db: Session, user_id: int, package_id: str) -> PaymentOrder:
    """创建充值订单

    Args:
        db: 数据库会话
        user_id: 用户 ID
        package_id: 套餐 ID（small/medium/large）

    Returns:
        创建的 PaymentOrder 对象

    Raises:
        InvalidPackageError: 无效的套餐
    """
    if package_id not in RECHARGE_PACKAGES:
        raise InvalidPackageError()

    package = RECHARGE_PACKAGES[package_id]
    order_no = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"

    order = PaymentOrder(
        order_no=order_no,
        user_id=user_id,
        amount_cents=package["price_cents"],
        points=package["points"],
        status="pending",
        expire_at=datetime.now(timezone.utc) + timedelta(minutes=ORDER_EXPIRE_MINUTES),
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    logger.info(f"创建充值订单: {order_no}, 用户={user_id}, 套餐={package_id}")
    return order


def confirm_order(db: Session, order_no: str) -> PaymentOrder:
    """确认支付

    模拟支付确认，为用户充值点数。

    Args:
        db: 数据库会话
        order_no: 订单号

    Returns:
        更新后的 PaymentOrder 对象

    Raises:
        OrderNotFoundError: 订单不存在
        OrderExpiredError: 订单已过期
        OrderAlreadyPaidError: 订单已支付
    """
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == order_no).first()
    if not order:
        raise OrderNotFoundError()

    # 检查订单状态
    if order.status == "paid":
        raise OrderAlreadyPaidError()

    # 检查订单是否已取消/过期
    if order.status == "expired":
        raise OrderAlreadyPaidError("订单已取消或过期")

    # 检查是否过期
    # SQLite 存储的是 offset-naive datetime，需要统一处理
    expire_at = order.expire_at
    if expire_at.tzinfo is None:
        # 如果是 naive datetime，假设它是 UTC
        expire_at = expire_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expire_at:
        order.status = "expired"
        db.commit()
        raise OrderExpiredError()

    # 更新订单状态
    order.status = "paid"
    order.paid_at = datetime.now(timezone.utc)

    # 充值点数
    wallet = get_wallet(db, order.user_id)
    wallet.balance += order.points
    wallet.total_recharged += order.points

    # 记录流水
    transaction = PointTransaction(
        user_id=order.user_id,
        amount=order.points,
        balance_after=wallet.balance,
        type="recharge",
        description=f"充值 {order.points} 点",
        reference_id=order.order_no,
    )
    db.add(transaction)

    db.commit()
    db.refresh(order)

    logger.info(f"订单支付成功: {order_no}, 充值 {order.points} 点")
    return order


def cancel_order(db: Session, order_no: str) -> PaymentOrder:
    """取消订单

    Args:
        db: 数据库会话
        order_no: 订单号

    Returns:
        更新后的 PaymentOrder 对象

    Raises:
        OrderNotFoundError: 订单不存在
    """
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == order_no).first()
    if not order:
        raise OrderNotFoundError()

    if order.status == "pending":
        order.status = "expired"
        db.commit()
        logger.info(f"订单已取消: {order_no}")

    return order


def consume_points(
    db: Session,
    user_id: int,
    amount: int,
    desc: str,
    reference_id: Optional[str] = None,
) -> PointTransaction:
    """消费点数

    Args:
        db: 数据库会话
        user_id: 用户 ID
        amount: 消费数量（正数）
        desc: 消费描述
        reference_id: 关联 ID（如简历 ID）

    Returns:
        PointTransaction 流水记录

    Raises:
        InsufficientPointsError: 点数不足
    """
    wallet = get_wallet(db, user_id)

    # 检查余额
    if wallet.balance < amount:
        raise InsufficientPointsError(wallet.balance)

    # 扣减点数
    wallet.balance -= amount
    wallet.total_consumed += amount

    # 记录流水
    transaction = PointTransaction(
        user_id=user_id,
        amount=-amount,
        balance_after=wallet.balance,
        type="consume",
        description=desc,
        reference_id=reference_id,
    )
    db.add(transaction)
    # 由调用者控制 commit 时机，保证事务原子性
    db.flush()

    logger.info(f"消费点数: 用户={user_id}, 数量={amount}, 描述={desc}")
    return transaction


def refund_points(
    db: Session,
    user_id: int,
    amount: int,
    desc: str,
    reference_id: Optional[str] = None,
) -> PointTransaction:
    """退款点数

    在优化失败等场景下，将已扣除的点数返还给用户。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        amount: 退款数量（正数）
        desc: 退款描述
        reference_id: 关联 ID

    Returns:
        PointTransaction 流水记录
    """
    wallet = get_wallet(db, user_id)

    # 增加点数
    wallet.balance += amount
    wallet.total_consumed -= amount

    # 记录流水
    transaction = PointTransaction(
        user_id=user_id,
        amount=amount,
        balance_after=wallet.balance,
        type="refund",
        description=desc,
        reference_id=reference_id,
    )
    db.add(transaction)
    # 由调用者控制 commit 时机，保证事务原子性
    db.flush()

    logger.info(f"退款点数: 用户={user_id}, 数量={amount}, 描述={desc}")
    return transaction


def get_orders(
    db: Session,
    user_id: int,
    page: int = 1,
    size: int = 20,
) -> dict:
    """获取用户订单列表

    Args:
        db: 数据库会话
        user_id: 用户 ID
        page: 页码
        size: 每页数量

    Returns:
        dict 包含 total, page, page_size, items
    """
    query = db.query(PaymentOrder).filter(PaymentOrder.user_id == user_id)

    total = query.count()
    items = (
        query.order_by(PaymentOrder.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": size,
        "items": items,
    }
