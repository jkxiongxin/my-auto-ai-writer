"""分层大纲生成器模块，生成多层级的小说大纲结构."""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from src.core.concept_expander import ConceptExpansionResult
from src.core.strategy_selector import GenerationStrategy
from src.utils.llm_client import UniversalLLMClient

logger = logging.getLogger(__name__)


class OutlineGenerationError(Exception):
    """大纲生成异常."""
    pass


@dataclass
class OutlineNode:
    """大纲节点基础数据类."""
    title: str
    summary: str
    level: int = 1
    parent_id: Optional[str] = None
    children: List['OutlineNode'] = field(default_factory=list)


@dataclass
class SceneOutline:
    """场景大纲数据类."""
    name: str
    description: str
    characters: List[str] = field(default_factory=list)
    location: Optional[str] = None
    estimated_word_count: int = 500


@dataclass
class ChapterOutline:
    """章节大纲数据类."""
    number: int
    title: str
    summary: str
    key_events: List[str]
    estimated_word_count: int
    scenes: List[SceneOutline] = field(default_factory=list)
    volume_number: Optional[int] = None
    act_number: Optional[int] = None
    narrative_purpose: Optional[str] = None  # 叙事目的
    is_final_chapter: bool = False  # 是否为最后一章


@dataclass
class VolumeOutline:
    """卷大纲数据类."""
    number: int
    title: str
    summary: str
    theme: str
    chapters: List[ChapterOutline]
    estimated_word_count: int


@dataclass
class NovelOutline:
    """小说大纲数据类."""
    structure_type: str
    theme: str
    genre: str
    chapters: List[ChapterOutline]
    volumes: List[VolumeOutline] = field(default_factory=list)
    total_estimated_words: int = 0
    plot_points: List[str] = field(default_factory=list)
    character_arcs: Dict[str, str] = field(default_factory=dict)
    world_building_notes: List[str] = field(default_factory=list)


