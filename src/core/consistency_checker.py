"""基础一致性检查器模块，检查小说内容的角色和情节一致性."""

import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from src.core.character_system import Character
from src.utils.llm_client import UniversalLLMClient

logger = logging.getLogger(__name__)


class ConsistencyCheckError(Exception):
    """一致性检查异常."""
    pass


@dataclass
class ConsistencyIssue:
    """一致性问题数据类."""
    type: str  # character_inconsistency, plot_inconsistency, world_inconsistency
    character: str  # 相关角色名称
    field: str  # 相关字段（appearance, personality, behavior等）
    description: str  # 问题描述
    severity: str  # 严重程度：low, medium, high
    line_context: str  # 出问题的文本上下文
    suggestion: Optional[str] = None  # 修复建议


@dataclass
class ConsistencyCheckResult:
    """一致性检查结果数据类."""
    issues: List[ConsistencyIssue]  # 发现的问题列表
    severity: str  # 整体严重程度
    overall_score: float  # 整体一致性分数（0-10）
    suggestions: List[str]  # 修复建议列表
    has_issues: bool = field(init=False)  # 是否有问题
    
    def __post_init__(self):
        """初始化后处理."""
        self.has_issues = len(self.issues) > 0


class BasicConsistencyChecker:
    """基础一致性检查器，检查角色和情节的一致性.
    
    负责检查小说内容中的角色一致性（外貌、性格、行为）、
    情节逻辑一致性（前后事件的合理性）和世界设定一致性。
    
    Attributes:
        llm_client: LLM客户端实例
        max_retries: 最大重试次数
        timeout: 超时时间
    """
    
    def __init__(self, llm_client: UniversalLLMClient, max_retries: int = 3, timeout: int = 60):
        """初始化基础一致性检查器.
        
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
        
        # 严重程度权重配置
        self.severity_weights = {
            "low": 1,
            "medium": 3,
            "high": 5
        }
        
        # 问题类型配置
        self.issue_types = {
            "character_inconsistency": "角色一致性",
            "plot_inconsistency": "情节一致性", 
            "world_inconsistency": "世界设定一致性"
        }
        
        logger.info("基础一致性检查器初始化完成")
    
    async def check_consistency(
        self,
        content: str,
        characters: Dict[str, Character],
        chapter_info: Dict[str, Any]
    ) -> ConsistencyCheckResult:
        """检查内容的一致性.
        
        Args:
            content: 待检查的文本内容
            characters: 角色信息字典
            chapter_info: 章节信息（包含前文事件、当前事件等）
            
        Returns:
            ConsistencyCheckResult: 一致性检查结果
            
        Raises:
            ConsistencyCheckError: 当检查失败时抛出
        """
        # 输入验证
        if not content or not content.strip():
            raise ConsistencyCheckError("内容不能为空")
        
        if characters is None:
            raise ConsistencyCheckError("角色信息不能为空")
        
        logger.info(f"开始一致性检查: content_length={len(content)}, characters_count={len(characters)}")
        
        try:
            # 构建提示词
            prompt = self._build_prompt(content, characters, chapter_info)
            
            # 重试机制
            for attempt in range(self.max_retries):
                try:
                    # 调用LLM进行一致性分析
                    response = await asyncio.wait_for(
                        self.llm_client.generate_async(prompt),
                        timeout=self.timeout
                    )
                    
                    # 解析响应
                    result = self._parse_llm_response(response)
                    
                    logger.info(f"一致性检查完成: issues_count={len(result.issues)}, severity={result.severity}")
                    return result
                    
                except (ConsistencyCheckError, json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.warning(f"第{attempt + 1}次一致性检查尝试失败: {e}")
                    if attempt == self.max_retries - 1:
                        raise ConsistencyCheckError(f"LLM响应格式无效: {e}")
                    await asyncio.sleep(1)
                    
        except asyncio.TimeoutError:
            raise ConsistencyCheckError(f"一致性检查超时（{self.timeout}秒）")
        except ConsistencyCheckError:
            # 重新抛出ConsistencyCheckError，不要包装
            raise
        except Exception as e:
            logger.error(f"一致性检查失败: {e}", exc_info=True)
            raise ConsistencyCheckError(f"一致性检查失败: {e}")
    
    def _build_prompt(
        self,
        content: str,
        characters: Dict[str, Character],
        chapter_info: Dict[str, Any]
    ) -> str:
        """构建一致性检查提示词.
        
        Args:
            content: 文本内容
            characters: 角色信息
            chapter_info: 章节信息
            
        Returns:
            完整的提示词字符串
        """
        # 构建角色信息文本
        character_profiles = []
        for name, character in characters.items():
            profile = f"""
{name}:
- 角色类型: {character.role}
- 年龄: {character.age}
- 性格: {', '.join(character.personality)}
- 外貌: {character.appearance}
- 背景: {character.background}
- 动机: {character.motivation}
- 技能: {', '.join(character.skills)}
"""
            character_profiles.append(profile.strip())
        
        # 构建章节上下文信息
        chapter_context = ""
        if chapter_info:
            title = chapter_info.get("title", "")
            key_events = chapter_info.get("key_events", [])
            previous_events = chapter_info.get("previous_events", [])
            characters_involved = chapter_info.get("characters_involved", [])
            setting = chapter_info.get("setting", "")
            
            chapter_context = f"""
