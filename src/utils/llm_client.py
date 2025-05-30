"""统一LLM客户端."""

import asyncio
import time
import uuid
from typing import Dict, Any, Optional, List, AsyncGenerator
import logging
from contextlib import asynccontextmanager

from src.utils.config import get_settings
from src.utils.providers.base_provider import BaseLLMProvider, LLMProviderError
from src.utils.providers.openai_client import OpenAIClient
from src.utils.providers.ollama_client import OllamaClient
from src.utils.providers.custom_client import CustomClient
from src.utils.providers.router import LLMRouter, TaskType, RoutingStrategy
from src.utils.providers.fallback_manager import FallbackManager, FailureType
from src.utils.cache import RequestCache
from src.utils.monitoring import get_performance_monitor, get_concurrency_manager

logger = logging.getLogger(__name__)

# 延迟导入避免循环依赖
def get_generation_logger():
    try:
        from src.utils.generation_logger import get_generation_logger
        return get_generation_logger()
    except ImportError:
        return None


class UniversalLLMClient:
    """统一LLM客户端."""
    
    def __init__(self) -> None:
        """初始化统一LLM客户端."""
        self.settings = get_settings()
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.router = LLMRouter()
        self.fallback_manager = FallbackManager()
        self.cache = RequestCache()
        self.performance_monitor = get_performance_monitor()
        self.concurrency_manager = get_concurrency_manager()
        
        # 性能统计
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        
        # 初始化提供商
        self._initialize_providers()
        
        logger.info("统一LLM客户端初始化完成")
    
    def _initialize_providers(self) -> None:
        """初始化所有配置的提供商."""
        try:
            # 初始化OpenAI
            openai_config = self.settings.get_llm_config("openai")
            if openai_config.get("api_key"):
                self.providers["openai"] = OpenAIClient(openai_config)
                logger.info("OpenAI客户端初始化成功")
            else:
                logger.warning("OpenAI API密钥未配置，跳过初始化")
        except Exception as e:
            logger.error(f"OpenAI客户端初始化失败: {e}")
        
        try:
            # 初始化Ollama
            ollama_config = self.settings.get_llm_config("ollama")
            self.providers["ollama"] = OllamaClient(ollama_config)
            
            # 检查Ollama可用性
            if self.providers["ollama"].is_available():
                logger.info("Ollama客户端初始化成功")
            else:
                logger.warning("Ollama服务不可用")
                self.router.set_provider_availability("ollama", False)
        except Exception as e:
            logger.error(f"Ollama客户端初始化失败: {e}")
        
        try:
            # 初始化自定义模型
            custom_config = self.settings.get_llm_config("custom")
            if custom_config.get("base_url"):
                self.providers["custom"] = CustomClient(custom_config)
                logger.info("自定义模型客户端初始化成功")
            else:
                logger.info("自定义模型未配置，跳过初始化")
        except Exception as e:
            logger.error(f"自定义模型客户端初始化失败: {e}")
        
        # 更新路由器的提供商可用性
        for provider_name, provider in self.providers.items():
            is_available = provider.is_available()
            self.router.set_provider_availability(provider_name, is_available)
            logger.info(f"提供商 {provider_name} 可用性: {is_available}")
    
    async def generate(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        preferred_provider: Optional[str] = None,
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_cache: bool = True,
        log_generation: bool = True,
        step_type: Optional[str] = None,
        step_name: Optional[str] = None,
        **kwargs
    ) -> str:
        """生成文本.
        
        Args:
            prompt: 输入提示词
            task_type: 任务类型
            preferred_provider: 首选提供商
            strategy: 路由策略
            max_tokens: 最大令牌数
            temperature: 温度参数
            use_cache: 是否使用缓存
            log_generation: 是否记录生成日志
            step_type: 生成步骤类型（用于日志）
            step_name: 生成步骤名称（用于日志）
            **kwargs: 其他参数
            
        Returns:
            生成的文本内容
            
        Raises:
            LLMProviderError: 当所有提供商都失败时抛出
        """
        # 生成请求ID
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # 获取生成日志器
        generation_logger = None
        if log_generation:
            generation_logger = get_generation_logger()
        
        # 如果没有指定首选提供商，使用配置中的主要提供商
        if preferred_provider is None:
            preferred_provider = self.settings.primary_llm_provider
            logger.info(f"使用配置中的主要LLM提供商: {preferred_provider}")
        
        # 构建缓存键
        cache_key = None
        if use_cache:
            cache_key = self._build_cache_key(prompt, task_type, max_tokens, temperature, **kwargs)
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.debug("从缓存返回结果")
                return cached_result
        
        # 选择提供商
        try:
            provider_name = self.router.select_provider(
                prompt=prompt,
                task_type=task_type,
                strategy=strategy,
                required_tokens=max_tokens,
                preferred_provider=preferred_provider
            )
            logger.info(f"选择的LLM提供商: {provider_name}")
        except ValueError as e:
            raise LLMProviderError(f"无法选择可用提供商: {e}")
        
        # 使用并发控制和性能监控
        async with self.concurrency_manager.acquire_request_slot(provider_name, request_id):
            async with self.performance_monitor.track_request(task_type.value, provider_name) as metrics:
                # 生成文本，带降级机制
                result = await self._generate_with_fallback(
                    prompt, provider_name, task_type, max_tokens, temperature, **kwargs
                )
                
                # 记录token使用情况（如果可用）
                if hasattr(metrics, 'tokens_used'):
                    # 估算token数量（简单实现）
                    metrics.tokens_used = len(prompt.split()) + len(result.split())
        
        # 缓存结果
        if use_cache and cache_key:
            await self.cache.set(cache_key, result)
        
        # 记录生成日志
        if log_generation and generation_logger and step_type and step_name:
            try:
                end_time = time.time()
                duration_ms = int((end_time - start_time) * 1000)
                
                # 估算token使用情况
                token_usage = {
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(result.split()),
                    "total_tokens": len(prompt.split()) + len(result.split())
                }
                
                # 构建模型信息
                model_info = {
                    "provider": provider_name if 'provider_name' in locals() else preferred_provider,
                    "task_type": task_type.value,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                
                generation_logger.log_generation_step(
                    step_type=step_type,
                    step_name=step_name,
                    prompt=prompt,
                    response=result,
                    model_info=model_info,
                    duration_ms=duration_ms,
                    token_usage=token_usage
                )
            except Exception as e:
                logger.warning(f"记录生成日志失败: {e}")
        
        # 更新统计
        self.request_count += 1
        
        return result
    
    async def generate_async(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        **kwargs
    ) -> str:
        """异步生成文本的别名方法.
        
        Args:
            prompt: 输入提示词
            task_type: 任务类型
            **kwargs: 其他参数
            
        Returns:
            生成的文本内容
        """
        return await self.generate(prompt, task_type=task_type, **kwargs)
    
    async def _generate_with_fallback(
        self,
        prompt: str,
        primary_provider: str,
        task_type: TaskType,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """带降级机制的生成."""
        providers_to_try = [primary_provider]
        
        # 获取降级提供商
        fallback_provider = self.router.get_fallback_provider(primary_provider, task_type, max_tokens)
        if fallback_provider:
            providers_to_try.append(fallback_provider)
        
        last_exception = None
        
        for provider_name in providers_to_try:
            if provider_name not in self.providers:
                logger.warning(f"提供商 {provider_name} 不存在")
                continue
            
            if not self.fallback_manager.is_provider_healthy(provider_name):
                logger.warning(f"提供商 {provider_name} 不健康，跳过")
                continue
            
            try:
                start_time = time.time()
                
                result = await self.providers[provider_name].generate(
                    prompt, max_tokens, temperature, **kwargs
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                
                # 记录成功
                self.router.record_request_result(provider_name, True, response_time)
                self.fallback_manager.record_success(provider_name)
                
                logger.info(
                    f"生成成功",
                    extra={
                        "provider": provider_name,
                        "task_type": task_type.value,
                        "response_time": response_time,
                        "prompt_length": len(prompt),
                        "response_length": len(result)
                    }
                )
                
                return result
                
            except Exception as e:
                last_exception = e
                response_time = time.time() - start_time if 'start_time' in locals() else 0
                
                # 记录失败
                self.router.record_request_result(provider_name, False, response_time)
                
                # 判断是否应该降级
                if self.fallback_manager.should_fallback(e):
                    failure_type = self.fallback_manager.get_failure_type(e)
                    self.fallback_manager.record_failure(provider_name, failure_type, str(e))
                    
                    logger.warning(
                        f"提供商 {provider_name} 失败，尝试降级",
                        extra={
                            "provider": provider_name,
                            "error": str(e),
                            "failure_type": failure_type.value
                        }
                    )
                    
                    # 获取重试延迟
                    retry_delay = self.fallback_manager.get_retry_delay(provider_name, failure_type)
                    if retry_delay > 0 and len(providers_to_try) > 1:
                        await asyncio.sleep(min(retry_delay, 5))  # 最多等待5秒
                else:
                    # 不应该降级的错误（如认证错误），直接抛出
                    raise e
        
        # 所有提供商都失败了
        raise LLMProviderError(
            f"所有提供商都失败了，最后错误: {last_exception}"
        ) from last_exception
    
    async def generate_streaming(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        preferred_provider: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式生成文本.
        
        Args:
            prompt: 输入提示词
            task_type: 任务类型
            preferred_provider: 首选提供商
            max_tokens: 最大令牌数
            temperature: 温度参数
            **kwargs: 其他参数
            
        Yields:
            生成的文本片段
        """
        # 选择提供商
        provider_name = self.router.select_provider(
            prompt=prompt,
            task_type=task_type,
            preferred_provider=preferred_provider
        )
        
        if provider_name not in self.providers:
            raise LLMProviderError(f"提供商 {provider_name} 不存在")
        
        provider = self.providers[provider_name]
        
        # 检查是否支持流式传输
        if not hasattr(provider, 'generate_streaming'):
            raise LLMProviderError(f"提供商 {provider_name} 不支持流式传输")
        
        try:
            start_time = time.time()
            total_content = ""
            
            async for chunk in provider.generate_streaming(prompt, max_tokens, temperature, **kwargs):
                total_content += chunk
                yield chunk
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # 记录成功
            self.router.record_request_result(provider_name, True, response_time)
            self.fallback_manager.record_success(provider_name)
            
        except Exception as e:
            # 记录失败
            self.router.record_request_result(provider_name, False, 0)
            failure_type = self.fallback_manager.get_failure_type(e)
            self.fallback_manager.record_failure(provider_name, failure_type, str(e))
            
            raise LLMProviderError(f"流式生成失败: {e}") from e
    
    async def generate_batch(
        self,
        prompts: List[str],
        task_type: TaskType = TaskType.GENERAL,
        max_concurrent: Optional[int] = None,
        **kwargs
    ) -> List[str]:
        """批量生成文本.
        
        Args:
            prompts: 提示词列表
            task_type: 任务类型
            max_concurrent: 最大并发数（None使用系统默认）
            **kwargs: 其他参数
            
        Returns:
            生成结果列表
        """
        # 使用系统并发限制或指定的限制
        if max_concurrent is None:
            max_concurrent = min(
                self.concurrency_manager.max_concurrent_requests // 2,  # 留一半给其他请求
                len(prompts)
            )
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_one(prompt: str, index: int) -> tuple[int, str]:
            async with semaphore:
                try:
                    result = await self.generate(prompt, task_type=task_type, **kwargs)
                    return index, result
                except Exception as e:
                    logger.error(f"批量生成失败 (索引 {index}): {e}")
                    return index, ""  # 失败时返回空字符串
        
        # 创建任务
        tasks = [generate_one(prompt, i) for i, prompt in enumerate(prompts)]
        
        # 批量执行
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果，保持原始顺序
        results = [""] * len(prompts)
        for result in completed_results:
            if isinstance(result, Exception):
                logger.error(f"批量任务异常: {result}")
            else:
                index, content = result
                results[index] = content
        
        return results
    
    def _build_cache_key(
        self,
        prompt: str,
        task_type: TaskType,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """构建缓存键."""
        import hashlib
        
        # 构建缓存键内容
        cache_content = {
            "prompt": prompt,
            "task_type": task_type.value,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **{k: v for k, v in kwargs.items() if k not in ['preferred_provider', 'strategy']}
        }
        
        # 生成哈希
        content_str = str(sorted(cache_content.items()))
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]
    
    async def test_providers(self) -> Dict[str, Dict[str, Any]]:
        """测试所有提供商.
        
        Returns:
            测试结果字典
        """
        results = {}
        
        for provider_name, provider in self.providers.items():
            try:
                health_result = await provider.health_check()
                results[provider_name] = health_result
            except Exception as e:
                results[provider_name] = {
                    "healthy": False,
                    "provider": provider_name,
                    "error": str(e),
                    "timestamp": time.time()
                }
        
        return results
    
    async def get_provider_stats(self) -> Dict[str, Any]:
        """获取提供商统计信息.
        
        Returns:
            统计信息字典
        """
        router_stats = self.router.get_all_stats()
        fallback_stats = self.fallback_manager.get_health_summary()
        performance_stats = await self.performance_monitor.get_performance_summary()
        concurrency_stats = await self.concurrency_manager.get_concurrency_stats()
        
        # 计算平均响应时间
        avg_response_time = 0.0
        if self.request_count > 0:
            avg_response_time = self.total_response_time / self.request_count
        
        return {
            "router_stats": router_stats,
            "health_summary": fallback_stats,
            "performance_summary": performance_stats,
            "concurrency_stats": concurrency_stats,
            "available_providers": list(self.providers.keys()),
            "cache_stats": await self.cache.get_stats() if hasattr(self.cache, 'get_stats') else {},
            "client_stats": {
                "total_requests": self.request_count,
                "error_count": self.error_count,
                "success_rate": (self.request_count - self.error_count) / max(1, self.request_count),
                "avg_response_time": avg_response_time
            }
        }
    
    @asynccontextmanager
    async def provider_context(self, provider_name: str):
        """提供商上下文管理器."""
        if provider_name not in self.providers:
            raise LLMProviderError(f"提供商 {provider_name} 不存在")
        
        provider = self.providers[provider_name]
        try:
            yield provider
        finally:
            # 清理逻辑（如果需要）
            pass


# 全局客户端实例
_universal_client = None


def get_universal_client() -> UniversalLLMClient:
    """获取全局统一LLM客户端实例（单例）."""
    global _universal_client
    if _universal_client is None:
        _universal_client = UniversalLLMClient()
    return _universal_client


# 便捷函数
async def generate_text(
    prompt: str,
    task_type: TaskType = TaskType.GENERAL,
    **kwargs
) -> str:
    """生成文本的便捷函数."""
    client = get_universal_client()
    return await client.generate(prompt, task_type=task_type, **kwargs)


async def generate_text_streaming(
    prompt: str,
    task_type: TaskType = TaskType.GENERAL,
    **kwargs
) -> AsyncGenerator[str, None]:
    """流式生成文本的便捷函数."""
    client = get_universal_client()
    async for chunk in client.generate_streaming(prompt, task_type=task_type, **kwargs):
        yield chunk