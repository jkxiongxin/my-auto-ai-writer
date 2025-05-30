"""LLM客户端模块单元测试."""

from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

import pytest

from src.utils.llm_client import UniversalLLMClient
from src.utils.providers.base_provider import BaseLLMProvider
from src.utils.providers.openai_client import OpenAIClient
from src.utils.providers.ollama_client import OllamaClient
from src.utils.providers.custom_client import CustomClient
from src.utils.providers.router import LLMRouter
from src.utils.providers.fallback_manager import FallbackManager


class TestUniversalLLMClient:
    """测试统一LLM客户端."""

    @pytest.fixture
    def mock_openai_client(self) -> Mock:
        """模拟OpenAI客户端."""
        client = Mock(spec=OpenAIClient)
        client.generate = AsyncMock(return_value="OpenAI响应")
        client.is_available = Mock(return_value=True)
        return client

    @pytest.fixture
    def mock_ollama_client(self) -> Mock:
        """模拟Ollama客户端."""
        client = Mock(spec=OllamaClient)
        client.generate = AsyncMock(return_value="Ollama响应")
        client.is_available = Mock(return_value=True)
        return client

    @pytest.fixture
    def mock_custom_client(self) -> Mock:
        """模拟自定义客户端."""
        client = Mock(spec=CustomClient)
        client.generate = AsyncMock(return_value="自定义模型响应")
        client.is_available = Mock(return_value=True)
        return client

    @pytest.fixture
    def universal_client(self, mock_openai_client, mock_ollama_client, mock_custom_client) -> UniversalLLMClient:
        """创建统一LLM客户端实例."""
        with patch('src.utils.llm_client.OpenAIClient', return_value=mock_openai_client), \
             patch('src.utils.llm_client.OllamaClient', return_value=mock_ollama_client), \
             patch('src.utils.llm_client.CustomClient', return_value=mock_custom_client):
            return UniversalLLMClient()

    async def test_generate_with_openai_provider(self, universal_client) -> None:
        """测试使用OpenAI提供商生成文本."""
        result = await universal_client.generate("测试提示", provider="openai")
        
        assert result == "OpenAI响应"
        universal_client.providers["openai"].generate.assert_called_once()

    async def test_generate_with_ollama_provider(self, universal_client) -> None:
        """测试使用Ollama提供商生成文本."""
        result = await universal_client.generate("测试提示", provider="ollama")
        
        assert result == "Ollama响应"
        universal_client.providers["ollama"].generate.assert_called_once()

    async def test_generate_with_custom_provider(self, universal_client) -> None:
        """测试使用自定义提供商生成文本."""
        result = await universal_client.generate("测试提示", provider="custom")
        
        assert result == "自定义模型响应"
        universal_client.providers["custom"].generate.assert_called_once()

    async def test_generate_with_invalid_provider(self, universal_client) -> None:
        """测试使用无效提供商."""
        with pytest.raises(ValueError, match="未知的LLM提供商"):
            await universal_client.generate("测试提示", provider="invalid")

    async def test_provider_fallback_mechanism(self, universal_client) -> None:
        """测试提供商降级机制."""
        # 模拟主提供商失败
        universal_client.providers["openai"].generate.side_effect = Exception("API错误")
        
        # 应该自动降级到备用提供商
        result = await universal_client.generate("测试提示", preferred_provider="openai")
        
        # 验证降级到其他提供商
        assert result in ["Ollama响应", "自定义模型响应"]

    async def test_caching_mechanism(self, universal_client) -> None:
        """测试缓存机制."""
        prompt = "重复的提示"
        
        # 第一次调用
        result1 = await universal_client.generate(prompt, provider="openai")
        
        # 第二次调用相同提示
        result2 = await universal_client.generate(prompt, provider="openai")
        
        # 应该返回相同结果
        assert result1 == result2
        
        # 但OpenAI客户端应该只被调用一次（第二次从缓存返回）
        assert universal_client.providers["openai"].generate.call_count == 1


class TestOpenAIClient:
    """测试OpenAI客户端."""

    @pytest.fixture
    def openai_config(self) -> Dict[str, Any]:
        """OpenAI配置."""
        return {
            "api_key": "test-key",
            "model": "gpt-4-turbo",
            "max_tokens": 4000,
            "temperature": 0.7,
            "base_url": "https://api.openai.com/v1"
        }

    def test_openai_client_initialization(self, openai_config) -> None:
        """测试OpenAI客户端初始化."""
        client = OpenAIClient(openai_config)
        
        assert client.api_key == "test-key"
        assert client.model == "gpt-4-turbo"
        assert client.max_tokens == 4000

    async def test_openai_generate_success(self, openai_config) -> None:
        """测试OpenAI生成成功."""
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "生成的内容"
            
            mock_openai.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
            
            client = OpenAIClient(openai_config)
            result = await client.generate("测试提示")
            
            assert result == "生成的内容"

    async def test_openai_generate_api_error(self, openai_config) -> None:
        """测试OpenAI API错误处理."""
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_openai.return_value.chat.completions.create = AsyncMock(
                side_effect=Exception("API错误")
            )
            
            client = OpenAIClient(openai_config)
            
            with pytest.raises(Exception, match="API错误"):
                await client.generate("测试提示")

    def test_openai_is_available_with_valid_key(self, openai_config) -> None:
        """测试OpenAI可用性检查（有效密钥）."""
        client = OpenAIClient(openai_config)
        assert client.is_available() is True

    def test_openai_is_available_with_invalid_key(self) -> None:
        """测试OpenAI可用性检查（无效密钥）."""
        config = {"api_key": None, "model": "gpt-4-turbo"}
        client = OpenAIClient(config)
        assert client.is_available() is False


