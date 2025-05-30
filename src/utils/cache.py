"""缓存管理模块."""

import asyncio
import time
import json
import hashlib
from typing import Any, Optional, Dict, List
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseCache(ABC):
    """缓存基类."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """删除缓存值."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """清空缓存."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查键是否存在."""
        pass


class MemoryCache(BaseCache):
    """内存缓存实现."""
    
    def __init__(self, default_ttl: int = 3600, max_size: int = 1000) -> None:
        """初始化内存缓存.
        
        Args:
            default_ttl: 默认TTL（秒）
            max_size: 最大缓存项数
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task = None
        
        # 启动清理任务（延迟启动）
        self._start_cleanup_task()
    
    def _start_cleanup_task(self) -> None:
        """启动清理任务."""
        try:
            # 检查是否有运行中的事件循环
            loop = asyncio.get_running_loop()
            self._cleanup_task = loop.create_task(self._cleanup_expired())
        except RuntimeError:
            # 没有运行的事件循环，延迟启动
            self._cleanup_task = None
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值."""
        async with self._lock:
            if key not in self.cache:
                return None
            
            item = self.cache[key]
            
            # 检查是否过期
            if item["expires_at"] and time.time() > item["expires_at"]:
                del self.cache[key]
                return None
            
            # 更新访问时间
            item["accessed_at"] = time.time()
            item["access_count"] += 1
            
            return item["value"]
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值."""
        async with self._lock:
            # 确保清理任务已启动
            if self._cleanup_task is None:
                self._start_cleanup_task()
            
            # 检查缓存大小限制
            if len(self.cache) >= self.max_size and key not in self.cache:
                await self._evict_lru()
            
            ttl = ttl or self.default_ttl
            expires_at = time.time() + ttl if ttl > 0 else None
            
            self.cache[key] = {
                "value": value,
                "created_at": time.time(),
                "accessed_at": time.time(),
                "expires_at": expires_at,
                "access_count": 0,
                "ttl": ttl
            }
    
    async def delete(self, key: str) -> None:
        """删除缓存值."""
        async with self._lock:
            self.cache.pop(key, None)
    
    async def clear(self) -> None:
        """清空缓存."""
        async with self._lock:
            self.cache.clear()
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在."""
        result = await self.get(key)
        return result is not None
    
    async def _evict_lru(self) -> None:
        """驱逐最近最少使用的项."""
        if not self.cache:
            return
        
        # 找到最少使用的项
        lru_key = min(
            self.cache.keys(),
            key=lambda k: (self.cache[k]["access_count"], self.cache[k]["accessed_at"])
        )
        
        del self.cache[lru_key]
        logger.debug(f"驱逐LRU缓存项: {lru_key}")
    
    async def _cleanup_expired(self) -> None:
        """清理过期项."""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                
                async with self._lock:
                    current_time = time.time()
                    expired_keys = [
                        key for key, item in self.cache.items()
                        if item["expires_at"] and current_time > item["expires_at"]
                    ]
                    
                    for key in expired_keys:
                        del self.cache[key]
                    
                    if expired_keys:
                        logger.debug(f"清理过期缓存项: {len(expired_keys)} 个")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"缓存清理任务出错: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息."""
        async with self._lock:
            current_time = time.time()
            
            total_items = len(self.cache)
            expired_items = sum(
                1 for item in self.cache.values()
                if item["expires_at"] and current_time > item["expires_at"]
            )
            
            total_access_count = sum(item["access_count"] for item in self.cache.values())
            
            return {
                "type": "memory",
                "total_items": total_items,
                "expired_items": expired_items,
                "active_items": total_items - expired_items,
                "max_size": self.max_size,
                "usage_ratio": total_items / self.max_size,
                "total_access_count": total_access_count,
                "default_ttl": self.default_ttl
            }
    
    def __del__(self):
        """析构函数，取消清理任务."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()


class RequestCache:
    """请求缓存管理器."""
    
    def __init__(self, cache: Optional[BaseCache] = None) -> None:
        """初始化请求缓存.
        
        Args:
            cache: 缓存实现，默认使用内存缓存
        """
        self.cache = cache or MemoryCache(default_ttl=1800, max_size=1000)  # 30分钟TTL
        self.hit_count = 0
        self.miss_count = 0
        self.set_count = 0
        
        logger.info("请求缓存初始化完成")
    
    def _build_key(self, prefix: str, *args, **kwargs) -> str:
        """构建缓存键."""
        # 创建键内容
        key_data = {
            "prefix": prefix,
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        
        # 生成哈希
        key_str = json.dumps(key_data, ensure_ascii=False, sort_keys=True)
        hash_obj = hashlib.sha256(key_str.encode('utf-8'))
        return f"{prefix}:{hash_obj.hexdigest()[:16]}"
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值."""
        try:
            result = await self.cache.get(key)
            
            if result is not None:
                self.hit_count += 1
                logger.debug(f"缓存命中: {key}")
            else:
                self.miss_count += 1
                logger.debug(f"缓存未命中: {key}")
            
            return result
            
        except Exception as e:
            logger.error(f"缓存获取失败: {e}")
            self.miss_count += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值."""
        try:
            await self.cache.set(key, value, ttl)
            self.set_count += 1
            logger.debug(f"缓存设置: {key}")
            
        except Exception as e:
            logger.error(f"缓存设置失败: {e}")
    
    async def delete(self, key: str) -> None:
        """删除缓存值."""
        try:
            await self.cache.delete(key)
            logger.debug(f"缓存删除: {key}")
            
        except Exception as e:
            logger.error(f"缓存删除失败: {e}")
    
    async def clear(self) -> None:
        """清空缓存."""
        try:
            await self.cache.clear()
            self.hit_count = 0
            self.miss_count = 0
            self.set_count = 0
            logger.info("缓存已清空")
            
        except Exception as e:
            logger.error(f"缓存清空失败: {e}")
    
    async def get_or_set(
        self,
        key: str,
        factory,
        ttl: Optional[int] = None,
        *args,
        **kwargs
    ) -> Any:
        """获取缓存值，如果不存在则通过工厂函数生成并缓存."""
        # 尝试从缓存获取
        result = await self.get(key)
        if result is not None:
            return result
        
        # 缓存未命中，通过工厂函数生成
        try:
            if asyncio.iscoroutinefunction(factory):
                result = await factory(*args, **kwargs)
            else:
                result = factory(*args, **kwargs)
            
            # 缓存结果
            await self.set(key, result, ttl)
            return result
            
        except Exception as e:
            logger.error(f"工厂函数执行失败: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息."""
        total_requests = self.hit_count + self.miss_count
        hit_ratio = self.hit_count / total_requests if total_requests > 0 else 0
        
        cache_stats = {}
        if hasattr(self.cache, 'get_stats'):
            cache_stats = await self.cache.get_stats()
        
        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "set_count": self.set_count,
            "total_requests": total_requests,
            "hit_ratio": hit_ratio,
            "cache_stats": cache_stats
        }


