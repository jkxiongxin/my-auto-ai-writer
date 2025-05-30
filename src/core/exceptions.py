"""小说生成器异常模块

定义系统中使用的所有自定义异常类。
"""

class NovelGeneratorError(Exception):
    """小说生成器基础异常"""
    pass


class ConceptExpansionError(NovelGeneratorError):
    """概念扩展异常"""
    pass


class StrategySelectionError(NovelGeneratorError):
    """策略选择异常"""
    pass


class OutlineGenerationError(NovelGeneratorError):
    """大纲生成异常"""
    pass


class CharacterCreationError(NovelGeneratorError):
    """角色创建异常"""
    pass


class ChapterGenerationError(NovelGeneratorError):
    """章节生成异常"""
    pass


class ConsistencyCheckError(NovelGeneratorError):
    """一致性检查异常"""
    pass


class QualityAssessmentError(NovelGeneratorError):
    """质量评估异常"""
    pass


class LLMConnectionError(NovelGeneratorError):
    """LLM连接异常"""
    pass


class RetryableError(NovelGeneratorError):
    """可重试的异常（用于重试机制）"""
    pass


class ValidationError(NovelGeneratorError):
    """数据验证异常"""
    pass


class ConfigurationError(NovelGeneratorError):
    """配置错误异常"""
    pass


class ResourceExhaustedError(NovelGeneratorError):
    """资源耗尽异常（如API配额用完）"""
    pass


class TimeoutError(NovelGeneratorError):
    """超时异常"""
    pass