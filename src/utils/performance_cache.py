"""性能优化缓存策略."""

import asyncio
import time
import json
import hashlib
from typing import Any, Optional, Dict, List, Callable, Union
from dataclasses import dataclass
from enum import Enum
import logging

from src.utils.cache import BaseCache, MemoryCache
from src.utils.monitoring import get_performance_monitor

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """缓存策略枚举."""
    AGGRESSIVE = "aggressive"    # 激进缓存，长时间保存
    BALANCED = "balanced"        # 平衡策略，中等时间
    CONSERVATIVE = "conservative" # 保守策略，短时间缓存
    ADAPTIVE = "adaptive"        # 自适应策略，根据性能调整


@dataclass
class CacheConfig:
    """缓存配置."""
    
    strategy: CacheStrategy = CacheStrategy.BALANCED
    base_ttl: int = 3600  # 基础TTL（秒）
    max_ttl: int = 86400  # 最大TTL（秒）
    min_ttl: int = 300    # 最小TTL（秒）
    cache_hit_threshold: float = 0.8  # 命中率阈值
    response_time_threshold: float = 2.0  # 响应时间阈值（秒）
    memory_pressure_threshold: float = 0.8  # 内存压力阈值


class AdaptiveCache(BaseCache):
    """自适应缓存实现."""
    
    def __init__(
        self,
        config: CacheConfig,
        base_cache: Optional[BaseCache] = None
    ):
        """初始化自适应缓存.
        
        Args:
            config: 缓存配置
            base_cache: 底层缓存实现
        """
        self.config = config
        self.base_cache = base_cache or MemoryCache(
            default_ttl=config.base_ttl,
            max_size=2000
        )
        self.performance_monitor = get_performance_monitor()
        
        # 性能统计
        self.hit_count = 0
        self.miss_count = 0
        self.eviction_count = 0
        
        # 自适应参数
        self.current_ttl_multiplier = 1.0
        self.last_adjustment_time = time.time()
        self.adjustment_interval = 300  # 5分钟调整一次
        
        logger.info(f"自适应缓存初始化完成，策略: {config.strategy.value}")
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值."""
        result = await self.base_cache.get(key)
        
        if result is not None:
            self.hit_count += 1
        else:
            self.miss_count += 1
        
        # 触发自适应调整
        await self._maybe_adjust_strategy()
        
        return result
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值."""
        # 计算自适应TTL
        adapted_ttl = await self._calculate_adaptive_ttl(ttl)
        await self.base_cache.set(key, value, adapted_ttl)
    
    async def delete(self, key: str) -> None:
        """删除缓存值."""
        await self.base_cache.delete(key)
    
    async def clear(self) -> None:
        """清空缓存."""
        await self.base_cache.clear()
        self.hit_count = 0
        self.miss_count = 0
        self.eviction_count = 0
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在."""
        return await self.base_cache.exists(key)
    
    async def _calculate_adaptive_ttl(self, requested_ttl: Optional[int]) -> int:
        """计算自适应TTL."""
        base_ttl = requested_ttl or self.config.base_ttl
        
        if self.config.strategy == CacheStrategy.AGGRESSIVE:
            multiplier = 2.0
        elif self.config.strategy == CacheStrategy.CONSERVATIVE:
            multiplier = 0.5
        elif self.config.strategy == CacheStrategy.ADAPTIVE:
            multiplier = self.current_ttl_multiplier
        else:  # BALANCED
            multiplier = 1.0
        
        adapted_ttl = int(base_ttl * multiplier)
        
        # 应用边界限制
        adapted_ttl = max(self.config.min_ttl, adapted_ttl)
        adapted_ttl = min(self.config.max_ttl, adapted_ttl)
        
        return adapted_ttl
    
    async def _maybe_adjust_strategy(self) -> None:
        """可能调整策略."""
        current_time = time.time()
        
        # 检查是否需要调整
        if current_time - self.last_adjustment_time < self.adjustment_interval:
            return
        
        if self.config.strategy != CacheStrategy.ADAPTIVE:
            return
        
        # 获取性能指标
        performance_summary = await self.performance_monitor.get_performance_summary()
        if performance_summary.get("status") != "healthy":
            return
        
        # 计算当前命中率
        total_requests = self.hit_count + self.miss_count
        if total_requests == 0:
            return
        
        hit_ratio = self.hit_count / total_requests
        avg_response_time = performance_summary.get("avg_response_time", 0)
        memory_percent = performance_summary.get("memory_percent", 0) / 100
        
        # 调整TTL倍数
        old_multiplier = self.current_ttl_multiplier
        
        # 基于命中率调整
        if hit_ratio < self.config.cache_hit_threshold:
            # 命中率低，增加缓存时间
            self.current_ttl_multiplier *= 1.2
        elif hit_ratio > 0.95:
            # 命中率很高，可以适当减少缓存时间以节省内存
            self.current_ttl_multiplier *= 0.9
        
        # 基于响应时间调整
        if avg_response_time > self.config.response_time_threshold:
            # 响应时间长，增加缓存时间
            self.current_ttl_multiplier *= 1.1
        
        # 基于内存压力调整
        if memory_percent > self.config.memory_pressure_threshold:
            # 内存压力大，减少缓存时间
            self.current_ttl_multiplier *= 0.8
        
        # 限制调整范围
        self.current_ttl_multiplier = max(0.1, min(5.0, self.current_ttl_multiplier))
        
        # 记录调整
        if abs(self.current_ttl_multiplier - old_multiplier) > 0.1:
            logger.info(
                f"自适应缓存TTL倍数调整: {old_multiplier:.2f} -> {self.current_ttl_multiplier:.2f}",
                extra={
                    "hit_ratio": hit_ratio,
                    "avg_response_time": avg_response_time,
                    "memory_percent": memory_percent
                }
            )
        
        self.last_adjustment_time = current_time
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息."""
        total_requests = self.hit_count + self.miss_count
        hit_ratio = self.hit_count / total_requests if total_requests > 0 else 0
        
        base_stats = {}
        if hasattr(self.base_cache, 'get_stats'):
            base_stats = await self.base_cache.get_stats()
        
        return {
            "cache_type": "adaptive",
            "strategy": self.config.strategy.value,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "total_requests": total_requests,
            "hit_ratio": hit_ratio,
            "eviction_count": self.eviction_count,
            "current_ttl_multiplier": self.current_ttl_multiplier,
            "config": {
                "base_ttl": self.config.base_ttl,
                "max_ttl": self.config.max_ttl,
                "min_ttl": self.config.min_ttl
            },
            "base_cache_stats": base_stats
        }


