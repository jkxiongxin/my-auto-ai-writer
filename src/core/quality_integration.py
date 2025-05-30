"""质量评估集成模块，整合质量评估系统到整体流程中."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from src.core.quality_assessment import (
    QualityAssessmentSystem,
    QualityMetrics,
    RevisionSuggestion,
    RevisionResult
)
from src.core.character_system import Character, CharacterDatabase
from src.core.consistency_checker import BasicConsistencyChecker, ConsistencyCheckResult
from src.utils.llm_client import UniversalLLMClient

logger = logging.getLogger(__name__)


class QualityIntegrationError(Exception):
    """质量集成异常."""
    pass


class EnhancedQualityChecker:
    """增强质量检查器，整合多种质量评估功能.
    
    结合基础一致性检查和高级质量评估，
    提供完整的小说质量检查和改进服务。
    
    Attributes:
        llm_client: LLM客户端实例
        quality_system: 质量评估系统实例
        consistency_checker: 一致性检查器实例
    """
    
    def __init__(
        self,
        llm_client: UniversalLLMClient,
        quality_thresholds: Optional[Dict[str, float]] = None,
        revision_config: Optional[Dict[str, Any]] = None
    ):
        """初始化增强质量检查器.
        
        Args:
            llm_client: 统一LLM客户端实例
            quality_thresholds: 质量阈值配置
            revision_config: 修订配置
            
        Raises:
            ValueError: 当llm_client为None时抛出
        """
        if llm_client is None:
            raise ValueError("llm_client不能为None")
        
        self.llm_client = llm_client
        
        # 创建组件实例
        self.consistency_checker = BasicConsistencyChecker(llm_client)
        self.quality_system = QualityAssessmentSystem(
            llm_client=llm_client,
            consistency_checker=self.consistency_checker,
            quality_thresholds=quality_thresholds,
            revision_config=revision_config
        )
        
        logger.info("增强质量检查器初始化完成")
    
    async def comprehensive_quality_check(
        self,
        content: str,
        characters: Dict[str, Character],
        chapter_info: Dict[str, Any],
        style_guide: Optional[str] = None,
        include_suggestions: bool = True
    ) -> Dict[str, Any]:
        """执行全面质量检查.
        
        Args:
            content: 待检查的文本内容
            characters: 角色信息字典
            chapter_info: 章节信息
            style_guide: 风格指南（可选）
            include_suggestions: 是否包含改进建议
            
        Returns:
            包含质量评估和建议的完整报告
            
        Raises:
            QualityIntegrationError: 当检查失败时抛出
        """
        try:
            logger.info(f"开始全面质量检查: content_length={len(content)}")
            
            # 1. 执行质量评估
            quality_metrics = await self.quality_system.assess_quality(
                content, characters, chapter_info, style_guide
            )
            
            # 2. 执行一致性检查
            consistency_result = await self.consistency_checker.check_consistency(
                content, characters, chapter_info
            )
            
            # 3. 生成修订建议（如果需要）
            revision_suggestions = []
            if include_suggestions and quality_metrics.overall_score < 8.0:
                revision_suggestions = await self.quality_system.generate_revision_suggestions(
                    content, quality_metrics
                )
            
            # 4. 编译完整报告
            report = self._compile_quality_report(
                quality_metrics,
                consistency_result,
                revision_suggestions,
                content
            )
            
            logger.info(f"全面质量检查完成: overall_score={quality_metrics.overall_score}")
            return report
            
        except Exception as e:
            logger.error(f"全面质量检查失败: {e}", exc_info=True)
            raise QualityIntegrationError(f"全面质量检查失败: {e}")
    
    async def batch_quality_check(
        self,
        contents: List[str],
        characters: Dict[str, Character],
        chapter_infos: List[Dict[str, Any]],
        style_guide: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """批量质量检查.
        
        Args:
            contents: 待检查的文本内容列表
            characters: 角色信息字典
            chapter_infos: 章节信息列表
            style_guide: 风格指南（可选）
            
        Returns:
            质量检查报告列表
            
        Raises:
            QualityIntegrationError: 当检查失败时抛出
        """
        if len(contents) != len(chapter_infos):
            raise QualityIntegrationError("内容数量与章节信息数量不匹配")
        
        logger.info(f"开始批量质量检查: {len(contents)}个内容")
        
        results = []
        for i, (content, chapter_info) in enumerate(zip(contents, chapter_infos)):
            try:
                report = await self.comprehensive_quality_check(
                    content, characters, chapter_info, style_guide, include_suggestions=False
                )
                results.append(report)
                logger.debug(f"完成第{i+1}个内容的质量检查")
            except Exception as e:
                logger.error(f"第{i+1}个内容质量检查失败: {e}")
                # 创建错误报告
                error_report = {
                    "overall_score": 0.0,
                    "grade": "F",
                    "error": str(e),
                    "checked_at": datetime.now().isoformat()
                }
                results.append(error_report)
        
        logger.info(f"批量质量检查完成: {len(results)}个结果")
        return results
    
    async def intelligent_revision(
        self,
        content: str,
        characters: Dict[str, Character],
        chapter_info: Dict[str, Any],
        target_score: float = 8.0,
        max_iterations: int = 3,
        style_guide: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """智能修订内容直到达到目标质量.
        
        Args:
            content: 原始内容
            characters: 角色信息
            chapter_info: 章节信息
            target_score: 目标分数
            max_iterations: 最大迭代次数
            style_guide: 风格指南（可选）
            
        Returns:
            (修订后内容, 修订历史, 最终质量报告)
        """
        try:
            logger.info(f"开始智能修订: target_score={target_score}")
            
            # 执行迭代修订
            revised_content, revision_history, final_metrics = await self.quality_system.iterative_revision(
                content, characters, chapter_info, target_score, max_iterations
            )
            
            # 最终质量检查
            final_consistency = await self.consistency_checker.check_consistency(
                revised_content, characters, chapter_info
            )
            
            # 编译最终报告
            final_report = self._compile_quality_report(
                final_metrics, final_consistency, [], revised_content
            )
            
            # 格式化修订历史
            formatted_history = []
            for revision in revision_history:
                formatted_history.append({
                    "revision_type": revision.revision_type,
                    "changes_made": revision.changes_made,
                    "improvement_score": revision.improvement_score,
                    "revision_time": revision.revision_time.isoformat()
                })
            
            logger.info(f"智能修订完成: 执行{len(revision_history)}次修订")
            return revised_content, formatted_history, final_report
            
        except Exception as e:
            logger.error(f"智能修订失败: {e}", exc_info=True)
            raise QualityIntegrationError(f"智能修订失败: {e}")
    
    def _compile_quality_report(
        self,
        quality_metrics: QualityMetrics,
        consistency_result: ConsistencyCheckResult,
        revision_suggestions: List[RevisionSuggestion],
        content: str
    ) -> Dict[str, Any]:
        """编译质量报告.
        
        Args:
            quality_metrics: 质量评估结果
            consistency_result: 一致性检查结果
            revision_suggestions: 修订建议列表
            content: 原始内容
            
        Returns:
            完整的质量报告字典
        """
        # 转换维度信息
        dimensions = {}
        for name, dimension in quality_metrics.dimensions.items():
            dimensions[name] = {
                "name": dimension.name,
                "score": dimension.score,
                "weight": dimension.weight,
                "issues": dimension.issues,
                "suggestions": dimension.suggestions,
                "details": dimension.details
            }
        
        # 转换一致性问题
        consistency_issues = []
        for issue in consistency_result.issues:
            consistency_issues.append({
                "type": issue.type,
                "character": issue.character,
                "field": issue.field,
                "description": issue.description,
                "severity": issue.severity,
                "line_context": issue.line_context,
                "suggestion": issue.suggestion
            })
        
        # 转换修订建议
        formatted_suggestions = []
        for suggestion in revision_suggestions:
            formatted_suggestions.append({
                "type": suggestion.type,
                "priority": suggestion.priority,
                "description": suggestion.description,
                "target_content": suggestion.target_content,
                "suggested_change": suggestion.suggested_change,
                "reason": suggestion.reason
            })
        
        # 计算统合分数（质量评估 + 一致性）
        integrated_score = (quality_metrics.overall_score + consistency_result.overall_score) / 2
        
        return {
            "overall_score": round(integrated_score, 2),
            "grade": quality_metrics.grade,
            "assessment_time": quality_metrics.assessment_time.isoformat(),
            "word_count": quality_metrics.word_count,
            "chapter_count": quality_metrics.chapter_count,
            "character_count": quality_metrics.character_count,
            "quality_dimensions": dimensions,
            "consistency": {
                "score": consistency_result.overall_score,
                "severity": consistency_result.severity,
                "issues": consistency_issues,
                "suggestions": consistency_result.suggestions
            },
            "revision_suggestions": formatted_suggestions,
            "summary": self._generate_summary(quality_metrics, consistency_result),
            "recommendations": self._generate_recommendations(quality_metrics, consistency_result)
        }
    
    def _generate_summary(
        self,
        quality_metrics: QualityMetrics,
        consistency_result: ConsistencyCheckResult
    ) -> str:
        """生成质量总结.
        
        Args:
            quality_metrics: 质量评估结果
            consistency_result: 一致性检查结果
            
        Returns:
            质量总结文本
        """
        avg_score = (quality_metrics.overall_score + consistency_result.overall_score) / 2
        
        if avg_score >= 9.0:
            return "内容质量优秀，各维度表现均衡，建议保持当前水准。"
        elif avg_score >= 7.5:
            return "内容质量良好，存在少量可改进的地方。"
        elif avg_score >= 6.0:
            return "内容质量可接受，建议重点关注得分较低的维度。"
        elif avg_score >= 4.0:
            return "内容质量需要改进，存在较多问题需要修复。"
        else:
            return "内容质量较差，建议进行全面修订。"
    
    def _generate_recommendations(
        self,
        quality_metrics: QualityMetrics,
        consistency_result: ConsistencyCheckResult
    ) -> List[str]:
        """生成改进建议.
        
        Args:
            quality_metrics: 质量评估结果
            consistency_result: 一致性检查结果
            
        Returns:
            改进建议列表
        """
        recommendations = []
        
        # 基于质量维度生成建议
        for name, dimension in quality_metrics.dimensions.items():
            if dimension.score < 7.0:
                recommendations.append(f"改进{dimension.name}：当前分数{dimension.score:.1f}")
        
        # 基于一致性问题生成建议
        if consistency_result.overall_score < 7.0:
            recommendations.append(f"提高内容一致性：当前分数{consistency_result.overall_score:.1f}")
        
        # 基于问题严重程度生成建议
        high_severity_issues = [
            issue for issue in consistency_result.issues 
            if issue.severity == "high"
        ]
        if high_severity_issues:
            recommendations.append(f"优先修复{len(high_severity_issues)}个高严重性一致性问题")
        
        # 如果没有具体建议，提供通用建议
        if not recommendations:
            recommendations.append("整体质量良好，可考虑细节优化")
        
        return recommendations
    
    def get_quality_trends(
        self,
        historical_reports: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析质量趋势.
        
        Args:
            historical_reports: 历史质量报告列表
            
        Returns:
            质量趋势分析结果
        """
        if not historical_reports:
            return {"error": "没有历史数据"}
        
        # 提取分数序列
        scores = [report.get("overall_score", 0) for report in historical_reports]
        
        # 计算趋势
        if len(scores) >= 2:
            trend = "上升" if scores[-1] > scores[0] else "下降" if scores[-1] < scores[0] else "稳定"
            improvement = round(scores[-1] - scores[0], 2)
        else:
            trend = "稳定"
            improvement = 0.0
        
        # 计算平均分和最佳分
        avg_score = round(sum(scores) / len(scores), 2)
        best_score = max(scores)
        worst_score = min(scores)
        
        return {
            "trend": trend,
            "improvement": improvement,
            "average_score": avg_score,
            "best_score": best_score,
            "worst_score": worst_score,
            "total_checks": len(historical_reports),
            "latest_score": scores[-1] if scores else 0
        }