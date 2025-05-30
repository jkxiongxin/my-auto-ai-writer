"""并发章节生成引擎 - 性能优化版本."""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
import logging
from dataclasses import dataclass

from src.core.chapter_generator import (
    ChapterGenerationEngine, ChapterContent, GenerationContext,
    ChapterGenerationError
)
from src.core.concept_expander import ConceptExpansionResult
from src.core.strategy_selector import GenerationStrategy
from src.core.outline_generator import ChapterOutline
from src.core.character_system import CharacterDatabase
from src.utils.llm_client import UniversalLLMClient
from src.utils.performance_cache import get_smart_cache_manager
from src.utils.monitoring import get_performance_monitor, get_concurrency_manager

logger = logging.getLogger(__name__)


@dataclass
class ChapterGenerationTask:
    """章节生成任务."""
    
    id: str
    chapter_outline: ChapterOutline
    character_db: CharacterDatabase
    concept: ConceptExpansionResult
    strategy: GenerationStrategy
    dependencies: List[str]  # 依赖的任务ID
    priority: int = 0  # 优先级（越高越先执行）
    estimated_time: float = 180.0  # 预估生成时间（秒）


@dataclass
class GenerationResult:
    """生成结果."""
    
    task_id: str
    content: Optional[ChapterContent]
    success: bool
    error: Optional[str] = None
    generation_time: float = 0.0
    cache_hit: bool = False


