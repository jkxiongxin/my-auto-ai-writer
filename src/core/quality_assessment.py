"""质量评估系统模块，实现小说内容的多维度质量评估."""

import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import re

from src.core.character_system import Character
from src.core.consistency_checker import BasicConsistencyChecker, ConsistencyCheckResult
from src.utils.llm_client import UniversalLLMClient

logger = logging.getLogger(__name__)


class QualityAssessmentError(Exception):
    """质量评估异常."""
    pass


@dataclass
class QualityDimension:
    """质量维度数据类."""
    name: str  # 维度名称
    score: float  # 分数 (0-10)
    weight: float  # 权重 (0-1)
    issues: List[str]  # 问题列表
    suggestions: List[str]  # 改进建议
    details: Dict[str, Any] = field(default_factory=dict)  # 详细信息


@dataclass
class QualityMetrics:
    """质量指标数据类."""
    overall_score: float  # 总体分数 (0-10)
    dimensions: Dict[str, QualityDimension]  # 各维度评估
    grade: str  # 等级 (A/B/C/D/F)
    assessment_time: datetime
    word_count: int
    chapter_count: int
    character_count: int
    
    def get_weighted_score(self) -> float:
        """计算加权总分."""
        if not self.dimensions:
            return 0.0
        
        total_weighted = sum(
            dim.score * dim.weight 
            for dim in self.dimensions.values()
        )
        total_weight = sum(dim.weight for dim in self.dimensions.values())
        
        return total_weighted / total_weight if total_weight > 0 else 0.0


@dataclass
class RevisionSuggestion:
    """修订建议数据类."""
    type: str  # 修订类型: plot, character, language, style
    priority: str  # 优先级: high, medium, low
    description: str  # 描述
    target_content: str  # 目标内容片段
    suggested_change: str  # 建议修改
    reason: str  # 修改原因


@dataclass
class RevisionResult:
    """修订结果数据类."""
    original_content: str
    revised_content: str
    changes_made: List[str]
    improvement_score: float  # 改进分数
    revision_type: str  # 修订类型
    revision_time: datetime


