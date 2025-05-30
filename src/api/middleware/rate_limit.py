"""速率限制中间件."""

import time
from collections import defaultdict, deque
from typing import Callable, Dict, Deque

from fastapi import Request, Response, HTTPException

from src.utils.logger import get_logger
from src.utils.config import settings

logger = get_logger(__name__)


class RateLimiter:
    """速率限制器."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """初始化速率限制器.
        
        Args:
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口大小（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, Deque[float]] = defaultdict(deque)
    
    def is_allowed(self, client_id: str) -> bool:
        """检查是否允许请求."""
        
        now = time.time()
        client_requests = self.requests[client_id]
        
        # 清理过期的请求记录
        while client_requests and client_requests[0] <= now - self.window_seconds:
            client_requests.popleft()
        
        # 检查是否超过限制
        if len(client_requests) >= self.max_requests:
            return False
        
        # 记录当前请求
        client_requests.append(now)
        return True
    
    def get_remaining_requests(self, client_id: str) -> int:
        """获取剩余请求次数."""
        
        now = time.time()
        client_requests = self.requests[client_id]
        
        # 清理过期记录
        while client_requests and client_requests[0] <= now - self.window_seconds:
            client_requests.popleft()
        
        return max(0, self.max_requests - len(client_requests))
    
    def get_reset_time(self, client_id: str) -> float:
        """获取重置时间."""
        
        client_requests = self.requests[client_id]
        if not client_requests:
            return 0
        
        return client_requests[0] + self.window_seconds


# 全局速率限制器实例
_rate_limiters = {
    "global": RateLimiter(max_requests=1000, window_seconds=60),
    "generation": RateLimiter(max_requests=10, window_seconds=60),
    "export": RateLimiter(max_requests=20, window_seconds=60),
}


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """速率限制中间件."""
    
    # 获取客户端标识
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    client_id = f"{client_ip}:{hash(user_agent) % 10000}"
    
    # 获取请求路径
    path = request.url.path
    
    # 定义需要豁免速率限制的路径
    exempt_paths = [
        "/api/v1/progress/",       # 进度查询接口（完整路径）
        "/api/progress/",          # 进度查询接口（兼容路径）
        "/progress/",              # 进度查询接口（简化路径）
        "/api/v1/ws/progress/",    # WebSocket进度连接（完整路径）
        "/ws/progress/",           # WebSocket进度连接
        "/api/ws/progress/",       # WebSocket进度连接（兼容路径）
        "/health/",                # 健康检查接口
        "/api/health",             # 健康检查接口
        "/status",                 # 状态接口
        "/api/status",             # 状态接口
        "/metrics",                # 指标接口
        "/api/metrics",            # 指标接口
        "/api/v1/progress/active", # 活跃任务查询（完整路径）
        "/active",                 # 活跃任务查询（简化路径）
    ]
    
    # 特殊处理：WebSocket升级请求
    is_websocket_upgrade = (
        request.headers.get("upgrade", "").lower() == "websocket" and
        "progress" in path
    )
    
    # 检查是否为豁免路径
    is_exempt = (
        any(exempt_path in path for exempt_path in exempt_paths) or
        is_websocket_upgrade
    )
    
    # 如果是豁免路径，直接处理请求，不进行速率限制
    if is_exempt:
        logger.debug(f"豁免路径，跳过速率限制: {path}")
        response = await call_next(request)
        # 仍然添加信息头，但不进行限制
        response.headers["X-RateLimit-Exempt"] = "true"
        return response
    
    # 确定使用哪个限制器
    if "/generate-novel" in path:
        limiter_key = "generation"
    elif "/export" in path:
        limiter_key = "export"
    else:
        limiter_key = "global"
    
    limiter = _rate_limiters[limiter_key]
    
    # 检查速率限制
    if not limiter.is_allowed(client_id):
        remaining = limiter.get_remaining_requests(client_id)
        reset_time = limiter.get_reset_time(client_id)
        
        logger.warning(
            "速率限制触发",
            client_id=client_id,
            path=path,
            limiter=limiter_key,
            remaining=remaining,
            reset_time=reset_time,
        )
        
        raise HTTPException(
            status_code=429,
            detail="请求过于频繁，请稍后重试",
            headers={
                "X-RateLimit-Limit": str(limiter.max_requests),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(reset_time)),
                "Retry-After": str(int(reset_time - time.time())),
            }
        )
    
    # 处理请求
    response = await call_next(request)
    
    # 添加速率限制信息到响应头
    remaining = limiter.get_remaining_requests(client_id)
    reset_time = limiter.get_reset_time(client_id)
    
    response.headers["X-RateLimit-Limit"] = str(limiter.max_requests)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(int(reset_time))
    
    return response


def configure_rate_limits(config: dict) -> None:
    """配置速率限制."""
    
    global _rate_limiters
    
    for key, settings in config.items():
        if key in _rate_limiters:
            _rate_limiters[key] = RateLimiter(
                max_requests=settings.get("max_requests", 100),
                window_seconds=settings.get("window_seconds", 60)
            )
        else:
            _rate_limiters[key] = RateLimiter(
                max_requests=settings.get("max_requests", 100),
                window_seconds=settings.get("window_seconds", 60)
            )


def get_rate_limit_status() -> Dict[str, Dict]:
    """获取速率限制状态."""
    
    status = {}
    for key, limiter in _rate_limiters.items():
        status[key] = {
            "max_requests": limiter.max_requests,
            "window_seconds": limiter.window_seconds,
            "active_clients": len(limiter.requests),
        }
    
    return status