class HierarchicalOutlineGenerator:
    """分层大纲生成器，生成多层级的小说大纲结构.
    
    根据概念扩展结果和生成策略，创建详细的分层大纲，
    包括卷、章节、场景等多个层级的结构化内容。
    
    Attributes:
        llm_client: LLM客户端实例
        max_retries: 最大重试次数
        timeout: 超时时间
    """
    
    def __init__(self, llm_client: UniversalLLMClient, max_retries: int = 3, timeout: int = 120):
        """初始化分层大纲生成器.
        
        Args:
            llm_client: 统一LLM客户端实例
            max_retries: 最大重试次数
            timeout: 请求超时时间
            
        Raises:
            ValueError: 当llm_client为None时抛出
        """
        if llm_client is None:
            raise ValueError("llm_client不能为None")
        
        self.llm_client = llm_client
        self.max_retries = max_retries
        self.timeout = timeout
        
        # 配置不同结构类型的参数
        self.structure_configs = {
            "单线叙述": {"acts": 1, "distribution": "balanced"},
            "三幕剧": {"acts": 3, "distribution": "crescendo"},
            "五幕剧": {"acts": 5, "distribution": "pyramid"},
            "多卷本结构": {"acts": 3, "distribution": "epic"},
            "史诗结构": {"acts": 5, "distribution": "epic"}
        }
        
        logger.info("分层大纲生成器初始化完成")
    
    async def generate_outline(
        self,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy,
        target_words: int
    ) -> NovelOutline:
        """生成分层大纲.
        
        Args:
            concept: 概念扩展结果
            strategy: 生成策略
            target_words: 目标字数
            
        Returns:
            NovelOutline: 完整的小说大纲
            
        Raises:
            OutlineGenerationError: 当大纲生成失败时抛出
        """
        # 输入验证
        if concept is None:
            raise OutlineGenerationError("概念信息不能为空")
        
        if strategy is None:
            raise OutlineGenerationError("策略信息不能为空")
        
        if not (1000 <= target_words <= 10000000):
            raise OutlineGenerationError("目标字数必须在1000-1000万之间")
        
        logger.info(f"开始生成大纲: structure={strategy.structure_type}, words={target_words}")
        
        try:
            # 1. 生成章节大纲
            chapters = await self._generate_chapter_outlines(concept, strategy, target_words)
            
            # 2. 创建基础大纲结构
            outline = NovelOutline(
                structure_type=strategy.structure_type,
                theme=concept.theme,
                genre=concept.genre,
                chapters=chapters,
                total_estimated_words=sum(chapter.estimated_word_count for chapter in chapters)
            )
            
            # 3. 如果是多卷本结构，生成卷结构
            if strategy.volume_count and strategy.volume_count > 1:
                outline.volumes = self._organize_chapters_into_volumes(chapters, strategy.volume_count)
            
            # 4. 添加情节要点和角色弧线
            outline.plot_points = self._extract_plot_points(chapters)
            outline.character_arcs = self._generate_character_arcs(concept, chapters)
            
            # 5. 添加世界构建注释
            if strategy.world_building_depth in ["medium", "high"]:
                outline.world_building_notes = self._generate_world_building_notes(concept, strategy)
            
            # 6. 验证大纲结构
            if not self._validate_outline_structure(outline, strategy):
                raise OutlineGenerationError("生成的大纲结构验证失败")
            
            logger.info(f"大纲生成完成: {len(outline.chapters)}章, {outline.total_estimated_words}字")
            return outline
            
        except Exception as e:
            logger.error(f"大纲生成失败: {e}", exc_info=True)
            raise OutlineGenerationError(f"大纲生成失败: {e}")
    
    async def _generate_chapter_outlines(
        self,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy,
        target_words: int
    ) -> List[ChapterOutline]:
        """生成章节大纲.
        
        Args:
            concept: 概念扩展结果
            strategy: 生成策略
            target_words: 目标字数
            
        Returns:
            章节大纲列表
        """
        # 构建提示词
        prompt = self._build_outline_prompt(concept, strategy, target_words)
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                # 调用LLM生成大纲（带日志记录）
                response = await asyncio.wait_for(
                    self.llm_client.generate(
                        prompt,
                        step_type="outline_generation",
                        step_name="大纲生成",
                        log_generation=True
                    ),
                    timeout=self.timeout
                )
                
                # 解析响应
                chapters = self._parse_outline_response(response)
                
                # 分配字数
                word_distribution = self._calculate_word_distribution(
                    target_words, 
                    len(chapters), 
                    self.structure_configs.get(strategy.structure_type, {}).get("distribution", "balanced")
                )
                
                # 更新章节字数和其他信息
                for i, chapter in enumerate(chapters):
                    chapter.estimated_word_count = word_distribution[i]
                    chapter.act_number = self._determine_act_number(i, len(chapters), strategy.structure_type)
                    chapter.narrative_purpose = self._determine_narrative_purpose(i, len(chapters), strategy.structure_type)
                    # 标识最后一章
                    chapter.is_final_chapter = (i == len(chapters) - 1)
                
                return chapters
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"第{attempt + 1}次大纲生成尝试失败: {e}")
                if attempt == self.max_retries - 1:
                    raise OutlineGenerationError(f"LLM响应格式无效: {e}")
                await asyncio.sleep(2)
        
        raise OutlineGenerationError("章节大纲生成失败")
    
    def _build_outline_prompt(
        self,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy,
        target_words: int
    ) -> str:
        """构建大纲生成提示词.
        
        Args:
            concept: 概念扩展结果
            strategy: 生成策略
            target_words: 目标字数
            
        Returns:
            完整的提示词字符串
        """
        # 根据目标字数确定复杂度级别和情节密度指导
        complexity_guidance = self._build_complexity_guidance(target_words, strategy)
        
        prompt = f"""
请为以下小说概念生成详细的章节大纲。

概念信息:
- 主题: {concept.theme}
- 类型: {concept.genre}
- 主要冲突: {concept.main_conflict}
- 世界设定: {concept.world_type}
- 基调: {concept.tone}
- 核心信息: {concept.core_message or '探索人性的复杂'}

策略参数:
- 结构类型: {strategy.structure_type}
- 目标章节数: {strategy.chapter_count}
- 角色深度: {strategy.character_depth}
- 叙事节奏: {strategy.pacing}
- 总字数: {target_words}

{complexity_guidance}

请生成 {strategy.chapter_count} 个章节的详细大纲，以JSON格式返回：

{{
    "chapters": [
        {{
            "number": 1,
            "title": "章节标题",
            "summary": "章节摘要（100-200字）",
            "key_events": ["关键事件1", "关键事件2", "关键事件3"],
            "word_count": 预估字数,
            "scenes": [
                {{
                    "name": "场景名称",
                    "description": "场景描述"
                }}
            ]
        }}
    ]
}}

要求:
1. 遵循{strategy.structure_type}的经典结构
2. 确保情节连贯性和逻辑性
3. 每个章节都要有明确的叙事目的
4. 关键事件要推动主线情节发展
5. 场景设置要符合世界观设定
6. 严格按照复杂度指导控制情节密度和支线数量
7. 响应必须是有效的JSON格式
"""
        
        return prompt.strip()
    
    def _build_complexity_guidance(self, target_words: int, strategy: GenerationStrategy) -> str:
        """构建复杂度指导信息.
        
        Args:
            target_words: 目标字数
            strategy: 生成策略
            
        Returns:
            复杂度指导文本
        """
        guidance_parts = []
        guidance_parts.append("情节复杂度指导:")
        
        # 根据正确的字数分级确定复杂度级别
        if target_words <= 10000:
            # 短篇小说 (1-1万字)
            guidance_parts.append("- 复杂度级别: 简洁单线")
            guidance_parts.append("- 主线情节: 专注于一条清晰的主线，避免复杂的支线")
            guidance_parts.append("- 角色数量: 限制在2-4个主要角色")
            guidance_parts.append("- 关键事件: 每章1-2个关键事件，直接推进主线")
            guidance_parts.append("- 冲突类型: 专注于一个核心冲突")
            guidance_parts.append("- 场景设置: 每章1-2个主要场景，保持简洁")
            
        elif target_words <= 100000:
            # 中篇小说 (1万-10万字)
            guidance_parts.append("- 复杂度级别: 中等多线")
            guidance_parts.append("- 主线情节: 一条主线 + 1-2条支线")
            guidance_parts.append("- 角色数量: 4-8个角色，重点发展主要角色")
            guidance_parts.append("- 关键事件: 每章2-3个关键事件")
            guidance_parts.append("- 冲突类型: 一个主要冲突 + 1-2个次要冲突")
            guidance_parts.append("- 场景设置: 每章2-3个场景")
            guidance_parts.append("- 情节交织: 支线可以与主线产生交集")
            
        elif target_words <= 2000000:
            # 长篇小说 (10万-200万字)
            guidance_parts.append("- 复杂度级别: 复杂多线")
            guidance_parts.append("- 主线情节: 一条主线 + 3-5条支线")
            guidance_parts.append("- 角色数量: 8-15个角色，包括详细的配角弧线")
            guidance_parts.append("- 关键事件: 每章3-4个关键事件")
            guidance_parts.append("- 冲突类型: 多层次冲突系统")
            guidance_parts.append("- 场景设置: 每章2-4个场景")
            guidance_parts.append("- 情节交织: 支线之间相互影响")
            guidance_parts.append("- 世界构建: 包含复杂的背景设定")
            
        elif target_words <= 5000000:
            # 超长篇小说 (200万-500万字)
            guidance_parts.append("- 复杂度级别: 超复杂多线")
            guidance_parts.append("- 主线情节: 2-3条并行主线 + 多条支线")
            guidance_parts.append("- 角色数量: 15-30个角色，多个POV角色")
            guidance_parts.append("- 关键事件: 每章4-5个关键事件")
            guidance_parts.append("- 冲突类型: 多维度冲突网络")
            guidance_parts.append("- 场景设置: 每章3-5个场景")
            guidance_parts.append("- 情节交织: 复杂的情节网络")
            guidance_parts.append("- 世界构建: 详细的世界设定和历史背景")
            
        else:
            # 史诗小说 (500万-1000万字)
            guidance_parts.append("- 复杂度级别: 史诗级复杂")
            guidance_parts.append("- 主线情节: 多条并行主线 + 众多支线")
            guidance_parts.append("- 角色数量: 30+个角色，多个POV角色，多代传承")
            guidance_parts.append("- 关键事件: 每章5-6个关键事件")
            guidance_parts.append("- 冲突类型: 跨时代的多维度冲突网络")
            guidance_parts.append("- 场景设置: 每章4-6个场景")
            guidance_parts.append("- 情节交织: 史诗级的情节网络")
            guidance_parts.append("- 世界构建: 完整的世界观和多重时空设定")
        
        # 根据节奏类型添加额外指导
        if strategy.pacing == "fast":
            guidance_parts.append("- 节奏要求: 快节奏，事件紧凑，减少铺垫内容")
        elif strategy.pacing == "moderate":
            guidance_parts.append("- 节奏要求: 中等节奏，平衡动作与发展")
        elif strategy.pacing == "slow":
            guidance_parts.append("- 节奏要求: 慢节奏，重视角色发展和世界构建")
        elif strategy.pacing == "epic":
            guidance_parts.append("- 节奏要求: 史诗节奏，宏大叙事，多线程推进")
        
        # 根据角色深度添加指导
        if strategy.character_depth == "basic":
            guidance_parts.append("- 角色发展: 基础角色塑造，关注主要特征")
        elif strategy.character_depth == "medium":
            guidance_parts.append("- 角色发展: 中等深度，包含性格成长")
        elif strategy.character_depth == "deep":
            guidance_parts.append("- 角色发展: 深度角色弧线，复杂的内心世界")
        
        return "\n".join(guidance_parts)
    
    def _parse_outline_response(self, response: str) -> List[ChapterOutline]:
        """解析LLM大纲响应.
        
        Args:
            response: LLM的原始响应
            
        Returns:
            章节大纲列表
            
        Raises:
            OutlineGenerationError: 当解析失败时抛出
        """
        try:
            # 清理响应文本
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # 解析JSON
            data = json.loads(cleaned_response)
            
            if "chapters" not in data:
                raise KeyError("响应中缺少chapters字段")
            
            chapters = []
            for chapter_data in data["chapters"]:
                # 解析场景
                scenes = []
                for scene_data in chapter_data.get("scenes", []):
                    scene = SceneOutline(
                        name=scene_data.get("name", ""),
                        description=scene_data.get("description", "")
                    )
                    scenes.append(scene)
                
                # 创建章节大纲
                chapter = ChapterOutline(
                    number=chapter_data.get("number", 0),
                    title=chapter_data.get("title", ""),
                    summary=chapter_data.get("summary", ""),
                    key_events=chapter_data.get("key_events", []),
                    estimated_word_count=chapter_data.get("word_count", 0),
                    scenes=scenes
                )
                chapters.append(chapter)
            
            return chapters
            
        except json.JSONDecodeError as e:
            raise OutlineGenerationError(f"JSON解析失败: {e}")
        except KeyError as e:
            raise OutlineGenerationError(f"响应数据格式错误: {e}")
    
    def _calculate_word_distribution(
        self,
        total_words: int,
        chapter_count: int,
        distribution_type: str
    ) -> List[int]:
        """计算章节字数分配.
        
        Args:
            total_words: 总字数
            chapter_count: 章节数量
            distribution_type: 分配类型
            
        Returns:
            每个章节的字数列表
        """
        if distribution_type == "balanced":
            # 均衡分配
            base_words = total_words // chapter_count
            remainder = total_words % chapter_count
            distribution = [base_words] * chapter_count
            # 余数分配给前几章
            for i in range(remainder):
                distribution[i] += 1
                
        elif distribution_type == "crescendo":
            # 渐强分配（越来越多）
            weights = [i + 1 for i in range(chapter_count)]
            total_weight = sum(weights)
            distribution = [int(total_words * weight / total_weight) for weight in weights]
            
        elif distribution_type == "pyramid":
            # 金字塔分配（中间最多）
            mid = chapter_count // 2
            weights = []
            for i in range(chapter_count):
                distance_from_mid = abs(i - mid)
                weight = chapter_count - distance_from_mid
                weights.append(weight)
            total_weight = sum(weights)
            distribution = [int(total_words * weight / total_weight) for weight in weights]
            
        elif distribution_type == "epic":
            # 史诗分配（开头和结尾重，中间轻）
            weights = []
            for i in range(chapter_count):
                if i < chapter_count * 0.2 or i >= chapter_count * 0.8:
                    weight = 1.5  # 开头和结尾权重高
                else:
                    weight = 1.0  # 中间权重正常
                weights.append(weight)
            total_weight = sum(weights)
            distribution = [int(total_words * weight / total_weight) for weight in weights]
            
        else:
            # 默认均衡分配
            base_words = total_words // chapter_count
            distribution = [base_words] * chapter_count
        
        # 确保总和等于目标字数
        current_total = sum(distribution)
        if current_total != total_words:
            diff = total_words - current_total
            distribution[0] += diff
        
        return distribution
    
    def _determine_act_number(self, chapter_index: int, total_chapters: int, structure_type: str) -> int:
        """确定章节所属的幕数.
        
        Args:
            chapter_index: 章节索引（从0开始）
            total_chapters: 总章节数
            structure_type: 结构类型
            
        Returns:
            幕数
        """
        if structure_type == "三幕剧":
            if chapter_index < total_chapters * 0.25:
                return 1
            elif chapter_index < total_chapters * 0.75:
                return 2
            else:
                return 3
                
        elif structure_type == "五幕剧":
            act_size = total_chapters / 5
            return min(5, int(chapter_index / act_size) + 1)
            
        else:
            return 1
    
    def _determine_narrative_purpose(self, chapter_index: int, total_chapters: int, structure_type: str) -> str:
        """确定章节的叙事目的.
        
        Args:
            chapter_index: 章节索引
            total_chapters: 总章节数
            structure_type: 结构类型
            
        Returns:
            叙事目的描述
        """
        progress = chapter_index / (total_chapters - 1) if total_chapters > 1 else 0
        
        if progress < 0.1:
            return "开场引入"
        elif progress < 0.25:
            return "世界构建"
        elif progress < 0.5:
            return "情节发展"
        elif progress < 0.75:
            return "冲突升级"
        elif progress < 0.9:
            return "高潮部分"
        else:
            return "结局收尾"
    
    def _organize_chapters_into_volumes(self, chapters: List[ChapterOutline], volume_count: int) -> List[VolumeOutline]:
        """将章节组织成卷结构.
        
        Args:
            chapters: 章节列表
            volume_count: 卷数
            
        Returns:
            卷大纲列表
        """
        chapters_per_volume = len(chapters) // volume_count
        remainder = len(chapters) % volume_count
        
        volumes = []
        chapter_index = 0
        
        for vol_num in range(volume_count):
            # 计算当前卷的章节数
            current_volume_chapters = chapters_per_volume
            if vol_num < remainder:
                current_volume_chapters += 1
            
            # 提取当前卷的章节
            volume_chapters = chapters[chapter_index:chapter_index + current_volume_chapters]
            
            # 更新章节的卷编号
            for chapter in volume_chapters:
                chapter.volume_number = vol_num + 1
            
            # 创建卷大纲
            volume = VolumeOutline(
                number=vol_num + 1,
                title=f"第{vol_num + 1}卷",
                summary=f"第{vol_num + 1}卷的故事内容",
                theme=f"卷{vol_num + 1}主题",
                chapters=volume_chapters,
                estimated_word_count=sum(ch.estimated_word_count for ch in volume_chapters)
            )
            volumes.append(volume)
            
            chapter_index += current_volume_chapters
        
        return volumes
    
    def _extract_plot_points(self, chapters: List[ChapterOutline]) -> List[str]:
        """提取主要情节点.
        
        Args:
            chapters: 章节列表
            
        Returns:
            情节点列表
        """
        plot_points = []
        for chapter in chapters:
            if chapter.key_events:
                # 取每章的第一个关键事件作为情节点
                plot_points.append(f"第{chapter.number}章: {chapter.key_events[0]}")
        return plot_points
    
    def _generate_character_arcs(self, concept: ConceptExpansionResult, chapters: List[ChapterOutline]) -> Dict[str, str]:
        """生成角色弧线.
        
        Args:
            concept: 概念扩展结果
            chapters: 章节列表
            
        Returns:
            角色弧线字典
        """
        character_arcs = {}
        
        # 主角弧线
        if concept.protagonist_type:
            character_arcs["主角"] = f"{concept.protagonist_type}的成长历程"
        
        # 根据章节内容推断其他角色
        character_arcs["导师"] = "指导主角成长的智者"
        character_arcs["反派"] = "制造冲突的对手"
        
        return character_arcs
    
    def _generate_world_building_notes(self, concept: ConceptExpansionResult, strategy: GenerationStrategy) -> List[str]:
        """生成世界构建注释.
        
        Args:
            concept: 概念扩展结果
            strategy: 生成策略
            
        Returns:
            世界构建注释列表
        """
        notes = []
        
        notes.append(f"世界类型: {concept.world_type}")
        notes.append(f"基本设定: {concept.setting or '待详细设定'}")
        
        if strategy.magic_system:
            notes.append(f"魔法系统: {strategy.magic_system}")
        
        if strategy.tech_level:
            notes.append(f"科技水平: {strategy.tech_level}")
        
        if strategy.genre_specific_elements:
            notes.append(f"类型元素: {', '.join(strategy.genre_specific_elements)}")
        
        return notes
    
    def _validate_outline_structure(self, outline: NovelOutline, strategy: GenerationStrategy) -> bool:
        """验证大纲结构有效性.
        
        Args:
            outline: 小说大纲
            strategy: 生成策略
            
        Returns:
            验证是否通过
        """
        try:
            # 检查基本字段
            if not outline.structure_type or not outline.theme or not outline.genre:
                return False
            
            # 检查章节
            if not outline.chapters:
                return False
            
            # 检查章节编号连续性
            expected_numbers = list(range(1, len(outline.chapters) + 1))
            actual_numbers = [ch.number for ch in outline.chapters]
            if actual_numbers != expected_numbers:
                return False
            
            # 检查字数合理性
            if outline.total_estimated_words <= 0:
                return False
            
            # 检查多卷本结构
            if strategy.volume_count and strategy.volume_count > 1:
                if len(outline.volumes) != strategy.volume_count:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"大纲验证出错: {e}")
            return False
    
    def _create_outline_node(self, node_data: Dict[str, Any]) -> OutlineNode:
        """创建大纲节点.
        
        Args:
            node_data: 节点数据
            
        Returns:
            大纲节点对象
        """
        return OutlineNode(
            title=node_data.get("title", ""),
            summary=node_data.get("summary", ""),
            level=node_data.get("level", 1),
            parent_id=node_data.get("parent_id")
        )