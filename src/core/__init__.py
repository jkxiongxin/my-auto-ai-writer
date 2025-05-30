"""AI小说生成器核心模块包.

该包包含了小说生成的核心算法和组件：
- 概念扩展器：将简单创意扩展为详细概念
- 策略选择器：选择最佳的生成策略
- 大纲生成器：生成分层小说大纲
- 角色系统：管理角色生成和关系
- 章节生成引擎：生成高质量章节内容
- 一致性检查器：检查内容的角色和情节一致性
- 小说生成器：统一的生成接口
"""

from .concept_expander import ConceptExpander, ConceptExpansionResult
from .strategy_selector import StrategySelector, GenerationStrategy
from .outline_generator import HierarchicalOutlineGenerator, NovelOutline, ChapterOutline, SceneOutline
from .character_system import SimpleCharacterSystem, CharacterDatabase, Character
from .data_models import ChapterContent, GenerationContext, GenerationHistory
from .chapter_generator import ChapterGenerationEngine
from .consistency_checker import BasicConsistencyChecker, ConsistencyCheckResult, ConsistencyIssue
from .novel_generator import NovelGenerator

__all__ = [
    # 概念扩展
    'ConceptExpander',
    'ConceptExpansionResult',
    
    # 策略选择
    'StrategySelector',
    'GenerationStrategy',
    
    # 大纲生成
    'HierarchicalOutlineGenerator',
    'NovelOutline',
    'ChapterOutline',
    'SceneOutline',
    
    # 角色系统
    'SimpleCharacterSystem',
    'CharacterDatabase',
    'Character',
    
    # 章节生成
    'ChapterGenerationEngine',
    'ChapterContent',
    'GenerationContext',
    'GenerationHistory',
    
    # 一致性检查
    'BasicConsistencyChecker',
    'ConsistencyCheckResult',
    'ConsistencyIssue',
    
    # 小说生成器
    'NovelGenerator',
]