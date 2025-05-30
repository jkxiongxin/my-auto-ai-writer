"""概念扩展器单元测试."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import json

from src.core.concept_expander import ConceptExpander, ConceptExpansionError, ConceptExpansionResult
from src.utils.llm_client import UniversalLLMClient


class TestConceptExpander:
    """概念扩展器单元测试."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """模拟LLM客户端fixture."""
        client = AsyncMock(spec=UniversalLLMClient)
        
        # 创建一个函数来根据输入返回不同的响应
        def side_effect(prompt):
            if "火星殖民地调查连环谋杀案" in prompt:
                return json.dumps({
                    "theme": "科技与人性的冲突",
                    "genre": "科幻",
                    "main_conflict": "在火星殖民地调查连环谋杀案的过程中发现的阴谋",
                    "world_type": "火星殖民地",
                    "tone": "悬疑紧张",
                    "protagonist_type": "殖民地侦探",
                    "setting": "2150年的火星殖民地",
                    "core_message": "在孤独的环境中寻找真相"
                }, ensure_ascii=False)
            else:
                # 默认响应
                return json.dumps({
                    "theme": "科技与人性的冲突",
                    "genre": "科幻",
                    "main_conflict": "机器人获得情感后与人类社会的冲突",
                    "world_type": "近未来都市",
                    "tone": "深刻而温暖",
                    "protagonist_type": "具有情感的机器人",
                    "setting": "2050年的科技都市",
                    "core_message": "探讨什么是真正的人性"
                }, ensure_ascii=False)
        
        client.generate_async.side_effect = side_effect
        return client
    
    @pytest.fixture
    def mock_llm_client_invalid_json(self):
        """模拟返回无效JSON的LLM客户端."""
        client = AsyncMock(spec=UniversalLLMClient)
        client.generate_async.return_value = "这不是一个有效的JSON响应"
        return client
    
    @pytest.fixture
    def concept_expander(self, mock_llm_client):
        """概念扩展器fixture."""
        return ConceptExpander(mock_llm_client)
    
    @pytest.mark.asyncio
    async def test_expand_simple_concept_success_returns_complete_concept(self, concept_expander):
        """测试简单概念扩展成功_简单输入_返回完整概念."""
        # Given
        user_input = "一个机器人获得了情感"
        target_words = 10000
        
        # When
        result = await concept_expander.expand_concept(user_input, target_words)
        
        # Then
        assert isinstance(result, ConceptExpansionResult)
        assert result.theme is not None
        assert result.genre is not None
        assert result.main_conflict is not None
        assert len(result.theme) > 0
        assert result.confidence_score >= 0.0
        assert result.confidence_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_expand_scifi_concept_success_returns_scifi_elements(self, concept_expander):
        """测试科幻题材概念扩展成功_科幻输入_返回科幻元素."""
        # Given
        user_input = "在火星殖民地调查连环谋杀案"
        target_words = 15000
        style_preference = "科幻"
        
        # When
        result = await concept_expander.expand_concept(user_input, target_words, style_preference)
        
        # Then
        assert result.genre in ["科幻", "未来", "太空"]
        assert any(keyword in result.main_conflict for keyword in ["谋杀", "调查", "殖民地"])
        assert result.world_type is not None
    
    @pytest.mark.asyncio
    async def test_expand_concept_with_target_words_success_adjusts_complexity(self, concept_expander):
        """测试不同目标字数的概念扩展_不同字数_调整复杂度."""
        # Given
        user_input = "魔法学院的学生冒险"
        
        # When - 短篇
        result_short = await concept_expander.expand_concept(user_input, 3000)
        # When - 长篇
        result_long = await concept_expander.expand_concept(user_input, 50000)
        
        # Then
        assert result_short.complexity_level != result_long.complexity_level
        assert isinstance(result_short.complexity_level, str)
        assert isinstance(result_long.complexity_level, str)
    
    @pytest.mark.asyncio
    async def test_expand_concept_failure_empty_input_raises_error(self, concept_expander):
        """测试概念扩展失败_空输入_抛出异常."""
        # Given
        user_input = ""
        target_words = 10000
        
        # When & Then
        with pytest.raises(ConceptExpansionError, match="用户输入不能为空"):
            await concept_expander.expand_concept(user_input, target_words)
    
    @pytest.mark.asyncio
    async def test_expand_concept_failure_invalid_word_count_raises_error(self, concept_expander):
        """测试概念扩展失败_无效字数_抛出异常."""
        # Given
        user_input = "一个有趣的故事"
        target_words = 500  # 太少
        
        # When & Then
        with pytest.raises(ConceptExpansionError, match="目标字数必须在1000-200000之间"):
            await concept_expander.expand_concept(user_input, target_words)
    
    @pytest.mark.asyncio
    async def test_expand_concept_failure_invalid_json_raises_error(self, mock_llm_client_invalid_json):
        """测试概念扩展失败_无效JSON响应_抛出异常."""
        # Given
        expander = ConceptExpander(mock_llm_client_invalid_json)
        user_input = "测试输入"
        target_words = 5000
        
        # When & Then
        with pytest.raises(ConceptExpansionError, match="概念扩展失败"):
            await expander.expand_concept(user_input, target_words)
    
    def test_build_prompt_includes_all_parameters(self, concept_expander):
        """测试提示词构建_包含所有参数_生成完整提示词."""
        # Given
        user_input = "太空探险故事"
        target_words = 20000
        style_preference = "硬科幻"
        
        # When
        prompt = concept_expander._build_prompt(user_input, target_words, style_preference)
        
        # Then
        assert user_input in prompt
        assert str(target_words) in prompt
        assert style_preference in prompt
        assert "JSON格式" in prompt
    
    def test_parse_llm_response_success_returns_result(self, concept_expander):
        """测试LLM响应解析成功_有效JSON_返回结果对象."""
        # Given
        valid_json_response = json.dumps({
            "theme": "友谊与勇气",
            "genre": "奇幻",
            "main_conflict": "邪恶势力威胁世界",
            "world_type": "魔法世界",
            "tone": "冒险刺激"
        }, ensure_ascii=False)
        
        # When
        result = concept_expander._parse_llm_response(valid_json_response)
        
        # Then
        assert isinstance(result, ConceptExpansionResult)
        assert result.theme == "友谊与勇气"
        assert result.genre == "奇幻"
    
    def test_calculate_confidence_score_returns_valid_score(self, concept_expander):
        """测试置信度计算_有效输入_返回有效分数."""
        # Given
        concept_data = {
            "theme": "详细的主题描述",
            "genre": "科幻",
            "main_conflict": "复杂的冲突描述",
            "world_type": "详细的世界设定",
            "tone": "明确的基调"
        }
        
        # When
        score = concept_expander._calculate_confidence_score(concept_data)
        
        # Then
        assert 0.0 <= score <= 1.0
        assert isinstance(score, float)
    
    def test_determine_complexity_level_short_story_returns_simple(self, concept_expander):
        """测试复杂度判定_短篇小说_返回简单级别."""
        # Given
        target_words = 3000
        
        # When
        complexity = concept_expander._determine_complexity_level(target_words)
        
        # Then
        assert complexity == "simple"
    
    def test_determine_complexity_level_novel_returns_complex(self, concept_expander):
        """测试复杂度判定_长篇小说_返回复杂级别."""
        # Given
        target_words = 80000
        
        # When
        complexity = concept_expander._determine_complexity_level(target_words)
        
        # Then
        assert complexity == "complex"
    
    @pytest.mark.asyncio
    async def test_expand_concept_with_retry_mechanism_success_after_retry(self, mock_llm_client):
        """测试重试机制_首次失败后成功_最终返回结果."""
        # Given
        expander = ConceptExpander(mock_llm_client)
        
        # 模拟第一次调用失败，第二次成功
        valid_response = json.dumps({
            "theme": "重试后的主题",
            "genre": "科幻",
            "main_conflict": "重试后的冲突",
            "world_type": "重试后的世界",
            "tone": "重试后的基调"
        }, ensure_ascii=False)
        
        mock_llm_client.generate_async.side_effect = [
            "无效的JSON",  # 第一次失败
            valid_response   # 第二次成功
        ]
        
        # When
        result = await expander.expand_concept("测试故事", 5000)
        
        # Then
        assert result.theme == "重试后的主题"
        assert mock_llm_client.generate_async.call_count == 2