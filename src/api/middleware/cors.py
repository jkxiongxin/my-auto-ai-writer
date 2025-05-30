"""CORS中间件."""

from typing import Callable

from fastapi import Request, Response

from src.utils.logger import get_logger

logger = get_logger(__name__)


async def cors_middleware(request: Request, call_next: Callable) -> Response:
    """CORS中间件."""
    
    # 处理预检请求
    if request.method == "OPTIONS":
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        response.headers["Access-Control-Max-Age"] = "86400"  # 24小时
        return response
    
    # 处理正常请求
    response = await call_next(request)
    
    # 添加CORS头
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Expose-Headers"] = "X-Request-ID, X-Process-Time, X-RateLimit-Remaining"
    
    return response