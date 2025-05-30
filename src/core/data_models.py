"""共享数据模型模块 - 避免循环导入."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class ChapterContent:
    """章节内容数据类."""
    title: str
    content: str
    word_count: int
    summary: str  # 章节摘要
    key_events_covered: List[str]  # 已覆盖的关键事件
    character_developments: Dict[str, str] = field(default_factory=dict)  # 角色发展
    consistency_notes: List[str] = field(default_factory=list)  # 一致性注释
    generation_metadata: Dict[str, Any] = field(default_factory=dict)  # 生成元数据


@dataclass
class GenerationContext:
    """生成上下文数据类."""
    active_characters: List[str]  # 当前章节涉及的角色
    previous_summary: Optional[str] = None  # 前一章节摘要
    world_state: Dict[str, Any] = field(default_factory=dict)  # 世界状态
    plot_threads: List[str] = field(default_factory=list)  # 情节线索
    mood_tone: Optional[str] = None  # 当前章节的情绪基调
    setting_details: Dict[str, str] = field(default_factory=dict)  # 场景细节


@dataclass
class GenerationHistory:
    """生成历史数据类."""
    chapter_summaries: List[str]  # 章节摘要历史
    character_states: Dict[str, Dict[str, Any]]  # 角色状态历史
    world_events: List[str]  # 世界事件历史
    plot_progress: Dict[str, float]  # 情节进展
    tone_evolution: List[str]  # 基调演变