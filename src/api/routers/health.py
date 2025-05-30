"""健康检查路由."""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.utils.config import settings
from src.utils.llm_client import UniversalLLMClient
from src.models.database import get_db_session
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class HealthStatus(BaseModel):
    """健康状态响应模型."""
    
    status: str
    timestamp: datetime
    version: str
    uptime_seconds: float
    services: Dict[str, Any]


class DetailedHealthStatus(HealthStatus):
    """详细健康状态响应模型."""
    
    system_info: Dict[str, Any]
    performance_metrics: Dict[str, Any]


# 服务启动时间
_start_time = time.time()


@router.get("/", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """基础健康检查端点."""
    
    current_time = datetime.utcnow()
    uptime = time.time() - _start_time
    
    # 检查核心服务状态
    services_status = await _check_services_status()
    
    # 确定整体状态
    overall_status = "healthy" if all(
        service["status"] == "healthy" for service in services_status.values()
    ) else "degraded"
    
    return HealthStatus(
        status=overall_status,
        timestamp=current_time,
        version="1.0.0",
        uptime_seconds=uptime,
        services=services_status
    )


@router.get("/detailed", response_model=DetailedHealthStatus)
async def detailed_health_check() -> DetailedHealthStatus:
    """详细健康检查端点."""
    
    # 获取基础健康状态
    basic_health = await health_check()
    
    # 获取系统信息
    system_info = await _get_system_info()
    
    # 获取性能指标
    performance_metrics = await _get_performance_metrics()
    
    return DetailedHealthStatus(
        **basic_health.dict(),
        system_info=system_info,
        performance_metrics=performance_metrics
    )


@router.get("/readiness")
async def readiness_check() -> Dict[str, str]:
    """就绪状态检查（用于Kubernetes等容器编排）."""
    
    try:
        # 检查数据库连接
        async with get_db_session() as session:
            await session.execute("SELECT 1")
        
        # 检查LLM客户端
        llm_client = UniversalLLMClient()
        if not llm_client.is_available():
            raise Exception("LLM客户端不可用")
        
        return {"status": "ready"}
        
    except Exception as e:
        logger.error(f"就绪状态检查失败: {e}")
        raise HTTPException(status_code=503, detail="服务未就绪")


@router.get("/liveness")
async def liveness_check() -> Dict[str, str]:
    """存活状态检查（用于Kubernetes等容器编排）."""
    
    # 简单的存活检查
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


async def _check_services_status() -> Dict[str, Dict[str, Any]]:
    """检查各个服务的状态."""
    
    services = {}
    
    # 检查数据库
    try:
        async with get_db_session() as session:
            await session.execute("SELECT 1")
        services["database"] = {
            "status": "healthy",
            "message": "数据库连接正常"
        }
    except Exception as e:
        logger.warning(f"数据库健康检查失败: {e}")
        services["database"] = {
            "status": "unhealthy",
            "message": f"数据库连接失败: {str(e)}"
        }
    
    # 检查LLM服务
    try:
        llm_client = UniversalLLMClient()
        if llm_client.is_available():
            services["llm"] = {
                "status": "healthy",
                "message": "LLM服务可用",
                "providers": llm_client.get_available_providers()
            }
        else:
            services["llm"] = {
                "status": "degraded",
                "message": "部分LLM提供商不可用",
                "providers": llm_client.get_available_providers()
            }
    except Exception as e:
        logger.warning(f"LLM服务健康检查失败: {e}")
        services["llm"] = {
            "status": "unhealthy",
            "message": f"LLM服务不可用: {str(e)}"
        }
    
    # 检查缓存服务（如果启用）
    if settings.cache_enabled:
        try:
            from src.utils.cache import cache_manager
            await cache_manager.health_check()
            services["cache"] = {
                "status": "healthy",
                "message": "缓存服务正常"
            }
        except Exception as e:
            logger.warning(f"缓存服务健康检查失败: {e}")
            services["cache"] = {
                "status": "unhealthy",
                "message": f"缓存服务不可用: {str(e)}"
            }
    
    return services


async def _get_system_info() -> Dict[str, Any]:
    """获取系统信息."""
    
    import psutil
    import platform
    
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "disk_usage_percent": psutil.disk_usage('/').percent,
    }


async def _get_performance_metrics() -> Dict[str, Any]:
    """获取性能指标."""
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_usage_mb": round(process.memory_info().rss / (1024**2), 2),
        "memory_percent": process.memory_percent(),
        "open_files": len(process.open_files()),
        "threads": process.num_threads(),
        "uptime_seconds": time.time() - _start_time,
    }


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """获取应用指标（用于监控系统）."""
    
    metrics = {
        "uptime_seconds": time.time() - _start_time,
        "version": "1.0.0",
        "environment": settings.environment,
    }
    
    # 添加性能指标
    performance = await _get_performance_metrics()
    metrics.update(performance)
    
    # 添加服务状态
    services = await _check_services_status()
    metrics["services_healthy"] = sum(1 for s in services.values() if s["status"] == "healthy")
    metrics["services_total"] = len(services)
    
    return metrics