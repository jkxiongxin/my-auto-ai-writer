"""简单角色系统模块，管理小说中的角色生成、关系和发展弧线."""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from src.core.concept_expander import ConceptExpansionResult
from src.core.strategy_selector import GenerationStrategy
from src.core.outline_generator import NovelOutline
from src.utils.llm_client import UniversalLLMClient

logger = logging.getLogger(__name__)


class CharacterSystemError(Exception):
    """角色系统异常."""
    pass


@dataclass
class Character:
    """角色数据类."""
    name: str
    role: str  # 主角、配角、反派、导师等
    age: int
    personality: List[str]  # 性格特点
    background: str  # 背景故事
    goals: List[str]  # 目标和动机
    skills: List[str]  # 技能和能力
    appearance: str  # 外貌描述
    motivation: str  # 核心动机
    
    # 可选字段
    relationships: List[str] = field(default_factory=list)  # 关系列表
    character_arc: Optional[str] = None  # 角色弧线
    dialogue_style: Optional[str] = None  # 对话风格
    weaknesses: List[str] = field(default_factory=list)  # 弱点
    fears: List[str] = field(default_factory=list)  # 恐惧
    secrets: List[str] = field(default_factory=list)  # 秘密


@dataclass
class CharacterRelationship:
    """角色关系数据类."""
    character1: str
    character2: str
    type: str  # 关系类型：朋友、敌人、恋人、师徒等
    description: str
    development: str  # 关系发展过程
    strength: float = 0.5  # 关系强度 0-1
    conflict_potential: float = 0.0  # 冲突潜力 0-1


@dataclass
class CharacterArc:
    """角色发展弧线数据类."""
    character_name: str
    start_state: str  # 起始状态
    end_state: str   # 结束状态
    milestones: List[str]  # 发展里程碑
    transformation_type: str = "growth"  # 转变类型：成长、堕落、救赎等
    catalyst_events: List[str] = field(default_factory=list)  # 催化事件


class CharacterDatabase:
    """角色数据库，管理所有角色信息."""
    
    def __init__(self):
        """初始化角色数据库."""
        self.characters: List[Character] = []
        self.relationships: List[CharacterRelationship] = []
        self.character_arcs: Dict[str, CharacterArc] = {}
    
    def add_character(self, character: Character) -> None:
        """添加角色."""
        if not self.get_character_by_name(character.name):
            self.characters.append(character)
    
    def get_character_by_name(self, name: str) -> Optional[Character]:
        """根据名字获取角色."""
        return next((char for char in self.characters if char.name == name), None)
    
    def get_character_by_role(self, role: str) -> Optional[Character]:
        """根据角色类型获取角色."""
        return next((char for char in self.characters if char.role == role), None)
    
    def get_characters_by_role(self, role: str) -> List[Character]:
        """根据角色类型获取所有匹配的角色."""
        return [char for char in self.characters if char.role == role]
    
    def add_relationship(self, relationship: CharacterRelationship) -> None:
        """添加角色关系."""
        self.relationships.append(relationship)
    
    def get_relationships_for_character(self, character_name: str) -> List[CharacterRelationship]:
        """获取特定角色的所有关系."""
        return [
            rel for rel in self.relationships 
            if rel.character1 == character_name or rel.character2 == character_name
        ]


