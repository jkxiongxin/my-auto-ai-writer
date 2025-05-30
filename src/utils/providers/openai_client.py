"""OpenAI客户端实现."""

import asyncio
from typing import Dict, Any, Optional, List
import logging

try:
    import openai
except ImportError:
    openai = None

from src.utils.providers.base_provider import (
    BaseLLMProvider,
    LLMProviderError,
    RateLimitError,
    AuthenticationError,
    ConnectionError,
    InvalidRequestError,
)

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMProvider):
    """OpenAI客户端实现."""
    
    def _get_provider_name(self) -> str:
        """获取提供商名称."""
        return "openai"
    
    def _setup_provider(self) -> None:
        """设置OpenAI特定配置."""
        if openai is None:
            raise LLMProviderError("OpenAI库未安装，请运行: pip install openai")
        
        self.api_key = self.get_config_value("api_key")
        self.model = self.get_config_value("model", "gpt-4-turbo")
        self.base_url = self.get_config_value("base_url", "https://api.openai.com/v1")
        self.max_tokens = self.get_config_value("max_tokens", 4000)
        self.temperature = self.get_config_value("temperature", 0.7)
        self.timeout = self.get_config_value("timeout", 60)
        
        # 验证必需配置
        validation_result = self.validate_config()
        if not validation_result["is_valid"]:
            raise LLMProviderError(f"OpenAI配置验证失败: {validation_result['errors']}")
        
        # 创建客户端
        self.client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
        
        self.is_initialized = True
        logger.info(f"OpenAI客户端初始化成功，模型: {self.model}")
    
    def _get_required_config_keys(self) -> List[str]:
        """获取必需的配置键."""
        return ["api_key"]
    
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """使用OpenAI生成文本.
        
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
        if not self.is_initialized:
            raise LLMProviderError("OpenAI客户端未初始化")
        
        # 使用传入的参数或默认值
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        model = kwargs.get("model", self.model)
        
        # 构建消息
        messages = [{"role": "user", "content": prompt}]
        
        # 如果有系统提示词
        system_prompt = kwargs.get("system_prompt")
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        try:
            logger.debug(f"开始OpenAI生成，模型: {model}, 最大令牌: {max_tokens}")
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=kwargs.get("top_p", 1.0),
                frequency_penalty=kwargs.get("frequency_penalty", 0.0),
                presence_penalty=kwargs.get("presence_penalty", 0.0),
                stop=kwargs.get("stop"),
            )
            
            if not response.choices:
                raise LLMProviderError("OpenAI返回空响应")
            
            content = response.choices[0].message.content
            if content is None:
                raise LLMProviderError("OpenAI返回空内容")
            
            # 记录使用信息
            if hasattr(response, 'usage') and response.usage:
                logger.info(
                    f"OpenAI生成完成",
                    extra={
                        "model": model,
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                        "content_length": len(content)
                    }
                )
            
            return content.strip()
            
        except openai.RateLimitError as e:
            logger.warning(f"OpenAI速率限制: {e}")
            raise RateLimitError(f"OpenAI速率限制: {e}", self.provider_name)
        
        except openai.AuthenticationError as e:
            logger.error(f"OpenAI认证失败: {e}")
            raise AuthenticationError(f"OpenAI认证失败: {e}", self.provider_name)
        
        except openai.APIConnectionError as e:
            logger.error(f"OpenAI连接失败: {e}")
            raise ConnectionError(f"OpenAI连接失败: {e}", self.provider_name)
        
        except openai.BadRequestError as e:
            logger.error(f"OpenAI请求无效: {e}")
            raise InvalidRequestError(f"OpenAI请求无效: {e}", self.provider_name)
        
        except Exception as e:
            logger.error(f"OpenAI生成时发生未知错误: {e}")
            raise LLMProviderError(f"OpenAI生成失败: {e}", self.provider_name)
    
    def is_available(self) -> bool:
        """检查OpenAI是否可用."""
        try:
            # 检查库是否可用
            if openai is None:
                return False
            
            # 检查API密钥是否存在
            if not self.api_key:
                return False
            
            # 检查是否已初始化
            if not self.is_initialized:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"OpenAI可用性检查失败: {e}")
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """测试OpenAI连接."""
        try:
            # 简单的测试请求
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
                temperature=0.0
            )
            
            return {
                "success": True,
                "model": self.model,
                "response": response.choices[0].message.content if response.choices else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_models(self) -> List[str]:
        """获取可用模型列表."""
        try:
            models = await self.client.models.list()
            return [model.id for model in models.data if "gpt" in model.id.lower()]
        except Exception as e:
            logger.error(f"获取OpenAI模型列表失败: {e}")
            return []
    
    async def generate_streaming(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ):
        """流式生成文本.
        
        Args:
            prompt: 输入提示词
            max_tokens: 最大令牌数
            temperature: 温度参数
            **kwargs: 其他参数
            
        Yields:
            生成的文本片段
        """
        if not self.is_initialized:
            raise LLMProviderError("OpenAI客户端未初始化")
        
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        model = kwargs.get("model", self.model)
        
        messages = [{"role": "user", "content": prompt}]
        system_prompt = kwargs.get("system_prompt")
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **{k: v for k, v in kwargs.items() if k not in ['model', 'system_prompt']}
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI流式生成失败: {e}")
            raise LLMProviderError(f"OpenAI流式生成失败: {e}", self.provider_name)
    
    def get_token_count(self, text: str) -> int:
        """估算文本的令牌数.
        
        Args:
            text: 文本内容
            
        Returns:
            估算的令牌数
        """
        # 简单估算：中文约1.5字符/令牌，英文约4字符/令牌
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        other_chars = len(text) - chinese_chars
        
        estimated_tokens = chinese_chars / 1.5 + other_chars / 4
        return int(estimated_tokens)
    
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """估算生成成本（美元）.
        
        Args:
            prompt_tokens: 输入令牌数
            completion_tokens: 输出令牌数
            
        Returns:
            估算成本（美元）
        """
        # GPT-4 Turbo 价格（2024年价格）
        if "gpt-4" in self.model.lower():
            if "turbo" in self.model.lower():
                input_cost = prompt_tokens * 0.01 / 1000  # $0.01 per 1K tokens
                output_cost = completion_tokens * 0.03 / 1000  # $0.03 per 1K tokens
            else:
                input_cost = prompt_tokens * 0.03 / 1000  # $0.03 per 1K tokens
                output_cost = completion_tokens * 0.06 / 1000  # $0.06 per 1K tokens
        elif "gpt-3.5" in self.model.lower():
            input_cost = prompt_tokens * 0.0015 / 1000  # $0.0015 per 1K tokens
            output_cost = completion_tokens * 0.002 / 1000  # $0.002 per 1K tokens
        else:
            # 默认使用GPT-4 Turbo价格
            input_cost = prompt_tokens * 0.01 / 1000
            output_cost = completion_tokens * 0.03 / 1000
        
        return input_cost + output_cost


# 便捷函数
async def create_openai_client(config: Dict[str, Any]) -> OpenAIClient:
    """创建OpenAI客户端.
    
    Args:
        config: 配置字典
        
    Returns:
        OpenAI客户端实例
    """
    client = OpenAIClient(config)
    return client


def is_openai_available() -> bool:
    """检查OpenAI库是否可用."""
    return openai is not None