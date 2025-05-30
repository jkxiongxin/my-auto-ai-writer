"""策略选择器模块，根据目标字数和概念选择合适的生成策略."""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class StrategySelectionError(Exception):
    """策略选择异常."""
    pass


@dataclass
class GenerationStrategy:
    """生成策略数据类."""
    
    structure_type: str  # 结构类型：三幕剧、五幕剧、多卷本结构等
    chapter_count: int   # 章节数量
    character_depth: str # 角色深度：basic, medium, deep
    pacing: str          # 节奏：fast, moderate, slow, epic
    
    # 可选字段
    volume_count: Optional[int] = None              # 卷数（多卷本结构）
    world_building_depth: str = "medium"            # 世界构建深度
    magic_system: Optional[str] = None              # 魔法系统（奇幻）
    tech_level: Optional[str] = None                # 科技水平（科幻）
    genre_specific_elements: List[str] = field(default_factory=list)  # 类型特定元素
    
    # 计算字段
    words_per_chapter: Optional[int] = None         # 每章字数
    estimated_scenes: Optional[int] = None          # 预估场景数
    complexity_score: float = 0.0                  # 复杂度分数


class StrategySelector:
    """策略选择器，根据目标字数和概念信息选择最佳生成策略.
    
    负责分析用户的目标字数和概念信息，选择最适合的小说结构、
    章节分布、角色深度和叙事节奏等生成策略参数。
    
    Attributes:
        word_thresholds: 字数阈值配置
        structure_mappings: 结构映射配置
        genre_adjustments: 类型调整配置
    """
    
    def __init__(self):
        """初始化策略选择器."""
        # 字数阈值配置 - 按照正确的小说分级标准
        self.word_thresholds = {
            "short": (1, 10000),          # 短篇小说: 1-1万字
            "medium": (10001, 100000),    # 中篇小说: 1万-10万字
            "long": (100001, 2000000),    # 长篇小说: 10万-200万字
            "super_long": (2000001, 5000000), # 超长篇小说: 200万-500万字
            "epic": (5000001, 10000000),  # 史诗小说: 500万-1000万字
        }
        
        # 结构映射配置
        self.structure_mappings = {
            "short": "三幕剧",           # 短篇小说: 1-1万字
            "medium": "五幕剧",          # 中篇小说: 1万-10万字
            "long": "多卷本结构",        # 长篇小说: 10万-200万字
            "super_long": "史诗结构",    # 超长篇小说: 200万-500万字
            "epic": "史诗结构"           # 史诗小说: 500万-1000万字
        }
        
        # 类型调整配置
        self.genre_adjustments = {
            "奇幻": {
                "magic_system": "detailed",
                "world_building_depth": "high",
                "elements": ["魔法", "异世界", "种族"]
            },
            "科幻": {
                "tech_level": "advanced",
                "world_building_depth": "high", 
                "elements": ["科技", "未来", "太空"]
            },
            "悬疑": {
                "world_building_depth": "medium",
                "elements": ["推理", "线索", "悬念"]
            },
            "现实主义": {
                "world_building_depth": "low",
                "elements": ["现实", "情感", "社会"]
            }
        }
        
        logger.info("策略选择器初始化完成")
    
    def select_strategy(self, target_words: int, concept: Dict[str, Any]) -> GenerationStrategy:
        """选择生成策略.
        
        Args:
            target_words: 目标字数
            concept: 概念信息字典
            
        Returns:
            GenerationStrategy: 选择的生成策略
            
        Raises:
            StrategySelectionError: 当策略选择失败时抛出
        """
        # 输入验证 - 更新为支持更大字数范围
        if not (1000 <= target_words <= 10000000):
            raise StrategySelectionError("目标字数必须在1000-1000万之间")
        
        if not concept:
            raise StrategySelectionError("概念信息不能为空")
        
        logger.info(f"开始选择策略: target_words={target_words}, genre={concept.get('genre', 'unknown')}")
        
        try:
            # 1. 确定小说类型（长度）
            novel_type = self._determine_novel_type(target_words)
            
            # 2. 选择基础结构
            structure_type = self.structure_mappings[novel_type]
            
            # 3. 计算章节数量
            chapter_count = self._calculate_chapter_count(target_words, structure_type)
            
            # 4. 确定角色深度
            character_depth = self._determine_character_depth(target_words)
            
            # 5. 确定叙事节奏
            pacing = self._determine_pacing(target_words)
            
            # 6. 创建基础策略
            base_strategy = GenerationStrategy(
                structure_type=structure_type,
                chapter_count=chapter_count,
                character_depth=character_depth,
                pacing=pacing
            )
            
            # 7. 根据类型调整策略
            adjusted_strategy = self._adjust_for_genre(base_strategy, concept)
            
            # 8. 计算附加参数
            self._calculate_additional_parameters(adjusted_strategy, target_words)
            
            # 9. 验证策略
            if not self._validate_strategy(adjusted_strategy):
                raise StrategySelectionError("生成的策略验证失败")
            
            logger.info(f"策略选择完成: structure={adjusted_strategy.structure_type}, chapters={adjusted_strategy.chapter_count}")
            return adjusted_strategy
            
        except Exception as e:
            logger.error(f"策略选择失败: {e}", exc_info=True)
            raise StrategySelectionError(f"策略选择失败: {e}")
    
    def _determine_novel_type(self, target_words: int) -> str:
        """确定小说类型（基于字数）.
        
        Args:
            target_words: 目标字数
            
        Returns:
            小说类型字符串
        """
        for novel_type, (min_words, max_words) in self.word_thresholds.items():
            if min_words <= target_words <= max_words:
                return novel_type
        return "epic"  # 默认为史诗级别
    
    def _calculate_chapter_count(self, target_words: int, structure_type: str) -> int:
        """计算章节数量.
        
        根据新的字数分级标准和结构类型，智能计算合适的章节数量。
        确保每章字数在合理范围内，避免章节过短或过长。
        
        Args:
            target_words: 目标字数
            structure_type: 结构类型
            
        Returns:
            章节数量
        """
        # 基础章节数计算，按照正确的分级标准
        if target_words <= 10000:
            # 短篇小说 (1-1万字): 每章1500-2500字
            base_chapters = max(2, min(8, target_words // 2000))
        elif target_words <= 100000:
            # 中篇小说 (1万-10万字): 每章3000-5000字
            base_chapters = max(5, min(30, target_words // 4000))
        elif target_words <= 2000000:
            # 长篇小说 (10万-200万字): 每章4000-8000字
            base_chapters = max(20, min(400, target_words // 6000))
        elif target_words <= 5000000:
            # 超长篇小说 (200万-500万字): 每章6000-10000字
            base_chapters = max(250, min(800, target_words // 8000))
        else:
            # 史诗小说 (500万-1000万字): 每章8000-12000字
            base_chapters = max(500, min(1200, target_words // 10000))
        
        # 根据结构类型调整
        if structure_type == "三幕剧":
            # 三幕剧：确保章节数合理分配到三幕
            if target_words <= 10000:
                return max(3, min(base_chapters, 10))
            else:
                return max(6, min(base_chapters, 15))
        elif structure_type == "五幕剧":
            # 五幕剧：确保每幕有足够章节
            return max(8, min(base_chapters, 40))
        elif structure_type == "多卷本结构":
            # 多卷本：至少20章以支持多卷结构
            return max(20, min(base_chapters, 60))
        elif structure_type == "史诗结构":
            # 史诗结构：大量章节支持复杂叙事
            return max(30, base_chapters)
        else:
            return base_chapters
    
    def _determine_character_depth(self, target_words: int) -> str:
        """确定角色深度.
        
        Args:
            target_words: 目标字数
            
        Returns:
            角色深度级别
        """
        if target_words <= 10000:
            return "basic"      # 短篇小说：基础角色塑造
        elif target_words <= 100000:
            return "medium"     # 中篇小说：中等深度角色发展
        else:
            return "deep"       # 长篇及以上：深度角色弧线
    
    def _determine_pacing(self, target_words: int) -> str:
        """确定叙事节奏.
        
        Args:
            target_words: 目标字数
            
        Returns:
            节奏类型
        """
        if target_words <= 10000:
            return "fast"       # 短篇小说：快节奏
        elif target_words <= 100000:
            return "moderate"   # 中篇小说：中等节奏
        elif target_words <= 2000000:
            return "slow"       # 长篇小说：慢节奏
        else:
            return "epic"       # 超长篇/史诗：史诗节奏
    
    def _adjust_for_genre(self, strategy: GenerationStrategy, concept: Dict[str, Any]) -> GenerationStrategy:
        """根据类型调整策略.
        
        Args:
            strategy: 基础策略
            concept: 概念信息
            
        Returns:
            调整后的策略
        """
        genre = concept.get("genre", "现实主义")
        
        # 复制策略以避免修改原始对象
        adjusted_strategy = GenerationStrategy(
            structure_type=strategy.structure_type,
            chapter_count=strategy.chapter_count,
            character_depth=strategy.character_depth,
            pacing=strategy.pacing,
            volume_count=strategy.volume_count,
            world_building_depth=strategy.world_building_depth,
            magic_system=strategy.magic_system,
            tech_level=strategy.tech_level,
            genre_specific_elements=strategy.genre_specific_elements.copy()
        )
        
        # 根据类型进行调整
        if genre in self.genre_adjustments:
            adjustments = self.genre_adjustments[genre]
            
            # 设置特定属性
            if "magic_system" in adjustments:
                adjusted_strategy.magic_system = adjustments["magic_system"]
            
            if "tech_level" in adjustments:
                adjusted_strategy.tech_level = adjustments["tech_level"]
            
            if "world_building_depth" in adjustments:
                adjusted_strategy.world_building_depth = adjustments["world_building_depth"]
            
            # 添加类型特定元素
            if "elements" in adjustments:
                adjusted_strategy.genre_specific_elements.extend(adjustments["elements"])
        
        # 确保类型在特定元素中
        if genre not in adjusted_strategy.genre_specific_elements:
            adjusted_strategy.genre_specific_elements.append(genre)
        
        # 多卷本结构需要设置卷数
        if strategy.structure_type in ["多卷本结构", "史诗结构"]:
            adjusted_strategy.volume_count = self._calculate_volume_count(strategy.chapter_count)
        
        return adjusted_strategy
    
    def _calculate_volume_count(self, chapter_count: int) -> int:
        """计算卷数.
        
        Args:
            chapter_count: 章节数
            
        Returns:
            卷数
        """
        if chapter_count <= 15:
            return 2
        elif chapter_count <= 30:
            return 3
        else:
            return 4
    
    def _calculate_additional_parameters(self, strategy: GenerationStrategy, target_words: int) -> None:
        """计算附加参数.
        
        Args:
            strategy: 策略对象（会被修改）
            target_words: 目标字数
        """
        # 计算每章字数
        strategy.words_per_chapter = target_words // strategy.chapter_count
        
        # 估算场景数（每章1-3个场景）
        strategy.estimated_scenes = strategy.chapter_count * 2
        
        # 计算复杂度分数
        complexity_factors = [
            target_words / 100000,  # 字数因子
            strategy.chapter_count / 30,  # 章节因子
            {"basic": 0.3, "medium": 0.6, "deep": 1.0}[strategy.character_depth],  # 角色因子
            {"low": 0.3, "medium": 0.6, "high": 1.0}[strategy.world_building_depth],  # 世界构建因子
        ]
        
        strategy.complexity_score = min(1.0, sum(complexity_factors) / len(complexity_factors))
    
    def _validate_strategy(self, strategy: GenerationStrategy) -> bool:
        """验证策略有效性.
        
        Args:
            strategy: 待验证的策略
            
        Returns:
            验证是否通过
        """
        try:
            # 检查必需字段
            if not strategy.structure_type:
                return False
            
            if strategy.chapter_count <= 0:
                return False
            
            if strategy.character_depth not in ["basic", "medium", "deep"]:
                return False
            
            if strategy.pacing not in ["fast", "moderate", "slow", "epic"]:
                return False
            
            # 检查多卷本结构的卷数
            if strategy.structure_type in ["多卷本结构", "史诗结构"]:
                if not strategy.volume_count or strategy.volume_count < 2:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"策略验证出错: {e}")
            return False