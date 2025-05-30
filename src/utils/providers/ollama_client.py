"""Ollama客户端实现."""

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
    InvalidRequestError,
)

logger = logging.getLogger(__name__)


class OllamaClient(BaseLLMProvider):
    """Ollama客户端实现."""
    
    def _get_provider_name(self) -> str:
        """获取提供商名称."""
        return "ollama"
    
    def _setup_provider(self) -> None:
        """设置Ollama特定配置."""
        if httpx is None:
            raise LLMProviderError("httpx库未安装，请运行: pip install httpx")
        
        self.base_url = self.get_config_value("base_url", "http://localhost:11434")
        self.model = self.get_config_value("model", "llama2:13b-chat")
        self.timeout = self.get_config_value("timeout", 300)
        self.max_tokens = self.get_config_value("max_tokens", 4000)
        self.temperature = self.get_config_value("temperature", 0.7)
        
        # 确保base_url格式正确
        if not self.base_url.startswith(('http://', 'https://')):
            self.base_url = f"http://{self.base_url}"
        
        if not self.base_url.endswith('/'):
            self.base_url += '/'
        
        self.generate_url = f"{self.base_url}api/generate"
        self.chat_url = f"{self.base_url}api/chat"
        self.models_url = f"{self.base_url}api/tags"
        self.show_url = f"{self.base_url}api/show"
        
        self.is_initialized = True
        logger.info(f"Ollama客户端初始化成功，地址: {self.base_url}, 模型: {self.model}")
    
    def _get_required_config_keys(self) -> List[str]:
        """获取必需的配置键."""
        return ["base_url", "model"]
    
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """使用Ollama生成文本.
        
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
            raise LLMProviderError("Ollama客户端未初始化")
        
        # 使用传入的参数或默认值
        temperature = temperature if temperature is not None else self.temperature
        model = kwargs.get("model", self.model)
        
        # 构建请求数据
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        
        # 添加可选参数
        if max_tokens:
            data["options"]["num_predict"] = max_tokens
        
        if kwargs.get("top_p"):
            data["options"]["top_p"] = kwargs["top_p"]
        
        if kwargs.get("top_k"):
            data["options"]["top_k"] = kwargs["top_k"]
        
        if kwargs.get("repeat_penalty"):
            data["options"]["repeat_penalty"] = kwargs["repeat_penalty"]
        
        if kwargs.get("seed"):
            data["options"]["seed"] = kwargs["seed"]
        
        if kwargs.get("stop"):
            data["options"]["stop"] = kwargs["stop"]
        
        # 如果有系统提示词，使用chat API
        system_prompt = kwargs.get("system_prompt")
        if system_prompt:
            return await self._generate_with_chat(prompt, system_prompt, data["options"])
        
        try:
            logger.debug(f"开始Ollama生成，模型: {model}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.generate_url,
                    json=data,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                result = response.json()
                
                if "response" not in result:
                    raise LLMProviderError("Ollama返回格式无效")
                
                content = result["response"]
                
                # 记录使用信息
                logger.info(
                    f"Ollama生成完成",
                    extra={
                        "model": model,
                        "prompt_length": len(prompt),
                        "response_length": len(content),
                        "eval_count": result.get("eval_count", 0),
                        "eval_duration": result.get("eval_duration", 0),
                    }
                )
                
                return content.strip()
                
        except httpx.ConnectError as e:
            logger.error(f"Ollama连接失败: {e}")
            raise ConnectionError(f"无法连接到Ollama服务: {e}", self.provider_name)
        
        except httpx.TimeoutException as e:
            logger.error(f"Ollama请求超时: {e}")
            raise LLMProviderError(f"Ollama请求超时: {e}", self.provider_name)
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP错误: {e}")
            if e.response.status_code == 404:
                raise InvalidRequestError(f"模型 {model} 未找到", self.provider_name)
            else:
                raise LLMProviderError(f"Ollama HTTP错误 {e.response.status_code}: {e}", self.provider_name)
        
        except json.JSONDecodeError as e:
            logger.error(f"Ollama响应JSON解析失败: {e}")
            raise LLMProviderError(f"Ollama响应格式错误: {e}", self.provider_name)
        
        except Exception as e:
            logger.error(f"Ollama生成时发生未知错误: {e}")
            raise LLMProviderError(f"Ollama生成失败: {e}", self.provider_name)
    
    async def _generate_with_chat(
        self,
        prompt: str,
        system_prompt: str,
        options: Dict[str, Any]
    ) -> str:
        """使用chat API生成文本."""
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": options
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.chat_url,
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "message" not in result or "content" not in result["message"]:
                raise LLMProviderError("Ollama chat API返回格式无效")
            
            return result["message"]["content"].strip()
    
    def is_available(self) -> bool:
        """检查Ollama是否可用."""
        try:
            # 检查库是否可用
            if httpx is None:
                return False
            
            # 检查是否已初始化
            if not self.is_initialized:
                return False
            
            # 简单的连接测试
            import asyncio
            return asyncio.run(self._test_connection())
            
        except Exception as e:
            logger.error(f"Ollama可用性检查失败: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """测试Ollama连接."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(self.models_url)
                response.raise_for_status()
                return True
        except Exception:
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """测试Ollama连接."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 测试基础连接
                response = await client.get(self.models_url)
                response.raise_for_status()
                
                models_data = response.json()
                available_models = [model["name"] for model in models_data.get("models", [])]
                
                # 测试模型是否存在
                model_exists = self.model in available_models
                
                return {
                    "success": True,
                    "base_url": self.base_url,
                    "available_models": available_models,
                    "configured_model": self.model,
                    "model_exists": model_exists
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_models(self) -> List[str]:
        """获取可用模型列表."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.models_url)
                response.raise_for_status()
                
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
                
        except Exception as e:
            logger.error(f"获取Ollama模型列表失败: {e}")
            return []
    
    async def get_model_info(self, model_name: str = None) -> Dict[str, Any]:
        """获取模型信息."""
        model_name = model_name or self.model
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.show_url,
                    json={"name": model_name}
                )
                response.raise_for_status()
                
                return response.json()
                
        except Exception as e:
            logger.error(f"获取Ollama模型信息失败: {e}")
            return {}
    
    async def pull_model(self, model_name: str) -> bool:
        """拉取模型."""
        try:
            pull_url = f"{self.base_url}api/pull"
            
            async with httpx.AsyncClient(timeout=600) as client:  # 拉取模型可能需要更长时间
                response = await client.post(
                    pull_url,
                    json={"name": model_name, "stream": False}
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get("status") == "success"
                
        except Exception as e:
            logger.error(f"拉取Ollama模型失败: {e}")
            return False
    
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
            raise LLMProviderError("Ollama客户端未初始化")
        
        temperature = temperature if temperature is not None else self.temperature
        model = kwargs.get("model", self.model)
        
        data = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
            }
        }
        
        if max_tokens:
            data["options"]["num_predict"] = max_tokens
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    self.generate_url,
                    json=data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                chunk = json.loads(line)
                                if "response" in chunk:
                                    yield chunk["response"]
                                if chunk.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            logger.error(f"Ollama流式生成失败: {e}")
            raise LLMProviderError(f"Ollama流式生成失败: {e}", self.provider_name)
    
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
async def create_ollama_client(config: Dict[str, Any]) -> OllamaClient:
    """创建Ollama客户端.
    
    Args:
        config: 配置字典
        
    Returns:
        Ollama客户端实例
    """
    client = OllamaClient(config)
    return client


def is_ollama_available() -> bool:
    """检查httpx库是否可用."""
    return httpx is not None