class QualityAssessmentSystem:
    """质量评估系统，实现多维度质量评估和迭代修订.
    
    基于PRD文档要求，实现以下功能：
    1. 多维度质量评估（情节逻辑、角色一致性、语言质量、风格一致性）
    2. 迭代修订建议生成
    3. 质量改进跟踪
    4. 智能修订执行
    
    Attributes:
        llm_client: LLM客户端实例
        consistency_checker: 一致性检查器实例
        quality_thresholds: 质量阈值配置
        revision_config: 修订配置
    """
    
    def __init__(
        self,
        llm_client: UniversalLLMClient,
        consistency_checker: Optional[BasicConsistencyChecker] = None,
        quality_thresholds: Optional[Dict[str, float]] = None,
        revision_config: Optional[Dict[str, Any]] = None
    ):
        """初始化质量评估系统.
        
        Args:
            llm_client: 统一LLM客户端实例
            consistency_checker: 一致性检查器实例，如果为None则创建
            quality_thresholds: 质量阈值配置
            revision_config: 修订配置
            
        Raises:
            ValueError: 当llm_client为None时抛出
        """
        if llm_client is None:
            raise ValueError("llm_client不能为None")
        
        self.llm_client = llm_client
        self.consistency_checker = consistency_checker or BasicConsistencyChecker(llm_client)
        
        # 默认质量阈值配置
        self.quality_thresholds = quality_thresholds or {
            "excellent": 9.0,  # 优秀
            "good": 7.5,       # 良好
            "acceptable": 6.0,  # 可接受
            "poor": 4.0,       # 较差
            "unacceptable": 2.0  # 不可接受
        }
        
        # 默认修订配置
        self.revision_config = revision_config or {
            "max_iterations": 3,
            "min_improvement": 0.5,
            "parallel_revisions": False,
            "preserve_style": True
        }
        
        # 质量维度配置
        self.quality_dimensions = {
            "plot_logic": QualityDimension(
                name="情节逻辑",
                score=0.0,
                weight=0.3,
                issues=[],
                suggestions=[]
            ),
            "character_consistency": QualityDimension(
                name="角色一致性",
                score=0.0,
                weight=0.25,
                issues=[],
                suggestions=[]
            ),
            "language_quality": QualityDimension(
                name="语言质量",
                score=0.0,
                weight=0.25,
                issues=[],
                suggestions=[]
            ),
            "style_consistency": QualityDimension(
                name="风格一致性",
                score=0.0,
                weight=0.2,
                issues=[],
                suggestions=[]
            )
        }
        
        logger.info("质量评估系统初始化完成")
    
    async def assess_quality(
        self,
        content: str,
        characters: Dict[str, Character],
        chapter_info: Dict[str, Any],
        style_guide: Optional[str] = None
    ) -> QualityMetrics:
        """对内容进行全面质量评估.
        
        Args:
            content: 待评估的文本内容
            characters: 角色信息字典
            chapter_info: 章节信息
            style_guide: 风格指南（可选）
            
        Returns:
            QualityMetrics: 质量评估结果
            
        Raises:
            QualityAssessmentError: 当评估失败时抛出
        """
        # 输入验证
        if not content or not content.strip():
            raise QualityAssessmentError("评估内容不能为空")
        
        logger.info(f"开始质量评估: content_length={len(content)}")
        
        try:
            # 重置维度分数
            dimensions = {}
            for key, template in self.quality_dimensions.items():
                dimensions[key] = QualityDimension(
                    name=template.name,
                    score=0.0,
                    weight=template.weight,
                    issues=[],
                    suggestions=[]
                )
            
            # 并行执行各维度评估
            assessment_tasks = [
                self._assess_plot_logic(content, chapter_info),
                self._assess_character_consistency(content, characters, chapter_info),
                self._assess_language_quality(content),
                self._assess_style_consistency(content, style_guide)
            ]
            
            results = await asyncio.gather(*assessment_tasks, return_exceptions=True)
            
            # 处理评估结果
            dimension_keys = ["plot_logic", "character_consistency", "language_quality", "style_consistency"]
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"维度 {dimension_keys[i]} 评估失败: {result}")
                    dimensions[dimension_keys[i]].score = 5.0  # 默认分数
                    dimensions[dimension_keys[i]].issues.append(f"评估失败: {result}")
                else:
                    dimensions[dimension_keys[i]] = result
            
            # 计算总体分数
            overall_score = self._calculate_overall_score(dimensions)
            
            # 确定等级
            grade = self._determine_grade(overall_score)
            
            # 统计基础信息
            word_count = len(content.split())
            chapter_count = 1  # 单章节评估
            character_count = len(characters)
            
            metrics = QualityMetrics(
                overall_score=overall_score,
                dimensions=dimensions,
                grade=grade,
                assessment_time=datetime.now(),
                word_count=word_count,
                chapter_count=chapter_count,
                character_count=character_count
            )
            
            logger.info(f"质量评估完成: overall_score={overall_score}, grade={grade}")
            return metrics
            
        except Exception as e:
            logger.error(f"质量评估失败: {e}", exc_info=True)
            raise QualityAssessmentError(f"质量评估失败: {e}")
    
    async def _assess_plot_logic(
        self,
        content: str,
        chapter_info: Dict[str, Any]
    ) -> QualityDimension:
        """评估情节逻辑性."""
        prompt = f"""
请评估以下小说章节的情节逻辑性。

章节信息:
{json.dumps(chapter_info, ensure_ascii=False, indent=2)}

章节内容:
{content}

请从以下方面评估：
1. 事件发展的逻辑性和合理性
2. 因果关系是否清晰
3. 情节转折是否自然
4. 冲突设置是否合理
5. 节奏掌控是否得当

请以JSON格式返回评估结果：
{{
    "score": 评分(0-10的浮点数),
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"],
    "details": {{
        "logic_clarity": 逻辑清晰度分数(0-10),
        "pacing": 节奏分数(0-10),
        "conflict_setup": 冲突设置分数(0-10)
    }}
}}
"""
        
        try:
            response = await self.llm_client.generate(
                prompt,
                step_type="quality_assessment",
                step_name="情节逻辑评估",
                log_generation=True
            )
            data = self._parse_llm_response(response)
            
            return QualityDimension(
                name="情节逻辑",
                score=data.get("score", 5.0),
                weight=0.3,
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                details=data.get("details", {})
            )
        except Exception as e:
            logger.warning(f"情节逻辑评估失败: {e}")
            return QualityDimension(
                name="情节逻辑",
                score=5.0,
                weight=0.3,
                issues=[f"评估失败: {e}"],
                suggestions=["建议重新检查情节逻辑"]
            )
    
    async def _assess_character_consistency(
        self,
        content: str,
        characters: Dict[str, Character],
        chapter_info: Dict[str, Any]
    ) -> QualityDimension:
        """评估角色一致性."""
        try:
            # 使用已有的一致性检查器
            consistency_result = await self.consistency_checker.check_consistency(
                content, characters, chapter_info
            )
            
            # 转换为质量维度
            score = consistency_result.overall_score
            issues = [issue.description for issue in consistency_result.issues if issue.type == "character_inconsistency"]
            suggestions = consistency_result.suggestions
            
            return QualityDimension(
                name="角色一致性",
                score=score,
                weight=0.25,
                issues=issues,
                suggestions=suggestions,
                details={
                    "consistency_issues_count": len(consistency_result.issues),
                    "severity": consistency_result.severity
                }
            )
        except Exception as e:
            logger.warning(f"角色一致性评估失败: {e}")
            return QualityDimension(
                name="角色一致性",
                score=5.0,
                weight=0.25,
                issues=[f"评估失败: {e}"],
                suggestions=["建议检查角色描述的一致性"]
            )
    
    async def _assess_language_quality(self, content: str) -> QualityDimension:
        """评估语言质量."""
        prompt = f"""
请评估以下文本的语言质量。

文本内容:
{content}

请从以下方面评估：
1. 语法正确性
2. 表达清晰度
3. 词汇丰富性
4. 句式变化
5. 修辞手法运用
6. 整体流畅性

请以JSON格式返回评估结果：
{{
    "score": 评分(0-10的浮点数),
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"],
    "details": {{
        "grammar": 语法分数(0-10),
        "clarity": 清晰度分数(0-10),
        "vocabulary": 词汇分数(0-10),
        "fluency": 流畅性分数(0-10)
    }}
}}
"""
        
        try:
            response = await self.llm_client.generate(
                prompt,
                step_type="quality_assessment",
                step_name="语言质量评估",
                log_generation=True
            )
            data = self._parse_llm_response(response)
            
            return QualityDimension(
                name="语言质量",
                score=data.get("score", 5.0),
                weight=0.25,
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                details=data.get("details", {})
            )
        except Exception as e:
            logger.warning(f"语言质量评估失败: {e}")
            return QualityDimension(
                name="语言质量",
                score=5.0,
                weight=0.25,
                issues=[f"评估失败: {e}"],
                suggestions=["建议检查语言表达的准确性和流畅性"]
            )
    
    async def _assess_style_consistency(
        self,
        content: str,
        style_guide: Optional[str] = None
    ) -> QualityDimension:
        """评估风格一致性."""
        style_context = f"\n\n风格指南:\n{style_guide}" if style_guide else ""
        
        prompt = f"""
请评估以下文本的风格一致性。{style_context}

文本内容:
{content}

请从以下方面评估：
1. 叙述视角是否一致
2. 语言风格是否统一
3. 情感基调是否连贯
4. 文体特征是否保持
5. 描述风格是否协调

请以JSON格式返回评估结果：
{{
    "score": 评分(0-10的浮点数),
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"],
    "details": {{
        "narrative_perspective": 叙述视角一致性(0-10),
        "tone": 语调一致性(0-10),
        "descriptive_style": 描述风格一致性(0-10)
    }}
}}
"""
        
        try:
            response = await self.llm_client.generate(
                prompt,
                step_type="quality_assessment",
                step_name="风格一致性评估",
                log_generation=True
            )
            data = self._parse_llm_response(response)
            
            return QualityDimension(
                name="风格一致性",
                score=data.get("score", 5.0),
                weight=0.2,
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                details=data.get("details", {})
            )
        except Exception as e:
            logger.warning(f"风格一致性评估失败: {e}")
            return QualityDimension(
                name="风格一致性",
                score=5.0,
                weight=0.2,
                issues=[f"评估失败: {e}"],
                suggestions=["建议保持统一的写作风格"]
            )
    
    def _calculate_overall_score(self, dimensions: Dict[str, QualityDimension]) -> float:
        """计算总体分数."""
        if not dimensions:
            return 0.0
        
        total_weighted = sum(
            dim.score * dim.weight
            for dim in dimensions.values()
        )
        total_weight = sum(dim.weight for dim in dimensions.values())
        
        return round(total_weighted / total_weight, 2) if total_weight > 0 else 0.0
    
    def _determine_grade(self, score: float) -> str:
        """根据分数确定等级."""
        if score >= self.quality_thresholds["excellent"]:
            return "A"
        elif score >= self.quality_thresholds["good"]:
            return "B"
        elif score >= self.quality_thresholds["acceptable"]:
            return "C"
        elif score >= self.quality_thresholds["poor"]:
            return "D"
        else:
            return "F"
    
    async def generate_revision_suggestions(
        self,
        content: str,
        quality_metrics: QualityMetrics,
        target_improvements: Optional[List[str]] = None
    ) -> List[RevisionSuggestion]:
        """生成修订建议.
        
        Args:
            content: 原始内容
            quality_metrics: 质量评估结果
            target_improvements: 目标改进维度列表
            
        Returns:
            修订建议列表
        """
        suggestions = []
        
        # 如果未指定目标改进维度，则选择分数最低的维度
        if not target_improvements:
            target_improvements = [
                dim_name for dim_name, dim in quality_metrics.dimensions.items()
                if dim.score < 7.0
            ]
        
        for dim_name in target_improvements:
            if dim_name in quality_metrics.dimensions:
                dim = quality_metrics.dimensions[dim_name]
                dim_suggestions = await self._generate_dimension_suggestions(
                    content, dim_name, dim
                )
                suggestions.extend(dim_suggestions)
        
        # 按优先级排序
        suggestions.sort(key=lambda x: {
            "high": 3, "medium": 2, "low": 1
        }.get(x.priority, 0), reverse=True)
        
        return suggestions
    
    async def _generate_dimension_suggestions(
        self,
        content: str,
        dimension_name: str,
        dimension: QualityDimension
    ) -> List[RevisionSuggestion]:
        """为特定维度生成修订建议."""
        if dimension_name == "plot_logic":
            return await self._generate_plot_suggestions(content, dimension)
        elif dimension_name == "character_consistency":
            return await self._generate_character_suggestions(content, dimension)
        elif dimension_name == "language_quality":
            return await self._generate_language_suggestions(content, dimension)
        elif dimension_name == "style_consistency":
            return await self._generate_style_suggestions(content, dimension)
        else:
            return []
    
    async def _generate_plot_suggestions(
        self,
        content: str,
        dimension: QualityDimension
    ) -> List[RevisionSuggestion]:
        """生成情节相关的修订建议."""
        prompt = f"""
基于以下情节逻辑评估结果，生成具体的修订建议。

评估分数: {dimension.score}/10
发现的问题: {dimension.issues}
当前建议: {dimension.suggestions}

文本内容:
{content}

请生成具体的修订建议，包括：
1. 需要修改的具体段落或句子
2. 建议的修改方案
3. 修改原因

以JSON格式返回：
{{
    "suggestions": [
        {{
            "priority": "high/medium/low",
            "description": "建议描述",
            "target_content": "需要修改的文本片段",
            "suggested_change": "建议的修改内容",
            "reason": "修改原因"
        }}
    ]
}}
"""
        
        try:
            response = await self.llm_client.generate(
                prompt,
                step_type="quality_assessment",
                step_name="情节修订建议生成",
                log_generation=True
            )
            data = self._parse_llm_response(response)
            
            suggestions = []
            for item in data.get("suggestions", []):
                suggestions.append(RevisionSuggestion(
                    type="plot",
                    priority=item.get("priority", "medium"),
                    description=item.get("description", ""),
                    target_content=item.get("target_content", ""),
                    suggested_change=item.get("suggested_change", ""),
                    reason=item.get("reason", "")
                ))
            
            return suggestions
        except Exception as e:
            logger.warning(f"生成情节修订建议失败: {e}")
            return []
    
    async def _generate_character_suggestions(
        self,
        content: str,
        dimension: QualityDimension
    ) -> List[RevisionSuggestion]:
        """生成角色相关的修订建议."""
        # 基于一致性检查结果生成建议
        suggestions = []
        for issue in dimension.issues:
            suggestions.append(RevisionSuggestion(
                type="character",
                priority="high",
                description=f"角色一致性问题: {issue}",
                target_content="",
                suggested_change="检查并修正角色描述",
                reason="保持角色一致性"
            ))
        
        return suggestions
    
    async def _generate_language_suggestions(
        self,
        content: str,
        dimension: QualityDimension
    ) -> List[RevisionSuggestion]:
        """生成语言质量相关的修订建议."""
        prompt = f"""
基于语言质量评估结果，生成具体的语言修订建议。

评估分数: {dimension.score}/10
发现的问题: {dimension.issues}

文本内容:
{content}

请生成语言改进建议，重点关注：
1. 语法错误修正
2. 表达优化
3. 词汇替换
4. 句式改进

以JSON格式返回建议列表。
"""
        
        try:
            response = await self.llm_client.generate(
                prompt,
                step_type="quality_assessment",
                step_name="语言修订建议生成",
                log_generation=True
            )
            data = self._parse_llm_response(response)
            
            suggestions = []
            for item in data.get("suggestions", []):
                suggestions.append(RevisionSuggestion(
                    type="language",
                    priority=item.get("priority", "medium"),
                    description=item.get("description", ""),
                    target_content=item.get("target_content", ""),
                    suggested_change=item.get("suggested_change", ""),
                    reason=item.get("reason", "")
                ))
            
            return suggestions
        except Exception as e:
            logger.warning(f"生成语言修订建议失败: {e}")
            return []
    
    async def _generate_style_suggestions(
        self,
        content: str,
        dimension: QualityDimension
    ) -> List[RevisionSuggestion]:
        """生成风格相关的修订建议."""
        suggestions = []
        for issue in dimension.issues:
            suggestions.append(RevisionSuggestion(
                type="style",
                priority="medium",
                description=f"风格一致性问题: {issue}",
                target_content="",
                suggested_change="调整文本风格以保持一致性",
                reason="维护整体风格统一"
            ))
        
        return suggestions
    
    async def execute_revision(
        self,
        content: str,
        suggestion: RevisionSuggestion,
        preserve_style: bool = True
    ) -> RevisionResult:
        """执行具体的修订操作.
        
        Args:
            content: 原始内容
            suggestion: 修订建议
            preserve_style: 是否保持原有风格
            
        Returns:
            修订结果
        """
        prompt = f"""
请根据以下修订建议对文本进行修改。

原始文本:
{content}

修订建议:
- 类型: {suggestion.type}
- 描述: {suggestion.description}
- 目标内容: {suggestion.target_content}
- 建议修改: {suggestion.suggested_change}
- 修改原因: {suggestion.reason}

要求:
1. 只修改需要改进的部分
2. 保持整体结构和逻辑
{"3. 保持原有的写作风格和语调" if preserve_style else "3. 可以适当调整写作风格"}
4. 确保修改后的内容更加优质

请返回修改后的完整文本。
"""
        
        try:
            revised_content = await self.llm_client.generate(
                prompt,
                step_type="quality_assessment",
                step_name="内容修订执行",
                log_generation=True
            )
            
            # 简单的变更检测
            changes_made = [f"应用了{suggestion.type}类型的修订: {suggestion.description}"]
            
            return RevisionResult(
                original_content=content,
                revised_content=revised_content,
                changes_made=changes_made,
                improvement_score=0.5,  # 预估改进分数
                revision_type=suggestion.type,
                revision_time=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"执行修订失败: {e}")
            raise QualityAssessmentError(f"执行修订失败: {e}")
    
    async def iterative_revision(
        self,
        content: str,
        characters: Dict[str, Character],
        chapter_info: Dict[str, Any],
        target_score: float = 8.0,
        max_iterations: Optional[int] = None
    ) -> Tuple[str, List[RevisionResult], QualityMetrics]:
        """执行迭代修订直到达到目标质量.
        
        Args:
            content: 原始内容
            characters: 角色信息
            chapter_info: 章节信息
            target_score: 目标分数
            max_iterations: 最大迭代次数
            
        Returns:
            (修订后内容, 修订历史, 最终质量评估)
        """
        if max_iterations is None:
            max_iterations = self.revision_config["max_iterations"]
        
        current_content = content
        revision_history = []
        
        for iteration in range(max_iterations):
            # 评估当前质量
            metrics = await self.assess_quality(current_content, characters, chapter_info)
            
            logger.info(f"迭代 {iteration + 1}: 当前分数 {metrics.overall_score}")
            
            # 检查是否达到目标
            if metrics.overall_score >= target_score:
                logger.info(f"达到目标质量分数 {target_score}")
                break
            
            # 生成修订建议
            suggestions = await self.generate_revision_suggestions(current_content, metrics)
            
            if not suggestions:
                logger.info("没有更多修订建议")
                break
            
            # 执行优先级最高的修订
            revision_result = await self.execute_revision(
                current_content, 
                suggestions[0],
                self.revision_config["preserve_style"]
            )
            
            current_content = revision_result.revised_content
            revision_history.append(revision_result)
            
            # 检查改进是否足够
            if iteration > 0:
                last_improvement = revision_result.improvement_score
                if last_improvement < self.revision_config["min_improvement"]:
                    logger.info(f"改进幅度过小 ({last_improvement})，停止迭代")
                    break
        
        # 最终评估
        final_metrics = await self.assess_quality(current_content, characters, chapter_info)
        
        return current_content, revision_history, final_metrics
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM的JSON响应."""
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
            logger.warning(f"JSON解析失败: {e}, 响应: {response[:200]}...")
            return {}


# 为了向后兼容，创建别名
QualityAssessment = QualityAssessmentSystem