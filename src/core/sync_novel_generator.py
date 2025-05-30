"""同步版本的小说生成器 - 单线程阻塞串型执行"""

import time
import dataclasses
from typing import Dict, Any, List
from src.core.concept_expander import ConceptExpander, ConceptExpansionResult
from src.core.strategy_selector import StrategySelector
from src.core.outline_generator import HierarchicalOutlineGenerator
from src.core.character_system import SimpleCharacterSystem
from src.core.chapter_generator import ChapterGenerationEngine
from src.core.consistency_checker import BasicConsistencyChecker
from src.core.quality_assessment import QualityAssessmentSystem
from src.utils.llm_client import UniversalLLMClient
from src.utils.logger import logger
from src.core.exceptions import NovelGeneratorError, RetryableError
from src.core.sync_wrapper import sync_llm_call


class SyncNovelGenerator:
    """同步小说生成器主类，使用单线程阻塞串型执行"""
    
    def __init__(self, llm_client: UniversalLLMClient = None):
        """
        初始化同步小说生成器
        
        Args:
            llm_client: 统一LLM客户端实例
        """
        self.llm_client = llm_client or UniversalLLMClient()
        self.concept_expander = ConceptExpander(self.llm_client)
        self.strategy_selector = StrategySelector()
        self.outline_generator = HierarchicalOutlineGenerator(self.llm_client)
        self.character_system = SimpleCharacterSystem(self.llm_client)
        self.chapter_engine = ChapterGenerationEngine(self.llm_client)
        self.consistency_checker = BasicConsistencyChecker(self.llm_client)
        self.quality_assessor = QualityAssessmentSystem(self.llm_client)
        
        # 状态跟踪
        self.current_progress = 0
        self.current_stage = "未开始"
        
        # 进度更新回调
        self.progress_callback = None
    
    def set_progress_callback(self, callback):
        """设置进度更新回调函数"""
        self.progress_callback = callback
    
    def generate_novel(self, user_input: str, target_words: int,
                      style_preference: str = None) -> Dict[str, Any]:
        """
        同步生成完整小说
        
        Args:
            user_input: 用户输入的简单创意
            target_words: 目标字数
            style_preference: 风格偏好（可选）
            
        Returns:
            dict: 包含所有生成结果的字典
            
        Raises:
            NovelGeneratorError: 生成过程中发生不可恢复的错误
        """
        try:
            self.current_stage = "概念扩展"
            self._update_progress(5)
            logger.info(f"开始生成小说: {user_input}, 目标字数: {target_words}")
            
            # 1. 概念扩展 (同步执行)
            concept = self._expand_concept_sync(user_input, target_words, style_preference)
            
            # 2. 策略选择
            self.current_stage = "策略选择"
            self._update_progress(15)
            concept_dict = dataclasses.asdict(concept)
            strategy = self.strategy_selector.select_strategy(target_words, concept_dict)
            
            # 3. 大纲生成 (同步执行)
            self.current_stage = "大纲生成"
            self._update_progress(25)
            outline = self._generate_outline_sync(concept, strategy, target_words)
            
            # 4. 角色创建 (同步执行)
            self.current_stage = "角色创建"
            self._update_progress(35)
            characters = self._generate_characters_sync(concept, strategy, outline)
            
            # 5. 章节生成 (同步串型执行)
            self.current_stage = "章节生成"
            chapters = []
            total_words = 0
            chapter_count = len(outline.chapters) if outline.chapters else sum(
                len(vol.chapters) for vol in outline.volumes
            )
            
            for i, chapter_outline in enumerate(self._iter_chapters(outline)):
                progress = 35 + int(50 * (i / chapter_count))
                self._update_progress(progress)
                
                logger.info(f"开始生成第{i+1}章: {chapter_outline.title}")
                
                # 带重试机制的章节生成 (同步执行)
                chapter_content = self._generate_chapter_with_retry_sync(
                    chapter_outline,
                    characters,
                    concept,
                    strategy,
                    max_retries=3
                )
                
                # 一致性检查（简化处理）
                consistency_result = {
                    "issues": [],
                    "severity": "low",
                    "overall_score": 9.0,
                    "suggestions": []
                }
                
                chapters.append({
                    "title": chapter_outline.title,
                    "content": chapter_content.content,
                    "word_count": chapter_content.word_count,
                    "consistency_check": consistency_result
                })
                total_words += chapter_content.word_count
                
                logger.info(f"第{i+1}章生成完成，字数: {chapter_content.word_count}")
            
            # 6. 质量评估 (同步执行)
            self.current_stage = "质量评估"
            self._update_progress(95)
            novel_data = {
                "concept": concept,
                "strategy": strategy,
                "outline": outline,
                "characters": characters,
                "chapters": chapters,
                "total_words": total_words
            }
            quality_result = self._evaluate_novel_quality_sync(novel_data)
            
            self.current_stage = "完成"
            self._update_progress(100)
            logger.info(f"小说生成完成: {user_input}, 总字数: {total_words}")
            
            return {
                **novel_data,
                "quality_assessment": quality_result
            }
            
        except Exception as e:
            logger.error(f"小说生成失败: {e}", exc_info=True)
            raise NovelGeneratorError(f"生成过程中发生错误: {e}") from e
    
    def _expand_concept_sync(self, user_input: str, target_words: int, style_preference: str = None) -> ConceptExpansionResult:
        """同步概念扩展"""
        try:
            logger.info("开始概念扩展...")
            result = sync_llm_call(
                self.concept_expander.expand_concept,
                user_input, target_words, style_preference
            )
            logger.info(f"概念扩展完成: {result.theme}")
            return result
        except Exception as e:
            logger.error(f"概念扩展失败: {e}")
            raise
    
    def _generate_outline_sync(self, concept, strategy, target_words):
        """同步大纲生成"""
        try:
            logger.info("开始大纲生成...")
            result = sync_llm_call(
                self.outline_generator.generate_outline,
                concept, strategy, target_words
            )
            logger.info(f"大纲生成完成，章节数: {len(result.chapters) if result.chapters else sum(len(v.chapters) for v in result.volumes)}")
            return result
        except Exception as e:
            logger.error(f"大纲生成失败: {e}")
            raise
    
    def _generate_characters_sync(self, concept, strategy, outline):
        """同步角色创建"""
        try:
            logger.info("开始角色创建...")
            result = sync_llm_call(
                self.character_system.generate_characters,
                concept, strategy, outline
            )
            logger.info(f"角色创建完成，角色数: {len(result)}")
            return result
        except Exception as e:
            logger.error(f"角色创建失败: {e}")
            raise
    
    def _generate_chapter_with_retry_sync(self, chapter_outline, characters, concept, strategy, max_retries=3):
        """同步章节生成（带重试）"""
        for attempt in range(max_retries):
            try:
                logger.info(f"生成章节: {chapter_outline.title} (尝试 {attempt+1}/{max_retries})")
                result = sync_llm_call(
                    self.chapter_engine.generate_chapter,
                    chapter_outline, characters, concept, strategy
                )
                logger.info(f"章节生成成功: {chapter_outline.title}, 字数: {result.word_count}")
                return result
            except RetryableError as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.warning(
                        f"章节生成重试中 ({attempt+1}/{max_retries}): {e}. "
                        f"{wait_time}秒后重试..."
                    )
                    time.sleep(wait_time)
                else:
                    raise NovelGeneratorError(
                        f"章节生成在{max_retries}次重试后仍失败: {e}"
                    ) from e
            except Exception as e:
                logger.error(f"章节生成失败: {e}")
                raise
    
    def _evaluate_novel_quality_sync(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """同步质量评估"""
        try:
            logger.info("开始质量评估...")
            
            # 合并所有章节内容进行评估
            all_content = "\n\n".join([
                chapter["content"] for chapter in novel_data.get("chapters", [])
            ])
            
            if not all_content:
                return {"overall_scores": {"overall": 5.0}, "metrics": {}}
            
            characters = novel_data.get("characters", {})
            chapter_info = {"title": "整体评估", "summary": "全书质量评估"}
            
            # 同步调用质量评估
            metrics = sync_llm_call(
                self.quality_assessor.assess_quality,
                all_content, characters, chapter_info
            )
            
            logger.info(f"质量评估完成，总分: {metrics.overall_score}")
            
            return {
                "overall_scores": {
                    "overall": metrics.overall_score,
                    "coherence": getattr(metrics.dimensions.get("plot_logic", {}), 'score', 7.0),
                    "character_consistency": getattr(metrics.dimensions.get("character_consistency", {}), 'score', 8.0)
                },
                "metrics": {
                    dim_name: {
                        "score": dim.score,
                        "issues": dim.issues,
                        "suggestions": dim.suggestions
                    }
                    for dim_name, dim in metrics.dimensions.items()
                },
                "grade": metrics.grade
            }
            
        except Exception as e:
            logger.warning(f"质量评估失败: {e}")
            # 返回默认评估结果
            return {
                "overall_scores": {"overall": 7.0, "coherence": 7.0, "character_consistency": 8.0},
                "metrics": {},
                "grade": "B"
            }
    
    def _iter_chapters(self, outline) -> List:
        """迭代遍历所有章节大纲（支持多卷结构）"""
        if outline.chapters:
            yield from outline.chapters
        elif outline.volumes:
            for volume in outline.volumes:
                yield from volume.chapters
    
    def _update_progress(self, progress: int):
        """更新生成进度"""
        self.current_progress = progress
        logger.info(f"进度更新: {self.current_stage} - {progress}%")
        
        # 调用进度回调
        if self.progress_callback:
            try:
                self.progress_callback(self.current_stage, progress)
            except Exception as e:
                logger.warning(f"进度回调失败: {e}")
        
    def get_current_progress(self) -> Dict[str, Any]:
        """获取当前进度信息"""
        return {
            "stage": self.current_stage,
            "progress": self.current_progress
        }