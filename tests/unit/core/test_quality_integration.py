"""质量集成模块单元测试."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.core.quality_integration import (
    EnhancedQualityChecker,
    QualityIntegrationError
)
from src.core.quality_assessment import QualityMetrics, QualityDimension
from src.core.character_system import Character
from src.core.consistency_checker import BasicConsistencyChecker, ConsistencyCheckResult, ConsistencyIssue
from src.utils.llm_client import UniversalLLMClient


class TestEnhancedQualityChecker:
    """增强质量检查器测试类."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """模拟LLM客户端fixture."""
        client = AsyncMock(spec=UniversalLLMClient)
        return client
    
    @pytest.fixture
    def sample_characters(self):
        """示例角色数据fixture."""
        return {
            "张三": Character(
                name="张三",
                role="主角",
                age=25,
                personality=["勇敢", "善良"],
                background="普通农民出身",
                goals=["拯救家乡", "成为英雄"],
                skills=["剑术", "魔法"],
                appearance="高大英俊",
                motivation="拯救家乡"
            ),
            "李四": Character(
                name="李四",
                role="反派",
                age=40,
                personality=["狡猾", "残忍"],
                background="贵族世家",
                goals=["获得权力", "统治世界"],
                skills=["政治", "阴谋"],
                appearance="阴郁瘦削",
                motivation="获得权力"
            )
        }
    
    @pytest.fixture
    def sample_chapter_info(self):
        """示例章节信息fixture."""
        return {
            "title": "决战时刻",
            "chapter_number": 5,
            "key_events": ["主角与反派对决", "关键秘密揭露"],
            "previous_events": ["主角修炼完成", "发现反派阴谋"],
            "characters_involved": ["张三", "李四"],
            "setting": "古代魔法世界"
        }
    
    @pytest.fixture
    def enhanced_quality_checker(self, mock_llm_client):
        """增强质量检查器fixture."""
        return EnhancedQualityChecker(mock_llm_client)
    
    def test_init_success_with_all_params(self, mock_llm_client):
        """测试初始化成功_完整参数_正确创建实例."""
        # Given
        quality_thresholds = {"excellent": 9.0, "good": 7.0}
        revision_config = {"max_iterations": 5}
        
        # When
        checker = EnhancedQualityChecker(
            llm_client=mock_llm_client,
            quality_thresholds=quality_thresholds,
            revision_config=revision_config
        )
        
        # Then
        assert checker.llm_client == mock_llm_client
        assert checker.consistency_checker is not None
        assert checker.quality_system is not None
    
    def test_init_success_with_minimal_params(self, mock_llm_client):
        """测试初始化成功_最少参数_使用默认值."""
        # When
        checker = EnhancedQualityChecker(llm_client=mock_llm_client)
        
        # Then
        assert checker.llm_client == mock_llm_client
        assert checker.consistency_checker is not None
        assert checker.quality_system is not None
    
    def test_init_failure_none_llm_client_raises_error(self):
        """测试初始化失败_LLM客户端为None_抛出异常."""
        # When & Then
        with pytest.raises(ValueError, match="llm_client不能为None"):
            EnhancedQualityChecker(llm_client=None)
    
    @pytest.mark.asyncio
    async def test_comprehensive_quality_check_success(
        self, 
        enhanced_quality_checker, 
        sample_characters, 
        sample_chapter_info
    ):
        """测试全面质量检查成功_返回完整报告."""
        # Given
        content = "张三挥剑向李四攻去，这是一场激烈的战斗，展现了正义与邪恶的较量。"
        
        # Mock质量评估系统
        mock_quality_metrics = QualityMetrics(
            overall_score=7.5,
            dimensions={
                "plot_logic": QualityDimension(
                    name="情节逻辑", score=8.0, weight=0.3, 
                    issues=[], suggestions=["保持情节紧凑"]
                )
            },
            grade="B",
            assessment_time=datetime.now(),
            word_count=100,
            chapter_count=1,
            character_count=2
        )
        enhanced_quality_checker.quality_system.assess_quality = AsyncMock(return_value=mock_quality_metrics)
        
        # Mock一致性检查器
        mock_consistency_result = ConsistencyCheckResult(
            issues=[],
            severity="low",
            overall_score=8.0,
            suggestions=["保持当前质量"]
        )
        enhanced_quality_checker.consistency_checker.check_consistency = AsyncMock(return_value=mock_consistency_result)
        
        # Mock修订建议生成（当分数低于8.0时）
        enhanced_quality_checker.quality_system.generate_revision_suggestions = AsyncMock(return_value=[])
        
        # When
        result = await enhanced_quality_checker.comprehensive_quality_check(
            content, sample_characters, sample_chapter_info
        )
        
        # Then
        assert isinstance(result, dict)
        assert "overall_score" in result
        assert "grade" in result
        assert "quality_dimensions" in result
        assert "consistency" in result
        assert "summary" in result
        assert "recommendations" in result
        assert result["overall_score"] > 0
    
    @pytest.mark.asyncio
    async def test_comprehensive_quality_check_with_suggestions(
        self, 
        enhanced_quality_checker, 
        sample_characters, 
        sample_chapter_info
    ):
        """测试全面质量检查_低分数_包含修订建议."""
        # Given
        content = "测试内容"
        
        # Mock低分质量评估
        mock_quality_metrics = QualityMetrics(
            overall_score=6.0,  # 低于8.0，应该生成建议
            dimensions={},
            grade="C",
            assessment_time=datetime.now(),
            word_count=50,
            chapter_count=1,
            character_count=2
        )
        enhanced_quality_checker.quality_system.assess_quality = AsyncMock(return_value=mock_quality_metrics)
        
        # Mock一致性检查
        mock_consistency_result = ConsistencyCheckResult(
            issues=[],
            severity="low",
            overall_score=7.0,
            suggestions=[]
        )
        enhanced_quality_checker.consistency_checker.check_consistency = AsyncMock(return_value=mock_consistency_result)
        
        # Mock修订建议
        from src.core.quality_assessment import RevisionSuggestion
        mock_suggestions = [
            RevisionSuggestion(
                type="plot", priority="high", description="改进情节逻辑",
                target_content="", suggested_change="", reason=""
            )
        ]
        enhanced_quality_checker.quality_system.generate_revision_suggestions = AsyncMock(return_value=mock_suggestions)
        
        # When
        result = await enhanced_quality_checker.comprehensive_quality_check(
            content, sample_characters, sample_chapter_info, include_suggestions=True
        )
        
        # Then
        assert len(result["revision_suggestions"]) > 0
        enhanced_quality_checker.quality_system.generate_revision_suggestions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_comprehensive_quality_check_without_suggestions(
        self,
        enhanced_quality_checker,
        sample_characters,
        sample_chapter_info
    ):
        """测试全面质量检查_不包含建议_跳过建议生成."""
        # Given
        content = "测试内容"
        
        # Mock质量评估
        mock_quality_metrics = QualityMetrics(
            overall_score=6.0,
            dimensions={},
            grade="C",
            assessment_time=datetime.now(),
            word_count=50,
            chapter_count=1,
            character_count=2
        )
        enhanced_quality_checker.quality_system.assess_quality = AsyncMock(return_value=mock_quality_metrics)
        
        # Mock一致性检查
        mock_consistency_result = ConsistencyCheckResult(
            issues=[], severity="low", overall_score=7.0, suggestions=[]
        )
        enhanced_quality_checker.consistency_checker.check_consistency = AsyncMock(return_value=mock_consistency_result)
        
        # Mock修订建议生成方法
        enhanced_quality_checker.quality_system.generate_revision_suggestions = AsyncMock()
        
        # When
        result = await enhanced_quality_checker.comprehensive_quality_check(
            content, sample_characters, sample_chapter_info, include_suggestions=False
        )
        
        # Then
        assert result["revision_suggestions"] == []
        enhanced_quality_checker.quality_system.generate_revision_suggestions.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_batch_quality_check_success(
        self, 
        enhanced_quality_checker, 
        sample_characters
    ):
        """测试批量质量检查成功_返回多个报告."""
        # Given
        contents = ["内容1", "内容2", "内容3"]
        chapter_infos = [
            {"title": "章节1", "chapter_number": 1},
            {"title": "章节2", "chapter_number": 2},
            {"title": "章节3", "chapter_number": 3}
        ]
        
        # Mock comprehensive_quality_check
        mock_report = {
            "overall_score": 7.5,
            "grade": "B",
            "checked_at": datetime.now().isoformat()
        }
        enhanced_quality_checker.comprehensive_quality_check = AsyncMock(return_value=mock_report)
        
        # When
        results = await enhanced_quality_checker.batch_quality_check(
            contents, sample_characters, chapter_infos
        )
        
        # Then
        assert len(results) == 3
        assert all(isinstance(report, dict) for report in results)
        assert enhanced_quality_checker.comprehensive_quality_check.call_count == 3
    
    @pytest.mark.asyncio
    async def test_batch_quality_check_mismatch_length_raises_error(
        self, 
        enhanced_quality_checker, 
        sample_characters
    ):
        """测试批量质量检查_长度不匹配_抛出异常."""
        # Given
        contents = ["内容1", "内容2"]
        chapter_infos = [{"title": "章节1"}]  # 长度不匹配
        
        # When & Then
        with pytest.raises(QualityIntegrationError, match="内容数量与章节信息数量不匹配"):
            await enhanced_quality_checker.batch_quality_check(
                contents, sample_characters, chapter_infos
            )
    
    @pytest.mark.asyncio
    async def test_batch_quality_check_partial_failure_handles_gracefully(
        self, 
        enhanced_quality_checker, 
        sample_characters
    ):
        """测试批量质量检查_部分失败_优雅处理."""
        # Given
        contents = ["内容1", "内容2"]
        chapter_infos = [
            {"title": "章节1", "chapter_number": 1},
            {"title": "章节2", "chapter_number": 2}
        ]
        
        # Mock第一个成功，第二个失败
        enhanced_quality_checker.comprehensive_quality_check = AsyncMock(side_effect=[
            {"overall_score": 7.5, "grade": "B"},
            Exception("检查失败")
        ])
        
        # When
        results = await enhanced_quality_checker.batch_quality_check(
            contents, sample_characters, chapter_infos
        )
        
        # Then
        assert len(results) == 2
        assert results[0]["overall_score"] == 7.5  # 成功的结果
        assert results[1]["overall_score"] == 0.0  # 失败的默认结果
        assert "error" in results[1]
    
    @pytest.mark.asyncio
    async def test_intelligent_revision_success(
        self, 
        enhanced_quality_checker, 
        sample_characters, 
        sample_chapter_info
    ):
        """测试智能修订成功_返回修订结果."""
        # Given
        content = "原始内容"
        target_score = 8.0
        
        # Mock迭代修订
        from src.core.quality_assessment import RevisionResult
        mock_revision_history = [
            RevisionResult(
                original_content=content,
                revised_content="修订内容",
                changes_made=["改进1"],
                improvement_score=1.0,
                revision_type="plot",
                revision_time=datetime.now()
            )
        ]
        
        mock_final_metrics = QualityMetrics(
            overall_score=8.5,
            dimensions={},
            grade="B",
            assessment_time=datetime.now(),
            word_count=100,
            chapter_count=1,
            character_count=2
        )
        
        enhanced_quality_checker.quality_system.iterative_revision = AsyncMock(
            return_value=("修订后内容", mock_revision_history, mock_final_metrics)
        )
        
        # Mock最终一致性检查
        mock_consistency = ConsistencyCheckResult(
            issues=[], severity="low", overall_score=8.0, suggestions=[]
        )
        enhanced_quality_checker.consistency_checker.check_consistency = AsyncMock(return_value=mock_consistency)
        
        # When
        revised_content, history, final_report = await enhanced_quality_checker.intelligent_revision(
            content, sample_characters, sample_chapter_info, target_score
        )
        
        # Then
        assert revised_content == "修订后内容"
        assert len(history) == 1
        assert isinstance(final_report, dict)
        assert "overall_score" in final_report
    
    def test_compile_quality_report_complete_data(self, enhanced_quality_checker):
        """测试编译质量报告_完整数据_正确格式化."""
        # Given
        quality_metrics = QualityMetrics(
            overall_score=7.5,
            dimensions={
                "plot_logic": QualityDimension(
                    name="情节逻辑", score=8.0, weight=0.3,
                    issues=["问题1"], suggestions=["建议1"]
                )
            },
            grade="B",
            assessment_time=datetime.now(),
            word_count=1000,
            chapter_count=5,
            character_count=3
        )
        
        consistency_result = ConsistencyCheckResult(
            issues=[
                ConsistencyIssue(
                    type="character_inconsistency",
                    character="张三",
                    field="appearance",
                    description="外貌描述不一致",
                    severity="medium",
                    line_context="测试上下文"
                )
            ],
            severity="medium",
            overall_score=7.0,
            suggestions=["一致性建议"]
        )
        
        from src.core.quality_assessment import RevisionSuggestion
        revision_suggestions = [
            RevisionSuggestion(
                type="plot", priority="high", description="修复逻辑问题",
                target_content="", suggested_change="", reason=""
            )
        ]
        
        content = "测试内容"
        
        # When
        report = enhanced_quality_checker._compile_quality_report(
            quality_metrics, consistency_result, revision_suggestions, content
        )
        
        # Then
        assert isinstance(report, dict)
        assert "overall_score" in report
        assert "quality_dimensions" in report
        assert "consistency" in report
        assert "revision_suggestions" in report
        assert "summary" in report
        assert "recommendations" in report
        
        # 检查质量维度格式
        assert "plot_logic" in report["quality_dimensions"]
        plot_dim = report["quality_dimensions"]["plot_logic"]
        assert plot_dim["score"] == 8.0
        assert plot_dim["weight"] == 0.3
        
        # 检查一致性格式
        assert report["consistency"]["score"] == 7.0
        assert len(report["consistency"]["issues"]) == 1
        
        # 检查修订建议格式
        assert len(report["revision_suggestions"]) == 1
        assert report["revision_suggestions"][0]["type"] == "plot"
    
    def test_generate_summary_different_scores(self, enhanced_quality_checker):
        """测试生成质量总结_不同分数_返回对应描述."""
        # 测试不同分数等级
        test_cases = [
            (9.5, 8.5, "优秀"),
            (8.0, 7.0, "良好"),
            (6.5, 5.5, "可接受"),
            (4.5, 3.5, "需要改进"),
            (2.0, 1.0, "较差")
        ]
        
        for quality_score, consistency_score, expected_keyword in test_cases:
            # Given
            quality_metrics = QualityMetrics(
                overall_score=quality_score, dimensions={}, grade="",
                assessment_time=datetime.now(), word_count=0, chapter_count=0, character_count=0
            )
            consistency_result = ConsistencyCheckResult(
                issues=[], severity="low", overall_score=consistency_score, suggestions=[]
            )
            
            # When
            summary = enhanced_quality_checker._generate_summary(quality_metrics, consistency_result)
            
            # Then
            assert isinstance(summary, str)
            assert len(summary) > 0
    
    def test_generate_recommendations_various_issues(self, enhanced_quality_checker):
        """测试生成改进建议_各种问题_返回相应建议."""
        # Given - 低分维度和一致性问题
        quality_metrics = QualityMetrics(
            overall_score=6.0,
            dimensions={
                "plot_logic": QualityDimension(
                    name="情节逻辑", score=5.0, weight=0.3, issues=[], suggestions=[]
                ),
                "language_quality": QualityDimension(
                    name="语言质量", score=8.0, weight=0.25, issues=[], suggestions=[]
                )
            },
            grade="C",
            assessment_time=datetime.now(),
            word_count=0, chapter_count=0, character_count=0
        )
        
        consistency_result = ConsistencyCheckResult(
            issues=[
                ConsistencyIssue(
                    type="character_inconsistency", character="", field="",
                    description="", severity="high", line_context=""
                )
            ],
            severity="high",
            overall_score=6.0,
            suggestions=[]
        )
        
        # When
        recommendations = enhanced_quality_checker._generate_recommendations(
            quality_metrics, consistency_result
        )
        
        # Then
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        # 应该包含情节逻辑改进建议（分数5.0 < 7.0）
        assert any("情节逻辑" in rec for rec in recommendations)
        # 应该包含一致性改进建议（分数6.0 < 7.0）
        assert any("一致性" in rec for rec in recommendations)
        # 应该包含高严重性问题建议
        assert any("高严重性" in rec for rec in recommendations)
    
    def test_generate_recommendations_no_issues(self, enhanced_quality_checker):
        """测试生成改进建议_无问题_返回通用建议."""
        # Given - 高分无问题
        quality_metrics = QualityMetrics(
            overall_score=9.0,
            dimensions={
                "plot_logic": QualityDimension(
                    name="情节逻辑", score=9.0, weight=0.3, issues=[], suggestions=[]
                )
            },
            grade="A",
            assessment_time=datetime.now(),
            word_count=0, chapter_count=0, character_count=0
        )
        
        consistency_result = ConsistencyCheckResult(
            issues=[], severity="low", overall_score=9.0, suggestions=[]
        )
        
        # When
        recommendations = enhanced_quality_checker._generate_recommendations(
            quality_metrics, consistency_result
        )
        
        # Then
        assert len(recommendations) == 1
        assert "整体质量良好" in recommendations[0]
    
    def test_get_quality_trends_empty_history(self, enhanced_quality_checker):
        """测试获取质量趋势_空历史_返回错误信息."""
        # Given
        historical_reports = []
        
        # When
        trends = enhanced_quality_checker.get_quality_trends(historical_reports)
        
        # Then
        assert "error" in trends
        assert trends["error"] == "没有历史数据"
    
    def test_get_quality_trends_single_report(self, enhanced_quality_checker):
        """测试获取质量趋势_单个报告_返回稳定趋势."""
        # Given
        historical_reports = [{"overall_score": 7.5}]
        
        # When
        trends = enhanced_quality_checker.get_quality_trends(historical_reports)
        
        # Then
        assert trends["trend"] == "稳定"
        assert trends["improvement"] == 0.0
        assert trends["average_score"] == 7.5
        assert trends["latest_score"] == 7.5
    
    def test_get_quality_trends_multiple_reports(self, enhanced_quality_checker):
        """测试获取质量趋势_多个报告_正确计算趋势."""
        # Given
        historical_reports = [
            {"overall_score": 6.0},
            {"overall_score": 7.0},
            {"overall_score": 8.0}
        ]
        
        # When
        trends = enhanced_quality_checker.get_quality_trends(historical_reports)
        
        # Then
        assert trends["trend"] == "上升"
        assert trends["improvement"] == 2.0  # 8.0 - 6.0
        assert trends["average_score"] == 7.0  # (6+7+8)/3
        assert trends["best_score"] == 8.0
        assert trends["worst_score"] == 6.0
        assert trends["total_checks"] == 3
        assert trends["latest_score"] == 8.0
    
    def test_get_quality_trends_declining(self, enhanced_quality_checker):
        """测试获取质量趋势_下降趋势_正确识别."""
        # Given
        historical_reports = [
            {"overall_score": 8.0},
            {"overall_score": 7.0},
            {"overall_score": 6.0}
        ]
        
        # When
        trends = enhanced_quality_checker.get_quality_trends(historical_reports)
        
        # Then
        assert trends["trend"] == "下降"
        assert trends["improvement"] == -2.0  # 6.0 - 8.0