"""系统监控工具模块."""

import asyncio
import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标数据类."""
    
    timestamp: float
    cpu_percent: float
    memory_used: int
    memory_percent: float
    active_tasks: int
    response_time: Optional[float] = None
    request_count: int = 0
    error_count: int = 0
    cache_hit_ratio: float = 0.0


@dataclass
class RequestMetrics:
    """请求指标数据类."""
    
    start_time: float
    end_time: Optional[float] = None
    request_type: str = "unknown"
    provider: Optional[str] = None
    tokens_used: int = 0
    success: bool = False
    error_message: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        """请求持续时间."""
        if self.end_time is None:
            return None
        return self.end_time - self.start_time


class PerformanceMonitor:
    """性能监控器."""
    
    def __init__(self, max_history: int = 1000, collection_interval: float = 30.0):
        """初始化性能监控器.
        
        Args:
            max_history: 最大历史记录数
            collection_interval: 收集间隔（秒）
        """
        self.max_history = max_history
        self.collection_interval = collection_interval
        self.metrics_history: deque = deque(maxlen=max_history)
        self.request_metrics: deque = deque(maxlen=max_history)
        self.active_requests: Dict[str, RequestMetrics] = {}
        self.active_tasks = 0
        self._monitoring_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._started = False
        
        # 性能阈值
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "response_time": 30.0,  # 30秒
            "error_rate": 0.1  # 10%
        }
        
        # 告警回调
        self.alert_callbacks: List[Callable] = []
        
        logger.info("性能监控器初始化完成")
    
    async def start(self) -> None:
        """启动监控."""
        if self._started:
            return
        
        self._started = True
        self._monitoring_task = asyncio.create_task(self._collect_metrics())
        logger.info("性能监控已启动")
    
    async def stop(self) -> None:
        """停止监控."""
        if not self._started:
            return
        
        self._started = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("性能监控已停止")
    
    async def _collect_metrics(self) -> None:
        """收集性能指标."""
        while self._started:
            try:
                # 收集系统指标
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                
                # 计算缓存命中率
                cache_hit_ratio = await self._calculate_cache_hit_ratio()
                
                # 计算当前请求统计
                request_count, error_count = self._calculate_request_stats()
                
                # 创建指标记录
                metrics = PerformanceMetrics(
                    timestamp=time.time(),
                    cpu_percent=cpu_percent,
                    memory_used=memory.used,
                    memory_percent=memory.percent,
                    active_tasks=self.active_tasks,
                    request_count=request_count,
                    error_count=error_count,
                    cache_hit_ratio=cache_hit_ratio
                )
                
                # 添加到历史记录
                async with self._lock:
                    self.metrics_history.append(metrics)
                
                # 检查阈值和告警
                await self._check_thresholds(metrics)
                
                # 等待下次收集
                await asyncio.sleep(self.collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"性能指标收集失败: {e}")
                await asyncio.sleep(self.collection_interval)
    
    async def _calculate_cache_hit_ratio(self) -> float:
        """计算缓存命中率."""
        try:
            from src.utils.cache import get_request_cache
            cache = get_request_cache()
            stats = await cache.get_stats()
            return stats.get("hit_ratio", 0.0)
        except Exception:
            return 0.0
    
    def _calculate_request_stats(self) -> tuple[int, int]:
        """计算请求统计."""
        # 计算最近一分钟的请求统计
        current_time = time.time()
        recent_requests = [
            req for req in self.request_metrics
            if current_time - req.start_time <= 60
        ]
        
        request_count = len(recent_requests)
        error_count = sum(1 for req in recent_requests if not req.success)
        
        return request_count, error_count
    
    async def _check_thresholds(self, metrics: PerformanceMetrics) -> None:
        """检查性能阈值."""
        alerts = []
        
        # CPU使用率检查
        if metrics.cpu_percent > self.thresholds["cpu_percent"]:
            alerts.append(f"CPU使用率过高: {metrics.cpu_percent:.1f}%")
        
        # 内存使用率检查
        if metrics.memory_percent > self.thresholds["memory_percent"]:
            alerts.append(f"内存使用率过高: {metrics.memory_percent:.1f}%")
        
        # 错误率检查
        if metrics.request_count > 0:
            error_rate = metrics.error_count / metrics.request_count
            if error_rate > self.thresholds["error_rate"]:
                alerts.append(f"错误率过高: {error_rate:.1%}")
        
        # 触发告警
        for alert in alerts:
            await self._trigger_alert(alert, metrics)
    
    async def _trigger_alert(self, message: str, metrics: PerformanceMetrics) -> None:
        """触发告警."""
        logger.warning(f"性能告警: {message}")
        
        # 调用注册的告警回调
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message, metrics)
                else:
                    callback(message, metrics)
            except Exception as e:
                logger.error(f"告警回调执行失败: {e}")
    
    @asynccontextmanager
    async def track_request(
        self,
        request_type: str,
        provider: Optional[str] = None
    ):
        """请求追踪上下文管理器."""
        request_id = f"{request_type}_{int(time.time() * 1000)}"
        request_metrics = RequestMetrics(
            start_time=time.time(),
            request_type=request_type,
            provider=provider
        )
        
        # 添加到活跃请求
        async with self._lock:
            self.active_requests[request_id] = request_metrics
            self.active_tasks += 1
        
        try:
            yield request_metrics
            request_metrics.success = True
        except Exception as e:
            request_metrics.success = False
            request_metrics.error_message = str(e)
            raise
        finally:
            # 完成请求
            request_metrics.end_time = time.time()
            
            async with self._lock:
                self.active_requests.pop(request_id, None)
                self.active_tasks = max(0, self.active_tasks - 1)
                self.request_metrics.append(request_metrics)
    
    def add_alert_callback(self, callback: Callable) -> None:
        """添加告警回调."""
        self.alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable) -> None:
        """移除告警回调."""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    async def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """获取当前性能指标."""
        async with self._lock:
            if self.metrics_history:
                return self.metrics_history[-1]
            return None
    
    async def get_metrics_history(self, limit: int = 100) -> List[PerformanceMetrics]:
        """获取历史性能指标."""
        async with self._lock:
            return list(self.metrics_history)[-limit:]
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要."""
        async with self._lock:
            if not self.metrics_history:
                return {"status": "no_data"}
            
            recent_metrics = list(self.metrics_history)[-10:]  # 最近10次指标
            
            # 计算平均值
            avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
            avg_cache_hit = sum(m.cache_hit_ratio for m in recent_metrics) / len(recent_metrics)
            
            # 计算请求统计
            recent_requests = [
                req for req in self.request_metrics
                if time.time() - req.start_time <= 300  # 最近5分钟
            ]
            
            successful_requests = [req for req in recent_requests if req.success]
            avg_response_time = 0.0
            if successful_requests:
                response_times = [req.duration for req in successful_requests if req.duration]
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
            
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "cpu_percent": avg_cpu,
                "memory_percent": avg_memory,
                "cache_hit_ratio": avg_cache_hit,
                "active_tasks": self.active_tasks,
                "total_requests": len(recent_requests),
                "successful_requests": len(successful_requests),
                "error_rate": (len(recent_requests) - len(successful_requests)) / max(1, len(recent_requests)),
                "avg_response_time": avg_response_time,
                "thresholds": self.thresholds
            }


