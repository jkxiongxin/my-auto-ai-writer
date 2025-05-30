"""基础一致性检查器单元测试."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

from src.core.consistency_checker import (
    BasicConsistencyChecker,
    ConsistencyCheckResult,
    ConsistencyIssue,
    ConsistencyCheckError
)
from src.core.character_system import Character, CharacterDatabase
from src.core.concept_expander import ConceptExpansionResult


class TestBasicConsistencyChecker:
    """基础一致性检查器测试类."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """模拟LLM客户端fixture."""
        client = AsyncMock()
        client.generate_async.return_value = """
        {
            "consistency_issues": [],
            "severity": "low",
            "overall_score": 8.5,
            "suggestions": ["内容整体一致性良好"]
        }
        """
        return client
    
    @pytest.fixture
    def consistency_checker(self, mock_llm_client):
        """一致性检查器fixture."""
        return BasicConsistencyChecker(mock_llm_client)
    
    @pytest.fixture
    def sample_characters(self):
        """示例角色fixture."""
        characters = {
            "张三": Character(
                name="张三",
                role="主角",
                age=25,
                personality=["勇敢", "善良"],
                background="普通农村青年",
                goals=["拯救村庄"],
                skills=["剑术", "魔法"],
                appearance="高大魁梧，蓝色眼睛",
                motivation="保护家人"
            ),
            "李四": Character(
                name="李四",
                role="反派",
                age=35,
                personality=["狡猾", "贪婪"],
                background="堕落的前王国骑士",
                goals=["统治世界"],
                skills=["黑魔法", "诡计"],
                appearance="瘦削阴沉，黑色头发",
                motivation="追求权力"
            )
        }
        return characters
    
    @pytest.fixture
    def sample_chapter_info(self):
        """示例章节信息fixture."""
        return {
            "title": "第二章：觉醒",
            "key_events": ["主角学会飞行魔法", "与导师相遇"],
            "previous_events": ["主角害怕高度", "从未接触过魔法"],
            "characters_involved": ["张三", "王导师"],
            "setting": "魔法学院训练场"
        }
    
    @pytest.mark.asyncio
    async def test_check_consistency_success_no_issues(self, consistency_checker, sample_characters):
        """测试一致性检查成功_无问题_返回良好结果."""
        # Given
        content = "勇敢的张三挥舞着剑，用他蓝色的眼睛注视着敌人。"
        chapter_info = {"characters_involved": ["张三"]}
        
        # When
        result = await consistency_checker.check_consistency(content, sample_characters, chapter_info)
        
        # Then
        assert isinstance(result, ConsistencyCheckResult)
        assert result.overall_score >= 8.0
        assert result.severity == "low"
        assert len(result.issues) == 0
    
    @pytest.mark.asyncio
    async def test_check_consistency_character_inconsistency(self, consistency_checker, sample_characters):
        """测试一致性检查_角色不一致_检测到问题."""
        # Given - 张三设定是蓝色眼睛，但内容说绿色眼睛
        content = "矮小的张三用绿色眼睛怯懦地看着前方。"
        chapter_info = {"characters_involved": ["张三"]}
        
        # Mock LLM 返回检测到的问题
        consistency_checker.llm_client.generate_async.return_value = """
        {
            "consistency_issues": [
                {
                    "type": "character_inconsistency",
                    "character": "张三",
                    "field": "appearance",
                    "description": "眼睛颜色不一致：设定为蓝色，文中为绿色",
                    "severity": "medium",
                    "line_context": "用绿色眼睛怯懦地看着前方"
                },
                {
                    "type": "character_inconsistency", 
                    "character": "张三",
                    "field": "personality",
                    "description": "性格不一致：设定为勇敢，文中表现怯懦",
                    "severity": "high",
                    "line_context": "怯懦地看着前方"
                }
            ],
            "severity": "high",
            "overall_score": 4.5,
            "suggestions": ["修正张三的外貌描述", "调整张三的性格表现"]
        }
        """
        
        # When
        result = await consistency_checker.check_consistency(content, sample_characters, chapter_info)
        
        # Then
        assert result.overall_score < 5.0
        assert result.severity == "high"
        assert len(result.issues) == 2
        assert any("张三" in issue.character for issue in result.issues)
        assert any("眼睛颜色" in issue.description for issue in result.issues)
    
    @pytest.mark.asyncio
    async def test_check_consistency_plot_inconsistency(self, consistency_checker, sample_characters, sample_chapter_info):
        """测试一致性检查_情节不一致_检测到逻辑问题."""
        # Given - 主角之前害怕高度，现在突然能飞行
        content = "张三轻松地飞上了天空，没有任何恐惧，仿佛天生就会飞行。"
        
        # Mock LLM 返回逻辑问题
        consistency_checker.llm_client.generate_async.return_value = """
        {
            "consistency_issues": [
                {
                    "type": "plot_inconsistency",
                    "character": "张三",
                    "field": "behavior",
                    "description": "逻辑跳跃：前文提到害怕高度，现在突然毫无恐惧地飞行",
                    "severity": "medium",
                    "line_context": "轻松地飞上了天空，没有任何恐惧"
                }
            ],
            "severity": "medium",
            "overall_score": 6.0,
            "suggestions": ["添加主角克服恐惧的过程描述"]
        }
        """
        
        # When
        result = await consistency_checker.check_consistency(content, sample_characters, sample_chapter_info)
        
        # Then
        assert result.severity == "medium"
        assert len(result.issues) > 0
        assert any("逻辑跳跃" in issue.description for issue in result.issues)
    
    def test_assess_severity_high(self, consistency_checker):
        """测试严重度评估_高严重度_返回high."""
        # Given
        issues = [
            ConsistencyIssue(
                type="character_inconsistency",
                character="张三",
                field="personality",
                description="严重性格冲突",
                severity="high",
                line_context="测试文本"
            ),
            ConsistencyIssue(
                type="plot_inconsistency",
                character="张三",
                field="behavior",
                description="严重逻辑错误",
                severity="high",
                line_context="测试文本"
            )
        ]
        
        # When
        severity = consistency_checker._assess_severity(issues)
        
        # Then
        assert severity == "high"
    
    def test_assess_severity_medium(self, consistency_checker):
        """测试严重度评估_中等严重度_返回medium."""
        # Given
        issues = [
            ConsistencyIssue(
                type="character_inconsistency",
                character="张三", 
                field="appearance",
                description="外貌细节不一致",
                severity="medium",
                line_context="测试文本"
            ),
            ConsistencyIssue(
                type="character_inconsistency",
                character="李四",
                field="appearance", 
                description="轻微描述差异",
                severity="low",
                line_context="测试文本"
            )
        ]
        
        # When
        severity = consistency_checker._assess_severity(issues)
        
        # Then
        assert severity == "medium"
    
    def test_assess_severity_low(self, consistency_checker):
        """测试严重度评估_低严重度_返回low."""
        # Given
        issues = [
            ConsistencyIssue(
                type="character_inconsistency",
                character="张三",
                field="dialogue",
                description="对话风格略有差异",
                severity="low",
                line_context="测试文本"
            )
        ]
        
        # When
        severity = consistency_checker._assess_severity(issues)
        
        # Then
        assert severity == "low"
    
    def test_assess_severity_empty_issues(self, consistency_checker):
        """测试严重度评估_无问题_返回low."""
        # Given
        issues = []
        
        # When
        severity = consistency_checker._assess_severity(issues)
        
        # Then
        assert severity == "low"
    
    @pytest.mark.asyncio
    async def test_check_consistency_empty_content_raises_error(self, consistency_checker, sample_characters):
        """测试一致性检查_空内容_抛出异常."""
        # Given
        content = ""
        chapter_info = {}
        
        # When & Then
        with pytest.raises(ConsistencyCheckError, match="内容不能为空"):
            await consistency_checker.check_consistency(content, sample_characters, chapter_info)
    
    @pytest.mark.asyncio
    async def test_check_consistency_none_characters_raises_error(self, consistency_checker):
        """测试一致性检查_角色为None_抛出异常."""
        # Given
        content = "测试内容"
        characters = None
        chapter_info = {}
        
        # When & Then
        with pytest.raises(ConsistencyCheckError, match="角色信息不能为空"):
            await consistency_checker.check_consistency(content, characters, chapter_info)
    
    @pytest.mark.asyncio
    async def test_check_consistency_llm_timeout(self, mock_llm_client, sample_characters):
        """测试一致性检查_LLM超时_抛出异常."""
        # Given
        mock_llm_client.generate_async.side_effect = Exception("Timeout")
        consistency_checker = BasicConsistencyChecker(mock_llm_client, timeout=1)
        content = "测试内容"
        chapter_info = {}
        
        # When & Then
        with pytest.raises(ConsistencyCheckError, match="一致性检查失败"):
            await consistency_checker.check_consistency(content, sample_characters, chapter_info)
    
    @pytest.mark.asyncio
    async def test_check_consistency_invalid_json_response(self, mock_llm_client, sample_characters):
        """测试一致性检查_无效JSON响应_重试后抛出异常."""
        # Given
        mock_llm_client.generate_async.return_value = "Invalid JSON response"
        consistency_checker = BasicConsistencyChecker(mock_llm_client, max_retries=2)
        content = "测试内容"
        chapter_info = {}
        
        # When & Then
        with pytest.raises(ConsistencyCheckError, match="LLM响应格式无效"):
            await consistency_checker.check_consistency(content, sample_characters, chapter_info)
    
    def test_build_prompt_contains_essential_elements(self, consistency_checker, sample_characters, sample_chapter_info):
        """测试构建提示词_包含必要元素."""
        # Given
        content = "张三勇敢地面对敌人"
        
        # When
        prompt = consistency_checker._build_prompt(content, sample_characters, sample_chapter_info)
        
        # Then
        assert "张三" in prompt
        assert "勇敢" in prompt
        assert "蓝色眼睛" in prompt
        assert "第二章" in prompt
        assert "飞行魔法" in prompt
        assert "害怕高度" in prompt
    
    def test_parse_llm_response_valid_json(self, consistency_checker):
        """测试解析LLM响应_有效JSON_返回正确结果."""
        # Given
        response = """
        {
            "consistency_issues": [
                {
                    "type": "character_inconsistency",
                    "character": "张三",
                    "field": "appearance",
                    "description": "外貌不一致",
                    "severity": "medium",
                    "line_context": "测试文本"
                }
            ],
            "severity": "medium",
            "overall_score": 6.5,
            "suggestions": ["修正外貌描述"]
        }
        """
        
        # When
        result = consistency_checker._parse_llm_response(response)
        
        # Then
        assert isinstance(result, ConsistencyCheckResult)
        assert len(result.issues) == 1
        assert result.issues[0].character == "张三"
        assert result.severity == "medium"
        assert result.overall_score == 6.5
        assert len(result.suggestions) == 1
    
    def test_parse_llm_response_with_code_blocks(self, consistency_checker):
        """测试解析LLM响应_包含代码块_正确清理并解析."""
        # Given
        response = """```json
        {
            "consistency_issues": [],
            "severity": "low",
            "overall_score": 9.0,
            "suggestions": []
        }
        ```"""
        
        # When
        result = consistency_checker._parse_llm_response(response)
        
        # Then
        assert isinstance(result, ConsistencyCheckResult)
        assert len(result.issues) == 0
        assert result.overall_score == 9.0
    
    def test_parse_llm_response_invalid_json_raises_error(self, consistency_checker):
        """测试解析LLM响应_无效JSON_抛出异常."""
        # Given
        response = "This is not valid JSON"
        
        # When & Then
        with pytest.raises(ConsistencyCheckError, match="JSON解析失败"):
            consistency_checker._parse_llm_response(response)
    
    def test_parse_llm_response_missing_required_fields_raises_error(self, consistency_checker):
        """测试解析LLM响应_缺少必需字段_抛出异常."""
        # Given
        response = """
        {
            "consistency_issues": [],
            "severity": "low"
        }
        """
        
        # When & Then
        with pytest.raises(ConsistencyCheckError, match="响应数据格式错误"):
            consistency_checker._parse_llm_response(response)
    
    @pytest.mark.asyncio
    async def test_batch_check_consistency_multiple_contents(self, consistency_checker, sample_characters):
        """测试批量一致性检查_多个内容_返回多个结果."""
        # Given
        contents = [
            "张三勇敢地挥剑",
            "李四阴险地笑了",
            "王导师智慧地点头"
        ]
        chapter_infos = [
            {"characters_involved": ["张三"]},
            {"characters_involved": ["李四"]},
            {"characters_involved": ["王导师"]}
        ]
        
        # When
        results = await consistency_checker.batch_check_consistency(contents, sample_characters, chapter_infos)
        
        # Then
        assert len(results) == 3
        assert all(isinstance(result, ConsistencyCheckResult) for result in results)
    
    def test_generate_fix_suggestions_character_issue(self, consistency_checker):
        """测试生成修复建议_角色问题_返回具体建议."""
        # Given
        issues = [
            ConsistencyIssue(
                type="character_inconsistency",
                character="张三",
                field="appearance",
                description="眼睛颜色不一致：设定为蓝色，文中为绿色",
                severity="medium",
                line_context="绿色眼睛"
            )
        ]
        
        # When
        suggestions = consistency_checker.generate_fix_suggestions(issues)
        
        # Then
        assert len(suggestions) > 0
        assert any("张三" in suggestion for suggestion in suggestions)
        assert any("眼睛" in suggestion for suggestion in suggestions)
    
    def test_generate_fix_suggestions_plot_issue(self, consistency_checker):
        """测试生成修复建议_情节问题_返回具体建议."""
        # Given
        issues = [
            ConsistencyIssue(
                type="plot_inconsistency",
                character="张三",
                field="behavior",
                description="逻辑跳跃：前文害怕高度，现在突然飞行",
                severity="high",
                line_context="轻松飞行"
            )
        ]
        
        # When
        suggestions = consistency_checker.generate_fix_suggestions(issues)
        
        # Then
        assert len(suggestions) > 0
        assert any("逻辑" in suggestion or "过程" in suggestion for suggestion in suggestions)