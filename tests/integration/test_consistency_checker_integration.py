"""基础一致性检查器集成测试."""

import pytest
from unittest.mock import AsyncMock

from src.core.consistency_checker import BasicConsistencyChecker, ConsistencyCheckResult
from src.core.character_system import Character
from src.utils.llm_client import UniversalLLMClient


class TestConsistencyCheckerIntegration:
    """一致性检查器集成测试类."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """模拟LLM客户端fixture."""
        client = AsyncMock(spec=UniversalLLMClient)
        return client
    
    @pytest.fixture
    def consistency_checker(self, mock_llm_client):
        """一致性检查器fixture."""
        return BasicConsistencyChecker(mock_llm_client)
    
    @pytest.fixture
    def sample_characters(self):
        """示例角色fixture."""
        return {
            "李明": Character(
                name="李明",
                role="主角",
                age=22,
                personality=["坚韧", "聪明"],
                background="计算机专业学生",
                goals=["成为优秀程序员"],
                skills=["编程", "数学"],
                appearance="中等身材，戴眼镜",
                motivation="改变世界"
            ),
            "张教授": Character(
                name="张教授",
                role="导师",
                age=50,
                personality=["严格", "睿智"],
                background="计算机系教授",
                goals=["培养优秀学生"],
                skills=["教学", "研究"],
                appearance="高大威严，白发",
                motivation="传承知识"
            )
        }
    
    @pytest.mark.asyncio
    async def test_realistic_consistency_check_scenario(self, consistency_checker, sample_characters):
        """测试现实场景的一致性检查."""
        # Given - 模拟真实的LLM响应
        consistency_checker.llm_client.generate_async.return_value = """
        {
            "consistency_issues": [
                {
                    "type": "character_inconsistency",
                    "character": "李明",
                    "field": "appearance",
                    "description": "身高描述不一致：设定为中等身材，文中描述为高大",
                    "severity": "medium",
                    "line_context": "高大的李明走进教室"
                }
            ],
            "severity": "medium",
            "overall_score": 6.5,
            "suggestions": ["修正李明的身高描述，保持一致性"]
        }
        """
        
        content = """
        高大的李明走进教室，他的眼镜在灯光下闪闪发光。
        作为一名计算机专业的学生，他总是对编程充满热情。
        张教授看着这个聪明的学生，心中充满了期待。
        """
        
        chapter_info = {
            "title": "第一章：新学期",
            "characters_involved": ["李明", "张教授"],
            "setting": "大学教室",
            "key_events": ["李明上课", "与张教授交流"],
            "previous_events": []
        }
        
        # When
        result = await consistency_checker.check_consistency(content, sample_characters, chapter_info)
        
        # Then
        assert isinstance(result, ConsistencyCheckResult)
        assert result.has_issues
        assert len(result.issues) == 1
        assert result.issues[0].character == "李明"
        assert result.issues[0].type == "character_inconsistency"
        assert result.severity == "medium"
        assert result.overall_score == 6.5
        assert len(result.suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_batch_consistency_check_integration(self, consistency_checker, sample_characters):
        """测试批量一致性检查集成."""
        # Given
        consistency_checker.llm_client.generate_async.return_value = """
        {
            "consistency_issues": [],
            "severity": "low",
            "overall_score": 8.5,
            "suggestions": ["内容整体一致性良好"]
        }
        """
        
        contents = [
            "李明认真地听着张教授的讲课，不时在笔记本上记录重点。",
            "张教授看到李明的专注，心中暗自满意这个学生的学习态度。",
            "课程结束后，李明主动走向讲台，向张教授请教编程问题。"
        ]
        
        chapter_infos = [
            {
                "title": "第一章：课堂",
                "characters_involved": ["李明", "张教授"],
                "setting": "教室"
            },
            {
                "title": "第一章：课堂",
                "characters_involved": ["李明", "张教授"],
                "setting": "教室"
            },
            {
                "title": "第一章：课堂",
                "characters_involved": ["李明", "张教授"],
                "setting": "教室"
            }
        ]
        
        # When
        results = await consistency_checker.batch_check_consistency(contents, sample_characters, chapter_infos)
        
        # Then
        assert len(results) == 3
        assert all(isinstance(result, ConsistencyCheckResult) for result in results)
        assert all(not result.has_issues for result in results)
        assert all(result.overall_score >= 8.0 for result in results)
    
    def test_character_consistency_summary_integration(self, consistency_checker):
        """测试角色一致性总结集成."""
        # Given
        from src.core.consistency_checker import ConsistencyIssue, ConsistencyCheckResult
        
        results = [
            ConsistencyCheckResult(
                issues=[
                    ConsistencyIssue(
                        type="character_inconsistency",
                        character="李明",
                        field="appearance",
                        description="外貌不一致",
                        severity="medium",
                        line_context="测试"
                    )
                ],
                severity="medium",
                overall_score=7.0,
                suggestions=["修正外貌"]
            ),
            ConsistencyCheckResult(
                issues=[
                    ConsistencyIssue(
                        type="character_inconsistency",
                        character="李明",
                        field="personality",
                        description="性格不一致",
                        severity="low",
                        line_context="测试"
                    )
                ],
                severity="low",
                overall_score=8.0,
                suggestions=["调整性格"]
            ),
            ConsistencyCheckResult(
                issues=[],
                severity="low",
                overall_score=9.0,
                suggestions=[]
            )
        ]
        
        # When
        summary = consistency_checker.get_character_consistency_summary(results, "李明")
        
        # Then
        assert summary["character_name"] == "李明"
        assert summary["total_issues"] == 2
        assert "character_inconsistency" in summary["issues_by_type"]
        assert len(summary["issues_by_type"]["character_inconsistency"]) == 2
        assert summary["consistency_score"] > 0
        assert summary["most_common_issue_type"] == "character_inconsistency"
    
    def test_generate_fix_suggestions_integration(self, consistency_checker):
        """测试修复建议生成集成."""
        # Given
        from src.core.consistency_checker import ConsistencyIssue
        
        issues = [
            ConsistencyIssue(
                type="character_inconsistency",
                character="李明",
                field="appearance",
                description="眼镜描述不一致：有时戴眼镜，有时不戴",
                severity="medium",
                line_context="李明摘下眼镜"
            ),
            ConsistencyIssue(
                type="plot_inconsistency",
                character="张教授",
                field="behavior",
                description="逻辑跳跃：前文提到张教授很严格，现在突然很温和",
                severity="high",
                line_context="张教授温和地笑了"
            ),
            ConsistencyIssue(
                type="world_inconsistency",
                character="",
                field="setting",
                description="教室环境描述不一致",
                severity="low",
                line_context="豪华的教室"
            )
        ]
        
        # When
        suggestions = consistency_checker.generate_fix_suggestions(issues)
        
        # Then
        assert len(suggestions) >= 3
        
        # 检查李明的外貌问题建议
        assert any("李明" in suggestion for suggestion in suggestions)
        
        # 检查逻辑跳跃问题建议
        assert any("逻辑" in suggestion or "过程" in suggestion for suggestion in suggestions)
        
        # 检查世界设定问题建议
        assert any("世界设定" in suggestion for suggestion in suggestions)