class TestOllamaClient:
    """测试Ollama客户端."""

    @pytest.fixture
    def ollama_config(self) -> Dict[str, Any]:
        """Ollama配置."""
        return {
            "base_url": "http://localhost:11434",
            "model": "llama2:13b-chat",
            "timeout": 300,
            "max_tokens": 4000,
            "temperature": 0.7
        }

    def test_ollama_client_initialization(self, ollama_config) -> None:
        """测试Ollama客户端初始化."""
        client = OllamaClient(ollama_config)
        
        assert client.base_url == "http://localhost:11434"
        assert client.model == "llama2:13b-chat"
        assert client.timeout == 300

    async def test_ollama_generate_success(self, ollama_config) -> None:
        """测试Ollama生成成功."""
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_response = Mock()
            mock_response.json.return_value = {"response": "Ollama生成的内容"}
            mock_response.status_code = 200
            
            mock_httpx.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            client = OllamaClient(ollama_config)
            result = await client.generate("测试提示")
            
            assert result == "Ollama生成的内容"

    async def test_ollama_connection_error(self, ollama_config) -> None:
        """测试Ollama连接错误."""
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_httpx.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("连接错误")
            )
            
            client = OllamaClient(ollama_config)
            
            with pytest.raises(Exception, match="连接错误"):
                await client.generate("测试提示")

    def test_ollama_is_available_success(self, ollama_config) -> None:
        """测试Ollama可用性检查成功."""
        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            client = OllamaClient(ollama_config)
            assert client.is_available() is True

    def test_ollama_is_available_failure(self, ollama_config) -> None:
        """测试Ollama可用性检查失败."""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = Exception("连接失败")
            
            client = OllamaClient(ollama_config)
            assert client.is_available() is False


class TestCustomClient:
    """测试自定义客户端."""

    @pytest.fixture
    def custom_config(self) -> Dict[str, Any]:
        """自定义客户端配置."""
        return {
            "base_url": "http://custom-model.example.com",
            "api_key": "custom-key",
            "model": "custom-model-v1",
            "timeout": 300
        }

    def test_custom_client_initialization(self, custom_config) -> None:
        """测试自定义客户端初始化."""
        client = CustomClient(custom_config)
        
        assert client.base_url == "http://custom-model.example.com"
        assert client.api_key == "custom-key"
        assert client.model == "custom-model-v1"

    async def test_custom_generate_success(self, custom_config) -> None:
        """测试自定义客户端生成成功."""
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_response = Mock()
            mock_response.json.return_value = {"content": "自定义模型响应"}
            mock_response.status_code = 200
            
            mock_httpx.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            client = CustomClient(custom_config)
            result = await client.generate("测试提示")
            
            assert result == "自定义模型响应"

    def test_custom_is_available_with_config(self, custom_config) -> None:
        """测试自定义客户端可用性（有配置）."""
        client = CustomClient(custom_config)
        assert client.is_available() is True

    def test_custom_is_available_without_config(self) -> None:
        """测试自定义客户端可用性（无配置）."""
        config = {"base_url": None, "api_key": None}
        client = CustomClient(config)
        assert client.is_available() is False


class TestLLMRouter:
    """测试LLM路由器."""

    def test_select_best_provider_for_task(self) -> None:
        """测试为任务选择最佳提供商."""
        router = LLMRouter()
        
        # 测试不同任务类型的路由
        provider = router.select_provider("简单的故事生成", task_type="story_generation")
        assert provider in ["openai", "ollama", "custom"]
        
        # 测试概念扩展任务
        provider = router.select_provider("复杂的概念扩展", task_type="concept_expansion")
        assert provider in ["openai", "ollama", "custom"]

    def test_get_fallback_provider(self) -> None:
        """测试获取降级提供商."""
        router = LLMRouter()
        
        fallback = router.get_fallback_provider("openai")
        assert fallback in ["ollama", "custom"]
        
        fallback = router.get_fallback_provider("ollama")
        assert fallback in ["openai", "custom"]


class TestFallbackManager:
    """测试降级管理器."""

    def test_should_fallback_decision(self) -> None:
        """测试是否应该降级的决策."""
        manager = FallbackManager()
        
        # 测试不同错误类型
        assert manager.should_fallback(Exception("Rate limit exceeded")) is True
        assert manager.should_fallback(Exception("API key invalid")) is False
        assert manager.should_fallback(Exception("Connection timeout")) is True

    def test_record_provider_failure(self) -> None:
        """测试记录提供商失败."""
        manager = FallbackManager()
        
        # 记录失败
        manager.record_failure("openai", "rate_limit")
        manager.record_failure("openai", "timeout")
        
        # 验证失败记录
        failures = manager.get_failure_stats("openai")
        assert failures["total"] == 2
        assert failures["rate_limit"] == 1
        assert failures["timeout"] == 1

    def test_provider_health_status(self) -> None:
        """测试提供商健康状态."""
        manager = FallbackManager()
        
        # 初始状态应该是健康的
        assert manager.is_provider_healthy("openai") is True
        
        # 记录多次失败后应该变为不健康
        for _ in range(5):
            manager.record_failure("openai", "error")
        
        assert manager.is_provider_healthy("openai") is False


if __name__ == "__main__":
    pytest.main([__file__])