class ConcurrencyManager:
    """并发控制管理器."""
    
    def __init__(
        self,
        max_concurrent_requests: int = 10,
        max_concurrent_per_provider: int = 3,
        max_queue_size: int = 100
    ):
        """初始化并发管理器.
        
        Args:
            max_concurrent_requests: 最大并发请求数
            max_concurrent_per_provider: 每个提供商最大并发数
            max_queue_size: 最大队列大小
        """
        self.max_concurrent_requests = max_concurrent_requests
        self.max_concurrent_per_provider = max_concurrent_per_provider
        self.max_queue_size = max_queue_size
        
        # 全局信号量
        self.global_semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # 每个提供商的信号量
        self.provider_semaphores: Dict[str, asyncio.Semaphore] = {}
        
        # 队列管理
        self.request_queue = asyncio.Queue(maxsize=max_queue_size)
        self.active_requests: Dict[str, float] = {}  # request_id -> start_time
        
        # 统计信息
        self.total_requests = 0
        self.completed_requests = 0
        self.failed_requests = 0
        self.queue_full_count = 0
        
        logger.info("并发管理器初始化完成")
    
    def get_provider_semaphore(self, provider: str) -> asyncio.Semaphore:
        """获取提供商信号量."""
        if provider not in self.provider_semaphores:
            self.provider_semaphores[provider] = asyncio.Semaphore(
                self.max_concurrent_per_provider
            )
        return self.provider_semaphores[provider]
    
    @asynccontextmanager
    async def acquire_request_slot(self, provider: str, request_id: str):
        """获取请求槽位."""
        # 检查队列是否已满
        if self.request_queue.qsize() >= self.max_queue_size:
            self.queue_full_count += 1
            raise Exception("请求队列已满，请稍后重试")
        
        # 全局并发控制
        async with self.global_semaphore:
            # 提供商并发控制
            provider_sem = self.get_provider_semaphore(provider)
            async with provider_sem:
                try:
                    # 记录请求开始
                    self.active_requests[request_id] = time.time()
                    self.total_requests += 1
                    
                    yield
                    
                    # 请求成功
                    self.completed_requests += 1
                    
                except Exception as e:
                    # 请求失败
                    self.failed_requests += 1
                    raise
                finally:
                    # 清理活跃请求
                    self.active_requests.pop(request_id, None)
    
    async def get_concurrency_stats(self) -> Dict[str, Any]:
        """获取并发统计信息."""
        current_time = time.time()
        
        # 计算活跃请求的平均等待时间
        avg_wait_time = 0.0
        if self.active_requests:
            wait_times = [current_time - start_time for start_time in self.active_requests.values()]
            avg_wait_time = sum(wait_times) / len(wait_times)
        
        return {
            "max_concurrent_requests": self.max_concurrent_requests,
            "max_concurrent_per_provider": self.max_concurrent_per_provider,
            "active_requests": len(self.active_requests),
            "queue_size": self.request_queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "total_requests": self.total_requests,
            "completed_requests": self.completed_requests,
            "failed_requests": self.failed_requests,
            "queue_full_count": self.queue_full_count,
            "success_rate": self.completed_requests / max(1, self.total_requests),
            "avg_wait_time": avg_wait_time,
            "provider_usage": {
                provider: sem._value for provider, sem in self.provider_semaphores.items()
            }
        }
    
    def adjust_limits(
        self,
        max_concurrent_requests: Optional[int] = None,
        max_concurrent_per_provider: Optional[int] = None
    ) -> None:
        """动态调整并发限制."""
        if max_concurrent_requests is not None:
            self.max_concurrent_requests = max_concurrent_requests
            # 重新创建全局信号量
            self.global_semaphore = asyncio.Semaphore(max_concurrent_requests)
            logger.info(f"全局并发限制调整为: {max_concurrent_requests}")
        
        if max_concurrent_per_provider is not None:
            self.max_concurrent_per_provider = max_concurrent_per_provider
            # 重新创建提供商信号量
            self.provider_semaphores.clear()
            logger.info(f"提供商并发限制调整为: {max_concurrent_per_provider}")


# 全局实例
_performance_monitor = None
_concurrency_manager = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器实例."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def get_concurrency_manager() -> ConcurrencyManager:
    """获取全局并发管理器实例."""
    global _concurrency_manager
    if _concurrency_manager is None:
        _concurrency_manager = ConcurrencyManager()
    return _concurrency_manager