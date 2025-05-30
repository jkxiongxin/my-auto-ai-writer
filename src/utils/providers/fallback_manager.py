"""降级和容错管理模块."""

import time
from typing import Dict, Any, List, Optional, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """失败类型枚举."""
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    MODEL_NOT_FOUND = "model_not_found"
    INVALID_REQUEST = "invalid_request"
    UNKNOWN = "unknown"


@dataclass
class FailureRecord:
    """失败记录."""
    provider_name: str
    failure_type: FailureType
    error_message: str
    timestamp: float
    retry_after: Optional[int] = None  # 建议重试等待时间（秒）


@dataclass
class ProviderHealth:
    """提供商健康状态."""
    provider_name: str
    is_healthy: bool = True
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    consecutive_failures: int = 0
    failure_types: Dict[FailureType, int] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.failure_types:
            self.failure_types = {}


class FallbackManager:
    """降级和容错管理器."""
    
    def __init__(self) -> None:
        """初始化降级管理器."""
        self.provider_health: Dict[str, ProviderHealth] = {}
        self.failure_history: List[FailureRecord] = []
        self.circuit_breaker_config = {
            "failure_threshold": 5,       # 连续失败阈值
            "recovery_timeout": 300,      # 恢复超时时间（秒）
            "half_open_max_calls": 3,     # 半开状态最大调用次数
        }
        self.blacklist_duration = 600     # 黑名单持续时间（秒）
        self.max_history_size = 1000      # 最大历史记录数
        
        logger.info("降级管理器初始化完成")
    
    def record_failure(
        self,
        provider_name: str,
        failure_type: Union[FailureType, str],
        error_message: str = "",
        retry_after: Optional[int] = None
    ) -> None:
        """记录提供商失败.
        
        Args:
            provider_name: 提供商名称
            failure_type: 失败类型
            error_message: 错误消息
            retry_after: 建议重试等待时间
        """
        # 确保failure_type是FailureType枚举
        if isinstance(failure_type, str):
            try:
                failure_type = FailureType(failure_type)
            except ValueError:
                failure_type = FailureType.UNKNOWN
        
        current_time = time.time()
        
        # 创建失败记录
        failure_record = FailureRecord(
            provider_name=provider_name,
            failure_type=failure_type,
            error_message=error_message,
            timestamp=current_time,
            retry_after=retry_after
        )
        
        # 添加到历史记录
        self.failure_history.append(failure_record)
        
        # 限制历史记录大小
        if len(self.failure_history) > self.max_history_size:
            self.failure_history = self.failure_history[-self.max_history_size:]
        
        # 更新提供商健康状态
        if provider_name not in self.provider_health:
            self.provider_health[provider_name] = ProviderHealth(provider_name)
        
        health = self.provider_health[provider_name]
        health.failure_count += 1
        health.consecutive_failures += 1
        health.last_failure_time = current_time
        
        # 更新失败类型统计
        if failure_type not in health.failure_types:
            health.failure_types[failure_type] = 0
        health.failure_types[failure_type] += 1
        
        # 检查是否需要启动熔断器
        if health.consecutive_failures >= self.circuit_breaker_config["failure_threshold"]:
            health.is_healthy = False
            logger.warning(
                f"提供商 {provider_name} 触发熔断器，连续失败 {health.consecutive_failures} 次",
                extra={
                    "provider": provider_name,
                    "failure_type": failure_type.value,
                    "consecutive_failures": health.consecutive_failures
                }
            )
        
        logger.debug(
            f"记录提供商失败: {provider_name}",
            extra={
                "provider": provider_name,
                "failure_type": failure_type.value,
                "error_message": error_message,
                "consecutive_failures": health.consecutive_failures
            }
        )
    
    def record_success(self, provider_name: str) -> None:
        """记录提供商成功.
        
        Args:
            provider_name: 提供商名称
        """
        current_time = time.time()
        
        if provider_name not in self.provider_health:
            self.provider_health[provider_name] = ProviderHealth(provider_name)
        
        health = self.provider_health[provider_name]
        health.consecutive_failures = 0
        health.last_success_time = current_time
        
        # 如果之前是不健康状态，现在恢复健康
        if not health.is_healthy:
            health.is_healthy = True
            logger.info(f"提供商 {provider_name} 恢复健康状态")
        
        logger.debug(f"记录提供商成功: {provider_name}")
    
    def is_provider_healthy(self, provider_name: str) -> bool:
        """检查提供商是否健康.
        
        Args:
            provider_name: 提供商名称
            
        Returns:
            True如果健康，False否则
        """
        if provider_name not in self.provider_health:
            return True  # 默认健康
        
        health = self.provider_health[provider_name]
        current_time = time.time()
        
        # 如果当前是不健康状态，检查是否可以恢复
        if not health.is_healthy:
            # 检查恢复超时
            if (health.last_failure_time and 
                current_time - health.last_failure_time > self.circuit_breaker_config["recovery_timeout"]):
                
                # 进入半开状态，允许少量请求测试恢复
                logger.info(f"提供商 {provider_name} 进入半开状态，允许测试恢复")
                return True
        
        return health.is_healthy
    
    def should_fallback(self, error: Exception) -> bool:
        """判断是否应该降级.
        
        Args:
            error: 异常对象
            
        Returns:
            True如果应该降级，False否则
        """
        error_message = str(error).lower()
        
        # 不应该降级的情况
        non_fallback_patterns = [
            "invalid api key",
            "authentication failed", 
            "unauthorized",
            "forbidden"
        ]
        
        for pattern in non_fallback_patterns:
            if pattern in error_message:
                return False
        
        # 应该降级的情况
        fallback_patterns = [
            "rate limit",
            "timeout",
            "connection",
            "server error",
            "service unavailable",
            "internal server error",
            "bad gateway",
            "gateway timeout"
        ]
        
        for pattern in fallback_patterns:
            if pattern in error_message:
                return True
        
        # 默认降级（对于不明确的错误保守处理）
        return True
    
    def get_failure_type(self, error: Exception) -> FailureType:
        """根据异常获取失败类型.
        
        Args:
            error: 异常对象
            
        Returns:
            失败类型
        """
        error_message = str(error).lower()
        
        if "rate limit" in error_message:
            return FailureType.RATE_LIMIT
        elif any(pattern in error_message for pattern in ["auth", "unauthorized", "forbidden", "invalid api key"]):
            return FailureType.AUTHENTICATION
        elif any(pattern in error_message for pattern in ["connection", "connect", "network"]):
            return FailureType.CONNECTION
        elif "timeout" in error_message:
            return FailureType.TIMEOUT
        elif "model not found" in error_message:
            return FailureType.MODEL_NOT_FOUND
        elif any(pattern in error_message for pattern in ["invalid request", "bad request"]):
            return FailureType.INVALID_REQUEST
        else:
            return FailureType.UNKNOWN
    
    def get_retry_delay(self, provider_name: str, failure_type: FailureType) -> float:
        """获取重试延迟时间.
        
        Args:
            provider_name: 提供商名称
            failure_type: 失败类型
            
        Returns:
            建议的重试延迟时间（秒）
        """
        if provider_name not in self.provider_health:
            return 1.0
        
        health = self.provider_health[provider_name]
        base_delay = 1.0
        
        # 根据失败类型调整延迟
        if failure_type == FailureType.RATE_LIMIT:
            base_delay = 60.0  # 速率限制，等待更久
        elif failure_type == FailureType.CONNECTION:
            base_delay = 5.0   # 连接问题，中等延迟
        elif failure_type == FailureType.TIMEOUT:
            base_delay = 3.0   # 超时，短延迟
        
        # 根据连续失败次数指数退避
        multiplier = min(2 ** health.consecutive_failures, 32)  # 最大32倍
        
        return base_delay * multiplier
    
    def get_failure_stats(self, provider_name: str) -> Dict[str, Any]:
        """获取提供商失败统计.
        
        Args:
            provider_name: 提供商名称
            
        Returns:
            失败统计字典
        """
        if provider_name not in self.provider_health:
            return {
                "total": 0,
                "consecutive": 0,
                "is_healthy": True,
                "failure_types": {},
                "last_failure_time": None,
                "last_success_time": None
            }
        
        health = self.provider_health[provider_name]
        return {
            "total": health.failure_count,
            "consecutive": health.consecutive_failures,
            "is_healthy": health.is_healthy,
            "failure_types": {ft.value: count for ft, count in health.failure_types.items()},
            "last_failure_time": health.last_failure_time,
            "last_success_time": health.last_success_time
        }
    
    def get_recent_failures(
        self,
        provider_name: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取最近的失败记录.
        
        Args:
            provider_name: 提供商名称，None表示所有提供商
            since: 时间戳，只返回此时间之后的记录
            limit: 最大记录数
            
        Returns:
            失败记录列表
        """
        current_time = time.time()
        since = since or (current_time - 3600)  # 默认最近1小时
        
        filtered_failures = []
        for failure in reversed(self.failure_history):  # 最新的在前
            if failure.timestamp < since:
                break
            
            if provider_name and failure.provider_name != provider_name:
                continue
            
            filtered_failures.append({
                "provider_name": failure.provider_name,
                "failure_type": failure.failure_type.value,
                "error_message": failure.error_message,
                "timestamp": failure.timestamp,
                "retry_after": failure.retry_after
            })
            
            if len(filtered_failures) >= limit:
                break
        
        return filtered_failures
    
    def reset_provider_health(self, provider_name: str) -> None:
        """重置提供商健康状态.
        
        Args:
            provider_name: 提供商名称
        """
        if provider_name in self.provider_health:
            self.provider_health[provider_name] = ProviderHealth(provider_name)
            logger.info(f"重置提供商健康状态: {provider_name}")
    
    def clear_failure_history(self, provider_name: Optional[str] = None) -> None:
        """清除失败历史.
        
        Args:
            provider_name: 提供商名称，None表示清除所有
        """
        if provider_name:
            self.failure_history = [
                f for f in self.failure_history 
                if f.provider_name != provider_name
            ]
            logger.info(f"清除提供商失败历史: {provider_name}")
        else:
            self.failure_history.clear()
            logger.info("清除所有失败历史")
    
    def get_health_summary(self) -> Dict[str, Any]:
        """获取健康状态摘要.
        
        Returns:
            健康状态摘要字典
        """
        current_time = time.time()
        recent_failures = len([
            f for f in self.failure_history 
            if current_time - f.timestamp < 3600  # 最近1小时
        ])
        
        healthy_providers = sum(
            1 for health in self.provider_health.values() 
            if health.is_healthy
        )
        
        total_providers = len(self.provider_health)
        
        return {
            "total_providers": total_providers,
            "healthy_providers": healthy_providers,
            "unhealthy_providers": total_providers - healthy_providers,
            "recent_failures_count": recent_failures,
            "total_failure_records": len(self.failure_history),
            "providers": {
                name: {
                    "is_healthy": health.is_healthy,
                    "failure_count": health.failure_count,
                    "consecutive_failures": health.consecutive_failures
                }
                for name, health in self.provider_health.items()
            }
        }


# 全局降级管理器实例
_fallback_manager_instance = None


def get_fallback_manager() -> FallbackManager:
    """获取全局降级管理器实例（单例）."""
    global _fallback_manager_instance
    if _fallback_manager_instance is None:
        _fallback_manager_instance = FallbackManager()
    return _fallback_manager_instance


# 便捷函数
def record_provider_failure(
    provider_name: str,
    error: Exception,
    retry_after: Optional[int] = None
) -> None:
    """记录提供商失败的便捷函数."""
    manager = get_fallback_manager()
    failure_type = manager.get_failure_type(error)
    manager.record_failure(provider_name, failure_type, str(error), retry_after)


def record_provider_success(provider_name: str) -> None:
    """记录提供商成功的便捷函数."""
    manager = get_fallback_manager()
    manager.record_success(provider_name)


def is_provider_available(provider_name: str) -> bool:
    """检查提供商是否可用的便捷函数."""
    manager = get_fallback_manager()
    return manager.is_provider_healthy(provider_name)