章节信息:
- 标题: {title}
- 涉及角色: {', '.join(characters_involved)}
- 故事背景: {setting}
- 当前章节关键事件: {', '.join(key_events)}
- 前文已发生事件: {', '.join(previous_events)}
"""
        
        prompt = f"""
请对以下小说文本内容进行一致性检查，重点关注角色一致性和情节逻辑一致性。

角色设定信息:
{''.join(character_profiles)}

{chapter_context}

待检查文本:
{content}

请仔细检查以下方面的一致性问题：

1. 角色一致性：
   - 外貌描述是否与设定一致
   - 性格表现是否符合设定
   - 行为举止是否符合角色特点
   - 对话风格是否一致

2. 情节一致性：
   - 当前事件是否与前文事件逻辑连贯
   - 角色行为是否有合理动机
   - 是否存在逻辑跳跃或矛盾

3. 世界设定一致性：
   - 环境描述是否一致
   - 能力系统是否保持一致

请以JSON格式返回检查结果：

{{
    "consistency_issues": [
        {{
            "type": "character_inconsistency/plot_inconsistency/world_inconsistency",
            "character": "相关角色名称",
            "field": "相关字段（appearance/personality/behavior/dialogue等）",
            "description": "具体问题描述",
            "severity": "low/medium/high",
            "line_context": "出现问题的具体文本片段"
        }}
    ],
    "severity": "整体严重程度（low/medium/high）",
    "overall_score": 整体一致性分数（0-10的浮点数）,
    "suggestions": ["修复建议1", "修复建议2"]
}}

