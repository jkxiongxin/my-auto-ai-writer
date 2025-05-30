"""自定义模型客户端实现."""

import json
from typing import Dict, Any, Optional, List
import logging

try:
    import httpx
except ImportError:
    httpx = None

from src.utils.providers.base_provider import (
    BaseLLMProvider,
    LLMProviderError,
    ConnectionError,
    AuthenticationError,
    InvalidRequestError,
)

logger = logging.getLogger(__name__)


class CustomClient(BaseLLMProvider):
    """自定义模型客户端实现."""
    
    def _get_provider_name(self) -> str:
        """获取提供商名称."""
        return "custom"
    
    def _setup_provider(self) -> None:
        """设置自定义模型特定配置."""
        if httpx is None:
            raise LLMProviderError("httpx库未安装，请运行: pip install httpx")
        
        self.base_url = self.get_config_value("base_url")
        self.api_key = self.get_config_value("api_key")
        self.model = self.get_config_value("model", "custom-model-v1")
        self.timeout = self.get_config_value("timeout", 300)
        self.max_tokens = self.get_config_value("max_tokens", 4000)
        self.temperature = self.get_config_value("temperature", 0.7)
        
        # API格式配置
        self.api_format = self.get_config_value("api_format", "openai")  # openai, custom
        self.auth_type = self.get_config_value("auth_type", "bearer")  # bearer, api_key, basic
        self.generate_endpoint = self.get_config_value("generate_endpoint", "/v1/chat/completions")
        self.models_endpoint = self.get_config_value("models_endpoint", "/v1/models")
        
        # 请求格式配置
        self.request_format = self.get_config_value("request_format", {})
        self.response_format = self.get_config_value("response_format", {})
        
        # 确保base_url格式正确
        if self.base_url:
            if not self.base_url.startswith(('http://', 'https://')):
                self.base_url = f"https://{self.base_url}"
            
            if self.base_url.endswith('/'):
                self.base_url = self.base_url[:-1]
        
        self.is_initialized = True
        logger.info(f"自定义客户端初始化成功，地址: {self.base_url}, 模型: {self.model}")
    
    def _get_required_config_keys(self) -> List[str]:
        """获取必需的配置键."""
        return ["base_url"]
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头."""
        headers = {"Content-Type": "application/json"}
        
        if self.api_key:
            if self.auth_type == "bearer":
                headers["Authorization"] = f"Bearer {self.api_key}"
            elif self.auth_type == "api_key":
                headers["X-API-Key"] = self.api_key
            elif self.auth_type == "basic":
                import base64
                credentials = base64.b64encode(f":{self.api_key}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"
        
        return headers
    
    def _build_request_data(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """构建请求数据."""
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        model = kwargs.get("model", self.model)
        
        if self.api_format == "openai":
            # OpenAI兼容格式
            messages = [{"role": "user", "content": prompt}]
            system_prompt = kwargs.get("system_prompt")
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
            
            data = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False,
            }
            
            # 添加可选参数
            for key in ["top_p", "frequency_penalty", "presence_penalty", "stop"]:
                if key in kwargs:
                    data[key] = kwargs[key]
                    
        else:
            # 自定义格式
            data = {
                "model": model,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            
            # 使用配置的请求格式
            if self.request_format:
                data.update(self.request_format)
            
            # 添加其他参数
            for key, value in kwargs.items():
                if key not in ["model", "system_prompt"]:
                    data[key] = value
        
        return data
    
    def _parse_response(self, response_data: Dict[str, Any]) -> str:
        """解析响应数据."""
        if self.api_format == "openai":
            # OpenAI兼容格式
            if "choices" in response_data and response_data["choices"]:
                choice = response_data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
                elif "text" in choice:
                    return choice["text"]
            
            raise LLMProviderError("无效的OpenAI格式响应")
        
        else:
            # 自定义格式
            response_config = self.response_format or {}
            content_path = response_config.get("content_path", ["response"])
            
            # 按路径获取内容
            current = response_data
            for key in content_path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    raise LLMProviderError(f"响应中未找到路径 {content_path}")
            
            if isinstance(current, str):
                return current
            else:
                raise LLMProviderError("响应内容不是字符串")
    
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """使用自定义模型生成文本.
        
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
            raise LLMProviderError("自定义客户端未初始化")
        
        if not self.base_url:
            raise LLMProviderError("未配置自定义模型URL")
        
        # 构建请求
        url = f"{self.base_url}{self.generate_endpoint}"
        headers = self._build_headers()
        data = self._build_request_data(prompt, max_tokens, temperature, **kwargs)
        
        try:
            logger.debug(f"开始自定义模型生成，URL: {url}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=data, headers=headers)
                
                # 处理HTTP错误
                if response.status_code == 401:
                    raise AuthenticationError("认证失败，请检查API密钥", self.provider_name)
                elif response.status_code == 404:
                    raise InvalidRequestError("端点未找到，请检查URL配置", self.provider_name)
                elif response.status_code >= 400:
                    error_text = response.text
                    raise LLMProviderError(f"HTTP错误 {response.status_code}: {error_text}", self.provider_name)
                
                response.raise_for_status()
                result = response.json()
                
                # 解析响应
                content = self._parse_response(result)
                
                # 记录使用信息
                logger.info(
                    f"自定义模型生成完成",
                    extra={
                        "model": self.model,
                        "prompt_length": len(prompt),
                        "response_length": len(content),
                        "url": url
                    }
                )
                
                return content.strip()
                
        except httpx.ConnectError as e:
            logger.error(f"自定义模型连接失败: {e}")
            raise ConnectionError(f"无法连接到自定义模型服务: {e}", self.provider_name)
        
        except httpx.TimeoutException as e:
            logger.error(f"自定义模型请求超时: {e}")
            raise LLMProviderError(f"自定义模型请求超时: {e}", self.provider_name)
        
        except json.JSONDecodeError as e:
            logger.error(f"自定义模型响应JSON解析失败: {e}")
            raise LLMProviderError(f"自定义模型响应格式错误: {e}", self.provider_name)
        
        except Exception as e:
            logger.error(f"自定义模型生成时发生未知错误: {e}")
            raise LLMProviderError(f"自定义模型生成失败: {e}", self.provider_name)
    
    def is_available(self) -> bool:
        """检查自定义模型是否可用."""
        try:
            # 检查库是否可用
            if httpx is None:
                return False
            
            # 检查基本配置
            if not self.base_url:
                return False
            
            # 检查是否已初始化
            if not self.is_initialized:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"自定义模型可用性检查失败: {e}")
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """测试自定义模型连接."""
        try:
            # 测试基础连接
            url = f"{self.base_url}{self.models_endpoint}"
            headers = self._build_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 404:
                    # 如果models端点不存在，尝试生成端点
                    test_url = f"{self.base_url}{self.generate_endpoint}"
                    test_response = await client.get(test_url, headers=headers)
                    
                    return {
                        "success": True,
                        "base_url": self.base_url,
                        "models_endpoint_available": False,
                        "generate_endpoint_accessible": test_response.status_code != 404,
                        "configured_model": self.model
                    }
                
                response.raise_for_status()
                
                # 尝试解析模型列表
                try:
                    models_data = response.json()
                    if isinstance(models_data, dict) and "data" in models_data:
                        available_models = [model.get("id", "unknown") for model in models_data["data"]]
                    else:
                        available_models = []
                except:
                    available_models = []
                
                return {
                    "success": True,
                    "base_url": self.base_url,
                    "models_endpoint_available": True,
                    "available_models": available_models,
                    "configured_model": self.model
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_models(self) -> List[str]:
        """获取可用模型列表."""
        try:
            url = f"{self.base_url}{self.models_endpoint}"
            headers = self._build_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                # 处理OpenAI格式
                if isinstance(data, dict) and "data" in data:
                    return [model.get("id", "unknown") for model in data["data"]]
                
                # 处理其他格式
                elif isinstance(data, list):
                    return [str(model) for model in data]
                
                else:
                    return [self.model]  # 返回配置的模型
                
        except Exception as e:
            logger.error(f"获取自定义模型列表失败: {e}")
            return [self.model]  # 返回配置的模型
    
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
            raise LLMProviderError("自定义客户端未初始化")
        
        # 构建请求
        url = f"{self.base_url}{self.generate_endpoint}"
        headers = self._build_headers()
        data = self._build_request_data(prompt, max_tokens, temperature, **kwargs)
        
        # 启用流式传输
        if self.api_format == "openai":
            data["stream"] = True
        else:
            data["stream"] = True
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=data, headers=headers) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            if line.startswith("data: "):
                                line = line[6:]  # 移除 "data: " 前缀
                            
                            if line.strip() == "[DONE]":
                                break
                            
                            try:
                                chunk = json.loads(line)
                                
                                if self.api_format == "openai":
                                    # OpenAI格式
                                    if "choices" in chunk and chunk["choices"]:
                                        delta = chunk["choices"][0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            yield content
                                else:
                                    # 自定义格式
                                    content = chunk.get("response", "")
                                    if content:
                                        yield content
                                        
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            logger.error(f"自定义模型流式生成失败: {e}")
            raise LLMProviderError(f"自定义模型流式生成失败: {e}", self.provider_name)
    
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


# 便捷函数
async def create_custom_client(config: Dict[str, Any]) -> CustomClient:
    """创建自定义客户端.
    
    Args:
        config: 配置字典
        
    Returns:
        自定义客户端实例
    """
    client = CustomClient(config)
    return client


def is_custom_available() -> bool:
    """检查httpx库是否可用."""
    return httpx is not None