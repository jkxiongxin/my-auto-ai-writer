"""策略选择器单元测试."""

import pytest
from dataclasses import dataclass
from typing import Dict, Any

from src.core.strategy_selector import StrategySelector, StrategySelectionError, GenerationStrategy


class TestStrategySelector:
    """策略选择器单元测试."""
    
    @pytest.fixture
    def strategy_selector(self):
        """策略选择器fixture."""
        return StrategySelector()
    
    def test_select_strategy_short_story_returns_three_act_structure(self, strategy_selector):
        """测试短篇小说策略选择_5000字_返回三幕剧结构."""
        # Given
        target_words = 5000
        concept = {"genre": "科幻", "theme": "人工智能"}
        
        # When
        strategy = strategy_selector.select_strategy(target_words, concept)
        
        # Then
        assert isinstance(strategy, GenerationStrategy)
        assert strategy.structure_type == "三幕剧"
        assert 3 <= strategy.chapter_count <= 6
        assert strategy.character_depth == "basic"
        assert strategy.pacing == "fast"
    
    def test_select_strategy_medium_story_returns_five_act_structure(self, strategy_selector):
        """测试中篇小说策略选择_25000字_返回五幕剧结构."""
        # Given
        target_words = 25000
        concept = {"genre": "奇幻", "theme": "魔法冒险"}
        
        # When
        strategy = strategy_selector.select_strategy(target_words, concept)
        
        # Then
        assert strategy.structure_type == "五幕剧"
        assert 8 <= strategy.chapter_count <= 15
        assert strategy.character_depth == "medium"
        assert strategy.pacing == "moderate"
    
    def test_select_strategy_novel_returns_multi_volume_structure(self, strategy_selector):
        """测试长篇小说策略选择_100000字_返回多卷本结构."""
        # Given
        target_words = 100000
        concept = {"genre": "奇幻", "theme": "史诗冒险"}
        
        # When
        strategy = strategy_selector.select_strategy(target_words, concept)
        
        # Then
        assert strategy.structure_type == "多卷本结构"
        assert 2 <= strategy.volume_count <= 4
        assert 20 <= strategy.chapter_count <= 40
        assert strategy.character_depth == "deep"
        assert strategy.pacing == "epic"
    
    def test_select_strategy_fantasy_genre_adjusts_parameters(self, strategy_selector):
        """测试奇幻类型策略选择_奇幻输入_调整参数."""
        # Given
        target_words = 15000
        concept = {"genre": "奇幻", "theme": "魔法世界"}
        
        # When
        strategy = strategy_selector.select_strategy(target_words, concept)
        
        # Then
        assert strategy.world_building_depth in ["medium", "high"]
        assert strategy.magic_system is not None
        assert "奇幻" in strategy.genre_specific_elements
    
    def test_select_strategy_scifi_genre_adjusts_parameters(self, strategy_selector):
        """测试科幻类型策略选择_科幻输入_调整参数."""
        # Given
        target_words = 20000
        concept = {"genre": "科幻", "theme": "太空探索"}
        
        # When
        strategy = strategy_selector.select_strategy(target_words, concept)
        
        # Then
        assert strategy.world_building_depth in ["medium", "high"]
        assert strategy.tech_level is not None
        assert "科幻" in strategy.genre_specific_elements
    
    def test_select_strategy_edge_case_minimum_words_success(self, strategy_selector):
        """测试边界情况_最小字数1000_成功返回策略."""
        # Given
        target_words = 1000
        concept = {"genre": "现实主义"}
        
        # When
        strategy = strategy_selector.select_strategy(target_words, concept)
        
        # Then
        assert strategy is not None
        assert strategy.structure_type == "单线叙述"
        assert strategy.chapter_count >= 1
    
    def test_select_strategy_edge_case_maximum_words_success(self, strategy_selector):
        """测试边界情况_最大字数200000_成功返回策略."""
        # Given
        target_words = 200000
        concept = {"genre": "史诗奇幻"}
        
        # When
        strategy = strategy_selector.select_strategy(target_words, concept)
        
        # Then
        assert strategy is not None
        assert strategy.structure_type == "史诗结构"
        assert strategy.volume_count >= 3
    
    def test_select_strategy_invalid_word_count_raises_error(self, strategy_selector):
        """测试无效字数_500字_抛出异常."""
        # Given
        target_words = 500  # 太少
        concept = {"genre": "科幻"}
        
        # When & Then
        with pytest.raises(StrategySelectionError, match="目标字数必须在1000-200000之间"):
            strategy_selector.select_strategy(target_words, concept)
    
    def test_select_strategy_empty_concept_raises_error(self, strategy_selector):
        """测试空概念_空字典_抛出异常."""
        # Given
        target_words = 10000
        concept = {}
        
        # When & Then
        with pytest.raises(StrategySelectionError, match="概念信息不能为空"):
            strategy_selector.select_strategy(target_words, concept)
    
    def test_calculate_chapter_count_returns_appropriate_count(self, strategy_selector):
        """测试章节数计算_不同字数_返回合适数量."""
        # Given & When & Then
        assert 3 <= strategy_selector._calculate_chapter_count(5000, "三幕剧") <= 6
        assert 8 <= strategy_selector._calculate_chapter_count(25000, "五幕剧") <= 15
        assert 20 <= strategy_selector._calculate_chapter_count(100000, "多卷本结构") <= 40
    
    def test_determine_pacing_returns_appropriate_pacing(self, strategy_selector):
        """测试节奏判定_不同字数_返回合适节奏."""
        # Given & When & Then
        assert strategy_selector._determine_pacing(3000) == "fast"
        assert strategy_selector._determine_pacing(25000) == "moderate"
        assert strategy_selector._determine_pacing(100000) == "epic"
    
    def test_adjust_for_genre_fantasy_returns_fantasy_elements(self, strategy_selector):
        """测试类型调整_奇幻类型_返回奇幻元素."""
        # Given
        base_strategy = GenerationStrategy(
            structure_type="三幕剧",
            chapter_count=5,
            character_depth="medium",
            pacing="moderate"
        )
        concept = {"genre": "奇幻", "theme": "魔法"}
        
        # When
        adjusted_strategy = strategy_selector._adjust_for_genre(base_strategy, concept)
        
        # Then
        assert adjusted_strategy.magic_system is not None
        assert "奇幻" in adjusted_strategy.genre_specific_elements
        assert adjusted_strategy.world_building_depth in ["medium", "high"]
    
    def test_adjust_for_genre_scifi_returns_scifi_elements(self, strategy_selector):
        """测试类型调整_科幻类型_返回科幻元素."""
        # Given
        base_strategy = GenerationStrategy(
            structure_type="五幕剧",
            chapter_count=10,
            character_depth="medium",
            pacing="moderate"
        )
        concept = {"genre": "科幻", "theme": "太空"}
        
        # When
        adjusted_strategy = strategy_selector._adjust_for_genre(base_strategy, concept)
        
        # Then
        assert adjusted_strategy.tech_level is not None
        assert "科幻" in adjusted_strategy.genre_specific_elements
        assert adjusted_strategy.world_building_depth in ["medium", "high"]
    
    def test_strategy_validation_valid_strategy_passes(self, strategy_selector):
        """测试策略验证_有效策略_通过验证."""
        # Given
        strategy = GenerationStrategy(
            structure_type="三幕剧",
            chapter_count=5,
            character_depth="medium",
            pacing="moderate"
        )
        
        # When & Then
        assert strategy_selector._validate_strategy(strategy) is True
    
    def test_strategy_validation_invalid_strategy_fails(self, strategy_selector):
        """测试策略验证_无效策略_验证失败."""
        # Given
        strategy = GenerationStrategy(
            structure_type="",  # 无效的结构类型
            chapter_count=0,    # 无效的章节数
            character_depth="medium",
            pacing="moderate"
        )
        
        # When & Then
        assert strategy_selector._validate_strategy(strategy) is False