class LLMResponseCache:
    """LLM响应专用缓存."""
    
    def __init__(self, cache: Optional[BaseCache] = None):
        """初始化LLM响应缓存.
        
        Args:
            cache: 底层缓存实现
        """
        # 使用自适应缓存
        config = CacheConfig(
            strategy=CacheStrategy.ADAPTIVE,
            base_ttl=7200,  # 2小时
            max_ttl=86400,  # 24小时
            min_ttl=600,    # 10分钟
        )
        self.cache = cache or AdaptiveCache(config)
        
        # 响应类型特定的TTL
        self.type_specific_ttl = {
            "concept_expansion": 86400,      # 概念扩展：24小时
            "strategy_selection": 43200,     # 策略选择：12小时
            "outline_generation": 21600,     # 大纲生成：6小时
            "character_creation": 28800,     # 角色创建：8小时
            "chapter_generation": 14400,     # 章节生成：4小时
            "consistency_check": 7200,       # 一致性检查：2小时
            "quality_assessment": 3600,      # 质量评估：1小时
        }
        
        logger.info("LLM响应缓存初始化完成")
    
    def _build_llm_cache_key(
        self,
        task_type: str,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """构建LLM缓存键."""
        # 提取关键参数
        key_data = {
            "task_type": task_type,
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # 添加其他重要参数
        for key, value in kwargs.items():
            if key in ["style_preference", "target_words", "genre"]:
                key_data[key] = value
        
        # 生成缓存键
        key_str = json.dumps(key_data, sort_keys=True)
        hash_obj = hashlib.sha256(key_str.encode())
        return f"llm:{task_type}:{hash_obj.hexdigest()[:16]}"
    
    async def get_llm_response(
        self,
        task_type: str,
        prompt: str,
        **kwargs
    ) -> Optional[str]:
        """获取LLM响应缓存."""
        cache_key = self._build_llm_cache_key(task_type, prompt, **kwargs)
        return await self.cache.get(cache_key)
    
    async def cache_llm_response(
        self,
        task_type: str,
        prompt: str,
        response: str,
        custom_ttl: Optional[int] = None,
        **kwargs
    ) -> None:
        """缓存LLM响应."""
        cache_key = self._build_llm_cache_key(task_type, prompt, **kwargs)
        
        # 使用任务类型特定的TTL
        ttl = custom_ttl or self.type_specific_ttl.get(task_type, 3600)
        
        await self.cache.set(cache_key, response, ttl)
        
        logger.debug(f"缓存LLM响应: {task_type}, TTL: {ttl}秒")
    
    async def invalidate_task_cache(self, task_type: str) -> None:
        """失效特定任务类型的缓存."""
        # 这是一个简化实现，实际可能需要更复杂的键管理
        logger.info(f"请求失效任务缓存: {task_type}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息."""
        if hasattr(self.cache, 'get_cache_stats'):
            return await self.cache.get_cache_stats()
        return {}


class SmartCacheManager:
    """智能缓存管理器."""
    
    def __init__(self):
        """初始化智能缓存管理器."""
        self.llm_cache = LLMResponseCache()
        self.performance_monitor = get_performance_monitor()
        
        # 缓存预热配置
        self.warmup_enabled = True
        self.warmup_patterns = [
            "概念扩展",
            "故事大纲",
            "角色设定",
            "章节生成"
        ]
        
        logger.info("智能缓存管理器初始化完成")
    
    async def get_or_generate(
        self,
        task_type: str,
        prompt: str,
        generator_func: Callable,
        use_cache: bool = True,
        **kwargs
    ) -> str:
        """获取缓存或生成新内容."""
        # 尝试从缓存获取
        if use_cache:
            cached_result = await self.llm_cache.get_llm_response(task_type, prompt, **kwargs)
            if cached_result:
                logger.debug(f"缓存命中: {task_type}")
                return cached_result
        
        # 缓存未命中，生成新内容
        start_time = time.time()
        
        try:
            if asyncio.iscoroutinefunction(generator_func):
                result = await generator_func(prompt, **kwargs)
            else:
                result = generator_func(prompt, **kwargs)
            
            # 缓存结果
            if use_cache:
                await self.llm_cache.cache_llm_response(task_type, prompt, result, **kwargs)
            
            generation_time = time.time() - start_time
            logger.info(f"内容生成完成: {task_type}, 耗时: {generation_time:.2f}秒")
            
            return result
            
        except Exception as e:
            logger.error(f"内容生成失败: {task_type}, 错误: {e}")
            raise
    
    async def warmup_cache(self, patterns: Optional[List[str]] = None) -> None:
        """预热缓存."""
        if not self.warmup_enabled:
            return
        
        patterns = patterns or self.warmup_patterns
        logger.info(f"开始缓存预热，模式: {patterns}")
        
        # 这里可以实现具体的预热逻辑
        # 例如：预生成常见的提示词响应
        
        for pattern in patterns:
            try:
                # 模拟预热（实际实现中可以预生成常见内容）
                logger.debug(f"预热模式: {pattern}")
                await asyncio.sleep(0.1)  # 避免阻塞
            except Exception as e:
                logger.error(f"预热失败: {pattern}, 错误: {e}")
        
        logger.info("缓存预热完成")
    
    async def get_cache_performance(self) -> Dict[str, Any]:
        """获取缓存性能统计."""
        llm_stats = await self.llm_cache.get_cache_stats()
        
        return {
            "llm_cache": llm_stats,
            "warmup_enabled": self.warmup_enabled,
            "warmup_patterns": self.warmup_patterns,
            "timestamp": time.time()
        }
    
    async def optimize_cache(self) -> None:
        """优化缓存性能."""
        logger.info("开始缓存优化")
        
        # 获取性能指标
        performance_summary = await self.performance_monitor.get_performance_summary()
        
        # 根据内存使用情况调整缓存策略
        memory_percent = performance_summary.get("memory_percent", 0)
        
        if memory_percent > 85:
            logger.warning("内存使用率过高，清理部分缓存")
            # 这里可以实现更智能的清理策略
            # 例如：清理访问频率低的缓存项
        
        logger.info("缓存优化完成")


# 全局实例
_smart_cache_manager = None


def get_smart_cache_manager() -> SmartCacheManager:
    """获取全局智能缓存管理器实例."""
    global _smart_cache_manager
    if _smart_cache_manager is None:
        _smart_cache_manager = SmartCacheManager()
    return _smart_cache_manager