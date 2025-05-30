"""质量评估系统单元测试."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.core.quality_assessment import (
    QualityAssessmentSystem,
    QualityAssessmentError,
    QualityDimension,
    QualityMetrics,
    RevisionSuggestion,
    RevisionResult
)
from src.core.character_system import Character
from src.core.consistency_checker import BasicConsistencyChecker, ConsistencyCheckResult, ConsistencyIssue
from src.utils.llm_client import UniversalLLMClient


class TestQualityAssessmentSystem:
    """质量评估系统测试类."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """模拟LLM客户端fixture."""
        client = AsyncMock(spec=UniversalLLMClient)
        return client
    
    @pytest.fixture
    def mock_consistency_checker(self, mock_llm_client):
        """模拟一致性检查器fixture."""
        checker = AsyncMock(spec=BasicConsistencyChecker)
        checker.check_consistency.return_value = ConsistencyCheckResult(
            issues=[],
            severity="low",
            overall_score=8.5,
            suggestions=["保持当前质量"]
        )
        return checker
    
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
    def quality_assessment_system(self, mock_llm_client, mock_consistency_checker):
        """质量评估系统fixture."""
        return QualityAssessmentSystem(
            llm_client=mock_llm_client,
            consistency_checker=mock_consistency_checker
        )
    
    def test_init_success_with_all_params(self, mock_llm_client, mock_consistency_checker):
        """测试初始化成功_完整参数_正确创建实例."""
        # Given
        quality_thresholds = {"excellent": 9.0, "good": 7.0}
        revision_config = {"max_iterations": 5}
        
        # When
        system = QualityAssessmentSystem(
            llm_client=mock_llm_client,
            consistency_checker=mock_consistency_checker,
            quality_thresholds=quality_thresholds,
            revision_config=revision_config
        )
        
        # Then
        assert system.llm_client == mock_llm_client
        assert system.consistency_checker == mock_consistency_checker
        assert system.quality_thresholds == quality_thresholds
        assert system.revision_config == revision_config
    
    def test_init_success_with_minimal_params(self, mock_llm_client):
        """测试初始化成功_最少参数_使用默认值."""
        # When
        system = QualityAssessmentSystem(llm_client=mock_llm_client)
        
        # Then
        assert system.llm_client == mock_llm_client
        assert system.consistency_checker is not None
        assert "excellent" in system.quality_thresholds
        assert "max_iterations" in system.revision_config
    
    def test_init_failure_none_llm_client_raises_error(self):
        """测试初始化失败_LLM客户端为None_抛出异常."""
        # When & Then
        with pytest.raises(ValueError, match="llm_client不能为None"):
            QualityAssessmentSystem(llm_client=None)
    
    @pytest.mark.asyncio
    async def test_assess_quality_success_simple_content(
        self, 
        quality_assessment_system, 
        sample_characters, 
        sample_chapter_info
    ):
        """测试质量评估成功_简单内容_返回完整评估结果."""
        # Given
        content = "张三挥剑向李四攻去，李四狡猾地躲避了攻击。这是一场激烈的战斗。"
        
        # 模拟LLM响应
        quality_assessment_system.llm_client.generate_async.side_effect = [
            '{"score": 8.0, "issues": [], "suggestions": ["保持情节紧凑"], "details": {"logic_clarity": 8.0}}',
            '{"score": 7.5, "issues": ["语言略显平淡"], "suggestions": ["丰富描述"], "details": {"grammar": 8.0}}',
            '{"score": 7.0, "issues": [], "suggestions": ["保持风格"], "details": {"tone": 7.0}}'
        ]
        
        # When
        result = await quality_assessment_system.assess_quality(
            content, sample_characters, sample_chapter_info
        )
        
        # Then
        assert isinstance(result, QualityMetrics)
        assert 0 <= result.overall_score <= 10
        assert result.grade in ["A", "B", "C", "D", "F"]
        assert len(result.dimensions) == 4
        assert "plot_logic" in result.dimensions
        assert "character_consistency" in result.dimensions
        assert "language_quality" in result.dimensions
        assert "style_consistency" in result.dimensions
        assert result.word_count > 0
    
    @pytest.mark.asyncio
    async def test_assess_quality_failure_empty_content_raises_error(
        self, 
        quality_assessment_system, 
        sample_characters, 
        sample_chapter_info
    ):
        """测试质量评估失败_空内容_抛出异常."""
        # When & Then
        with pytest.raises(QualityAssessmentError, match="评估内容不能为空"):
            await quality_assessment_system.assess_quality(
                "", sample_characters, sample_chapter_info
            )
    
    @pytest.mark.asyncio
    async def test_assess_quality_partial_failure_handles_gracefully(
        self, 
        quality_assessment_system, 
        sample_characters, 
        sample_chapter_info
    ):
        """测试质量评估部分失败_优雅处理_返回部分结果."""
        # Given
        content = "测试内容"
        
        # 模拟部分LLM调用失败
        quality_assessment_system.llm_client.generate_async.side_effect = [
            Exception("LLM调用失败"),  # 情节逻辑评估失败
            '{"score": 7.5, "issues": [], "suggestions": []}',  # 语言质量成功
            '{"score": 7.0, "issues": [], "suggestions": []}'   # 风格一致性成功
        ]
        
        # When
        result = await quality_assessment_system.assess_quality(
            content, sample_characters, sample_chapter_info
        )
        
        # Then
        assert isinstance(result, QualityMetrics)
        assert result.dimensions["plot_logic"].score == 5.0  # 默认分数
        assert "评估失败" in result.dimensions["plot_logic"].issues[0]
    
    def test_calculate_overall_score_weighted_average(self, quality_assessment_system):
        """测试总体分数计算_加权平均_正确计算."""
        # Given
        dimensions = {
            "plot_logic": QualityDimension(
                name="情节逻辑", score=8.0, weight=0.3, issues=[], suggestions=[]
            ),
            "character_consistency": QualityDimension(
                name="角色一致性", score=7.0, weight=0.25, issues=[], suggestions=[]
            ),
            "language_quality": QualityDimension(
                name="语言质量", score=9.0, weight=0.25, issues=[], suggestions=[]
            ),
            "style_consistency": QualityDimension(
                name="风格一致性", score=6.0, weight=0.2, issues=[], suggestions=[]
            )
        }
        
        # When
        score = quality_assessment_system._calculate_overall_score(dimensions)
        
        # Then
        expected = (8.0*0.3 + 7.0*0.25 + 9.0*0.25 + 6.0*0.2) / (0.3+0.25+0.25+0.2)
        assert abs(score - expected) < 0.01
    
    def test_determine_grade_all_levels(self, quality_assessment_system):
        """测试等级判定_所有等级_正确分类."""
        # 测试所有等级
        test_cases = [
            (9.5, "A"),  # 优秀
            (8.0, "B"),  # 良好
            (6.5, "C"),  # 可接受
            (4.5, "D"),  # 较差
            (1.0, "F")   # 不可接受
        ]
        
        for score, expected_grade in test_cases:
            # When
            grade = quality_assessment_system._determine_grade(score)
            
            # Then
            assert grade == expected_grade, f"分数 {score} 应该对应等级 {expected_grade}"
    
    @pytest.mark.asyncio
    async def test_generate_revision_suggestions_auto_target(
        self, 
        quality_assessment_system
    ):
        """测试生成修订建议_自动目标_选择低分维度."""
        # Given
        content = "测试内容"
        metrics = QualityMetrics(
            overall_score=6.5,
            dimensions={
                "plot_logic": QualityDimension(
                    name="情节逻辑", score=5.0, weight=0.3, 
                    issues=["逻辑跳跃"], suggestions=["完善逻辑"]
                ),
                "language_quality": QualityDimension(
                    name="语言质量", score=8.0, weight=0.25, 
                    issues=[], suggestions=[]
                )
            },
            grade="C",
            assessment_time=datetime.now(),
            word_count=100,
            chapter_count=1,
            character_count=2
        )
        
        # Mock LLM响应
        quality_assessment_system.llm_client.generate_async.return_value = '''
        {
            "suggestions": [
                {
                    "priority": "high",
                    "description": "修复逻辑跳跃问题",
                    "target_content": "测试段落",
                    "suggested_change": "添加过渡内容",
                    "reason": "提高逻辑连贯性"
                }
            ]
        }
        '''
        
        # When
        suggestions = await quality_assessment_system.generate_revision_suggestions(
            content, metrics
        )
        
        # Then
        assert len(suggestions) > 0
        assert suggestions[0].type == "plot"
        assert suggestions[0].priority == "high"
    
    @pytest.mark.asyncio
    async def test_execute_revision_success(self, quality_assessment_system):
        """测试执行修订成功_返回修订结果."""
        # Given
        content = "原始内容"
        suggestion = RevisionSuggestion(
            type="language",
            priority="high",
            description="改进语言表达",
            target_content="原始内容",
            suggested_change="使用更丰富的词汇",
            reason="提高语言质量"
        )
        
        # Mock LLM响应
        quality_assessment_system.llm_client.generate_async.return_value = "修订后的内容"
        
        # When
        result = await quality_assessment_system.execute_revision(content, suggestion)
        
        # Then
        assert isinstance(result, RevisionResult)
        assert result.original_content == content
        assert result.revised_content == "修订后的内容"
        assert result.revision_type == "language"
        assert len(result.changes_made) > 0
    
    @pytest.mark.asyncio
    async def test_iterative_revision_reaches_target(
        self,
        quality_assessment_system,
        sample_characters,
        sample_chapter_info
    ):
        """测试迭代修订_达到目标分数_停止迭代."""
        # Given
        content = "测试内容"
        target_score = 8.0
        
        # Mock assess_quality返回递增的分数
        assess_calls = [
            QualityMetrics(
                overall_score=6.0, dimensions={}, grade="C",
                assessment_time=datetime.now(), word_count=100,
                chapter_count=1, character_count=2
            ),
            QualityMetrics(
                overall_score=8.5, dimensions={}, grade="B",
                assessment_time=datetime.now(), word_count=100,
                chapter_count=1, character_count=2
            ),
            QualityMetrics(
                overall_score=8.5, dimensions={}, grade="B",
                assessment_time=datetime.now(), word_count=100,
                chapter_count=1, character_count=2
            )
        ]
        quality_assessment_system.assess_quality = AsyncMock(side_effect=assess_calls)
        
        # Mock其他方法
        quality_assessment_system.generate_revision_suggestions = AsyncMock(return_value=[
            RevisionSuggestion(
                type="plot", priority="high", description="测试建议",
                target_content="", suggested_change="", reason=""
            )
        ])
        quality_assessment_system.execute_revision = AsyncMock(return_value=RevisionResult(
            original_content=content, revised_content="修订内容",
            changes_made=["测试修改"], improvement_score=1.0,
            revision_type="plot", revision_time=datetime.now()
        ))
        
        # When
        final_content, history, final_metrics = await quality_assessment_system.iterative_revision(
            content, sample_characters, sample_chapter_info, target_score
        )
        
        # Then
        assert final_metrics.overall_score >= target_score
        assert len(history) >= 1  # 至少执行了一次修订
    
    @pytest.mark.asyncio
    async def test_iterative_revision_max_iterations(
        self, 
        quality_assessment_system, 
        sample_characters, 
        sample_chapter_info
    ):
        """测试迭代修订_达到最大迭代次数_停止迭代."""
        # Given
        content = "测试内容"
        target_score = 10.0  # 不可能达到的高分
        max_iterations = 2
        
        # Mock assess_quality始终返回低分
        low_score_metrics = QualityMetrics(
            overall_score=5.0, dimensions={}, grade="D",
            assessment_time=datetime.now(), word_count=100, 
            chapter_count=1, character_count=2
        )
        quality_assessment_system.assess_quality = AsyncMock(return_value=low_score_metrics)
        
        # Mock其他方法
        quality_assessment_system.generate_revision_suggestions = AsyncMock(return_value=[
            RevisionSuggestion(
                type="plot", priority="high", description="测试建议",
                target_content="", suggested_change="", reason=""
            )
        ])
        quality_assessment_system.execute_revision = AsyncMock(return_value=RevisionResult(
            original_content=content, revised_content="修订内容",
            changes_made=["测试修改"], improvement_score=0.1,
            revision_type="plot", revision_time=datetime.now()
        ))
        
        # When
        final_content, history, final_metrics = await quality_assessment_system.iterative_revision(
            content, sample_characters, sample_chapter_info, target_score, max_iterations
        )
        
        # Then
        assert len(history) <= max_iterations
        assert final_metrics.overall_score < target_score  # 没有达到目标分数
    
    def test_parse_llm_response_valid_json(self, quality_assessment_system):
        """测试解析LLM响应_有效JSON_正确解析."""
        # Given
        response = '{"score": 8.5, "issues": ["test"], "suggestions": ["improve"]}'
        
        # When
        result = quality_assessment_system._parse_llm_response(response)
        
        # Then
        assert result["score"] == 8.5
        assert result["issues"] == ["test"]
        assert result["suggestions"] == ["improve"]
    
    def test_parse_llm_response_json_with_markdown(self, quality_assessment_system):
        """测试解析LLM响应_包含Markdown格式_正确清理并解析."""
        # Given
        response = '```json\n{"score": 7.0, "issues": []}\n```'
        
        # When
        result = quality_assessment_system._parse_llm_response(response)
        
        # Then
        assert result["score"] == 7.0
        assert result["issues"] == []
    
    def test_parse_llm_response_invalid_json_returns_empty(self, quality_assessment_system):
        """测试解析LLM响应_无效JSON_返回空字典."""
        # Given
        response = "这不是JSON格式"
        
        # When
        result = quality_assessment_system._parse_llm_response(response)
        
        # Then
        assert result == {}


class TestQualityDimension:
    """质量维度测试类."""
    
    def test_quality_dimension_creation(self):
        """测试质量维度创建_基本属性_正确设置."""
        # Given & When
        dimension = QualityDimension(
            name="测试维度",
            score=8.5,
            weight=0.3,
            issues=["问题1", "问题2"],
            suggestions=["建议1", "建议2"]
        )
        
        # Then
        assert dimension.name == "测试维度"
        assert dimension.score == 8.5
        assert dimension.weight == 0.3
        assert dimension.issues == ["问题1", "问题2"]
        assert dimension.suggestions == ["建议1", "建议2"]
        assert dimension.details == {}


class TestQualityMetrics:
    """质量指标测试类."""
    
    def test_get_weighted_score_calculation(self):
        """测试加权分数计算_多个维度_正确计算."""
        # Given
        dimensions = {
            "dim1": QualityDimension(
                name="维度1", score=8.0, weight=0.4, issues=[], suggestions=[]
            ),
            "dim2": QualityDimension(
                name="维度2", score=6.0, weight=0.6, issues=[], suggestions=[]
            )
        }
        
        metrics = QualityMetrics(
            overall_score=7.0,
            dimensions=dimensions,
            grade="B",
            assessment_time=datetime.now(),
            word_count=1000,
            chapter_count=5,
            character_count=3
        )
        
        # When
        weighted_score = metrics.get_weighted_score()
        
        # Then
        expected = (8.0 * 0.4 + 6.0 * 0.6) / (0.4 + 0.6)
        assert abs(weighted_score - expected) < 0.01
    
    def test_get_weighted_score_empty_dimensions(self):
        """测试加权分数计算_空维度_返回零."""
        # Given
        metrics = QualityMetrics(
            overall_score=0.0,
            dimensions={},
            grade="F",
            assessment_time=datetime.now(),
            word_count=0,
            chapter_count=0,
            character_count=0
        )
        
        # When
        weighted_score = metrics.get_weighted_score()
        
        # Then
        assert weighted_score == 0.0


class TestRevisionSuggestion:
    """修订建议测试类."""
    
    def test_revision_suggestion_creation(self):
        """测试修订建议创建_完整信息_正确设置."""
        # Given & When
        suggestion = RevisionSuggestion(
            type="plot",
            priority="high",
            description="修复逻辑问题",
            target_content="问题段落",
            suggested_change="添加过渡内容",
            reason="提高连贯性"
        )
        
        # Then
        assert suggestion.type == "plot"
        assert suggestion.priority == "high"
        assert suggestion.description == "修复逻辑问题"
        assert suggestion.target_content == "问题段落"
        assert suggestion.suggested_change == "添加过渡内容"
        assert suggestion.reason == "提高连贯性"


class TestRevisionResult:
    """修订结果测试类."""
    
    def test_revision_result_creation(self):
        """测试修订结果创建_完整信息_正确设置."""
        # Given
        revision_time = datetime.now()
        
        # When
        result = RevisionResult(
            original_content="原始内容",
            revised_content="修订内容",
            changes_made=["修改1", "修改2"],
            improvement_score=1.5,
            revision_type="language",
            revision_time=revision_time
        )
        
        # Then
        assert result.original_content == "原始内容"
        assert result.revised_content == "修订内容"
        assert result.changes_made == ["修改1", "修改2"]
        assert result.improvement_score == 1.5
        assert result.revision_type == "language"
        assert result.revision_time == revision_time