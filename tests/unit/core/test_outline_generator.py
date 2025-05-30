"""分层大纲生成器单元测试."""

import pytest
from unittest.mock import AsyncMock, Mock
import json
from typing import Dict, Any, List

from src.core.outline_generator import (
    HierarchicalOutlineGenerator, 
    OutlineGenerationError, 
    OutlineNode, 
    ChapterOutline,
    VolumeOutline,
    NovelOutline
)
from src.core.concept_expander import ConceptExpansionResult
from src.core.strategy_selector import GenerationStrategy
from src.utils.llm_client import UniversalLLMClient


class TestHierarchicalOutlineGenerator:
    """分层大纲生成器单元测试."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """模拟LLM客户端fixture."""
        client = AsyncMock(spec=UniversalLLMClient)
        
        # 模拟章节大纲生成响应
        chapter_response = {
            "chapters": [
                {
                    "number": 1,
                    "title": "开始的征程",
                    "summary": "主角踏上冒险之旅",
                    "key_events": ["遇见导师", "获得任务", "离开家乡"],
                    "word_count": 3000,
                    "scenes": [
                        {"name": "家乡告别", "description": "主角告别家人"},
                        {"name": "遇见导师", "description": "偶遇神秘导师"}
                    ]
                },
                {
                    "number": 2,
                    "title": "第一次挑战",
                    "summary": "主角面临第一个重大挑战",
                    "key_events": ["遭遇敌人", "学会技能", "获得伙伴"],
                    "word_count": 3000,
                    "scenes": [
                        {"name": "森林遭遇", "description": "在森林中遇到危险"},
                        {"name": "技能觉醒", "description": "发现自己的特殊能力"}
                    ]
                }
            ]
        }
        
        client.generate_async.return_value = json.dumps(chapter_response, ensure_ascii=False)
        return client
    
    @pytest.fixture
    def sample_concept(self):
        """示例概念fixture."""
        return ConceptExpansionResult(
            theme="友谊与成长",
            genre="奇幻",
            main_conflict="邪恶势力威胁世界",
            world_type="魔法世界",
            tone="冒险刺激",
            protagonist_type="年轻魔法师",
            setting="中世纪奇幻世界",
            core_message="友谊能战胜一切",
            complexity_level="medium",
            confidence_score=0.85
        )
    
    @pytest.fixture
    def sample_strategy(self):
        """示例策略fixture."""
        return GenerationStrategy(
            structure_type="三幕剧",
            chapter_count=6,
            character_depth="medium",
            pacing="moderate",
            world_building_depth="high",
            magic_system="detailed",
            genre_specific_elements=["奇幻", "魔法", "冒险"]
        )
    
    @pytest.fixture
    def outline_generator(self, mock_llm_client):
        """大纲生成器fixture."""
        return HierarchicalOutlineGenerator(mock_llm_client)
    
    @pytest.mark.asyncio
    async def test_generate_outline_simple_success_returns_complete_outline(self, outline_generator, sample_concept, sample_strategy):
        """测试简单大纲生成成功_基本输入_返回完整大纲."""
        # Given
        target_words = 6000
        
        # When
        outline = await outline_generator.generate_outline(sample_concept, sample_strategy, target_words)
        
        # Then
        assert isinstance(outline, NovelOutline)
        assert outline.structure_type == "三幕剧"
        assert len(outline.chapters) > 0
        assert all(isinstance(chapter, ChapterOutline) for chapter in outline.chapters)
        assert outline.total_estimated_words > 0
    
    @pytest.mark.asyncio
    async def test_generate_outline_multi_volume_success_returns_volume_structure(self, outline_generator, sample_concept):
        """测试多卷本大纲生成成功_多卷策略_返回卷结构."""
        # Given
        multi_volume_strategy = GenerationStrategy(
            structure_type="多卷本结构",
            chapter_count=20,
            character_depth="deep",
            pacing="epic",
            volume_count=3
        )
        target_words = 60000
        
        # When
        outline = await outline_generator.generate_outline(sample_concept, multi_volume_strategy, target_words)
        
        # Then
        assert outline.structure_type == "多卷本结构"
        assert len(outline.volumes) == 3
        assert all(isinstance(volume, VolumeOutline) for volume in outline.volumes)
        assert outline.total_estimated_words > 0
    
    @pytest.mark.asyncio
    async def test_generate_chapter_outline_success_returns_detailed_chapters(self, outline_generator, sample_concept, sample_strategy):
        """测试章节大纲生成成功_章节策略_返回详细章节."""
        # Given
        target_words = 6000
        
        # When
        chapters = await outline_generator._generate_chapter_outlines(sample_concept, sample_strategy, target_words)
        
        # Then
        assert len(chapters) == 2  # Mock返回2个章节
        assert all(isinstance(chapter, ChapterOutline) for chapter in chapters)
        
        first_chapter = chapters[0]
        assert first_chapter.number == 1
        assert first_chapter.title == "开始的征程"
        assert len(first_chapter.key_events) > 0
        assert len(first_chapter.scenes) > 0
        assert first_chapter.estimated_word_count > 0
    
    def test_create_outline_node_success_creates_valid_node(self, outline_generator):
        """测试大纲节点创建成功_有效数据_创建有效节点."""
        # Given
        node_data = {
            "title": "测试章节",
            "summary": "这是一个测试章节",
            "level": 1
        }
        
        # When
        node = outline_generator._create_outline_node(node_data)
        
        # Then
        assert isinstance(node, OutlineNode)
        assert node.title == "测试章节"
        assert node.summary == "这是一个测试章节"
        assert node.level == 1
    
    def test_calculate_word_distribution_balanced_returns_balanced_distribution(self, outline_generator):
        """测试字数分配_均衡策略_返回均衡分配."""
        # Given
        total_words = 10000
        chapter_count = 5
        
        # When
        distribution = outline_generator._calculate_word_distribution(total_words, chapter_count, "balanced")
        
        # Then
        assert len(distribution) == chapter_count
        assert sum(distribution) == total_words
        assert all(word_count > 0 for word_count in distribution)
        
        # 检查分配相对均衡（最大差异不超过20%）
        avg_words = total_words / chapter_count
        for word_count in distribution:
            assert abs(word_count - avg_words) / avg_words <= 0.2
    
    def test_calculate_word_distribution_crescendo_returns_crescendo_distribution(self, outline_generator):
        """测试字数分配_渐强策略_返回渐强分配."""
        # Given
        total_words = 10000
        chapter_count = 5
        
        # When
        distribution = outline_generator._calculate_word_distribution(total_words, chapter_count, "crescendo")
        
        # Then
        assert len(distribution) == chapter_count
        assert sum(distribution) == total_words
        
        # 检查渐强模式（后面章节比前面章节字数多）
        for i in range(1, len(distribution)):
            assert distribution[i] >= distribution[i-1]
    
    def test_validate_outline_structure_valid_returns_true(self, outline_generator, sample_concept, sample_strategy):
        """测试大纲结构验证_有效大纲_返回True."""
        # Given
        outline = NovelOutline(
            structure_type="三幕剧",
            theme=sample_concept.theme,
            genre=sample_concept.genre,
            chapters=[
                ChapterOutline(
                    number=1,
                    title="第一章",
                    summary="开始",
                    key_events=["事件1"],
                    estimated_word_count=1000,
                    scenes=[]
                )
            ],
            volumes=[],
            total_estimated_words=1000
        )
        
        # When
        is_valid = outline_generator._validate_outline_structure(outline, sample_strategy)
        
        # Then
        assert is_valid is True
    
    def test_validate_outline_structure_invalid_returns_false(self, outline_generator, sample_strategy):
        """测试大纲结构验证_无效大纲_返回False."""
        # Given
        invalid_outline = NovelOutline(
            structure_type="",  # 无效的结构类型
            theme="",
            genre="",
            chapters=[],  # 空章节列表
            volumes=[],
            total_estimated_words=0
        )
        
        # When
        is_valid = outline_generator._validate_outline_structure(invalid_outline, sample_strategy)
        
        # Then
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_generate_outline_failure_invalid_concept_raises_error(self, outline_generator, sample_strategy):
        """测试大纲生成失败_无效概念_抛出异常."""
        # Given
        invalid_concept = None
        target_words = 5000
        
        # When & Then
        with pytest.raises(OutlineGenerationError, match="概念信息不能为空"):
            await outline_generator.generate_outline(invalid_concept, sample_strategy, target_words)
    
    @pytest.mark.asyncio
    async def test_generate_outline_failure_invalid_strategy_raises_error(self, outline_generator, sample_concept):
        """测试大纲生成失败_无效策略_抛出异常."""
        # Given
        invalid_strategy = None
        target_words = 5000
        
        # When & Then
        with pytest.raises(OutlineGenerationError, match="策略信息不能为空"):
            await outline_generator.generate_outline(sample_concept, invalid_strategy, target_words)
    
    @pytest.mark.asyncio
    async def test_generate_outline_failure_invalid_word_count_raises_error(self, outline_generator, sample_concept, sample_strategy):
        """测试大纲生成失败_无效字数_抛出异常."""
        # Given
        invalid_word_count = 500  # 太少
        
        # When & Then
        with pytest.raises(OutlineGenerationError, match="目标字数必须在1000-200000之间"):
            await outline_generator.generate_outline(sample_concept, sample_strategy, invalid_word_count)
    
    def test_build_outline_prompt_includes_all_parameters(self, outline_generator, sample_concept, sample_strategy):
        """测试大纲提示词构建_包含所有参数_生成完整提示词."""
        # Given
        target_words = 10000
        
        # When
        prompt = outline_generator._build_outline_prompt(sample_concept, sample_strategy, target_words)
        
        # Then
        assert sample_concept.theme in prompt
        assert sample_concept.genre in prompt
        assert sample_strategy.structure_type in prompt
        assert str(target_words) in prompt
        assert "JSON格式" in prompt
    
    def test_parse_outline_response_valid_json_returns_chapters(self, outline_generator):
        """测试大纲响应解析_有效JSON_返回章节列表."""
        # Given
        valid_response = json.dumps({
            "chapters": [
                {
                    "number": 1,
                    "title": "第一章",
                    "summary": "开始的故事",
                    "key_events": ["事件1", "事件2"],
                    "word_count": 2000,
                    "scenes": [{"name": "场景1", "description": "描述1"}]
                }
            ]
        }, ensure_ascii=False)
        
        # When
        chapters = outline_generator._parse_outline_response(valid_response)
        
        # Then
        assert len(chapters) == 1
        assert isinstance(chapters[0], ChapterOutline)
        assert chapters[0].title == "第一章"
        assert len(chapters[0].key_events) == 2