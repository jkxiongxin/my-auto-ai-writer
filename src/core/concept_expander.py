"""概念扩展器模块，将简单创意扩展为详细的小说概念."""

import json
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

from src.utils.llm_client import UniversalLLMClient

logger = logging.getLogger(__name__)


class ConceptExpansionError(Exception):
    """概念扩展异常."""
    pass


@dataclass
class ConceptExpansionResult:
    """概念扩展结果."""
    
    theme: str
    genre: str
    main_conflict: str
    world_type: str
    tone: str
    protagonist_type: Optional[str] = None
    setting: Optional[str] = None
    core_message: Optional[str] = None
    complexity_level: str = "medium"
    confidence_score: float = 0.0
    raw_data: Optional[Dict[str, Any]] = None


class ConceptExpander:
    """概念扩展器，将简单创意扩展为详细的小说概念.
    
    将用户输入的简单创意（如"机器人获得情感"）扩展为包含
    背景设定、人物关系、冲突设计等详细元素的完整小说概念。
    
    Attributes:
        llm_client: LLM客户端实例
        max_retries: 最大重试次数
        timeout: 超时时间（秒）
    """
    
    def __init__(self, llm_client: UniversalLLMClient, max_retries: int = 3, timeout: int = 60):
        """初始化概念扩展器.
        
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
        
        logger.info("概念扩展器初始化完成")
    
    async def expand_concept(
        self,
        user_input: str,
        target_words: int,
        style_preference: Optional[str] = None
    ) -> ConceptExpansionResult:
        """扩展用户创意为详细概念.
        
        Args:
            user_input: 用户输入的简单创意
            target_words: 目标字数，影响概念复杂度
            style_preference: 风格偏好（科幻、奇幻、现实主义等）
            
        Returns:
            ConceptExpansionResult: 包含扩展后概念的结果对象
            
        Raises:
            ConceptExpansionError: 当概念扩展失败时抛出
        """
        # 输入验证
        if not user_input or not user_input.strip():
            raise ConceptExpansionError("用户输入不能为空")
        
        if not (1000 <= target_words <= 200000):
            raise ConceptExpansionError("目标字数必须在1000-200000之间")
        
        logger.info(f"开始扩展概念: input='{user_input[:50]}...', target_words={target_words}")
        
        try:
            # 构建提示词
            prompt = self._build_prompt(user_input, target_words, style_preference)
            
            # 重试机制
            for attempt in range(self.max_retries):
                try:
                    # 调用LLM（带日志记录）
                    response = await asyncio.wait_for(
                        self.llm_client.generate(
                            prompt,
                            step_type="concept_expansion",
                            step_name="概念扩展",
                            log_generation=True
                        ),
                        timeout=self.timeout
                    )
                    
                    # 解析响应
                    result = self._parse_llm_response(response)
                    
                    # 设置复杂度级别
                    result.complexity_level = self._determine_complexity_level(target_words)
                    
                    logger.info(f"概念扩展完成: theme='{result.theme}', confidence={result.confidence_score:.2f}")
                    return result
                    
                except (json.JSONDecodeError, KeyError, ValueError, ConceptExpansionError) as e:
                    logger.warning(f"第{attempt + 1}次尝试失败: {e}")
                    if attempt == self.max_retries - 1:
                        raise ConceptExpansionError(f"LLM响应格式无效: {e}")
                    await asyncio.sleep(1)  # 短暂等待后重试
                    
        except asyncio.TimeoutError:
            raise ConceptExpansionError(f"概念扩展超时（{self.timeout}秒）")
        except Exception as e:
            logger.error(f"概念扩展失败: {e}", exc_info=True)
            raise ConceptExpansionError(f"概念扩展失败: {e}")
    
    def _build_prompt(self, user_input: str, target_words: int, style_preference: Optional[str]) -> str:
        """构建LLM提示词.
        
        Args:
            user_input: 用户输入
            target_words: 目标字数
            style_preference: 风格偏好
            
        Returns:
            完整的提示词字符串
        """
        style_text = f"，风格偏好：{style_preference}" if style_preference else ""
        
        prompt = f"""