class SimpleCharacterSystem:
    """简单角色系统，生成和管理小说角色.
    
    负责根据概念、策略和大纲生成合适的角色，
    建立角色间的关系，规划角色发展弧线。
    
    Attributes:
        llm_client: LLM客户端实例
        max_retries: 最大重试次数
        timeout: 超时时间
    """
    
    def __init__(self, llm_client: UniversalLLMClient, max_retries: int = 3, timeout: int = 120):
        """初始化简单角色系统.
        
        Args:
            llm_client: 统一LLM客户端实例
            max_retries: 最大重试次数
            timeout: 请求超时时间
            
        Raises:
            ValueError: 当llm_client为None时抛出
        """
        if llm_client is None:
            raise ValueError("llm_client不能为None")
        
        self.llm_client = llm_client
        self.max_retries = max_retries
        self.timeout = timeout
        
        # 角色类型配置
        self.character_role_configs = {
            "basic": ["主角", "反派", "导师"],
            "medium": ["主角", "反派", "导师", "朋友", "家人"],
            "deep": ["主角", "反派", "导师", "朋友", "家人", "竞争者", "盟友", "背叛者"]
        }
        
        # 关系类型配置
        self.relationship_types = [
            "朋友", "敌人", "恋人", "师徒", "家人", "竞争者", 
            "盟友", "陌生人", "背叛者", "救赎者"
        ]
        
        logger.info("简单角色系统初始化完成")
    
    async def generate_characters(
        self,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy,
        outline: NovelOutline
    ) -> CharacterDatabase:
        """生成角色数据库.
        
        Args:
            concept: 概念扩展结果
            strategy: 生成策略
            outline: 小说大纲
            
        Returns:
            CharacterDatabase: 完整的角色数据库
            
        Raises:
            CharacterSystemError: 当角色生成失败时抛出
        """
        # 输入验证
        if concept is None:
            raise CharacterSystemError("概念信息不能为空")
        
        if strategy is None:
            raise CharacterSystemError("策略信息不能为空")
        
        if outline is None:
            raise CharacterSystemError("大纲信息不能为空")
        
        logger.info(f"开始生成角色: depth={strategy.character_depth}, genre={concept.genre}")
        
        try:
            # 1. 确定需要的角色类型
            required_roles = self.determine_character_roles(strategy)
            
            # 2. 生成角色和关系
            characters, relationships = await self._generate_characters_and_relationships(
                concept, strategy, outline, required_roles
            )
            
            # 3. 创建角色数据库
            character_db = CharacterDatabase()
            
            # 4. 添加角色
            for character in characters:
                if self.validate_character_consistency(character):
                    character_db.add_character(character)
                else:
                    logger.warning(f"角色 {character.name} 验证失败，跳过")
            
            # 5. 添加关系
            for relationship in relationships:
                character_db.add_relationship(relationship)
            
            # 6. 分析和补充关系
            additional_relationships = self.analyze_character_relationships(character_db.characters)
            for rel in additional_relationships:
                if not self._relationship_exists(character_db, rel):
                    character_db.add_relationship(rel)
            
            # 7. 生成角色弧线
            character_arcs = await self.generate_character_arcs(character_db, concept, outline)
            character_db.character_arcs = character_arcs
            
            logger.info(f"角色生成完成: {len(character_db.characters)}个角色, {len(character_db.relationships)}个关系")
            return character_db
            
        except Exception as e:
            logger.error(f"角色生成失败: {e}", exc_info=True)
            raise CharacterSystemError(f"角色生成失败: {e}")
    
    async def _generate_characters_and_relationships(
        self,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy,
        outline: NovelOutline,
        required_roles: List[str]
    ) -> Tuple[List[Character], List[CharacterRelationship]]:
        """生成角色和关系.
        
        Args:
            concept: 概念扩展结果
            strategy: 生成策略
            outline: 小说大纲
            required_roles: 需要的角色类型列表
            
        Returns:
            角色列表和关系列表的元组
        """
        # 构建提示词
        prompt = self._build_character_prompt(concept, strategy, outline, required_roles)
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                # 调用LLM生成角色（带日志记录）
                response = await asyncio.wait_for(
                    self.llm_client.generate(
                        prompt,
                        step_type="character_creation",
                        step_name="角色创建",
                        log_generation=True
                    ),
                    timeout=self.timeout
                )
                
                # 解析响应
                characters, relationships = self._parse_character_response(response)
                
                return characters, relationships
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"第{attempt + 1}次角色生成尝试失败: {e}")
                if attempt == self.max_retries - 1:
                    raise CharacterSystemError(f"LLM响应格式无效: {e}")
                await asyncio.sleep(2)
        
        raise CharacterSystemError("角色生成失败")
    
    def _build_character_prompt(
        self,
        concept: ConceptExpansionResult,
        strategy: GenerationStrategy,
        outline: NovelOutline,
        required_roles: List[str]
    ) -> str:
        """构建角色生成提示词.
        
        Args:
            concept: 概念扩展结果
            strategy: 生成策略
            outline: 小说大纲
            required_roles: 需要的角色类型
            
        Returns:
            完整的提示词字符串
        """
        # 提取大纲中的关键事件
        key_events = []
        for chapter in outline.chapters[:3]:  # 前3章的关键事件
            key_events.extend(chapter.key_events)
        
        prompt = f"""
请为以下小说概念生成详细的角色设定。

小说信息:
- 主题: {concept.theme}
- 类型: {concept.genre}
- 主要冲突: {concept.main_conflict}
- 世界设定: {concept.world_type}
- 基调: {concept.tone}
- 主角类型: {concept.protagonist_type or '待设定'}

策略参数:
- 角色深度: {strategy.character_depth}
- 结构类型: {strategy.structure_type}
- 世界构建深度: {strategy.world_building_depth}

需要生成的角色类型: {', '.join(required_roles)}

故事关键事件: {', '.join(key_events[:5])}

请生成角色设定，以JSON格式返回：

{{
    "characters": [
        {{
            "name": "角色姓名",
            "role": "角色类型（主角/反派/导师等）",
            "age": 年龄数字,
            "personality": ["性格特点1", "性格特点2", "性格特点3"],
            "background": "详细的背景故事（150-300字）",
            "goals": ["目标1", "目标2", "目标3"],
            "skills": ["技能1", "技能2", "技能3"],
            "appearance": "外貌描述（50-100字）",
            "motivation": "核心动机（一句话概括）",
            "weaknesses": ["弱点1", "弱点2"],
            "fears": ["恐惧1", "恐惧2"],
            "secrets": ["秘密1"]
        }}
    ],
    "relationships": [
        {{
            "character1": "角色1姓名",
            "character2": "角色2姓名",
            "type": "关系类型（朋友/敌人/师徒/恋人等）",
            "description": "关系描述",
            "development": "关系发展过程"
        }}
    ]
}}

要求:
1. 角色要符合{concept.genre}类型的设定
2. 确保角色间有合理的冲突和协作关系
3. 每个角色都要有明确的动机和目标
4. 角色的背景要与世界设定一致
5. 性格特点要鲜明且互补
6. 响应必须是有效的JSON格式
"""
        
        return prompt.strip()
    
    def _parse_character_response(self, response: str) -> Tuple[List[Character], List[CharacterRelationship]]:
        """解析LLM角色响应.
        
        Args:
            response: LLM的原始响应
            
        Returns:
            角色列表和关系列表的元组
            
        Raises:
            CharacterSystemError: 当解析失败时抛出
        """
        try:
            # 清理响应文本
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # 解析JSON
            data = json.loads(cleaned_response)
            
            if "characters" not in data:
                raise KeyError("响应中缺少characters字段")
            
            # 解析角色
            characters = []
            for char_data in data["characters"]:
                character = Character(
                    name=char_data.get("name", ""),
                    role=char_data.get("role", ""),
                    age=char_data.get("age", 0),
                    personality=char_data.get("personality", []),
                    background=char_data.get("background", ""),
                    goals=char_data.get("goals", []),
                    skills=char_data.get("skills", []),
                    appearance=char_data.get("appearance", ""),
                    motivation=char_data.get("motivation", ""),
                    weaknesses=char_data.get("weaknesses", []),
                    fears=char_data.get("fears", []),
                    secrets=char_data.get("secrets", [])
                )
                characters.append(character)
            
            # 解析关系
            relationships = []
            for rel_data in data.get("relationships", []):
                relationship = CharacterRelationship(
                    character1=rel_data.get("character1", ""),
                    character2=rel_data.get("character2", ""),
                    type=rel_data.get("type", ""),
                    description=rel_data.get("description", ""),
                    development=rel_data.get("development", "")
                )
                relationships.append(relationship)
            
            return characters, relationships
            
        except json.JSONDecodeError as e:
            raise CharacterSystemError(f"JSON解析失败: {e}")
        except KeyError as e:
            raise CharacterSystemError(f"响应数据格式错误: {e}")
    
    def determine_character_roles(self, strategy: GenerationStrategy) -> List[str]:
        """确定需要的角色类型.
        
        Args:
            strategy: 生成策略
            
        Returns:
            角色类型列表
        """
        depth = strategy.character_depth
        base_roles = self.character_role_configs.get(depth, self.character_role_configs["basic"])
        
        # 根据类型添加特定角色
        additional_roles = []
        if hasattr(strategy, 'genre_specific_elements'):
            if "奇幻" in strategy.genre_specific_elements:
                additional_roles.extend(["魔法师", "精灵", "矮人"])
            elif "科幻" in strategy.genre_specific_elements:
                additional_roles.extend(["科学家", "机器人", "外星人"])
            elif "悬疑" in strategy.genre_specific_elements:
                additional_roles.extend(["侦探", "嫌疑人", "证人"])
        
        return base_roles + additional_roles[:3]  # 限制额外角色数量
    
    def validate_character_consistency(self, character: Character) -> bool:
        """验证角色一致性.
        
        Args:
            character: 待验证的角色
            
        Returns:
            验证是否通过
        """
        try:
            # 检查必需字段
            if not character.name or not character.name.strip():
                return False
            
            if not character.role or not character.role.strip():
                return False
            
            if character.age <= 0:
                return False
            
            if not character.personality:
                return False
            
            if not character.background or not character.background.strip():
                return False
            
            if not character.goals:
                return False
            
            if not character.motivation or not character.motivation.strip():
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"角色验证出错: {e}")
            return False
    
    def analyze_character_relationships(self, characters: List[Character]) -> List[CharacterRelationship]:
        """分析角色关系.
        
        Args:
            characters: 角色列表
            
        Returns:
            推断的关系列表
        """
        relationships = []
        
        # 找到主角
        protagonist = next((char for char in characters if char.role == "主角"), None)
        if not protagonist:
            return relationships
        
        for character in characters:
            if character.name == protagonist.name:
                continue
            
            # 根据角色类型推断关系
            relationship_type = self._infer_relationship_type(protagonist.role, character.role)
            if relationship_type:
                relationship = CharacterRelationship(
                    character1=protagonist.name,
                    character2=character.name,
                    type=relationship_type,
                    description=f"{protagonist.name}与{character.name}的{relationship_type}关系",
                    development="随故事发展而变化"
                )
                relationships.append(relationship)
        
        return relationships
    
    def _infer_relationship_type(self, role1: str, role2: str) -> Optional[str]:
        """推断两个角色类型间的关系.
        
        Args:
            role1: 角色1的类型
            role2: 角色2的类型
            
        Returns:
            关系类型或None
        """
        # 定义角色间的典型关系
        relationship_matrix = {
            ("主角", "反派"): "敌对",
            ("主角", "导师"): "师徒",
            ("主角", "朋友"): "朋友",
            ("主角", "家人"): "家人",
            ("主角", "恋人"): "恋人",
            ("主角", "竞争者"): "竞争",
            ("主角", "盟友"): "盟友",
            ("主角", "背叛者"): "背叛"
        }
        
        return relationship_matrix.get((role1, role2))
    
    def _relationship_exists(self, character_db: CharacterDatabase, new_relationship: CharacterRelationship) -> bool:
        """检查关系是否已存在.
        
        Args:
            character_db: 角色数据库
            new_relationship: 新关系
            
        Returns:
            关系是否已存在
        """
        for existing_rel in character_db.relationships:
            if ((existing_rel.character1 == new_relationship.character1 and 
                 existing_rel.character2 == new_relationship.character2) or
                (existing_rel.character1 == new_relationship.character2 and 
                 existing_rel.character2 == new_relationship.character1)):
                return True
        return False
    
    async def generate_character_arcs(
        self,
        character_db: CharacterDatabase,
        concept: ConceptExpansionResult,
        outline: NovelOutline
    ) -> Dict[str, CharacterArc]:
        """生成角色发展弧线.
        
        Args:
            character_db: 角色数据库
            concept: 概念扩展结果
            outline: 小说大纲
            
        Returns:
            角色弧线字典
        """
        character_arcs = {}
        
        # 为主要角色生成弧线
        main_characters = [char for char in character_db.characters if char.role in ["主角", "反派", "导师"]]
        
        for character in main_characters:
            arc = self._create_character_arc(character, concept, outline)
            if arc:
                character_arcs[character.name] = arc
        
        return character_arcs
    
    def _create_character_arc(
        self,
        character: Character,
        concept: ConceptExpansionResult,
        outline: NovelOutline
    ) -> Optional[CharacterArc]:
        """为单个角色创建发展弧线.
        
        Args:
            character: 角色对象
            concept: 概念扩展结果
            outline: 小说大纲
            
        Returns:
            角色弧线或None
        """
        try:
            # 根据角色类型确定发展类型
            if character.role == "主角":
                transformation_type = "growth"
                start_state = "无知/弱小"
                end_state = "智慧/强大"
            elif character.role == "反派":
                transformation_type = "corruption"
                start_state = "强大/自信"
                end_state = "失败/觉悟"
            elif character.role == "导师":
                transformation_type = "sacrifice"
                start_state = "隐居/保守"
                end_state = "传承/解脱"
            else:
                transformation_type = "support"
                start_state = "普通"
                end_state = "成长"
            
            # 基于大纲创建里程碑
            milestones = []
            chapter_count = len(outline.chapters)
            
            if chapter_count > 0:
                milestones.append(f"第{1}章: 角色登场")
            if chapter_count > 2:
                milestones.append(f"第{chapter_count//3}章: 初次成长")
            if chapter_count > 4:
                milestones.append(f"第{chapter_count*2//3}章: 重大转折")
            if chapter_count > 1:
                milestones.append(f"第{chapter_count}章: 最终蜕变")
            
            return CharacterArc(
                character_name=character.name,
                start_state=start_state,
                end_state=end_state,
                milestones=milestones,
                transformation_type=transformation_type
            )
            
        except Exception as e:
            logger.error(f"创建角色弧线失败: {e}")
            return None