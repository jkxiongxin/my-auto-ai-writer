"""错误处理中间件."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logger import get_logger

logger = get_logger(__name__)


async def error_handler_middleware(request: Request, call_next: Callable) -> Response:
    """错误处理中间件."""
    
    # 生成请求ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    
    try:
        # 添加请求ID到响应头
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        # 记录请求日志
        process_time = time.time() - start_time
        logger.info(
            "请求处理完成",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=f"{process_time:.3f}s",
            request_id=request_id,
        )
        
        return response
        
    except HTTPException as exc:
        # HTTP异常处理
        process_time = time.time() - start_time
        logger.warning(
            "HTTP异常",
            method=request.method,
            url=str(request.url),
            status_code=exc.status_code,
            detail=exc.detail,
            process_time=f"{process_time:.3f}s",
            request_id=request_id,
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error_type": "HTTPException",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id}
        )
        
    except Exception as exc:
        # 未处理异常
        process_time = time.time() - start_time
        logger.error(
            "未处理异常",
            method=request.method,
            url=str(request.url),
            error=str(exc),
            error_type=type(exc).__name__,
            process_time=f"{process_time:.3f}s",
            request_id=request_id,
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "detail": "服务器内部错误",
                "error_type": "InternalServerError",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id}
        )


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """错误处理中间件类."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求."""
        return await error_handler_middleware(request, call_next)