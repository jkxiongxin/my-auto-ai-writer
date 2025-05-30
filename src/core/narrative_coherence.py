"""叙事连贯性管理器 - 确保章节间情节的连贯性和一致性."""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from src.core.data_models import ChapterContent
from src.core.outline_generator import ChapterOutline
from src.core.character_system import CharacterDatabase, Character
from src.core.concept_expander import ConceptExpansionResult
from src.utils.llm_client import UniversalLLMClient

logger = logging.getLogger(__name__)


@dataclass
class NarrativeState:
    """叙事状态数据类."""
    
    # 时间和地点
    current_time: str = "故事开始"
    current_location: str = "未指定"
    time_progression: List[str] = field(default_factory=list)
    
    # 角色状态
    character_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    character_relationships: Dict[str, Dict[str, str]] = field(default_factory=dict)
    character_locations: Dict[str, str] = field(default_factory=dict)
    
    # 情节状态
    active_plot_threads: List[str] = field(default_factory=list)
    resolved_conflicts: List[str] = field(default_factory=list)
    pending_revelations: List[str] = field(default_factory=list)
    
    # 世界状态
    world_changes: List[str] = field(default_factory=list)
    established_facts: List[str] = field(default_factory=list)
    secrets_revealed: List[str] = field(default_factory=list)
    
    # 情绪和氛围
    current_mood: str = "平和"
    tension_level: float = 0.5  # 0-1之间
    
    # 伏笔和回响
    foreshadowing_elements: List[str] = field(default_factory=list)
    callback_opportunities: List[str] = field(default_factory=list)


@dataclass
class ChapterTransition:
    """章节转换信息."""
    
    from_chapter: int
    to_chapter: int
    time_gap: str = "无间隔"
    location_change: bool = False
    pov_change: bool = False  # 视角变化
    mood_shift: str = "保持"
    key_connections: List[str] = field(default_factory=list)
    transition_text: str = ""


@dataclass
class CoherenceAnalysis:
    """连贯性分析结果."""
    
    coherence_score: float = 0.0  # 0-1之间
    issues_found: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    character_consistency: float = 0.0
    plot_consistency: float = 0.0
    timeline_consistency: float = 0.0


