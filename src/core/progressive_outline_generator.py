"""渐进式大纲生成器模块，支持在生成过程中逐步完善大纲."""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from src.core.concept_expander import ConceptExpansionResult
from src.core.strategy_selector import GenerationStrategy
from src.core.outline_generator import NovelOutline, ChapterOutline, SceneOutline
from src.utils.llm_client import UniversalLLMClient

logger = logging.getLogger(__name__)


@dataclass
class WorldBuilding:
    """世界观构建数据类."""
    setting: str  # 基本设定
    time_period: str  # 时代背景
    locations: List[str]  # 主要地点
    social_structure: str  # 社会结构
    technology_level: str  # 科技水平
    magic_system: Optional[str] = None  # 魔法体系
    cultural_elements: List[str] = field(default_factory=list)  # 文化元素
    rules_and_laws: List[str] = field(default_factory=list)  # 世界规则


@dataclass
class RoughOutline:
    """粗略大纲数据类."""
    story_arc: str  # 整体故事弧线
    main_themes: List[str]  # 主要主题
    act_structure: List[str]  # 幕结构
    major_plot_points: List[str]  # 主要情节点
    character_roles: Dict[str, str]  # 角色定位
    estimated_chapters: int  # 预估章节数


@dataclass
class ProgressiveOutlineState:
    """渐进式大纲状态."""
    world_building: WorldBuilding
    rough_outline: RoughOutline
    detailed_chapters: List[ChapterOutline] = field(default_factory=list)
    current_act: int = 1
    completed_plot_points: List[str] = field(default_factory=list)
    pending_plot_threads: List[str] = field(default_factory=list)


