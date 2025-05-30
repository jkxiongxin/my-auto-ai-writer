"""FastAPI应用主入口."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.utils.config import settings
from src.utils.logger import get_logger
from src.models.database import init_database, close_database
from .routers import health, generation, projects, quality, export, progress
from .middleware.error_handler import error_handler_middleware
from .middleware.logging import logging_middleware
from .middleware.rate_limit import rate_limit_middleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期管理."""
    # 启动时初始化
    logger.info("正在启动AI小说生成器API服务...")
    
    try:
        # 初始化数据库
        await init_database()
        logger.info("数据库初始化完成")
        
        # 其他启动任务可以在这里添加
        logger.info("API服务启动完成")
        
        yield
        
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        raise
    finally:
        # 关闭时清理
        logger.info("正在关闭API服务...")
        await close_database()
        logger.info("API服务已关闭")


def create_app() -> FastAPI:
    """创建FastAPI应用实例."""
    
    app = FastAPI(
        title="AI智能小说生成器",
        description="AI Novel Generator - 智能小说生成系统API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods_list,
        allow_headers=settings.cors_allow_headers_list,
    )
    
    # 添加自定义中间件
    app.middleware("http")(error_handler_middleware)
    app.middleware("http")(logging_middleware)
    app.middleware("http")(rate_limit_middleware)
    
    # 注册路由
    app.include_router(health.router, prefix="/health", tags=["健康检查"])
    app.include_router(generation.router, prefix="/api/v1", tags=["小说生成"])
    app.include_router(projects.router, prefix="/api/v1", tags=["项目管理"])
    app.include_router(quality.router, prefix="/api/v1", tags=["质量检查"])
    app.include_router(export.router, prefix="/api/v1", tags=["导出功能"])
    app.include_router(progress.router, prefix="/api/v1", tags=["进度追踪"])
    
    # 静态文件服务（前端界面）
    try:
        app.mount("/static", StaticFiles(directory="frontend"), name="static")
        logger.info("前端静态文件服务已启用")
    except Exception as e:
        logger.warning(f"无法挂载静态文件服务: {e}")
    
    # 全局异常处理器
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """全局异常处理器."""
        logger.error(f"未处理的异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "服务器内部错误",
                "error_type": "InternalServerError",
                "request_id": getattr(request.state, "request_id", None),
            }
        )
    
    # 404处理器
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc) -> JSONResponse:
        """404错误处理器."""
        return JSONResponse(
            status_code=404,
            content={
                "detail": f"路径 {request.url.path} 未找到",
                "error_type": "NotFound",
                "request_id": getattr(request.state, "request_id", None),
            }
        )
    
    return app


# 创建应用实例
app = create_app()


@app.get("/", tags=["根路径"])
async def root() -> dict:
    """根路径欢迎信息."""
    return {
        "message": "欢迎使用AI智能小说生成器",
        "version": "1.0.0",
        "docs_url": "/docs",
        "frontend_url": "/static/index.html",
        "status": "running"
    }


@app.get("/app", tags=["前端"])
async def frontend_app():
    """重定向到前端应用."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
    )