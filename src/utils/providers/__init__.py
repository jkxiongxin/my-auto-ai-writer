"""LLM提供商模块导出."""

from src.utils.providers.base_provider import (
    BaseLLMProvider,
    LLMProviderError,
    RateLimitError,
    AuthenticationError,
    ConnectionError,
    ModelNotFoundError,
    InvalidRequestError,
)

from src.utils.providers.openai_client import (
    OpenAIClient,
    create_openai_client,
    is_openai_available,
)

from src.utils.providers.ollama_client import (
    OllamaClient,
    create_ollama_client,
    is_ollama_available,
)

from src.utils.providers.custom_client import (
    CustomClient,
    create_custom_client,
    is_custom_available,
)

from src.utils.providers.router import (
    LLMRouter,
    TaskType,
    RoutingStrategy,
    ProviderCapability,
    get_router,
    select_provider_for_task,
    get_fallback_for_provider,
)

from src.utils.providers.fallback_manager import (
    FallbackManager,
    FailureType,
    FailureRecord,
    ProviderHealth,
    get_fallback_manager,
    record_provider_failure,
    record_provider_success,
    is_provider_available,
)

__all__ = [
    # 基础提供商
    "BaseLLMProvider",
    "LLMProviderError",
    "RateLimitError",
    "AuthenticationError",
    "ConnectionError",
    "ModelNotFoundError",
    "InvalidRequestError",
    
    # OpenAI提供商
    "OpenAIClient",
    "create_openai_client",
    "is_openai_available",
    
    # Ollama提供商
    "OllamaClient",
    "create_ollama_client",
    "is_ollama_available",
    
    # 自定义提供商
    "CustomClient",
    "create_custom_client",
    "is_custom_available",
    
    # 路由器
    "LLMRouter",
    "TaskType",
    "RoutingStrategy",
    "ProviderCapability",
    "get_router",
    "select_provider_for_task",
    "get_fallback_for_provider",
    
    # 降级管理器
    "FallbackManager",
    "FailureType",
    "FailureRecord",
    "ProviderHealth",
    "get_fallback_manager",
    "record_provider_failure",
    "record_provider_success",
    "is_provider_available",
]