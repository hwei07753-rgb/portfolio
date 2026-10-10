"""
FastAPI 应用入口

AI 简历优化助手后端服务启动文件。
配置所有路由、中间件和生命周期事件。
"""

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import time

from backend.database import init_db
from backend.routers import auth, jobs, knowledge, optimize, payment, resume, stats

# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 应用生命周期
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理

    启动时初始化数据库，关闭时清理资源。
    """
    logger.info("正在启动 AI 简历优化助手...")
    init_db()
    logger.info("数据库初始化完成")
    yield
    logger.info("正在关闭 AI 简历优化助手...")


# ---------------------------------------------------------------------------
# 创建 FastAPI 应用
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI 简历优化助手",
    description="基于大语言模型的智能简历优化平台",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# 中间件配置
# ---------------------------------------------------------------------------

# CORS（允许前端跨域请求）
# 生产环境应将 allow_origins 限制为具体域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录每个请求的方法、路径、状态码和耗时"""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} "
        f"({duration:.2f}s)"
    )
    return response

# ---------------------------------------------------------------------------
# 注册路由
# 各路由模块内部已定义完整前缀（如 prefix="/api/auth"），
# 此处无需再传 prefix 参数，避免重复拼接。
# ---------------------------------------------------------------------------

app.include_router(auth.router)        # /api/auth/*
app.include_router(resume.router)      # /api/resume/*
app.include_router(optimize.router)    # /api/optimize/*
app.include_router(knowledge.router)   # /api/knowledge/*
app.include_router(payment.router)     # /api/payment/*, /api/wallet/*
app.include_router(stats.router)       # /api/stats/*
app.include_router(jobs.router)       # /api/jobs/*


# ---------------------------------------------------------------------------
# 静态文件服务（前端页面）
# ---------------------------------------------------------------------------

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 挂载前端静态文件（如果目录存在）
frontend_assets = BASE_DIR / "frontend" / "assets"
if frontend_assets.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_assets)), name="assets")

frontend_static = BASE_DIR / "frontend" / "static"
if frontend_static.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_static)), name="static")


# ---------------------------------------------------------------------------
# 根路径 & 健康检查
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """健康检查响应模型"""

    status: str
    service: str
    version: str


@app.get(
    "/",
    tags=["根路径"],
    summary="首页",
    description="返回前端页面。",
)
async def root():
    """GET /

    返回前端 index.html 页面。
    """
    from fastapi.responses import FileResponse

    index_path = BASE_DIR / "frontend" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "message": "欢迎使用 AI 简历优化助手 API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["健康检查"],
    summary="健康检查",
    description="用于监控服务状态，返回服务运行信息。",
)
async def health() -> HealthResponse:
    """GET /api/health

    健康检查端点，供运维监控和负载均衡器探活使用。

    响应 (200):
        HealthResponse: status, service, version
    """
    return HealthResponse(
        status="ok",
        service="ai-resume-optimizer",
        version="1.0.0",
    )


# ---------------------------------------------------------------------------
# 直接运行入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