要求：
1. 仔细比对文本内容与角色设定
2. 检查情节逻辑的合理性
3. 如果没有发现问题，consistency_issues为空数组
4. 分数越高表示一致性越好（10分为完全一致）
5. 响应必须是有效的JSON格式
"""
        
        return prompt.strip()
    
    def _parse_llm_response(self, response: str) -> ConsistencyCheckResult:
        """解析LLM响应为一致性检查结果.
        
        Args:
            response: LLM的原始响应
            
        Returns:
            ConsistencyCheckResult: 解析后的结果对象
            
        Raises:
            ConsistencyCheckError: 当解析失败时抛出
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
            
            # 验证必需字段
            required_fields = ["consistency_issues", "severity", "overall_score", "suggestions"]
            for field in required_fields:
                if field not in data:
                    raise KeyError(f"缺少必需字段: {field}")
            
            # 解析问题列表
            issues = []
            for issue_data in data["consistency_issues"]:
                issue = ConsistencyIssue(
                    type=issue_data.get("type", ""),
                    character=issue_data.get("character", ""),
                    field=issue_data.get("field", ""),
                    description=issue_data.get("description", ""),
                    severity=issue_data.get("severity", "low"),
                    line_context=issue_data.get("line_context", ""),
                    suggestion=issue_data.get("suggestion")
                )
                issues.append(issue)
            
            # 创建结果对象
            result = ConsistencyCheckResult(
                issues=issues,
                severity=data["severity"],
                overall_score=float(data["overall_score"]),
                suggestions=data["suggestions"]
            )
            
            return result
            
        except json.JSONDecodeError as e:
            raise ConsistencyCheckError(f"JSON解析失败: {e}")
        except KeyError as e:
            raise ConsistencyCheckError(f"响应数据格式错误: {e}")
        except (ValueError, TypeError) as e:
            raise ConsistencyCheckError(f"数据类型错误: {e}")
    
    def _assess_severity(self, issues: List[ConsistencyIssue]) -> str:
        """评估问题的整体严重程度.
        
        Args:
            issues: 问题列表
            
        Returns:
            整体严重程度字符串
        """
        if not issues:
            return "low"
        
        # 计算加权严重程度分数
        total_weight = 0
        for issue in issues:
            weight = self.severity_weights.get(issue.severity, 1)
            total_weight += weight
        
        # 根据平均权重确定整体严重程度
        if not issues:
            return "low"
        
        avg_weight = total_weight / len(issues)
        
        if avg_weight >= 4:
            return "high"
        elif avg_weight >= 2:
            return "medium"
        else:
            return "low"
    
    async def batch_check_consistency(
        self,
        contents: List[str],
        characters: Dict[str, Character],
        chapter_infos: List[Dict[str, Any]]
    ) -> List[ConsistencyCheckResult]:
        """批量检查多个内容的一致性.
        
        Args:
            contents: 待检查的文本内容列表
            characters: 角色信息字典
            chapter_infos: 章节信息列表
            
        Returns:
            一致性检查结果列表
            
        Raises:
            ConsistencyCheckError: 当检查失败时抛出
        """
        if len(contents) != len(chapter_infos):
            raise ConsistencyCheckError("内容数量与章节信息数量不匹配")
        
        logger.info(f"开始批量一致性检查: {len(contents)}个内容")
        
        results = []
        for i, (content, chapter_info) in enumerate(zip(contents, chapter_infos)):
            try:
                result = await self.check_consistency(content, characters, chapter_info)
                results.append(result)
                logger.debug(f"完成第{i+1}个内容的一致性检查")
            except Exception as e:
                logger.error(f"第{i+1}个内容一致性检查失败: {e}")
                # 创建一个默认的失败结果
                error_result = ConsistencyCheckResult(
                    issues=[],
                    severity="high",
                    overall_score=0.0,
                    suggestions=[f"检查失败: {e}"]
                )
                results.append(error_result)
        
        logger.info(f"批量一致性检查完成: {len(results)}个结果")
        return results
    
    def generate_fix_suggestions(self, issues: List[ConsistencyIssue]) -> List[str]:
        """根据问题生成修复建议.
        
        Args:
            issues: 问题列表
            
        Returns:
            修复建议列表
        """
        suggestions = []
        
        for issue in issues:
            if issue.type == "character_inconsistency":
                if issue.field == "appearance":
                    # 针对外貌问题，生成更具体的建议
                    if "眼睛" in issue.description:
                        suggestions.append(f"修正{issue.character}的眼睛颜色描述，确保与角色设定一致")
                    elif "身高" in issue.description:
                        suggestions.append(f"统一{issue.character}的身高描述")
                    else:
                        suggestions.append(f"修正{issue.character}的外貌描述，确保与角色设定一致")
                elif issue.field == "personality":
                    suggestions.append(f"调整{issue.character}的性格表现，使其符合既定人设")
                elif issue.field == "behavior":
                    suggestions.append(f"修改{issue.character}的行为描述，保持角色一致性")
                elif issue.field == "dialogue":
                    suggestions.append(f"调整{issue.character}的对话风格，保持前后一致")
                else:
                    suggestions.append(f"检查并修正{issue.character}的{issue.field}相关描述")
            
            elif issue.type == "plot_inconsistency":
                if "逻辑跳跃" in issue.description:
                    suggestions.append("添加必要的过渡情节和逻辑过程，使故事发展更加合理")
                elif "矛盾" in issue.description:
                    suggestions.append("检查并解决前后文的逻辑矛盾")
                else:
                    suggestions.append("完善情节发展的逻辑链条，确保前后连贯")
            
            elif issue.type == "world_inconsistency":
                suggestions.append("检查并统一世界设定相关的描述")
            
            # 如果问题本身包含建议，也添加进去
            if issue.suggestion:
                suggestions.append(issue.suggestion)
        
        # 去重并返回
        return list(set(suggestions))
    
    def get_character_consistency_summary(
        self,
        results: List[ConsistencyCheckResult],
        character_name: str
    ) -> Dict[str, Any]:
        """获取特定角色的一致性总结.
        
        Args:
            results: 一致性检查结果列表
            character_name: 角色名称
            
        Returns:
            角色一致性总结字典
        """
        character_issues = []
        total_mentions = 0
        
        for result in results:
            for issue in result.issues:
                if issue.character == character_name:
                    character_issues.append(issue)
            
            # 统计角色在结果中的提及次数（简化实现）
            total_mentions += 1
        
        # 按问题类型分组
        issues_by_type = {}
        for issue in character_issues:
            issue_type = issue.type
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)
        
        # 计算一致性分数
        if total_mentions == 0:
            consistency_score = 10.0
        else:
            issue_penalty = len(character_issues) / total_mentions * 2
            consistency_score = max(0, 10.0 - issue_penalty)
        
        return {
            "character_name": character_name,
            "total_issues": len(character_issues),
            "issues_by_type": issues_by_type,
            "consistency_score": round(consistency_score, 2),
            "most_common_issue_type": max(issues_by_type.keys(), key=lambda k: len(issues_by_type[k])) if issues_by_type else None
        }