class NarrativeCoherenceManager:
    """叙事连贯性管理器.
    
    负责维护章节间的连贯性，包括：
    1. 角色状态一致性
    2. 时间线连贯性
    3. 情节线索延续
    4. 世界设定一致性
    5. 情绪基调转换
    """
    
    def __init__(self, llm_client: UniversalLLMClient):
        """初始化连贯性管理器.
        
        Args:
            llm_client: LLM客户端实例
        """
        self.llm_client = llm_client
        self.narrative_state = NarrativeState()
        self.chapter_history: List[ChapterContent] = []
        self.transitions: List[ChapterTransition] = []
        
        logger.info("叙事连贯性管理器初始化完成")
    
    async def prepare_chapter_context(
        self,
        chapter_outline: ChapterOutline,
        character_db: CharacterDatabase,
        concept: ConceptExpansionResult,
        previous_chapters: List[ChapterContent]
    ) -> Dict[str, Any]:
        """为新章节准备连贯性上下文.
        
        Args:
            chapter_outline: 当前章节大纲
            character_db: 角色数据库
            concept: 概念扩展结果
            previous_chapters: 之前的章节
            
        Returns:
            包含连贯性信息的上下文字典
        """
        logger.info(f"为第{chapter_outline.number}章准备连贯性上下文")
        
        try:
            # 1. 更新叙事状态
            if previous_chapters:
                await self._update_narrative_state(previous_chapters[-1])
            
            # 2. 分析章节转换
            transition = None
            if previous_chapters:
                transition = await self._analyze_chapter_transition(
                    previous_chapters[-1], chapter_outline
                )
                self.transitions.append(transition)
            
            # 3. 提取连贯性要点
            coherence_context = {
                "narrative_state": self._serialize_narrative_state(),
                "transition_info": self._serialize_transition(transition) if transition else None,
                "character_continuity": await self._prepare_character_continuity(character_db),
                "plot_continuity": self._prepare_plot_continuity(chapter_outline),
                "world_continuity": self._prepare_world_continuity(),
                "mood_continuity": self._prepare_mood_continuity(chapter_outline),
                "previous_chapter_summary": self._get_previous_chapter_summary(previous_chapters),
                "coherence_guidelines": self._generate_coherence_guidelines(chapter_outline)
            }
            
            return coherence_context
            
        except Exception as e:
            logger.error(f"准备连贯性上下文失败: {e}")
            return {}
    
    async def _update_narrative_state(self, completed_chapter: ChapterContent):
        """更新叙事状态."""
        try:
            # 分析章节内容，提取状态变化
            analysis_prompt = f"""
            请分析以下章节内容，提取关键的叙事状态变化：
            
            章节标题: {completed_chapter.title}
            章节内容: {completed_chapter.content[:1000]}...
            
            请以JSON格式返回分析结果：
            {{
                "time_changes": ["时间变化描述"],
                "location_changes": ["地点变化"],
                "character_developments": {{"角色名": "发展描述"}},
                "plot_developments": ["情节发展"],
                "world_changes": ["世界状态变化"],
                "mood_shift": "情绪变化描述",
                "revealed_secrets": ["揭示的秘密"],
                "new_conflicts": ["新出现的冲突"],
                "resolved_issues": ["解决的问题"]
            }}
            """
            
            response = await self.llm_client.generate(analysis_prompt)
            
            try:
                # 清理响应文本
                cleaned_response = response.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()
                
                # 如果响应为空或者不是JSON，使用默认值
                if not cleaned_response or cleaned_response in ["", "null", "None"]:
                    logger.warning("LLM返回空响应，使用默认状态更新")
                    analysis = {}
                else:
                    analysis = json.loads(cleaned_response)
                
                # 更新各种状态
                if "time_changes" in analysis:
                    self.narrative_state.time_progression.extend(analysis["time_changes"])
                
                if "location_changes" in analysis:
                    for location in analysis["location_changes"]:
                        self.narrative_state.current_location = location
                
                if "character_developments" in analysis:
                    for char_name, development in analysis["character_developments"].items():
                        if char_name not in self.narrative_state.character_states:
                            self.narrative_state.character_states[char_name] = {}
                        self.narrative_state.character_states[char_name]["last_development"] = development
                
                if "plot_developments" in analysis:
                    self.narrative_state.active_plot_threads.extend(analysis["plot_developments"])
                
                if "world_changes" in analysis:
                    self.narrative_state.world_changes.extend(analysis["world_changes"])
                
                if "revealed_secrets" in analysis:
                    self.narrative_state.secrets_revealed.extend(analysis["revealed_secrets"])
                
                if "resolved_issues" in analysis:
                    self.narrative_state.resolved_conflicts.extend(analysis["resolved_issues"])
                
                logger.info(f"叙事状态更新完成: {completed_chapter.title}")
                
            except json.JSONDecodeError as e:
                logger.warning(f"无法解析LLM返回的状态分析结果: {e}")
                # 继续执行，不阻断流程
                
        except Exception as e:
            logger.error(f"更新叙事状态失败: {e}")
    
    async def _analyze_chapter_transition(
        self,
        previous_chapter: ChapterContent,
        next_outline: ChapterOutline
    ) -> ChapterTransition:
        """分析章节转换."""
        
        transition_prompt = f"""
        请分析从上一章到下一章的转换情况：
        
        上一章标题: {previous_chapter.title}
        上一章结尾: {previous_chapter.content[-300:]}
        
        下一章标题: {next_outline.title}
        下一章摘要: {next_outline.summary}
        
        请以JSON格式返回转换分析：
        {{
            "time_gap": "时间间隔描述",
            "location_change": true/false,
            "mood_shift": "情绪转变描述",
            "key_connections": ["连接要点"],
            "suggested_opening": "建议的开头方式"
        }}
        """
        
        try:
            response = await self.llm_client.generate(transition_prompt)
            
            # 清理响应文本
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # 如果响应为空或者不是JSON，使用默认值
            if not cleaned_response or cleaned_response in ["", "null", "None"]:
                logger.warning("LLM返回空的转换分析响应，使用默认值")
                analysis = {}
            else:
                analysis = json.loads(cleaned_response)
            
            return ChapterTransition(
                from_chapter=previous_chapter.title,
                to_chapter=next_outline.number,
                time_gap=analysis.get("time_gap", "无间隔"),
                location_change=analysis.get("location_change", False),
                mood_shift=analysis.get("mood_shift", "保持"),
                key_connections=analysis.get("key_connections", []),
                transition_text=analysis.get("suggested_opening", "")
            )
            
        except Exception as e:
            logger.error(f"分析章节转换失败: {e}")
            return ChapterTransition(
                from_chapter=previous_chapter.title,
                to_chapter=next_outline.number
            )
    
    async def _prepare_character_continuity(self, character_db: CharacterDatabase) -> Dict[str, Any]:
        """准备角色连贯性信息."""
        
        character_info = {}
        
        # 安全地处理character_db.characters
        if hasattr(character_db, 'characters') and hasattr(character_db.characters, 'values'):
            characters = character_db.characters.values()
        elif isinstance(character_db.characters, dict):
            characters = character_db.characters.values()
        elif isinstance(character_db.characters, list):
            characters = character_db.characters
        else:
            logger.warning("无法解析角色数据库格式")
            return {}
        
        for character in characters:
            char_state = self.narrative_state.character_states.get(character.name, {})
            character_info[character.name] = {
                "basic_info": {
                    "role": character.role,
                    "motivation": character.motivation,
                    "personality": character.personality
                },
                "current_state": char_state,
                "last_appearance": char_state.get("last_appearance", "未出现"),
                "development_arc": char_state.get("development_arc", "待发展")
            }
        
        return character_info
    
    def _prepare_plot_continuity(self, chapter_outline: ChapterOutline) -> Dict[str, Any]:
        """准备情节连贯性信息."""
        
        return {
            "active_threads": self.narrative_state.active_plot_threads[-5:],  # 最近5个线索
            "chapter_events": chapter_outline.key_events,
            "unresolved_conflicts": [
                thread for thread in self.narrative_state.active_plot_threads
                if thread not in self.narrative_state.resolved_conflicts
            ],
            "pending_revelations": self.narrative_state.pending_revelations
        }
    
    def _prepare_world_continuity(self) -> Dict[str, Any]:
        """准备世界设定连贯性信息."""
        
        return {
            "current_location": self.narrative_state.current_location,
            "established_facts": self.narrative_state.established_facts[-10:],
            "world_changes": self.narrative_state.world_changes[-5:],
            "secrets_status": self.narrative_state.secrets_revealed
        }
    
    def _prepare_mood_continuity(self, chapter_outline: ChapterOutline) -> Dict[str, Any]:
        """准备情绪基调连贯性信息."""
        
        return {
            "current_mood": self.narrative_state.current_mood,
            "tension_level": self.narrative_state.tension_level,
            "chapter_purpose": chapter_outline.narrative_purpose,
            "mood_evolution": "根据情节自然演变"
        }
    
    def _get_previous_chapter_summary(self, previous_chapters: List[ChapterContent]) -> str:
        """获取前一章节摘要."""
        
        if not previous_chapters:
            return "这是第一章"
        
        last_chapter = previous_chapters[-1]
        return f"第{last_chapter.title}: {last_chapter.summary[:200]}"
    
    def _generate_coherence_guidelines(self, chapter_outline: ChapterOutline) -> List[str]:
        """生成连贯性指导原则."""
        
        guidelines = [
            "确保角色行为与之前建立的性格一致",
            "维持时间线的逻辑性和连续性",
            "延续上一章未完成的情节线索",
            "保持世界设定的一致性",
            "自然地承接上一章的情绪基调",
            "适当回应之前章节中的伏笔",
            "避免突兀的人物性格变化",
            "确保对话风格与角色身份匹配"
        ]
        
        # 根据章节特点添加特殊指导
        if chapter_outline.narrative_purpose == "冲突升级":
            guidelines.append("逐步升级紧张感，避免突然爆发")
        elif chapter_outline.narrative_purpose == "高潮部分":
            guidelines.append("充分利用之前积累的情节张力")
        elif chapter_outline.narrative_purpose == "结局收尾":
            guidelines.append("回应并解决主要的情节线索")
        
        return guidelines
    
    async def analyze_coherence(
        self,
        chapter_content: ChapterContent,
        previous_chapters: List[ChapterContent],
        character_db: CharacterDatabase
    ) -> CoherenceAnalysis:
        """分析章节连贯性."""
        
        logger.info(f"分析第{chapter_content.title}章的连贯性")
        
        try:
            analysis_prompt = f"""
            请分析以下章节的连贯性：
            
            当前章节: {chapter_content.title}
            当前内容: {chapter_content.content[:800]}
            
            上一章节摘要: {previous_chapters[-1].summary if previous_chapters else "无"}
            
            请从以下几个方面评分(0-1)并给出具体问题：
            1. 角色一致性 - 角色行为是否符合设定
            2. 情节连贯性 - 是否自然承接上一章
            3. 时间线一致性 - 时间发展是否合理
            4. 世界设定一致性 - 是否与已建立的世界观符合
            
            以JSON格式返回：
            {{
                "character_consistency": 0.85,
                "plot_consistency": 0.90,
                "timeline_consistency": 0.88,
                "world_consistency": 0.92,
                "overall_score": 0.89,
                "issues": ["发现的问题"],
                "suggestions": ["改进建议"]
            }}
            """
            
            response = await self.llm_client.generate(analysis_prompt)
            
            # 清理响应文本
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # 如果响应为空或者不是JSON，使用默认值
            if not cleaned_response or cleaned_response in ["", "null", "None"]:
                logger.warning("LLM返回空的连贯性分析响应，使用默认值")
                analysis_data = {}
            else:
                analysis_data = json.loads(cleaned_response)
            
            return CoherenceAnalysis(
                coherence_score=analysis_data.get("overall_score", 0.5),
                character_consistency=analysis_data.get("character_consistency", 0.5),
                plot_consistency=analysis_data.get("plot_consistency", 0.5),
                timeline_consistency=analysis_data.get("timeline_consistency", 0.5),
                issues_found=analysis_data.get("issues", []),
                suggestions=analysis_data.get("suggestions", [])
            )
            
        except Exception as e:
            logger.error(f"连贯性分析失败: {e}")
            return CoherenceAnalysis(coherence_score=0.5)
    
    def _serialize_narrative_state(self) -> Dict[str, Any]:
        """序列化叙事状态."""
        
        return {
            "current_time": self.narrative_state.current_time,
            "current_location": self.narrative_state.current_location,
            "character_states": dict(list(self.narrative_state.character_states.items())[-5:]),
            "active_plot_threads": self.narrative_state.active_plot_threads[-5:],
            "current_mood": self.narrative_state.current_mood,
            "tension_level": self.narrative_state.tension_level,
            "world_changes": self.narrative_state.world_changes[-3:],
            "established_facts": self.narrative_state.established_facts[-5:]
        }
    
    def _serialize_transition(self, transition: ChapterTransition) -> Dict[str, Any]:
        """序列化转换信息."""
        
        return {
            "time_gap": transition.time_gap,
            "location_change": transition.location_change,
            "mood_shift": transition.mood_shift,
            "key_connections": transition.key_connections,
            "transition_guidance": transition.transition_text
        }
    
    def get_coherence_summary(self) -> Dict[str, Any]:
        """获取连贯性管理摘要."""
        
        return {
            "chapters_processed": len(self.chapter_history),
            "active_plot_threads": len(self.narrative_state.active_plot_threads),
            "character_states": len(self.narrative_state.character_states),
            "world_facts": len(self.narrative_state.established_facts),
            "transitions_tracked": len(self.transitions),
            "current_narrative_state": self._serialize_narrative_state()
        }
    
    def reset_state(self):
        """重置连贯性状态."""
        
        self.narrative_state = NarrativeState()
        self.chapter_history = []
        self.transitions = []
        
        logger.info("连贯性管理器状态已重置")