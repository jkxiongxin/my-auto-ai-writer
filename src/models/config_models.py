"""配置相关数据模型."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, JSON
from sqlalchemy.sql import func

from .database import Base


class GenerationConfig(Base):
    """生成配置模型."""
    
    __tablename__ = 'generation_configs'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    
    # LLM配置
    provider = Column(String(50), default="openai")
    model = Column(String(100), default="gpt-4-turbo")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2000)
    
    # 生成策略配置
    strategy_config = Column(JSON)
    
    # 质量控制配置
    quality_thresholds = Column(JSON)
    
    # 重试和容错配置
    retry_count = Column(Integer, default=3)
    timeout_seconds = Column(Integer, default=60)
    fallback_providers = Column(JSON)
    
    # 状态
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class LLMProviderConfig(Base):
    """LLM提供商配置模型."""
    
    __tablename__ = 'llm_provider_configs'
    
    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String(50), unique=True, nullable=False, index=True)
    
    # 连接配置
    api_endpoint = Column(String(500))
    api_key_hash = Column(String(255))  # 加密存储
    
    # 模型配置
    available_models = Column(JSON)
    default_model = Column(String(100))
    model_limits = Column(JSON)  # 每个模型的限制
    
    # 性能配置
    max_concurrent_requests = Column(Integer, default=3)
    rate_limit_per_minute = Column(Integer, default=60)
    priority = Column(Integer, default=100)  # 优先级，数字越小优先级越高
    
    # 成本配置
    cost_per_1k_tokens = Column(Float, default=0.0)
    monthly_budget_limit = Column(Float)
    current_monthly_cost = Column(Float, default=0.0)
    
    # 状态
    is_enabled = Column(Boolean, default=True)
    is_healthy = Column(Boolean, default=True)
    last_health_check = Column(DateTime)
    
    # 统计信息
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    average_response_time = Column(Float, default=0.0)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class QualityThresholds(Base):
    """质量阈值配置模型."""
    
    __tablename__ = 'quality_thresholds'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    
    # 质量阈值
    min_overall_score = Column(Float, default=7.0)
    min_coherence_score = Column(Float, default=7.5)
    min_character_consistency = Column(Float, default=8.0)
    min_plot_consistency = Column(Float, default=7.0)
    min_writing_quality = Column(Float, default=6.5)
    
    # 错误容忍度
    max_critical_issues = Column(Integer, default=0)
    max_warning_issues = Column(Integer, default=5)
    max_total_issues = Column(Integer, default=10)
    
    # 自动修复配置
    auto_fix_enabled = Column(Boolean, default=True)
    auto_fix_thresholds = Column(JSON)
    
    # 重新生成触发条件
    regenerate_on_failure = Column(Boolean, default=True)
    max_regeneration_attempts = Column(Integer, default=2)
    
    # 适用范围
    target_word_range = Column(JSON)  # {"min": 1000, "max": 50000}
    applicable_genres = Column(JSON)
    
    # 状态
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())