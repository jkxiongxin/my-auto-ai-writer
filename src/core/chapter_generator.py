"""章节生成引擎模块，负责生成高质量的小说章节内容."""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from src.core.data_models import ChapterContent, GenerationContext, GenerationHistory
from src.core.concept_expander import ConceptExpansionResult
from src.core.strategy_selector import GenerationStrategy
from src.core.outline_generator import NovelOutline, ChapterOutline
from src.core.character_system import CharacterDatabase, Character
from src.utils.llm_client import UniversalLLMClient

logger = logging.getLogger(__name__)


class ChapterGenerationError(Exception):
    """章节生成异常."""
    pass




class ChapterGenerationEngine:
    """章节生成引擎，生成高质量的小说章节内容.
    
    负责根据概念、策略、大纲和角色信息，生成连贯且高质量的章节内容。
    包含上下文管理、生成历史追踪和质量控制机制。
    
    Attributes:
        llm_client: LLM客户端实例
        max_retries: 最大重试次数
        timeout: 超时时间
        quality_threshold: 质量阈值
    """
    
    def __init__(
        self,
        llm_client: UniversalLLMClient,
        max_retries: int = 3,
        timeout: int = 180,
        quality_threshold: float = 0.7,
        enable_coherence_management: bool = True
    ):
        """初始化章节生成引擎.
        
        Args:
            llm_client: 统一LLM客户端实例
            max_retries: 最大重试次数
            timeout: 请求超时时间
            quality_threshold: 质量阈值（0-1）
            enable_coherence_management: 是否启用连贯性管理
            
        Raises:
            ValueError: 当llm_client为None时抛出
        """
        if llm_client is None:
            raise ValueError("llm_client不能为None")
        
        self.llm_client = llm_client
        self.max_retries = max_retries
        self.timeout = timeout
        self.quality_threshold = quality_threshold
        self.enable_coherence_management = enable_coherence_management
        
        # 初始化连贯性管理器（延迟导入避免循环依赖）
        if enable_coherence_management:
            from src.core.narrative_coherence import NarrativeCoherenceManager
            self.coherence_manager = NarrativeCoherenceManager(llm_client)
            logger.info("连贯性管理器已启用")
        else:
            self.coherence_manager = None
            logger.info("连贯性管理器已禁用")
        
        # 初始化生成历史
        self.generation_history = GenerationHistory(
            chapter_summaries=[],
            character_states={},
            world_events=[],
            plot_progress={},
            tone_evolution=[]
        )
        
        # 生成质量配置
        self.quality_configs = {
            "min_word_ratio": 0.8,  # 最少字数比例
            "max_word_ratio": 1.2,  # 最多字数比例
            "coherence_threshold": 0.7,  # 连贯性阈值
            "character_consistency_threshold": 0.8  # 角色一致性阈值
        }
        
        logger.info("章节生成引擎初始化完成")
    
    async def generate_chapter(
        self,
        chapter_outline: ChapterOutline,
        character_db: CharacterDatabase,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy,
        previous_chapters: Optional[List[ChapterContent]] = None
    ) -> ChapterContent:
        """生成单个章节内容.
        
        Args:
            chapter_outline: 章节大纲
            character_db: 角色数据库
            concept: 概念扩展结果
            strategy: 生成策略
            previous_chapters: 之前生成的章节列表
            
        Returns:
            ChapterContent: 生成的章节内容
            
        Raises:
            ChapterGenerationError: 当章节生成失败时抛出
        """
        # 输入验证
        if chapter_outline is None:
            raise ChapterGenerationError("章节大纲不能为空")
        
        if character_db is None:
            raise ChapterGenerationError("角色数据库不能为空")
        
        if concept is None:
            raise ChapterGenerationError("概念信息不能为空")
        
        logger.info(f"开始生成章节: {chapter_outline.title} (目标字数: {chapter_outline.estimated_word_count})")
        
        try:
            # 1. 构建生成上下文
            context = self._build_generation_context(
                chapter_outline, character_db, previous_chapters
            )
            
            # 2. 准备连贯性上下文（如果启用）
            coherence_context = {}
            if self.coherence_manager:
                coherence_context = await self.coherence_manager.prepare_chapter_context(
                    chapter_outline, character_db, concept, previous_chapters
                )
                logger.info(f"连贯性上下文已准备: {len(coherence_context)} 个要素")
            
            # 3. 生成章节内容
            content = await self._generate_chapter_content(
                chapter_outline, character_db, concept, strategy, context, coherence_context
            )
            
            # 3. 质量控制检查
            if not self._validate_chapter_quality(content, chapter_outline):
                # 如果质量不达标，重新生成一次
                logger.warning(f"章节 {chapter_outline.title} 质量不达标，重新生成")
                content = await self._generate_chapter_content(
                    chapter_outline, character_db, concept, strategy, context
                )
            
            # 4. 连贯性分析和状态更新（如果启用）
            if self.coherence_manager:
                try:
                    # 分析生成内容的连贯性
                    coherence_analysis = await self.coherence_manager.analyze_coherence(
                        content, previous_chapters or [], character_db
                    )
                    
                    logger.info(f"连贯性分析: 评分 {coherence_analysis.coherence_score:.2f}")
                    
                    # 如果连贯性分数过低，记录警告
                    if coherence_analysis.coherence_score < self.quality_configs["coherence_threshold"]:
                        logger.warning(
                            f"连贯性分数较低: {coherence_analysis.coherence_score:.2f}, "
                            f"问题: {coherence_analysis.issues_found}"
                        )
                    
                    # 将连贯性信息添加到元数据
                    content.consistency_notes.extend(coherence_analysis.issues_found)
                    content.consistency_notes.extend(coherence_analysis.suggestions)
                    
                    # 更新连贯性管理器的状态
                    await self.coherence_manager._update_narrative_state(content)
                    
                except Exception as e:
                    logger.error(f"连贯性分析失败: {e}")
            
            # 5. 更新生成历史
            self._update_generation_history(content, chapter_outline)
            
            # 6. 生成章节摘要
            content.summary = self._generate_chapter_summary(content)
            
            # 7. 添加生成元数据
            coherence_score = 0.0
            if self.coherence_manager:
                try:
                    # 获取连贯性分析结果
                    coherence_analysis = await self.coherence_manager.analyze_coherence(
                        content, previous_chapters or [], character_db
                    )
                    coherence_score = coherence_analysis.coherence_score
                except:
                    pass
            
            content.generation_metadata = {
                "generation_time": datetime.now().isoformat(),
                "target_words": chapter_outline.estimated_word_count,
                "actual_words": content.word_count,
                "word_ratio": content.word_count / chapter_outline.estimated_word_count,
                "quality_passed": True,
                "coherence_score": coherence_score,
                "coherence_enabled": self.enable_coherence_management
            }
            
            logger.info(f"章节生成完成: {content.title} ({content.word_count}字)")
            return content
            
        except Exception as e:
            logger.error(f"章节生成失败: {e}", exc_info=True)
            raise ChapterGenerationError(f"章节生成失败: {e}")
    
    def _build_generation_context(
        self,
        chapter_outline: ChapterOutline,
        character_db: CharacterDatabase,
        previous_chapters: Optional[List[ChapterContent]]
    ) -> GenerationContext:
        """构建生成上下文.
        
        Args:
            chapter_outline: 章节大纲
            character_db: 角色数据库
            previous_chapters: 之前的章节
            
        Returns:
            GenerationContext: 生成上下文对象
        """
        # 确定活跃角色
        active_characters = self._determine_active_characters(chapter_outline, character_db)
        
        # 获取前一章节摘要
        previous_summary = None
        if previous_chapters:
            previous_summary = previous_chapters[-1].summary
        
        # 构建世界状态
        world_state = self._build_world_state(previous_chapters)
        
        # 提取情节线索
        plot_threads = self._extract_plot_threads(chapter_outline, previous_chapters)
        
        # 确定情绪基调
        mood_tone = self._determine_mood_tone(chapter_outline)
        
        # 构建场景细节
        setting_details = self._build_setting_details(chapter_outline)
        
        return GenerationContext(
            active_characters=active_characters,
            previous_summary=previous_summary,
            world_state=world_state,
            plot_threads=plot_threads,
            mood_tone=mood_tone,
            setting_details=setting_details
        )
    
    def _determine_active_characters(
        self, 
        chapter_outline: ChapterOutline, 
        character_db: CharacterDatabase
    ) -> List[str]:
        """确定当前章节的活跃角色.
        
        Args:
            chapter_outline: 章节大纲
            character_db: 角色数据库
            
        Returns:
            活跃角色名称列表
        """
        active_characters = []
        
        # 从场景中提取角色
        for scene in chapter_outline.scenes:
            active_characters.extend(scene.characters)
        
        # 如果没有明确指定角色，默认包含主角
        if not active_characters:
            protagonist = character_db.get_character_by_role("主角")
            if protagonist:
                active_characters.append(protagonist.name)
        
        # 去重并返回
        return list(set(active_characters))
    
    def _build_world_state(self, previous_chapters: Optional[List[ChapterContent]]) -> Dict[str, Any]:
        """构建当前世界状态.
        
        Args:
            previous_chapters: 之前的章节
            
        Returns:
            世界状态字典
        """
        world_state = {
            "timeline": "故事开始",
            "major_events": [],
            "world_changes": [],
            "character_locations": {}
        }
        
        if previous_chapters:
            # 从历史章节中提取世界状态信息
            for chapter in previous_chapters:
                world_state["major_events"].extend(chapter.key_events_covered)
        
        return world_state
    
    def _extract_plot_threads(
        self, 
        chapter_outline: ChapterOutline, 
        previous_chapters: Optional[List[ChapterContent]]
    ) -> List[str]:
        """提取情节线索.
        
        Args:
            chapter_outline: 章节大纲
            previous_chapters: 之前的章节
            
        Returns:
            情节线索列表
        """
        plot_threads = chapter_outline.key_events.copy()
        
        if previous_chapters:
            # 从之前章节中继承未完成的情节线索
            for chapter in previous_chapters[-2:]:  # 最近两章
                for event in chapter.key_events_covered:
                    if "待解决" in event or "悬念" in event:
                        plot_threads.append(event)
        
        return plot_threads
    
    def _determine_mood_tone(self, chapter_outline: ChapterOutline) -> str:
        """确定章节情绪基调.
        
        Args:
            chapter_outline: 章节大纲
            
        Returns:
            情绪基调描述
        """
        # 基于章节摘要和关键事件推断基调
        summary_text = chapter_outline.summary.lower()
        
        if any(keyword in summary_text for keyword in ["战斗", "冲突", "紧张", "危险"]):
            return "紧张刺激"
        elif any(keyword in summary_text for keyword in ["死亡", "失败", "悲伤", "绝望"]):
            return "悲伤沉重"
        elif any(keyword in summary_text for keyword in ["胜利", "成功", "喜悦", "庆祝"]):
            return "欢快愉悦"
        elif any(keyword in summary_text for keyword in ["思考", "回忆", "沉思", "反省"]):
            return "深沉内省"
        else:
            return "平和稳定"
    
    def _build_setting_details(self, chapter_outline: ChapterOutline) -> Dict[str, str]:
        """构建场景细节.
        
        Args:
            chapter_outline: 章节大纲
            
        Returns:
            场景细节字典
        """
        setting_details = {}
        
        for i, scene in enumerate(chapter_outline.scenes):
            setting_details[f"scene_{i+1}"] = {
                "name": scene.name,
                "description": scene.description,
                "location": scene.location or "未指定",
                "atmosphere": "根据情节发展"
            }
        
        return setting_details
    
    async def _generate_chapter_content(
        self,
        chapter_outline: ChapterOutline,
        character_db: CharacterDatabase,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy,
        context: GenerationContext,
        coherence_context: Optional[Dict[str, Any]] = None
    ) -> ChapterContent:
        """生成章节内容.
        
        Args:
            chapter_outline: 章节大纲
            character_db: 角色数据库
            concept: 概念扩展结果
            strategy: 生成策略
            context: 生成上下文
            coherence_context: 连贯性上下文
            
        Returns:
            生成的章节内容
        """
        # 构建提示词
        prompt = self._build_chapter_prompt(
            chapter_outline, character_db, concept, strategy, context, coherence_context
        )
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                # 调用LLM生成内容（带日志记录）
                response = await asyncio.wait_for(
                    self.llm_client.generate(
                        prompt,
                        step_type="chapter_generation",
                        step_name=f"第{chapter_outline.number}章: {chapter_outline.title}",
                        log_generation=True
                    ),
                    timeout=self.timeout
                )
                
                # 解析响应并创建章节内容
                content = self._parse_chapter_response(response, chapter_outline)
                
                return content
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"第{attempt + 1}次章节生成尝试失败: {e}")
                if attempt == self.max_retries - 1:
                    raise ChapterGenerationError(f"LLM响应格式无效: {e}")
                await asyncio.sleep(3)
        
        raise ChapterGenerationError("章节内容生成失败")
    
    def _build_chapter_prompt(
        self,
        chapter_outline: ChapterOutline,
        character_db: CharacterDatabase,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy,
        context: GenerationContext,
        coherence_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建章节生成提示词.
        
        Args:
            chapter_outline: 章节大纲
            character_db: 角色数据库
            concept: 概念扩展结果
            strategy: 生成策略
            context: 生成上下文
            coherence_context: 连贯性上下文
            
        Returns:
            完整的提示词字符串
        """
        # 获取活跃角色的详细信息
        character_info = []
        for char_name in context.active_characters:
            character = character_db.get_character_by_name(char_name)
            if character:
                char_info = f"- {character.name}: {character.role}, {character.motivation}"
                if character.personality:
                    char_info += f", 性格: {', '.join(character.personality[:3])}"
                character_info.append(char_info)
        
        # 构建上下文信息和衔接指导
        context_info = ""
        transition_guidance = ""
        
        if context.previous_summary:
            context_info += f"前一章节摘要: {context.previous_summary}\n"
            
            # 构建详细的衔接指导
            transition_guidance = self._build_seamless_transition_guidance(context, chapter_outline)
        
        if context.plot_threads:
            context_info += f"当前情节线索: {', '.join(context.plot_threads[:3])}\n"
        
        # 构建连贯性指导
        coherence_guidance = ""
        if coherence_context:
            coherence_guidance = self._build_coherence_guidance(coherence_context)
        
        # 判断是否为最后一章
        is_last_chapter = getattr(chapter_outline, 'is_final_chapter', False)
        
        # 构建章节结尾要求
        ending_requirements = ""
        if is_last_chapter:
            ending_requirements = """
9. 章节结尾要求: 作为全书最后一章，应该给出完整的结局，解决所有主要冲突和悬念
"""
        else:
            ending_requirements = f"""
9. 章节结尾要求:
   - 必须在关键时刻戛然而止，营造强烈的悬念感
   - 可以在冲突即将爆发、真相即将揭晓、或重要决定即将做出时停笔
   - 让读者迫不及待想要阅读下一章
   - 避免圆满的小结局，避免"这一天就这样结束了"类的总结性结尾
   - 结尾要有强烈的戏剧张力，可以用悬疑、冲突、意外转折等手法
   - 示例结尾风格: "就在这时，门突然被推开了..." / "电话铃声在寂静的夜里突然响起..." / "他刚要开口，却看到了那个不应该出现在这里的人..."
"""

        prompt = f"""
请为小说生成第{chapter_outline.number}章的详细内容。

小说基本信息:
- 主题: {concept.theme}
- 类型: {concept.genre}
- 基调: {concept.tone}
- 世界设定: {concept.world_type}

章节大纲:
- 标题: {chapter_outline.title}
- 摘要: {chapter_outline.summary}
- 关键事件: {', '.join(chapter_outline.key_events)}
- 目标字数: {chapter_outline.estimated_word_count}
- 叙事目的: {chapter_outline.narrative_purpose or '推进情节'}

活跃角色:
{chr(10).join(character_info)}

上下文信息:
{context_info}

{transition_guidance}

场景设置:
- 情绪基调: {context.mood_tone}
- 主要场景: {', '.join([scene.name for scene in chapter_outline.scenes[:2]])}

{coherence_guidance}

请生成这一章的完整内容，要求:
1. 严格控制在{chapter_outline.estimated_word_count}字左右（误差不超过20%）
2. 完整覆盖所有关键事件
3. 保持角色性格一致性
4. 文笔流畅，情节连贯
5. 符合{concept.genre}类型的风格特点
6. 体现{context.mood_tone}的情绪基调
7. 适当使用对话推进情节
8. 包含必要的场景描写和心理描写
9. 严格遵循章节衔接指导，确保与上一章无缝连接{ending_requirements}

以纯文本格式输出章节内容，不需要JSON格式。
"""
        
        return prompt.strip()
    
    def _build_seamless_transition_guidance(
        self,
        context: GenerationContext,
        chapter_outline: ChapterOutline
    ) -> str:
        """构建无缝衔接指导信息.
        
        Args:
            context: 生成上下文
            chapter_outline: 当前章节大纲
            
        Returns:
            衔接指导文本
        """
        if not context.previous_summary:
            return ""
        
        guidance_parts = []
        guidance_parts.append("章节衔接要求:")
        
        # 分析上一章的结尾情况
        previous_summary = context.previous_summary
        
        # 根据上一章的内容推断衔接方式
        if any(keyword in previous_summary for keyword in ["突然", "意外", "震惊", "惊讶"]):
            guidance_parts.append("- 开头处理: 从角色的震惊反应开始，处理突发事件的后续影响")
            guidance_parts.append("- 情绪延续: 保持紧张或惊讶的情绪基调")
            guidance_parts.append("- 时间衔接: 紧接上一章的时间点，无时间跳跃")
            
        elif any(keyword in previous_summary for keyword in ["对话", "说", "问", "回答"]):
            guidance_parts.append("- 开头处理: 可以继续对话，或展示对话后角色的反应和思考")
            guidance_parts.append("- 情绪延续: 承接对话中体现的情绪氛围")
            guidance_parts.append("- 时间衔接: 从对话结束的那一刻继续")
            
        elif any(keyword in previous_summary for keyword in ["决定", "选择", "计划"]):
            guidance_parts.append("- 开头处理: 展示决定的执行过程或后果")
            guidance_parts.append("- 行动连贯: 直接展现角色如何付诸行动")
            guidance_parts.append("- 时间衔接: 可以有短暂的时间推进，但要明确交代")
            
        elif any(keyword in previous_summary for keyword in ["离开", "前往", "到达"]):
            guidance_parts.append("- 开头处理: 从新的场景或环境开始，但要简要提及转场过程")
            guidance_parts.append("- 场景衔接: 明确地理位置的变化和转移过程")
            guidance_parts.append("- 时间衔接: 可以有适当的时间流逝，但要自然过渡")
            
        else:
            # 通用衔接指导
            guidance_parts.append("- 开头处理: 自然承接上一章的情境，避免突兀的场景跳跃")
            guidance_parts.append("- 情绪延续: 保持上一章结尾的情绪基调或合理的情绪转变")
            guidance_parts.append("- 时间衔接: 明确时间关系，避免模糊的时间跳跃")
        
        # 添加通用的衔接原则
        guidance_parts.append("- 衔接技巧: 可以使用角色的内心独白、环境描写或行动描述来实现自然过渡")
        guidance_parts.append("- 避免重复: 不要重述上一章的内容，而是基于其结果继续推进")
        guidance_parts.append("- 读者体验: 让读者感觉这是连续阅读体验，没有断裂感")
        
        # 针对当前章节的特殊要求
        if chapter_outline.key_events:
            first_event = chapter_outline.key_events[0]
            guidance_parts.append(f"- 事件引入: 巧妙地引出本章的第一个关键事件「{first_event}」")
        
        return "\n".join(guidance_parts)
    
    def _build_coherence_guidance(self, coherence_context: Dict[str, Any]) -> str:
        """构建连贯性指导信息.
        
        Args:
            coherence_context: 连贯性上下文
            
        Returns:
            连贯性指导文本
        """
        guidance_parts = []
        
        # 添加连贯性要求标题
        guidance_parts.append("连贯性要求:")
        
        # 角色连贯性
        if "character_continuity" in coherence_context:
            char_info = coherence_context["character_continuity"]
            if char_info:
                guidance_parts.append("- 角色状态保持:")
                for char_name, char_data in list(char_info.items())[:3]:  # 最多3个角色
                    current_state = char_data.get("current_state", {})
                    if current_state:
                        guidance_parts.append(f"  * {char_name}: {current_state.get('last_development', '保持一致性')}")
        
        # 情节连贯性
        if "plot_continuity" in coherence_context:
            plot_info = coherence_context["plot_continuity"]
            active_threads = plot_info.get("active_threads", [])
            if active_threads:
                guidance_parts.append("- 需要延续的情节线索:")
                for thread in active_threads[:3]:  # 最多3个线索
                    guidance_parts.append(f"  * {thread}")
        
        # 世界状态连贯性
        if "world_continuity" in coherence_context:
            world_info = coherence_context["world_continuity"]
            current_location = world_info.get("current_location")
            if current_location and current_location != "未指定":
                guidance_parts.append(f"- 当前位置: {current_location}")
            
            established_facts = world_info.get("established_facts", [])
            if established_facts:
                guidance_parts.append("- 已确立的事实:")
                for fact in established_facts[-2:]:  # 最近2个事实
                    guidance_parts.append(f"  * {fact}")
        
        # 转换指导
        if "transition_info" in coherence_context and coherence_context["transition_info"]:
            transition = coherence_context["transition_info"]
            if transition.get("key_connections"):
                guidance_parts.append("- 与上一章的连接要点:")
                for connection in transition["key_connections"][:2]:
                    guidance_parts.append(f"  * {connection}")
            
            if transition.get("transition_guidance"):
                guidance_parts.append(f"- 开头建议: {transition['transition_guidance']}")
        
        # 连贯性原则
        if "coherence_guidelines" in coherence_context:
            guidelines = coherence_context["coherence_guidelines"]
            if guidelines:
                guidance_parts.append("- 连贯性原则:")
                for guideline in guidelines[:4]:  # 最多4个原则
                    guidance_parts.append(f"  * {guideline}")
        
        return "\n".join(guidance_parts) if len(guidance_parts) > 1 else ""
    
    def _parse_chapter_response(self, response: str, chapter_outline: ChapterOutline) -> ChapterContent:
        """解析LLM章节响应.
        
        Args:
            response: LLM的原始响应
            chapter_outline: 章节大纲
            
        Returns:
            解析后的章节内容
            
        Raises:
            ChapterGenerationError: 当解析失败时抛出
        """
        try:
            # 清理响应文本
            content_text = response.strip()
            
            # 移除可能的代码块标记
            if content_text.startswith("```"):
                lines = content_text.split('\n')
                if len(lines) > 2:
                    content_text = '\n'.join(lines[1:-1])
            
            # 计算字数
            word_count = len(content_text)
            
            # 创建章节内容对象
            chapter_content = ChapterContent(
                title=chapter_outline.title,
                content=content_text,
                word_count=word_count,
                summary="",  # 稍后生成
                key_events_covered=chapter_outline.key_events.copy(),
                character_developments={},
                consistency_notes=[]
            )
            
            return chapter_content
            
        except Exception as e:
            raise ChapterGenerationError(f"章节响应解析失败: {e}")
    
    def _validate_chapter_quality(self, content: ChapterContent, outline: ChapterOutline) -> bool:
        """验证章节质量.
        
        Args:
            content: 章节内容
            outline: 章节大纲
            
        Returns:
            质量是否达标
        """
        try:
            # 检查字数是否在合理范围内
            target_words = outline.estimated_word_count
            word_ratio = content.word_count / target_words
            
            if not (self.quality_configs["min_word_ratio"] <= word_ratio <= self.quality_configs["max_word_ratio"]):
                logger.warning(f"字数比例不合格: {word_ratio:.2f}")
                return False
            
            # 检查内容是否过短
            if content.word_count < 500:
                logger.warning("内容过短")
                return False
            
            # 检查内容是否包含基本的故事元素
            content_lower = content.content.lower()
            
            # 至少应该包含一些基本的叙述元素
            narrative_elements = ["。", "，", "说", "看", "想", "走", "来"]
            if not any(element in content_lower for element in narrative_elements):
                logger.warning("缺少基本叙述元素")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"质量验证出错: {e}")
            return False
    
    def _update_generation_history(self, content: ChapterContent, outline: ChapterOutline) -> None:
        """更新生成历史.
        
        Args:
            content: 章节内容
            outline: 章节大纲
        """
        try:
            # 添加章节摘要到历史
            if content.summary:
                self.generation_history.chapter_summaries.append(content.summary)
            
            # 更新情节进展
            for event in content.key_events_covered:
                self.generation_history.plot_progress[event] = 1.0
            
            # 记录基调演变
            if outline.narrative_purpose:
                self.generation_history.tone_evolution.append(outline.narrative_purpose)
            
        except Exception as e:
            logger.error(f"更新生成历史失败: {e}")
    
    def _generate_chapter_summary(self, content: ChapterContent) -> str:
        """生成章节摘要.
        
        Args:
            content: 章节内容
            
        Returns:
            章节摘要字符串
        """
        try:
            # 简单的摘要生成：取前200字作为摘要基础
            content_preview = content.content[:200]
            
            # 找到最后一个完整句子
            last_period = content_preview.rfind('。')
            if last_period > 50:
                summary = content_preview[:last_period + 1]
            else:
                summary = content_preview + "..."
            
            return f"第{content.title}: {summary}"
            
        except Exception as e:
            logger.error(f"生成章节摘要失败: {e}")
            return f"第{content.title}: 内容摘要生成失败"
    
    def get_generation_history(self) -> GenerationHistory:
        """获取生成历史.
        
        Returns:
            GenerationHistory: 生成历史对象
        """
        return self.generation_history
    
    def reset_generation_history(self) -> None:
        """重置生成历史."""
        self.generation_history = GenerationHistory(
            chapter_summaries=[],
            character_states={},
            world_events=[],
            plot_progress={},
            tone_evolution=[]
        )
        logger.info("生成历史已重置")