class GenerationCache:
    """生成内容缓存管理器."""
    
    def __init__(self, cache: Optional[BaseCache] = None) -> None:
        """初始化生成缓存.
        
        Args:
            cache: 缓存实现，默认使用内存缓存
        """
        self.cache = cache or MemoryCache(default_ttl=86400, max_size=100)  # 24小时TTL
        
        logger.info("生成缓存初始化完成")
    
    def _build_generation_key(
        self,
        content_type: str,
        user_input: str,
        target_words: int,
        style_preference: Optional[str] = None,
        **kwargs
    ) -> str:
        """构建生成内容缓存键."""
        key_data = {
            "type": content_type,
            "input": user_input,
            "words": target_words,
            "style": style_preference,
            **kwargs
        }
        
        key_str = json.dumps(key_data, ensure_ascii=False, sort_keys=True)
        hash_obj = hashlib.sha256(key_str.encode('utf-8'))
        return f"gen:{content_type}:{hash_obj.hexdigest()[:16]}"
    
    async def get_generation(
        self,
        content_type: str,
        user_input: str,
        target_words: int,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """获取生成内容缓存."""
        key = self._build_generation_key(content_type, user_input, target_words, **kwargs)
        return await self.cache.get(key)
    
    async def cache_generation(
        self,
        content_type: str,
        user_input: str,
        target_words: int,
        result: Dict[str, Any],
        ttl: Optional[int] = None,
        **kwargs
    ) -> None:
        """缓存生成内容."""
        key = self._build_generation_key(content_type, user_input, target_words, **kwargs)
        
        # 添加缓存元数据
        cached_result = {
            "result": result,
            "cached_at": time.time(),
            "content_type": content_type,
            "input_hash": hashlib.sha256(user_input.encode()).hexdigest()[:8]
        }
        
        await self.cache.set(key, cached_result, ttl)
    
    async def invalidate_user_cache(self, user_input: str) -> None:
        """失效用户相关的缓存（简单实现，实际可能需要更复杂的逻辑）."""
        # 这里简化处理，实际应用中可能需要维护键的索引
        logger.info(f"请求失效用户缓存: {user_input[:50]}...")


# 全局缓存实例
_request_cache = None
_generation_cache = None


def get_request_cache() -> RequestCache:
    """获取全局请求缓存实例（单例）."""
    global _request_cache
    if _request_cache is None:
        _request_cache = RequestCache()
    return _request_cache


def get_generation_cache() -> GenerationCache:
    """获取全局生成缓存实例（单例）."""
    global _generation_cache
    if _generation_cache is None:
        _generation_cache = GenerationCache()
    return _generation_cache


# 便捷装饰器
def cache_result(ttl: int = 3600, key_prefix: str = "cache"):
    """缓存结果装饰器."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache = get_request_cache()
            
            # 构建缓存键
            key = cache._build_key(key_prefix, func.__name__, *args, **kwargs)
            
            # 尝试从缓存获取
            result = await cache.get(key)
            if result is not None:
                return result
            
            # 执行函数
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # 缓存结果
            await cache.set(key, result, ttl)
            return result
        
        return wrapper
    return decorator