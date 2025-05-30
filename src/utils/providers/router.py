"""LLM智能路由器."""

import random
from typing import Dict, Any, List, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """任务类型枚举."""
    CONCEPT_EXPANSION = "concept_expansion"
    OUTLINE_GENERATION = "outline_generation"
    CHARACTER_CREATION = "character_creation"
    CHAPTER_GENERATION = "chapter_generation"
    STORY_GENERATION = "story_generation"  # 添加故事生成任务
    CONSISTENCY_CHECK = "consistency_check"
    QUALITY_ASSESSMENT = "quality_assessment"
    GENERAL = "general"


@dataclass
class ProviderCapability:
    """提供商能力配置."""
    provider_name: str
    quality_score: float  # 质量评分 (0-10)
    speed_score: float    # 速度评分 (0-10)
    reliability_score: float  # 可靠性评分 (0-10)
    cost_score: float     # 成本评分 (0-10, 分数越高成本越低)
    supported_tasks: List[TaskType]
    max_tokens: int
    is_available: bool = True
    priority: int = 5     # 优先级 (1-10, 数字越小优先级越高)


class RoutingStrategy(Enum):
    """路由策略枚举."""
    QUALITY_FIRST = "quality_first"      # 质量优先
    SPEED_FIRST = "speed_first"          # 速度优先
    COST_FIRST = "cost_first"            # 成本优先
    BALANCED = "balanced"                # 平衡策略
    ROUND_ROBIN = "round_robin"          # 轮询
    FAILOVER = "failover"                # 故障转移


