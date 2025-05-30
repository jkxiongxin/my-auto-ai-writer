"""配置管理模块."""

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """应用程序设置."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 基本配置
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # API配置
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    api_reload: bool = Field(default=True)
    api_workers: int = Field(default=1)
    allowed_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")

    # 安全配置
    secret_key: str = Field(default="dev-secret-key")
    access_token_expire_minutes: int = Field(default=30)
    algorithm: str = Field(default="HS256")

    # 数据库配置
    database_url: str = Field(default="sqlite+aiosqlite:///./ai_novel_generator.db")
    database_echo: bool = Field(default=False)

    # OpenAI配置
    openai_api_key: Optional[str] = Field(default=None)
    openai_model: str = Field(default="gpt-4-turbo-preview")
    openai_max_tokens: int = Field(default=4000)
    openai_temperature: float = Field(default=0.7)
    openai_base_url: str = Field(default="https://api.openai.com/v1")

    # Ollama配置
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama2:13b-chat")
    ollama_timeout: int = Field(default=300)
    ollama_max_tokens: int = Field(default=4000)
    ollama_temperature: float = Field(default=0.7)

    # 自定义模型配置
    custom_model_base_url: Optional[str] = Field(default=None)
    custom_model_api_key: Optional[str] = Field(default=None)
    custom_model_name: str = Field(default="custom-model-v1")
    custom_model_timeout: int = Field(default=300)

    # LLM路由配置
    primary_llm_provider: str = Field(default="openai")
    fallback_llm_providers: str = Field(default="ollama,custom")
    
    # LLM速率限制配置
    llm_rate_limit_delay: float = Field(default=10.0, description="LLM调用之间的最小间隔（秒）")
    llm_max_retries: int = Field(default=3, description="LLM调用最大重试次数")
    llm_retry_attempts: int = Field(default=3)
    llm_retry_delay: int = Field(default=1)
    llm_request_timeout: int = Field(default=60)

    # 缓存配置
    redis_url: str = Field(default="redis://localhost:6379/0")
    cache_ttl: int = Field(default=3600)
    cache_enabled: bool = Field(default=True)

    # 请求缓存
    request_cache_enabled: bool = Field(default=True)
    request_cache_ttl: int = Field(default=1800)
    request_cache_max_size: int = Field(default=1000)

    # 生成缓存
    generation_cache_enabled: bool = Field(default=True)
    generation_cache_ttl: int = Field(default=86400)
    generation_cache_max_size: int = Field(default=100)

    # 性能配置
    max_concurrent_generations: int = Field(default=3)
    max_word_count: int = Field(default=200000)
    min_word_count: int = Field(default=1000)
    default_word_count: int = Field(default=10000)

    # 超时设置
    generation_timeout: int = Field(default=7200)
    chapter_generation_timeout: int = Field(default=600)
    concept_expansion_timeout: int = Field(default=120)

    # 质量控制
    min_coherence_score: float = Field(default=6.0)
    min_character_consistency: float = Field(default=0.7)
    quality_check_enabled: bool = Field(default=True)

    # 监控配置
    metrics_enabled: bool = Field(default=True)
    metrics_port: int = Field(default=9090)
    metrics_path: str = Field(default="/metrics")

    # 日志配置
    log_format: str = Field(default="json")
    log_file: str = Field(default="logs/ai_novel_generator.log")
    log_rotation: str = Field(default="daily")
    log_retention_days: int = Field(default=30)

    # 文件存储
    upload_dir: str = Field(default="data/uploads")
    export_dir: str = Field(default="data/exports")
    samples_dir: str = Field(default="data/samples")
    templates_dir: str = Field(default="data/templates")

    # 文件大小限制（字节）
    max_upload_size: int = Field(default=10485760)  # 10MB
    max_export_size: int = Field(default=52428800)  # 50MB

    # 速率限制
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests_per_minute: int = Field(default=60)
    rate_limit_burst_size: int = Field(default=10)

    # 生成速率限制
    generation_rate_limit_per_hour: int = Field(default=10)
    generation_rate_limit_per_day: int = Field(default=50)

    # CORS配置
    cors_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: str = Field(default="GET,POST,PUT,DELETE,OPTIONS")
    cors_allow_headers: str = Field(default="*")

    # 功能标志
    feature_multi_volume_generation: bool = Field(default=True)
    feature_advanced_character_system: bool = Field(default=False)
    feature_real_time_collaboration: bool = Field(default=False)

    # 实验性功能
    experimental_batch_generation: bool = Field(default=False)
    experimental_streaming_response: bool = Field(default=True)
    experimental_auto_editing: bool = Field(default=False)

    @field_validator("primary_llm_provider")
    @classmethod
    def validate_primary_provider(cls, v: str) -> str:
        """验证主要LLM提供商."""
        valid_providers = ["openai", "ollama", "custom"]
        if v not in valid_providers:
            raise ValueError(f"无效的主要LLM提供商: {v}. 必须是: {valid_providers}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"无效的日志级别: {v}. 必须是: {valid_levels}")
        return v.upper()

    # 属性方法，用于获取解析后的列表
    @property
    def fallback_llm_providers_list(self) -> List[str]:
        """获取后备LLM提供商列表."""
        return [provider.strip() for provider in self.fallback_llm_providers.split(",") if provider.strip()]

    @property
    def allowed_origins_list(self) -> List[str]:
        """获取允许的来源列表."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        """获取CORS来源列表."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cors_allow_methods_list(self) -> List[str]:
        """获取CORS允许方法列表."""
        return [method.strip() for method in self.cors_allow_methods.split(",") if method.strip()]

    @property
    def cors_allow_headers_list(self) -> List[str]:
        """获取CORS允许头部列表."""
        if self.cors_allow_headers == "*":
            return ["*"]
        return [header.strip() for header in self.cors_allow_headers.split(",") if header.strip()]

    def get_llm_config(self, provider: str) -> Dict[str, Any]:
        """获取指定LLM提供商的配置."""
        if provider == "openai":
            return {
                "api_key": self.openai_api_key,
                "model": self.openai_model,
                "max_tokens": self.openai_max_tokens,
                "temperature": self.openai_temperature,
                "base_url": self.openai_base_url,
            }
        elif provider == "ollama":
            return {
                "base_url": self.ollama_base_url,
                "model": self.ollama_model,
                "timeout": self.ollama_timeout,
                "max_tokens": self.ollama_max_tokens,
                "temperature": self.ollama_temperature,
            }
        elif provider == "custom":
            return {
                "base_url": self.custom_model_base_url,
                "api_key": self.custom_model_api_key,
                "model": self.custom_model_name,
                "timeout": self.custom_model_timeout,
            }
        else:
            raise ValueError(f"未知的LLM提供商: {provider}")


@lru_cache()
def get_settings() -> Settings:
    """获取应用程序设置（带缓存）."""
    settings = Settings()
    
    # 添加配置加载日志
    logger.info(f"配置文件加载完成")
    logger.info(f"主要LLM提供商: {settings.primary_llm_provider}")
    logger.info(f"后备LLM提供商: {settings.fallback_llm_providers}")
    logger.info(f"数据库URL: {settings.database_url}")
    logger.info(f"日志级别: {settings.log_level}")
    
    return settings


# 全局设置实例
settings = get_settings()