请将以下简单的创意扩展为详细的小说概念。

用户创意: {user_input}
目标字数: {target_words}{style_text}

请分析这个创意，并扩展为包含以下要素的完整概念。请以JSON格式返回，包含以下字段：

{{
    "theme": "小说的核心主题（如：成长、救赎、科技与人性等）",
    "genre": "文学类型（如：科幻、奇幻、悬疑、现实主义等）",
    "main_conflict": "主要冲突和核心矛盾（详细描述）",
    "world_type": "故事世界类型（如：现代都市、架空世界、未来社会等）",
    "tone": "作品基调（如：轻松幽默、深刻严肃、冒险刺激等）",
    "protagonist_type": "主角类型（可选）",
    "setting": "故事背景设定（可选）", 
    "core_message": "要传达的核心信息（可选）"
}}

要求：
1. 根据目标字数调整概念的复杂度和深度
2. 确保各元素之间逻辑一致
3. 响应必须是有效的JSON格式
4. 每个字段的内容要具体且有启发性
"""
        
        return prompt.strip()
    
    def _parse_llm_response(self, response: str) -> ConceptExpansionResult:
        """解析LLM响应为结构化结果.
        
        Args:
            response: LLM的原始响应
            
        Returns:
            ConceptExpansionResult: 解析后的结果对象
            
        Raises:
            ConceptExpansionError: 当解析失败时抛出
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
            concept_data = json.loads(cleaned_response)
            
            # 验证必需字段
            required_fields = ["theme", "genre", "main_conflict", "world_type", "tone"]
            for field in required_fields:
                if field not in concept_data or not concept_data[field]:
                    raise KeyError(f"缺少必需字段: {field}")
            
            # 计算置信度分数
            confidence_score = self._calculate_confidence_score(concept_data)
            
            # 创建结果对象
            result = ConceptExpansionResult(
                theme=concept_data["theme"],
                genre=concept_data["genre"],
                main_conflict=concept_data["main_conflict"],
                world_type=concept_data["world_type"],
                tone=concept_data["tone"],
                protagonist_type=concept_data.get("protagonist_type"),
                setting=concept_data.get("setting"),
                core_message=concept_data.get("core_message"),
                confidence_score=confidence_score,
                raw_data=concept_data
            )
            
            return result
            
        except json.JSONDecodeError as e:
            raise ConceptExpansionError(f"JSON解析失败: {e}")
        except KeyError as e:
            raise ConceptExpansionError(f"响应数据格式错误: {e}")
    
    def _calculate_confidence_score(self, concept_data: Dict[str, Any]) -> float:
        """计算概念扩展的置信度分数.
        
        Args:
            concept_data: 解析后的概念数据
            
        Returns:
            0.0-1.0之间的置信度分数
        """
        score = 0.0
        max_score = 1.0
        
        # 基于内容质量的评分
        required_fields = ["theme", "genre", "main_conflict", "world_type", "tone"]
        
        for field in required_fields:
            if field in concept_data and concept_data[field]:
                content = str(concept_data[field])
                
                # 基于内容长度评分（更详细的内容获得更高分数）
                if len(content) >= 10:
                    score += 0.15
                elif len(content) >= 5:
                    score += 0.10
                else:
                    score += 0.05
                
                # 基于内容丰富度评分
                if any(keyword in content for keyword in ["、", "，", "和", "但", "而且", "然而"]):
                    score += 0.05
        
        # 可选字段加分
        optional_fields = ["protagonist_type", "setting", "core_message"]
        for field in optional_fields:
            if field in concept_data and concept_data[field]:
                score += 0.05
        
        return min(score, max_score)
    
    def _determine_complexity_level(self, target_words: int) -> str:
        """根据目标字数确定复杂度级别.
        
        Args:
            target_words: 目标字数
            
        Returns:
            复杂度级别字符串
        """
        if target_words <= 5000:
            return "simple"
        elif target_words <= 30000:
            return "medium"
        else:
            return "complex"