class LLMRouter:
    """LLM智能路由器."""
    
    def __init__(self) -> None:
        """初始化路由器."""
        self.providers: Dict[str, ProviderCapability] = {}
        self.failure_counts: Dict[str, int] = {}
        self.success_counts: Dict[str, int] = {}
        self.response_times: Dict[str, List[float]] = {}
        self.round_robin_index = 0
        
        # 获取配置
        from src.utils.config import get_settings
        self.settings = get_settings()
        
        # 默认提供商能力配置
        self._setup_default_capabilities()
        
        # 根据配置调整优先级
        self._adjust_provider_priorities()
        
        logger.info("LLM路由器初始化完成")
        logger.info(f"主要LLM提供商: {self.settings.primary_llm_provider}")
        logger.info(f"后备LLM提供商: {self.settings.fallback_llm_providers_list}")
    
    def _setup_default_capabilities(self) -> None:
        """设置默认提供商能力配置."""
        # OpenAI GPT-4 Turbo
        self.providers["openai"] = ProviderCapability(
            provider_name="openai",
            quality_score=9.5,
            speed_score=8.0,
            reliability_score=9.0,
            cost_score=6.0,  # 成本较高
            supported_tasks=list(TaskType),  # 支持所有任务
            max_tokens=128000,
            priority=1
        )
        
        # Ollama (本地部署)
        self.providers["ollama"] = ProviderCapability(
            provider_name="ollama",
            quality_score=7.5,
            speed_score=6.0,
            reliability_score=7.0,
            cost_score=10.0,  # 免费使用
            supported_tasks=[
                TaskType.CONCEPT_EXPANSION,
                TaskType.OUTLINE_GENERATION,
                TaskType.CHARACTER_CREATION,
                TaskType.CHAPTER_GENERATION,
                TaskType.STORY_GENERATION,
                TaskType.GENERAL
            ],
            max_tokens=32768,
            priority=2
        )
        
        # 自定义模型
        self.providers["custom"] = ProviderCapability(
            provider_name="custom",
            quality_score=7.0,
            speed_score=7.0,
            reliability_score=6.0,
            cost_score=8.0,
            supported_tasks=[
                TaskType.CONCEPT_EXPANSION,
                TaskType.CHAPTER_GENERATION,
                TaskType.STORY_GENERATION,
                TaskType.GENERAL
            ],
            max_tokens=16384,
            priority=3
        )
    
    def _adjust_provider_priorities(self) -> None:
        """根据配置调整提供商优先级."""
        # 设置主要提供商的优先级为最高（1）
        if self.settings.primary_llm_provider in self.providers:
            self.providers[self.settings.primary_llm_provider].priority = 1
            logger.info(f"设置主要提供商 {self.settings.primary_llm_provider} 优先级为 1")
        
        # 设置后备提供商的优先级
        fallback_providers = self.settings.fallback_llm_providers_list
        for i, provider_name in enumerate(fallback_providers):
            if provider_name in self.providers:
                self.providers[provider_name].priority = i + 2  # 从2开始
                logger.info(f"设置后备提供商 {provider_name} 优先级为 {i + 2}")
        
        # 其他提供商优先级设为最低
        for provider_name, capability in self.providers.items():
            if (provider_name != self.settings.primary_llm_provider and
                provider_name not in fallback_providers):
                capability.priority = 10
                logger.info(f"设置其他提供商 {provider_name} 优先级为 10")
    
    def update_provider_capability(
        self,
        provider_name: str,
        capability: ProviderCapability
    ) -> None:
        """更新提供商能力配置."""
        self.providers[provider_name] = capability
        logger.info(f"更新提供商能力配置: {provider_name}")
    
    def set_provider_availability(self, provider_name: str, is_available: bool) -> None:
        """设置提供商可用性."""
        if provider_name in self.providers:
            self.providers[provider_name].is_available = is_available
            logger.info(f"设置提供商 {provider_name} 可用性: {is_available}")
    
    def select_provider(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
        required_tokens: Optional[int] = None,
        exclude_providers: Optional[List[str]] = None,
        preferred_provider: Optional[str] = None
    ) -> str:
        """选择最佳提供商.
        
        Args:
            prompt: 输入提示词
            task_type: 任务类型
            strategy: 路由策略
            required_tokens: 需要的令牌数
            exclude_providers: 排除的提供商列表
            preferred_provider: 首选提供商
            
        Returns:
            选择的提供商名称
            
        Raises:
            ValueError: 当没有可用提供商时抛出
        """
        # 如果传入的是字符串，尝试转换为TaskType
        if isinstance(task_type, str):
            try:
                task_type = TaskType(task_type)
            except ValueError:
                # 如果无法转换，使用GENERAL类型
                task_type = TaskType.GENERAL
                logger.warning(f"未知任务类型: {task_type}，使用GENERAL")
        
        # 获取可用提供商
        available_providers = self._get_available_providers(
            task_type, required_tokens, exclude_providers
        )
        
        if not available_providers:
            raise ValueError(f"没有可用的提供商支持任务类型: {task_type}")
        
        # 如果指定了首选提供商且可用，直接返回
        if preferred_provider and preferred_provider in available_providers:
            logger.info(f"使用首选提供商: {preferred_provider}")
            return preferred_provider
        
        # 根据策略选择提供商
        if strategy == RoutingStrategy.QUALITY_FIRST:
            provider = self._select_by_quality(available_providers)
        elif strategy == RoutingStrategy.SPEED_FIRST:
            provider = self._select_by_speed(available_providers)
        elif strategy == RoutingStrategy.COST_FIRST:
            provider = self._select_by_cost(available_providers)
        elif strategy == RoutingStrategy.BALANCED:
            provider = self._select_balanced(available_providers)
        elif strategy == RoutingStrategy.ROUND_ROBIN:
            provider = self._select_round_robin(available_providers)
        elif strategy == RoutingStrategy.FAILOVER:
            provider = self._select_failover(available_providers)
        else:
            provider = self._select_balanced(available_providers)
        
        logger.info(f"选择提供商: {provider}, 策略: {strategy.value}, 任务: {task_type.value}")
        return provider
    
    def _get_available_providers(
        self,
        task_type: TaskType,
        required_tokens: Optional[int] = None,
        exclude_providers: Optional[List[str]] = None
    ) -> List[str]:
        """获取可用提供商列表."""
        available = []
        exclude_providers = exclude_providers or []
        
        for name, capability in self.providers.items():
            if (capability.is_available and 
                name not in exclude_providers and
                task_type in capability.supported_tasks):
                
                # 检查令牌数限制
                if required_tokens and required_tokens > capability.max_tokens:
                    continue
                
                available.append(name)
        
        return available
    
    def _select_by_quality(self, providers: List[str]) -> str:
        """按质量评分选择提供商."""
        return max(providers, key=lambda p: self.providers[p].quality_score)
    
    def _select_by_speed(self, providers: List[str]) -> str:
        """按速度评分选择提供商."""
        return max(providers, key=lambda p: self.providers[p].speed_score)
    
    def _select_by_cost(self, providers: List[str]) -> str:
        """按成本评分选择提供商（成本越低分数越高）."""
        return max(providers, key=lambda p: self.providers[p].cost_score)
    
    def _select_balanced(self, providers: List[str]) -> str:
        """平衡策略选择提供商."""
        def calculate_score(provider_name: str) -> float:
            capability = self.providers[provider_name]
            
            # 计算成功率
            total_requests = self.success_counts.get(provider_name, 0) + self.failure_counts.get(provider_name, 0)
            success_rate = self.success_counts.get(provider_name, 0) / max(total_requests, 1)
            
            # 计算平均响应时间评分
            response_times = self.response_times.get(provider_name, [])
            avg_response_time = sum(response_times) / len(response_times) if response_times else 1.0
            response_score = max(0, 10 - avg_response_time)  # 响应时间越短分数越高
            
            # 综合评分 (质量40%, 速度25%, 可靠性20%, 成本10%, 历史表现5%)
            score = (
                capability.quality_score * 0.4 +
                capability.speed_score * 0.25 +
                capability.reliability_score * 0.2 +
                capability.cost_score * 0.1 +
                (success_rate * 10 + response_score) * 0.05
            )
            
            # 优先级调整
            score -= (capability.priority - 1) * 0.5
            
            return score
        
        return max(providers, key=calculate_score)
    
    def _select_round_robin(self, providers: List[str]) -> str:
        """轮询策略选择提供商."""
        if not providers:
            raise ValueError("没有可用提供商")
        
        # 按优先级排序
        sorted_providers = sorted(providers, key=lambda p: self.providers[p].priority)
        
        provider = sorted_providers[self.round_robin_index % len(sorted_providers)]
        self.round_robin_index += 1
        
        return provider
    
    def _select_failover(self, providers: List[str]) -> str:
        """故障转移策略选择提供商."""
        # 按优先级和成功率排序
        def failover_score(provider_name: str) -> Tuple[int, float]:
            capability = self.providers[provider_name]
            total_requests = self.success_counts.get(provider_name, 0) + self.failure_counts.get(provider_name, 0)
            success_rate = self.success_counts.get(provider_name, 1) / max(total_requests, 1)
            return (capability.priority, -success_rate)  # 优先级低，成功率高的排在前面
        
        sorted_providers = sorted(providers, key=failover_score)
        return sorted_providers[0]
    
    def get_fallback_provider(
        self,
        current_provider: str,
        task_type: TaskType = TaskType.GENERAL,
        required_tokens: Optional[int] = None
    ) -> Optional[str]:
        """获取降级提供商.
        
        Args:
            current_provider: 当前失败的提供商
            task_type: 任务类型
            required_tokens: 需要的令牌数
            
        Returns:
            降级提供商名称，如果没有则返回None
        """
        available_providers = self._get_available_providers(
            task_type, required_tokens, exclude_providers=[current_provider]
        )
        
        if not available_providers:
            return None
        
        # 选择最佳降级提供商
        return self._select_failover(available_providers)
    
    def record_request_result(
        self,
        provider_name: str,
        success: bool,
        response_time: float
    ) -> None:
        """记录请求结果.
        
        Args:
            provider_name: 提供商名称
            success: 是否成功
            response_time: 响应时间（秒）
        """
        if success:
            self.success_counts[provider_name] = self.success_counts.get(provider_name, 0) + 1
        else:
            self.failure_counts[provider_name] = self.failure_counts.get(provider_name, 0) + 1
        
        # 记录响应时间（保留最近100次）
        if provider_name not in self.response_times:
            self.response_times[provider_name] = []
        
        self.response_times[provider_name].append(response_time)
        if len(self.response_times[provider_name]) > 100:
            self.response_times[provider_name] = self.response_times[provider_name][-100:]
        
        logger.debug(f"记录请求结果: {provider_name}, 成功: {success}, 响应时间: {response_time:.2f}s")
    
    def get_provider_stats(self, provider_name: str) -> Dict[str, Any]:
        """获取提供商统计信息.
        
        Args:
            provider_name: 提供商名称
            
        Returns:
            统计信息字典
        """
        success_count = self.success_counts.get(provider_name, 0)
        failure_count = self.failure_counts.get(provider_name, 0)
        total_requests = success_count + failure_count
        
        response_times = self.response_times.get(provider_name, [])
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        return {
            "provider_name": provider_name,
            "total_requests": total_requests,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_count / max(total_requests, 1),
            "average_response_time": avg_response_time,
            "is_available": self.providers.get(provider_name, {}).is_available if provider_name in self.providers else False,
            "capability": self.providers.get(provider_name)
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有提供商统计信息."""
        return {name: self.get_provider_stats(name) for name in self.providers.keys()}
    
    def reset_stats(self, provider_name: Optional[str] = None) -> None:
        """重置统计信息.
        
        Args:
            provider_name: 提供商名称，如果为None则重置所有
        """
        if provider_name:
            self.success_counts.pop(provider_name, None)
            self.failure_counts.pop(provider_name, None)
            self.response_times.pop(provider_name, None)
            logger.info(f"重置提供商统计信息: {provider_name}")
        else:
            self.success_counts.clear()
            self.failure_counts.clear()
            self.response_times.clear()
            self.round_robin_index = 0
            logger.info("重置所有提供商统计信息")


# 全局路由器实例
_router_instance = None


def get_router() -> LLMRouter:
    """获取全局路由器实例（单例）."""
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance


# 便捷函数
def select_provider_for_task(
    task_type: TaskType,
    prompt: str = "",
    strategy: RoutingStrategy = RoutingStrategy.BALANCED,
    **kwargs
) -> str:
    """为特定任务选择提供商的便捷函数."""
    router = get_router()
    return router.select_provider(prompt, task_type, strategy, **kwargs)


def get_fallback_for_provider(provider_name: str, task_type: TaskType = TaskType.GENERAL) -> Optional[str]:
    """获取指定提供商的降级方案的便捷函数."""
    router = get_router()
    return router.get_fallback_provider(provider_name, task_type)