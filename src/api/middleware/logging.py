"""日志中间件."""

import time
from typing import Callable

from fastapi import Request, Response

from src.utils.logger import get_logger

logger = get_logger(__name__)


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """日志中间件."""
    
    start_time = time.time()
    
    # 记录请求开始
    logger.info(
        "请求开始",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "unknown"),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    
    # 处理请求
    response = await call_next(request)
    
    # 计算处理时间
    process_time = time.time() - start_time
    
    # 记录请求结束
    logger.info(
        "请求结束",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=f"{process_time:.3f}s",
        response_size=response.headers.get("content-length", "unknown"),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    
    # 添加处理时间到响应头
    response.headers["X-Process-Time"] = f"{process_time:.3f}"
    
    return response