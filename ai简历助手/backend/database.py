"""
数据库配置模块

提供 SQLAlchemy 引擎、会话工厂和基类。
支持 SQLite（开发）和 PostgreSQL（生产）。
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy 声明基类

    所有模型类继承此类，用于 ORM 映射。
    """
    pass


def _set_sqlite_pragma(dbapi_conn, connection_record):
    """设置 SQLite PRAGMA 以支持并发访问

    - WAL 模式：允许并发读写
    - busy_timeout：遇到锁定时等待 50 秒再报错
    - journal_mode：使用 WAL 提升并发性能
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=50000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


# 创建数据库引擎
# SQLite 需要设置 check_same_thread=False 以支持多线程
# 生产环境使用 PostgreSQL 时可配置连接池参数
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=(
        {"check_same_thread": False}
        if settings.DATABASE_URL.startswith("sqlite")
        else {}
    ),
    echo=False,  # 生产环境关闭 SQL 日志，调试时可设为 True
    pool_size=5,  # 连接池大小（SQLite 不生效，PostgreSQL 有效）
    max_overflow=10,  # 最大溢出连接数
    pool_pre_ping=True,  # 连接前检测可用性，避免使用已断开的连接
)

# 为 SQLite 注册连接事件，设置 WAL 模式和 busy_timeout
if settings.DATABASE_URL.startswith("sqlite"):
    event.listen(engine, "connect", _set_sqlite_pragma)

# 会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入：获取数据库会话

    使用 yield 确保请求结束后自动关闭会话。

    Yields:
        SQLAlchemy Session 实例

    Example:
        ```python
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
        ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """初始化数据库

    根据模型定义创建所有表。如果表已存在则跳过。

    注意：生产环境建议使用 Alembic 进行数据库迁移。
    """
    # 导入 models 包以注册所有模型到 Base.metadata
    import backend.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    print("[Info] Database tables created successfully.")


if __name__ == "__main__":
    # 直接运行此文件时初始化数据库
    import sys
    from pathlib import Path

    # 确保项目根目录在 Python 路径中
    root_dir = str(Path(__file__).parent.parent)
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    init_db()