class ProgressiveOutlineGenerator:
    """渐进式大纲生成器.
    
    先生成世界观和粗略大纲，然后在故事生成过程中逐步完善章节详情。
    """
    
    def __init__(self, llm_client: UniversalLLMClient, max_retries: int = 3):
        """初始化渐进式大纲生成器."""
        self.llm_client = llm_client
        self.max_retries = max_retries
        
        logger.info("渐进式大纲生成器初始化完成")
    
    async def generate_initial_outline(
        self,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy,
        target_words: int
    ) -> ProgressiveOutlineState:
        """生成初始大纲（世界观 + 粗略大纲）.
        
        Args:
            concept: 概念扩展结果
            strategy: 生成策略
            target_words: 目标字数
            
        Returns:
            ProgressiveOutlineState: 初始大纲状态
        """
        logger.info("开始生成初始大纲（世界观 + 粗略结构）")
        
        # 1. 生成世界观
        world_building = await self._generate_world_building(concept, strategy)
        
        # 2. 生成粗略大纲
        rough_outline = await self._generate_rough_outline(
            concept, strategy, target_words, world_building
        )
        
        # 3. 创建初始状态
        state = ProgressiveOutlineState(
            world_building=world_building,
            rough_outline=rough_outline
        )
        
        logger.info(f"初始大纲生成完成: {rough_outline.estimated_chapters}章预估")
        return state
    
    async def _generate_world_building(
        self,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy
    ) -> WorldBuilding:
        """生成详细的世界观设定."""
        
        prompt = f"""
请为以下小说概念创建详细的世界观设定。

概念信息:
- 主题: {concept.theme}
- 类型: {concept.genre}
- 世界类型: {concept.world_type}
- 基调: {concept.tone}
- 主要冲突: {concept.main_conflict}

要求创建完整的世界观，包括：
1. 基本设定描述
2. 时代背景
3. 主要地点列表
4. 社会结构
5. 科技水平
6. 文化元素
7. 世界规则

以JSON格式返回：
{{
    "setting": "世界基本设定描述",
    "time_period": "时代背景",
    "locations": ["地点1", "地点2", "地点3"],
    "social_structure": "社会结构描述",
    "technology_level": "科技水平",
    "magic_system": "魔法体系（如适用）",
    "cultural_elements": ["文化元素1", "文化元素2"],
    "rules_and_laws": ["世界规则1", "世界规则2"]
}}

确保世界观完整、一致，能够支撑整个故事的发展。
"""
        
        for attempt in range(self.max_retries):
            try:
                response = await self.llm_client.generate(
                    prompt,
                    step_type="world_building",
                    step_name="世界观构建",
                    log_generation=True
                )
                
                # 解析响应
                data = self._parse_json_response(response)
                
                return WorldBuilding(
                    setting=data.get("setting", ""),
                    time_period=data.get("time_period", ""),
                    locations=data.get("locations", []),
                    social_structure=data.get("social_structure", ""),
                    technology_level=data.get("technology_level", ""),
                    magic_system=data.get("magic_system"),
                    cultural_elements=data.get("cultural_elements", []),
                    rules_and_laws=data.get("rules_and_laws", [])
                )
                
            except Exception as e:
                logger.warning(f"世界观生成第{attempt + 1}次尝试失败: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2)
    
    async def _generate_rough_outline(
        self,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy,
        target_words: int,
        world_building: WorldBuilding
    ) -> RoughOutline:
        """生成粗略大纲结构."""
        
        complexity_guidance = self._get_complexity_guidance(target_words)
        
        prompt = f"""
基于已建立的世界观，为小说创建粗略的整体大纲结构。

世界观设定:
- 基本设定: {world_building.setting}
- 时代背景: {world_building.time_period}
- 主要地点: {', '.join(world_building.locations)}
- 社会结构: {world_building.social_structure}

小说信息:
- 主题: {concept.theme}
- 类型: {concept.genre}
- 主要冲突: {concept.main_conflict}
- 目标字数: {target_words}
- 结构类型: {strategy.structure_type}

{complexity_guidance}

请创建粗略的整体结构，包括：
1. 整体故事弧线
2. 主要主题
3. 幕结构划分
4. 关键情节点
5. 主要角色定位
6. 预估章节数

以JSON格式返回：
{{
    "story_arc": "整体故事弧线描述",
    "main_themes": ["主题1", "主题2"],
    "act_structure": ["第一幕：开端", "第二幕：发展", "第三幕：高潮"],
    "major_plot_points": ["情节点1", "情节点2", "情节点3"],
    "character_roles": {{
        "主角": "角色定位",
        "配角": "角色定位"
    }},
    "estimated_chapters": 预估章节数
}}

注意：此时只需要创建整体框架，不需要详细的章节内容。
"""
        
        for attempt in range(self.max_retries):
            try:
                response = await self.llm_client.generate(
                    prompt,
                    step_type="rough_outline",
                    step_name="粗略大纲生成",
                    log_generation=True
                )
                
                data = self._parse_json_response(response)
                
                return RoughOutline(
                    story_arc=data.get("story_arc", ""),
                    main_themes=data.get("main_themes", []),
                    act_structure=data.get("act_structure", []),
                    major_plot_points=data.get("major_plot_points", []),
                    character_roles=data.get("character_roles", {}),
                    estimated_chapters=data.get("estimated_chapters", strategy.chapter_count)
                )
                
            except Exception as e:
                logger.warning(f"粗略大纲生成第{attempt + 1}次尝试失败: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2)
    
    async def refine_next_chapter(
        self,
        state: ProgressiveOutlineState,
        chapter_number: int,
        previous_chapters_summary: Optional[str] = None
    ) -> ChapterOutline:
        """根据当前进展完善下一章的详细大纲.
        
        Args:
            state: 当前大纲状态
            chapter_number: 章节编号
            previous_chapters_summary: 之前章节摘要
            
        Returns:
            ChapterOutline: 详细的章节大纲
        """
        logger.info(f"开始完善第{chapter_number}章的详细大纲")
        
        # 确定当前所在的幕
        current_act = self._determine_current_act(
            chapter_number, state.rough_outline.estimated_chapters, state.rough_outline.act_structure
        )
        
        # 选择相关的情节点
        relevant_plot_points = self._select_relevant_plot_points(
            state, chapter_number, current_act
        )
        
        prompt = f"""
基于已建立的世界观和整体大纲，完善第{chapter_number}章的详细内容。

世界观背景:
- 设定: {state.world_building.setting}
- 主要地点: {', '.join(state.world_building.locations)}
- 社会结构: {state.world_building.social_structure}

整体大纲:
- 故事弧线: {state.rough_outline.story_arc}
- 当前幕: {current_act}（共{len(state.rough_outline.act_structure)}幕）
- 相关情节点: {', '.join(relevant_plot_points)}

章节信息:
- 章节编号: {chapter_number}
- 总章节数: {state.rough_outline.estimated_chapters}
- 已完成情节点: {', '.join(state.completed_plot_points)}

{f"前几章摘要: {previous_chapters_summary}" if previous_chapters_summary else ""}

请为第{chapter_number}章创建详细大纲：

以JSON格式返回：
{{
    "title": "章节标题",
    "summary": "章节摘要",
    "key_events": ["关键事件1", "关键事件2"],
    "scenes": [
        {{
            "name": "场景名称",
            "description": "场景描述",
            "location": "发生地点",
            "characters": ["参与角色"]
        }}
    ],
    "plot_advancement": "本章推进的情节",
    "character_development": "角色发展",
    "estimated_word_count": 预估字数
}}

确保本章内容与整体故事弧线一致，推进相关情节点。
"""
        
        for attempt in range(self.max_retries):
            try:
                response = await self.llm_client.generate(
                    prompt,
                    step_type="chapter_refinement",
                    step_name=f"第{chapter_number}章大纲完善",
                    log_generation=True
                )
                
                data = self._parse_json_response(response)
                
                # 解析场景
                scenes = []
                for scene_data in data.get("scenes", []):
                    scene = SceneOutline(
                        name=scene_data.get("name", ""),
                        description=scene_data.get("description", ""),
                        characters=scene_data.get("characters", []),
                        location=scene_data.get("location", "")
                    )
                    scenes.append(scene)
                
                chapter_outline = ChapterOutline(
                    number=chapter_number,
                    title=data.get("title", f"第{chapter_number}章"),
                    summary=data.get("summary", ""),
                    key_events=data.get("key_events", []),
                    estimated_word_count=data.get("estimated_word_count", 3000),
                    scenes=scenes
                )
                
                # 添加到状态中
                state.detailed_chapters.append(chapter_outline)
                
                # 更新已完成的情节点
                plot_advancement = data.get("plot_advancement", "")
                if plot_advancement and plot_advancement not in state.completed_plot_points:
                    state.completed_plot_points.append(plot_advancement)
                
                logger.info(f"第{chapter_number}章大纲完善完成")
                return chapter_outline
                
            except Exception as e:
                logger.warning(f"第{chapter_number}章大纲完善第{attempt + 1}次尝试失败: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2)
    
    def _get_complexity_guidance(self, target_words: int) -> str:
        """获取复杂度指导."""
        if target_words <= 10000:
            return "复杂度要求: 简洁单线结构，专注主线情节"
        elif target_words <= 100000:
            return "复杂度要求: 中等复杂度，可包含1-2条支线"
        elif target_words <= 2000000:
            return "复杂度要求: 复杂多线结构，多个情节线交织"
        else:
            return "复杂度要求: 史诗级复杂度，多重故事线和深度世界构建"
    
    def _determine_current_act(self, chapter_number: int, total_chapters: int, act_structure: List[str]) -> str:
        """确定当前章节所在的幕."""
        if not act_structure:
            return "未知幕"
        
        progress = chapter_number / total_chapters
        act_count = len(act_structure)
        
        for i in range(act_count):
            if progress <= (i + 1) / act_count:
                return act_structure[i]
        
        return act_structure[-1]
    
    def _select_relevant_plot_points(
        self, 
        state: ProgressiveOutlineState, 
        chapter_number: int, 
        current_act: str
    ) -> List[str]:
        """选择与当前章节相关的情节点."""
        # 选择还未完成的情节点
        remaining_points = [
            point for point in state.rough_outline.major_plot_points 
            if point not in state.completed_plot_points
        ]
        
        # 根据章节进度选择1-2个最相关的情节点
        total_chapters = state.rough_outline.estimated_chapters
        progress = chapter_number / total_chapters
        
        # 根据进度选择相应的情节点
        if progress < 0.3:
            # 前期：选择开端相关的情节点
            return remaining_points[:2]
        elif progress < 0.7:
            # 中期：选择发展相关的情节点
            mid_start = len(remaining_points) // 3
            return remaining_points[mid_start:mid_start + 2]
        else:
            # 后期：选择高潮/结局相关的情节点
            return remaining_points[-2:] if remaining_points else []
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析JSON响应."""
        try:
            # 清理响应文本
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            return json.loads(cleaned_response)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            raise
    
    def get_current_state_summary(self, state: ProgressiveOutlineState) -> str:
        """获取当前状态摘要."""
        completed_chapters = len(state.detailed_chapters)
        total_chapters = state.rough_outline.estimated_chapters
        
        summary = f"""
当前大纲状态:
- 世界观: 已完成（{state.world_building.setting}）
- 整体结构: 已完成（{state.rough_outline.story_arc}）
- 详细章节: {completed_chapters}/{total_chapters}
- 已完成情节点: {len(state.completed_plot_points)}个
"""
        return summary.strip()