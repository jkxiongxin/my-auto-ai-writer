"""简单角色系统单元测试."""

import pytest
from unittest.mock import AsyncMock, Mock
import json
from typing import Dict, Any, List

from src.core.character_system import (
    SimpleCharacterSystem, 
    CharacterSystemError, 
    Character,
    CharacterRelationship,
    CharacterArc,
    CharacterDatabase
)
from src.core.concept_expander import ConceptExpansionResult
from src.core.strategy_selector import GenerationStrategy
from src.core.outline_generator import NovelOutline, ChapterOutline
from src.utils.llm_client import UniversalLLMClient


class TestSimpleCharacterSystem:
    """简单角色系统单元测试."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """模拟LLM客户端fixture."""
        client = AsyncMock(spec=UniversalLLMClient)
        
        # 模拟角色生成响应
        character_response = {
            "characters": [
                {
                    "name": "艾莉丝",
                    "role": "主角",
                    "age": 18,
                    "personality": ["勇敢", "好奇", "善良"],
                    "background": "来自小村庄的普通女孩，意外发现自己拥有魔法天赋",
                    "goals": ["掌握魔法", "拯救世界", "找到归属感"],
                    "skills": ["初级魔法", "剑术基础", "草药知识"],
                    "appearance": "金色长发，绿色眼睛，身材娇小但意志坚定",
                    "motivation": "保护所爱之人"
                },
                {
                    "name": "马库斯",
                    "role": "导师",
                    "age": 45,
                    "personality": ["智慧", "严格", "神秘"],
                    "background": "前宫廷魔法师，因某个秘密而隐居",
                    "goals": ["训练艾莉丝", "守护古老秘密", "赎罪"],
                    "skills": ["高级魔法", "古代知识", "战斗经验"],
                    "appearance": "灰白胡须，深邃的蓝眼睛，身着朴素的长袍",
                    "motivation": "弥补过去的错误"
                }
            ],
            "relationships": [
                {
                    "character1": "艾莉丝",
                    "character2": "马库斯", 
                    "type": "师徒",
                    "description": "马库斯成为艾莉丝的魔法导师",
                    "development": "从陌生到信任，最终如父女般的深厚感情"
                }
            ]
        }
        
        client.generate_async.return_value = json.dumps(character_response, ensure_ascii=False)
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
    def sample_outline(self):
        """示例大纲fixture."""
        chapters = [
            ChapterOutline(
                number=1,
                title="魔法觉醒",
                summary="艾莉丝发现自己的魔法天赋",
                key_events=["魔法觉醒", "遇见导师", "开始训练"],
                estimated_word_count=3000,
                scenes=[]
            ),
            ChapterOutline(
                number=2,
                title="第一次考验",
                summary="艾莉丝面临第一个挑战",
                key_events=["接受任务", "进入森林", "战胜怪物"],
                estimated_word_count=3000,
                scenes=[]
            )
        ]
        
        return NovelOutline(
            structure_type="三幕剧",
            theme="友谊与成长",
            genre="奇幻",
            chapters=chapters,
            total_estimated_words=6000
        )
    
    @pytest.fixture
    def character_system(self, mock_llm_client):
        """角色系统fixture."""
        return SimpleCharacterSystem(mock_llm_client)
    
    @pytest.mark.asyncio
    async def test_generate_characters_success_returns_character_database(self, character_system, sample_concept, sample_strategy, sample_outline):
        """测试角色生成成功_基本输入_返回角色数据库."""
        # When
        character_db = await character_system.generate_characters(sample_concept, sample_strategy, sample_outline)
        
        # Then
        assert isinstance(character_db, CharacterDatabase)
        assert len(character_db.characters) > 0
        assert len(character_db.relationships) > 0
        
        # 检查主角存在
        protagonist = character_db.get_character_by_role("主角")
        assert protagonist is not None
        assert protagonist.name == "艾莉丝"
        assert protagonist.role == "主角"
        assert len(protagonist.personality) > 0
    
    @pytest.mark.asyncio
    async def test_generate_character_arcs_success_returns_character_arcs(self, character_system, sample_concept, sample_outline):
        """测试角色弧线生成成功_角色数据库_返回角色弧线."""
        # Given
        character_db = CharacterDatabase()
        character_db.add_character(Character(
            name="艾莉丝",
            role="主角",
            age=18,
            personality=["勇敢", "好奇"],
            background="村庄女孩",
            goals=["掌握魔法"],
            skills=["魔法"],
            appearance="金发绿眼",
            motivation="保护他人"
        ))
        
        # When
        arcs = await character_system.generate_character_arcs(character_db, sample_concept, sample_outline)
        
        # Then
        assert len(arcs) > 0
        assert "艾莉丝" in arcs
        assert isinstance(arcs["艾莉丝"], CharacterArc)
        assert len(arcs["艾莉丝"].milestones) > 0
    
    def test_validate_character_consistency_valid_returns_true(self, character_system):
        """测试角色一致性验证_有效角色_返回True."""
        # Given
        character = Character(
            name="测试角色",
            role="主角",
            age=25,
            personality=["勇敢", "聪明"],
            background="完整的背景故事",
            goals=["目标1", "目标2"],
            skills=["技能1"],
            appearance="外貌描述",
            motivation="明确的动机"
        )
        
        # When
        is_valid = character_system.validate_character_consistency(character)
        
        # Then
        assert is_valid is True
    
    def test_validate_character_consistency_invalid_returns_false(self, character_system):
        """测试角色一致性验证_无效角色_返回False."""
        # Given
        invalid_character = Character(
            name="",  # 空名字
            role="",  # 空角色
            age=0,    # 无效年龄
            personality=[],  # 空性格
            background="",   # 空背景
            goals=[],       # 空目标
            skills=[],      # 空技能
            appearance="",  # 空外貌
            motivation=""   # 空动机
        )
        
        # When
        is_valid = character_system.validate_character_consistency(invalid_character)
        
        # Then
        assert is_valid is False
    
    def test_analyze_character_relationships_returns_relationships(self, character_system):
        """测试角色关系分析_角色列表_返回关系列表."""
        # Given
        characters = [
            Character(name="艾莉丝", role="主角", age=18, personality=["勇敢"], background="", goals=[], skills=[], appearance="", motivation=""),
            Character(name="马库斯", role="导师", age=45, personality=["智慧"], background="", goals=[], skills=[], appearance="", motivation=""),
            Character(name="黑暗领主", role="反派", age=100, personality=["邪恶"], background="", goals=[], skills=[], appearance="", motivation="")
        ]
        
        # When
        relationships = character_system.analyze_character_relationships(characters)
        
        # Then
        assert len(relationships) > 0
        
        # 应该有师徒关系
        mentor_relationship = next((r for r in relationships if r.type == "师徒"), None)
        assert mentor_relationship is not None
        
        # 应该有敌对关系
        enemy_relationship = next((r for r in relationships if r.type == "敌对"), None)
        assert enemy_relationship is not None
    
    def test_determine_character_roles_returns_appropriate_roles(self, character_system, sample_strategy):
        """测试角色角色确定_策略参数_返回合适角色."""
        # When
        roles = character_system.determine_character_roles(sample_strategy)
        
        # Then
        assert "主角" in roles
        assert "导师" in roles
        assert len(roles) >= 3  # 至少主角、导师、反派
        
        # 深度角色应该有更多角色类型
        if sample_strategy.character_depth == "deep":
            assert len(roles) >= 5
    
    @pytest.mark.asyncio
    async def test_generate_characters_failure_invalid_concept_raises_error(self, character_system, sample_strategy, sample_outline):
        """测试角色生成失败_无效概念_抛出异常."""
        # Given
        invalid_concept = None
        
        # When & Then
        with pytest.raises(CharacterSystemError, match="概念信息不能为空"):
            await character_system.generate_characters(invalid_concept, sample_strategy, sample_outline)
    
    @pytest.mark.asyncio
    async def test_generate_characters_failure_invalid_strategy_raises_error(self, character_system, sample_concept, sample_outline):
        """测试角色生成失败_无效策略_抛出异常."""
        # Given
        invalid_strategy = None
        
        # When & Then
        with pytest.raises(CharacterSystemError, match="策略信息不能为空"):
            await character_system.generate_characters(sample_concept, invalid_strategy, sample_outline)
    
    def test_build_character_prompt_includes_all_parameters(self, character_system, sample_concept, sample_strategy, sample_outline):
        """测试角色提示词构建_包含所有参数_生成完整提示词."""
        # Given
        required_roles = ["主角", "反派", "导师"]
        
        # When
        prompt = character_system._build_character_prompt(sample_concept, sample_strategy, sample_outline, required_roles)
        
        # Then
        assert sample_concept.theme in prompt
        assert sample_concept.genre in prompt
        assert sample_strategy.character_depth in prompt
        assert "JSON格式" in prompt
        assert "主角" in prompt
    
    def test_parse_character_response_valid_json_returns_characters(self, character_system):
        """测试角色响应解析_有效JSON_返回角色列表."""
        # Given
        valid_response = json.dumps({
            "characters": [
                {
                    "name": "测试角色",
                    "role": "主角", 
                    "age": 20,
                    "personality": ["勇敢"],
                    "background": "背景",
                    "goals": ["目标"],
                    "skills": ["技能"],
                    "appearance": "外貌",
                    "motivation": "动机"
                }
            ],
            "relationships": [
                {
                    "character1": "角色1",
                    "character2": "角色2",
                    "type": "朋友",
                    "description": "友谊",
                    "development": "发展"
                }
            ]
        }, ensure_ascii=False)
        
        # When
        characters, relationships = character_system._parse_character_response(valid_response)
        
        # Then
        assert len(characters) == 1
        assert isinstance(characters[0], Character)
        assert characters[0].name == "测试角色"
        
        assert len(relationships) == 1
        assert isinstance(relationships[0], CharacterRelationship)
        assert relationships[0].type == "朋友"
    
    def test_character_database_operations(self, character_system):
        """测试角色数据库操作_增删查改_功能正常."""
        # Given
        db = CharacterDatabase()
        character = Character(
            name="测试角色",
            role="主角",
            age=25,
            personality=["勇敢"],
            background="背景",
            goals=["目标"],
            skills=["技能"],
            appearance="外貌",
            motivation="动机"
        )
        
        # When & Then - 添加角色
        db.add_character(character)
        assert len(db.characters) == 1
        
        # When & Then - 按名字查找
        found_character = db.get_character_by_name("测试角色")
        assert found_character is not None
        assert found_character.name == "测试角色"
        
        # When & Then - 按角色查找
        protagonist = db.get_character_by_role("主角")
        assert protagonist is not None
        assert protagonist.role == "主角"
        
        # When & Then - 查找不存在的角色
        not_found = db.get_character_by_name("不存在")
        assert not_found is None
    
    def test_character_arc_creation_and_tracking(self, character_system):
        """测试角色弧线创建和追踪_角色发展_正确追踪."""
        # Given
        character_name = "测试角色"
        start_state = "天真无知"
        end_state = "成熟智慧"
        milestones = ["第一次冒险", "遭遇挫折", "获得成长", "最终觉悟"]
        
        # When
        arc = CharacterArc(
            character_name=character_name,
            start_state=start_state,
            end_state=end_state,
            milestones=milestones
        )
        
        # Then
        assert arc.character_name == character_name
        assert arc.start_state == start_state
        assert arc.end_state == end_state
        assert len(arc.milestones) == 4
        assert "第一次冒险" in arc.milestones