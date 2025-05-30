"""基础LLM提供商抽象接口."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """LLM提供商基础抽象类."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """初始化提供商.
        
        Args:
            config: 提供商配置字典
        """
        self.config = config
        self.provider_name = self._get_provider_name()
        self.is_initialized = False
        self._setup_provider()
    
    @abstractmethod
    def _get_provider_name(self) -> str:
        """获取提供商名称."""
        pass
    
    @abstractmethod
    def _setup_provider(self) -> None:
        """设置提供商特定配置."""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """生成文本.
        
        Args:
            prompt: 输入提示词
            max_tokens: 最大令牌数
            temperature: 温度参数
            **kwargs: 其他参数
            
        Returns:
            生成的文本内容
            
        Raises:
            LLMProviderError: 当生成失败时抛出
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查提供商是否可用.
        
        Returns:
            True如果可用，False否则
        """
        pass
    
    async def generate_with_retry(
        self,
        prompt: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs
    ) -> str:
        """带重试机制的生成.
        
        Args:
            prompt: 输入提示词
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            **kwargs: 其他生成参数
            
        Returns:
            生成的文本内容
            
        Raises:
            LLMProviderError: 重试耗尽后仍失败时抛出
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()
                result = await self.generate(prompt, **kwargs)
                end_time = time.time()
                
                logger.info(
                    f"生成成功",
                    extra={
                        "provider": self.provider_name,
                        "attempt": attempt + 1,
                        "response_time": end_time - start_time,
                        "prompt_length": len(prompt),
                        "response_length": len(result)
                    }
                )
                
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"生成失败，尝试 {attempt + 1}/{max_retries + 1}",
                    extra={
                        "provider": self.provider_name,
                        "error": str(e),
                        "prompt_length": len(prompt)
                    }
                )
                
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # 指数退避
        
        # 所有重试都失败了
        raise LLMProviderError(
            f"提供商 {self.provider_name} 生成失败，已重试 {max_retries} 次: {last_exception}"
        ) from last_exception
    
    async def generate_batch(
        self,
        prompts: List[str],
        max_concurrent: int = 3,
        **kwargs
    ) -> List[str]:
        """批量生成文本.
        
        Args:
            prompts: 提示词列表
            max_concurrent: 最大并发数
            **kwargs: 其他生成参数
            
        Returns:
            生成结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_one(prompt: str) -> str:
            async with semaphore:
                return await self.generate(prompt, **kwargs)
        
        tasks = [generate_one(prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"批量生成失败 (索引 {i}): {result}")
                processed_results.append("")  # 失败时返回空字符串
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取配置值.
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self.config.get(key, default)
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置.
        
        Returns:
            验证结果字典，包含 is_valid 和 errors
        """
        result = {"is_valid": True, "errors": []}
        
        # 子类可以重写此方法添加特定验证
        required_keys = self._get_required_config_keys()
        for key in required_keys:
            if key not in self.config or self.config[key] is None:
                result["is_valid"] = False
                result["errors"].append(f"缺少必需配置: {key}")
        
        return result
    
    def _get_required_config_keys(self) -> List[str]:
        """获取必需的配置键.
        
        子类应重写此方法指定必需的配置项.
        
        Returns:
            必需配置键列表
        """
        return []
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查.
        
        Returns:
            健康状态字典
        """
        try:
            start_time = time.time()
            
            # 简单的测试生成
            test_result = await self.generate(
                "测试",
                max_tokens=10,
                temperature=0.0
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            return {
                "healthy": True,
                "provider": self.provider_name,
                "response_time": response_time,
                "test_successful": len(test_result) > 0,
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "provider": self.provider_name,
                "error": str(e),
                "timestamp": time.time()
            }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(provider='{self.provider_name}')>"


class LLMProviderError(Exception):
    """LLM提供商错误."""
    
    def __init__(self, message: str, provider: str = None, error_code: str = None) -> None:
        super().__init__(message)
        self.provider = provider
        self.error_code = error_code


class RateLimitError(LLMProviderError):
    """速率限制错误."""
    
    def __init__(self, message: str, provider: str = None, retry_after: int = None) -> None:
        super().__init__(message, provider, "rate_limit")
        self.retry_after = retry_after


class AuthenticationError(LLMProviderError):
    """认证错误."""
    
    def __init__(self, message: str, provider: str = None) -> None:
        super().__init__(message, provider, "authentication")


class ConnectionError(LLMProviderError):
    """连接错误."""
    
    def __init__(self, message: str, provider: str = None) -> None:
        super().__init__(message, provider, "connection")


class ModelNotFoundError(LLMProviderError):
    """模型未找到错误."""
    
    def __init__(self, message: str, provider: str = None, model: str = None) -> None:
        super().__init__(message, provider, "model_not_found")
        self.model = model


class InvalidRequestError(LLMProviderError):
    """无效请求错误."""
    
    def __init__(self, message: str, provider: str = None) -> None:
        super().__init__(message, provider, "invalid_request")