class ConcurrentChapterGenerator(ChapterGenerationEngine):
    """并发章节生成引擎.
    
    继承原有的章节生成引擎，增加并发生成、缓存优化和性能监控功能。
    """
    
    def __init__(
        self,
        llm_client: UniversalLLMClient,
        max_retries: int = 3,
        timeout: int = 180,
        quality_threshold: float = 0.7,
        max_concurrent_chapters: int = 3,
        enable_smart_caching: bool = True
    ):
        """初始化并发章节生成引擎.
        
        Args:
            llm_client: LLM客户端
            max_retries: 最大重试次数
            timeout: 超时时间
            quality_threshold: 质量阈值
            max_concurrent_chapters: 最大并发章节数
            enable_smart_caching: 是否启用智能缓存
        """
        super().__init__(llm_client, max_retries, timeout, quality_threshold)
        
        self.max_concurrent_chapters = max_concurrent_chapters
        self.enable_smart_caching = enable_smart_caching
        
        # 性能组件
        self.cache_manager = get_smart_cache_manager() if enable_smart_caching else None
        self.performance_monitor = get_performance_monitor()
        self.concurrency_manager = get_concurrency_manager()
        
        # 任务管理
        self.active_tasks: Dict[str, ChapterGenerationTask] = {}
        self.completed_tasks: Dict[str, GenerationResult] = {}
        self.task_queue = asyncio.Queue()
        
        # 性能统计
        self.total_generations = 0
        self.successful_generations = 0
        self.cache_hits = 0
        self.total_generation_time = 0.0
        
        logger.info(f"并发章节生成引擎初始化完成，最大并发数: {max_concurrent_chapters}")
    
    async def generate_chapter_optimized(
        self,
        chapter_outline: ChapterOutline,
        character_db: CharacterDatabase,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy,
        previous_chapters: Optional[List[ChapterContent]] = None,
        use_cache: bool = True
    ) -> ChapterContent:
        """优化的章节生成方法.
        
        Args:
            chapter_outline: 章节大纲
            character_db: 角色数据库
            concept: 概念扩展结果
            strategy: 生成策略
            previous_chapters: 之前的章节
            use_cache: 是否使用缓存
            
        Returns:
            生成的章节内容
        """
        start_time = time.time()
        cache_hit = False
        
        try:
            # 尝试从缓存获取
            if use_cache and self.cache_manager:
                cached_content = await self._try_get_from_cache(
                    chapter_outline, character_db, concept, strategy
                )
                if cached_content:
                    cache_hit = True
                    self.cache_hits += 1
                    logger.info(f"缓存命中: {chapter_outline.title}")
                    return cached_content
            
            # 使用性能监控和并发控制
            request_id = str(uuid.uuid4())
            
            async with self.concurrency_manager.acquire_request_slot("chapter_generation", request_id):
                async with self.performance_monitor.track_request("chapter_generation") as metrics:
                    # 生成章节内容
                    content = await super().generate_chapter(
                        chapter_outline, character_db, concept, strategy, previous_chapters
                    )
                    
                    # 记录性能指标
                    if hasattr(metrics, 'tokens_used'):
                        metrics.tokens_used = content.word_count
            
            # 缓存结果
            if use_cache and self.cache_manager:
                await self._cache_result(
                    chapter_outline, character_db, concept, strategy, content
                )
            
            # 更新统计
            generation_time = time.time() - start_time
            self.total_generations += 1
            self.successful_generations += 1
            self.total_generation_time += generation_time
            
            logger.info(
                f"章节生成完成: {chapter_outline.title}, "
                f"耗时: {generation_time:.2f}s, "
                f"缓存命中: {cache_hit}"
            )
            
            return content
            
        except Exception as e:
            self.total_generations += 1
            logger.error(f"优化章节生成失败: {e}")
            raise
    
    async def generate_chapters_batch_optimized(
        self,
        chapter_outlines: List[ChapterOutline],
        character_db: CharacterDatabase,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy,
        parallel_strategy: str = "sequential_optimized"  # 默认使用优化的串行模式
    ) -> List[ChapterContent]:
        """批量生成章节（优化版本）.
        
        注意：为保证章节间连贯性，同一本小说的章节必须按顺序生成。
        并发优化主要体现在单章节生成的内部优化和缓存机制。
        
        Args:
            chapter_outlines: 章节大纲列表
            character_db: 角色数据库
            concept: 概念扩展结果
            strategy: 生成策略
            parallel_strategy: 生成策略（推荐使用sequential_optimized）
            
        Returns:
            章节内容列表
        """
        if not chapter_outlines:
            return []
        
        logger.info(f"开始顺序生成 {len(chapter_outlines)} 个章节（保证连贯性）")
        
        # 统一使用优化的串行生成，确保章节连贯性
        return await self._generate_batch_sequential_optimized(
            chapter_outlines, character_db, concept, strategy
        )
    
    async def _generate_batch_serial(
        self,
        chapter_outlines: List[ChapterOutline],
        character_db: CharacterDatabase,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy
    ) -> List[ChapterContent]:
        """串行批量生成."""
        chapters = []
        previous_chapters = []
        
        for i, outline in enumerate(chapter_outlines):
            logger.info(f"串行生成章节 {i+1}/{len(chapter_outlines)}: {outline.title}")
            
            content = await self.generate_chapter_optimized(
                outline, character_db, concept, strategy, previous_chapters
            )
            chapters.append(content)
            previous_chapters.append(content)
        
        return chapters
    
    async def _generate_batch_parallel(
        self,
        chapter_outlines: List[ChapterOutline],
        character_db: CharacterDatabase,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy
    ) -> List[ChapterContent]:
        """并行批量生成."""
        max_concurrent = min(self.max_concurrent_chapters, len(chapter_outlines))
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_single(
            index: int,
            outline: ChapterOutline
        ) -> Tuple[int, ChapterContent]:
            """生成单个章节."""
            async with semaphore:
                content = await self.generate_chapter_optimized(
                    outline, character_db, concept, strategy, None
                )
                return index, content
        
        # 创建并行任务
        tasks = [
            generate_single(i, outline)
            for i, outline in enumerate(chapter_outlines)
        ]
        
        # 执行并行生成
        logger.info(f"开始并行生成，并发数: {max_concurrent}")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        chapters = [None] * len(chapter_outlines)
        successful_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"并行章节生成失败: {result}")
            else:
                index, content = result
                chapters[index] = content
                successful_count += 1
        
        # 处理失败的章节
        for i, chapter in enumerate(chapters):
            if chapter is None:
                logger.warning(f"章节 {i} 生成失败，使用降级策略")
                try:
                    # 降级到串行生成
                    chapters[i] = await self.generate_chapter_optimized(
                        chapter_outlines[i], character_db, concept, strategy, None
                    )
                except Exception as e:
                    logger.error(f"降级生成也失败: {e}")
                    # 创建空的章节内容作为占位符
                    from src.core.chapter_generator import ChapterContent
                    chapters[i] = ChapterContent(
                        title=chapter_outlines[i].title,
                        content=f"章节生成失败: {str(e)}",
                        word_count=0,
                        summary="生成失败",
                        key_events_covered=[]
                    )
        
        success_rate = successful_count / len(chapter_outlines)
        logger.info(f"并行生成完成，成功率: {success_rate:.1%}")
        
        return chapters
    
    async def _generate_batch_sequential_optimized(
        self,
        chapter_outlines: List[ChapterOutline],
        character_db: CharacterDatabase,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy
    ) -> List[ChapterContent]:
        """优化的串行生成，保证章节连贯性同时提升性能.
        
        这是推荐的章节生成方式，确保：
        1. 章节间的故事连贯性和逻辑一致性
        2. 角色发展的连续性
        3. 情节线的自然推进
        4. 通过缓存和性能监控提升效率
        """
        chapters = []
        previous_chapters = []
        
        logger.info(f"开始优化串行生成 {len(chapter_outlines)} 个章节")
        
        for i, outline in enumerate(chapter_outlines):
            logger.info(f"生成章节 {i+1}/{len(chapter_outlines)}: {outline.title}")
            
            try:
                # 使用优化的章节生成方法，包含缓存和性能监控
                content = await self.generate_chapter_optimized(
                    outline, character_db, concept, strategy, previous_chapters
                )
                chapters.append(content)
                previous_chapters.append(content)
                
                logger.info(f"章节 {i+1} 生成完成: {content.word_count} 字")
                
                # 可选：在章节间添加短暂延迟，避免API频率限制
                if i < len(chapter_outlines) - 1:  # 不在最后一章后延迟
                    await asyncio.sleep(0.5)  # 500ms延迟
                
            except Exception as e:
                logger.error(f"章节 {i+1} 生成失败: {e}")
                # 创建错误占位符，但不影响后续章节生成
                from src.core.chapter_generator import ChapterContent
                error_content = ChapterContent(
                    title=outline.title,
                    content=f"【章节生成失败】由于技术原因，本章节暂时无法生成。错误信息：{str(e)}",
                    word_count=50,
                    summary=f"第{outline.title}: 生成失败",
                    key_events_covered=[]
                )
                chapters.append(error_content)
                previous_chapters.append(error_content)
        
        success_count = sum(1 for ch in chapters if "生成失败" not in ch.content)
        success_rate = success_count / len(chapters) if chapters else 0
        total_words = sum(ch.word_count for ch in chapters)
        
        logger.info(
            f"串行生成完成: 成功率 {success_rate:.1%} ({success_count}/{len(chapters)}), "
            f"总字数 {total_words}"
        )
        
        return chapters
    
    async def _generate_batch_with_dependency_analysis(
        self,
        chapter_outlines: List[ChapterOutline],
        character_db: CharacterDatabase,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy
    ) -> List[ChapterContent]:
        """基于依赖关系分析的章节生成（实验性功能）.
        
        注意：此方法仅用于特殊场景，如外传、回忆章节等。
        对于常规小说，强烈推荐使用串行生成以保证连贯性。
        """
        logger.warning("使用实验性依赖分析生成方法，可能影响章节连贯性")
        
        # 分析章节类型和依赖关系
        independent_chapters = []  # 独立章节（如外传、回忆等）
        sequential_chapters = []   # 需要顺序生成的章节
        
        for i, outline in enumerate(chapter_outlines):
            # 简单的关键词检测来判断章节类型
            summary_lower = outline.summary.lower()
            title_lower = outline.title.lower()
            
            if any(keyword in summary_lower or keyword in title_lower
                   for keyword in ["外传", "番外", "回忆", "梦境", "独立", "前传"]):
                independent_chapters.append((i, outline))
                logger.info(f"检测到独立章节: {outline.title}")
            else:
                sequential_chapters.append((i, outline))
        
        chapters = [None] * len(chapter_outlines)
        
        # 并行生成独立章节（如果有的话）
        if independent_chapters:
            logger.info(f"并行生成 {len(independent_chapters)} 个独立章节")
            
            async def generate_independent_chapter(index: int, outline: ChapterOutline):
                try:
                    content = await self.generate_chapter_optimized(
                        outline, character_db, concept, strategy, None
                    )
                    return index, content
                except Exception as e:
                    logger.error(f"独立章节生成失败: {e}")
                    return index, None
            
            tasks = [
                generate_independent_chapter(i, outline)
                for i, outline in independent_chapters
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"独立章节任务失败: {result}")
                else:
                    index, content = result
                    if content:
                        chapters[index] = content
        
        # 串行生成顺序相关的章节
        if sequential_chapters:
            logger.info(f"串行生成 {len(sequential_chapters)} 个顺序章节")
            
            previous_chapters = []
            
            for i, outline in sequential_chapters:
                try:
                    # 获取已生成的前置章节（包括独立章节）
                    relevant_previous = [ch for ch in chapters[:i] if ch is not None]
                    relevant_previous.extend(previous_chapters)
                    
                    content = await self.generate_chapter_optimized(
                        outline, character_db, concept, strategy, relevant_previous
                    )
                    chapters[i] = content
                    previous_chapters.append(content)
                    
                except Exception as e:
                    logger.error(f"顺序章节生成失败: {e}")
                    # 创建占位符
                    from src.core.chapter_generator import ChapterContent
                    error_content = ChapterContent(
                        title=outline.title,
                        content=f"章节生成失败: {str(e)}",
                        word_count=0,
                        summary="生成失败",
                        key_events_covered=[]
                    )
                    chapters[i] = error_content
                    previous_chapters.append(error_content)
        
        # 处理任何剩余的None值
        for i, chapter in enumerate(chapters):
            if chapter is None:
                logger.warning(f"章节 {i} 未生成，创建占位符")
                from src.core.chapter_generator import ChapterContent
                chapters[i] = ChapterContent(
                    title=chapter_outlines[i].title,
                    content="章节生成失败",
                    word_count=0,
                    summary="生成失败",
                    key_events_covered=[]
                )
        
        success_count = sum(1 for ch in chapters if "生成失败" not in ch.content)
        success_rate = success_count / len(chapters) if chapters else 0
        
        logger.info(f"依赖分析生成完成，成功率: {success_rate:.1%}")
        
        return chapters
    
    async def _try_get_from_cache(
        self,
        chapter_outline: ChapterOutline,
        character_db: CharacterDatabase,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy
    ) -> Optional[ChapterContent]:
        """尝试从缓存获取章节内容."""
        if not self.cache_manager:
            return None
        
        try:
            # 构建缓存键
            cache_key_data = {
                "title": chapter_outline.title,
                "summary": chapter_outline.summary,
                "key_events": chapter_outline.key_events,
                "target_words": chapter_outline.estimated_word_count,
                "theme": concept.theme,
                "genre": concept.genre,
                "character_count": len(character_db.characters)
            }
            
            cached_result = await self.cache_manager.llm_cache.get_llm_response(
                task_type="chapter_generation",
                prompt=str(cache_key_data)
            )
            
            if cached_result:
                # 重构章节内容对象
                from src.core.chapter_generator import ChapterContent
                return ChapterContent(
                    title=chapter_outline.title,
                    content=cached_result,
                    word_count=len(cached_result),
                    summary=f"第{chapter_outline.title}: 缓存内容",
                    key_events_covered=chapter_outline.key_events.copy()
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"缓存获取失败: {e}")
            return None
    
    async def _cache_result(
        self,
        chapter_outline: ChapterOutline,
        character_db: CharacterDatabase,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy,
        content: ChapterContent
    ) -> None:
        """缓存生成结果."""
        if not self.cache_manager:
            return
        
        try:
            # 构建缓存键
            cache_key_data = {
                "title": chapter_outline.title,
                "summary": chapter_outline.summary,
                "key_events": chapter_outline.key_events,
                "target_words": chapter_outline.estimated_word_count,
                "theme": concept.theme,
                "genre": concept.genre,
                "character_count": len(character_db.characters)
            }
            
            await self.cache_manager.llm_cache.cache_llm_response(
                task_type="chapter_generation",
                prompt=str(cache_key_data),
                response=content.content,
                custom_ttl=14400  # 4小时
            )
            
        except Exception as e:
            logger.warning(f"缓存保存失败: {e}")
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息."""
        avg_generation_time = 0.0
        if self.successful_generations > 0:
            avg_generation_time = self.total_generation_time / self.successful_generations
        
        success_rate = 0.0
        if self.total_generations > 0:
            success_rate = self.successful_generations / self.total_generations
        
        cache_hit_rate = 0.0
        if self.total_generations > 0:
            cache_hit_rate = self.cache_hits / self.total_generations
        
        # 获取系统性能摘要
        performance_summary = await self.performance_monitor.get_performance_summary()
        
        return {
            "chapter_generation_stats": {
                "total_generations": self.total_generations,
                "successful_generations": self.successful_generations,
                "success_rate": success_rate,
                "cache_hits": self.cache_hits,
                "cache_hit_rate": cache_hit_rate,
                "avg_generation_time": avg_generation_time,
                "max_concurrent_chapters": self.max_concurrent_chapters,
                "active_tasks": len(self.active_tasks)
            },
            "system_performance": performance_summary,
            "cache_enabled": self.enable_smart_caching
        }
    
    async def optimize_performance(self) -> None:
        """优化性能设置."""
        logger.info("开始性能优化")
        
        try:
            # 获取性能统计
            stats = await self.get_performance_stats()
            chapter_stats = stats["chapter_generation_stats"]
            system_stats = stats["system_performance"]
            
            # 根据成功率调整并发数
            success_rate = chapter_stats["success_rate"]
            if success_rate < 0.8 and self.max_concurrent_chapters > 1:
                self.max_concurrent_chapters = max(1, self.max_concurrent_chapters - 1)
                logger.info(f"成功率较低，降低并发数至: {self.max_concurrent_chapters}")
            elif success_rate > 0.95 and self.max_concurrent_chapters < 5:
                self.max_concurrent_chapters += 1
                logger.info(f"成功率良好，提高并发数至: {self.max_concurrent_chapters}")
            
            # 根据系统负载调整设置
            cpu_percent = system_stats.get("cpu_percent", 0)
            memory_percent = system_stats.get("memory_percent", 0)
            
            if cpu_percent > 85 or memory_percent > 90:
                # 系统负载过高，启用更保守的设置
                self.timeout = min(300, self.timeout + 30)  # 增加超时时间
                logger.info(f"系统负载较高，调整超时时间至: {self.timeout}s")
            
            # 优化缓存
            if self.cache_manager:
                await self.cache_manager.optimize_cache()
            
        except Exception as e:
            logger.error(f"性能优化失败: {e}")
    
    def get_generation_recommendations(self) -> Dict[str, Any]:
        """获取生成建议."""
        stats = asyncio.create_task(self.get_performance_stats())
        
        recommendations = {
            "current_performance": "良好",
            "suggestions": [],
            "optimal_settings": {
                "max_concurrent_chapters": self.max_concurrent_chapters,
                "enable_caching": self.enable_smart_caching,
                "timeout": self.timeout
            }
        }
        
        # 基于统计数据提供建议
        if self.total_generations > 0:
            success_rate = self.successful_generations / self.total_generations
            cache_hit_rate = self.cache_hits / self.total_generations
            
            if success_rate < 0.9:
                recommendations["suggestions"].append("考虑降低并发数以提高成功率")
                recommendations["current_performance"] = "需要改进"
            
            if cache_hit_rate < 0.3:
                recommendations["suggestions"].append("考虑启用智能缓存以提高性能")
            
            if self.total_generation_time / max(1, self.successful_generations) > 300:
                recommendations["suggestions"].append("平均生成时间较长，考虑优化提示词或模型选择")
        
        return recommendations