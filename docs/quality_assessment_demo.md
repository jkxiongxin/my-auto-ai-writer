# 质量评估系统演示文档

## 概述

AI智能小说生成器的质量评估系统是一个基于PRD文档要求实现的多维度质量评估和智能修订系统。该系统能够：

1. **多维度质量评估**：从情节逻辑、角色一致性、语言质量、风格一致性等维度评估小说质量
2. **智能修订建议**：基于评估结果生成具体的修订建议
3. **迭代修订**：自动执行多轮修订直到达到目标质量
4. **批量检查**：支持对多个章节进行批量质量检查
5. **质量趋势分析**：跟踪和分析质量变化趋势

## 核心组件

### 1. QualityAssessmentSystem (核心质量评估系统)

```python
from src.core.quality_assessment import QualityAssessmentSystem
from src.utils.llm_client import UniversalLLMClient
from src.core.character_system import Character

# 初始化
llm_client = UniversalLLMClient()
quality_system = QualityAssessmentSystem(llm_client)

# 准备评估数据
content = "小说章节内容..."
characters = {
    "主角": Character(
        name="张三",
        role="主角",
        age=25,
        personality=["勇敢", "善良"],
        background="普通农民出身",
        goals=["拯救家乡", "成为英雄"],
        skills=["剑术", "魔法"],
        appearance="高大英俊",
        motivation="拯救家乡"
    )
}
chapter_info = {
    "title": "决战时刻",
    "chapter_number": 1,
    "key_events": ["主角觉醒", "初次战斗"],
    "characters_involved": ["张三"]
}

# 执行质量评估
metrics = await quality_system.assess_quality(
    content, characters, chapter_info
)

print(f"总体分数: {metrics.overall_score}")
print(f"等级: {metrics.grade}")
```

### 2. EnhancedQualityChecker (增强质量检查器)

```python
from src.core.quality_integration import EnhancedQualityChecker

# 初始化增强检查器
enhanced_checker = EnhancedQualityChecker(llm_client)

# 全面质量检查
report = await enhanced_checker.comprehensive_quality_check(
    content=content,
    characters=characters,
    chapter_info=chapter_info,
    include_suggestions=True
)

print(f"综合分数: {report['overall_score']}")
print(f"修订建议数量: {len(report['revision_suggestions'])}")
```

## API 接口使用

### 1. 增强质量检查

```http
POST /api/projects/{project_id}/enhanced-quality-check
Content-Type: application/json

{
    "project_id": 1,
    "check_types": ["consistency", "coherence", "character", "plot", "language", "style"],
    "include_suggestions": true,
    "style_guide": "保持古典文学风格"
}
```

**响应示例：**
```json
{
    "project_id": 1,
    "overall_score": 7.8,
    "grade": "B",
    "assessment_time": "2024-01-15T10:30:00Z",
    "word_count": 5000,
    "chapter_count": 3,
    "character_count": 5,
    "quality_dimensions": {
        "plot_logic": {
            "name": "情节逻辑",
            "score": 8.2,
            "weight": 0.3,
            "issues": [],
            "suggestions": ["保持情节紧凑"]
        },
        "character_consistency": {
            "name": "角色一致性",
            "score": 7.5,
            "weight": 0.25,
            "issues": ["主角性格描述前后不一致"],
            "suggestions": ["统一角色性格描述"]
        }
    },
    "consistency": {
        "score": 7.9,
        "severity": "low",
        "issues": [],
        "suggestions": ["保持当前质量"]
    },
    "revision_suggestions": [
        {
            "type": "character",
            "priority": "medium",
            "description": "统一主角性格描述",
            "target_content": "相关段落",
            "suggested_change": "保持性格一致性",
            "reason": "避免角色形象混乱"
        }
    ],
    "summary": "内容质量良好，存在少量可改进的地方。",
    "recommendations": [
        "改进角色一致性：当前分数7.5",
        "保持其他维度的高质量水准"
    ]
}
```

### 2. 智能修订

```http
POST /api/projects/{project_id}/intelligent-revision
Content-Type: application/json

{
    "project_id": 1,
    "target_score": 8.5,
    "max_iterations": 3,
    "style_guide": "保持原有风格"
}
```

**响应示例：**
```json
{
    "project_id": 1,
    "original_score": 6.8,
    "final_score": 8.3,
    "improvement": 1.5,
    "iterations_performed": 2,
    "revision_history": [
        {
            "revision_type": "plot",
            "changes_made": ["修复情节逻辑漏洞"],
            "improvement_score": 0.8,
            "revision_time": "2024-01-15T10:35:00Z"
        },
        {
            "revision_type": "language",
            "changes_made": ["优化语言表达"],
            "improvement_score": 0.7,
            "revision_time": "2024-01-15T10:40:00Z"
        }
    ],
    "final_report": {
        "overall_score": 8.3,
        "grade": "B",
        "summary": "经过智能修订，内容质量显著提升"
    }
}
```

### 3. 批量质量检查

```http
POST /api/projects/{project_id}/batch-quality-check
Content-Type: application/json

{
    "project_id": 1,
    "chapter_ids": [1, 2, 3],
    "style_guide": "统一检查标准"
}
```

**响应示例：**
```json
{
    "project_id": 1,
    "chapter_reports": [
        {
            "overall_score": 8.1,
            "grade": "B",
            "chapter_title": "第一章"
        },
        {
            "overall_score": 7.6,
            "grade": "B",
            "chapter_title": "第二章"
        },
        {
            "overall_score": 8.5,
            "grade": "A",
            "chapter_title": "第三章"
        }
    ],
    "overall_statistics": {
        "total_chapters": 3,
        "average_score": 8.07,
        "highest_score": 8.5,
        "lowest_score": 7.6,
        "score_distribution": {
            "A (9.0+)": 0,
            "B (7.5-8.9)": 3,
            "C (6.0-7.4)": 0,
            "D (4.0-5.9)": 0,
            "F (<4.0)": 0
        }
    }
}
```

## 质量维度详解

### 1. 情节逻辑 (Plot Logic)
- **评估内容**：事件发展的逻辑性、因果关系、情节转折、冲突设置、节奏掌控
- **权重**：30%
- **评分标准**：
  - 9-10分：逻辑严密，情节发展自然
  - 7-8分：逻辑基本合理，偶有小问题
  - 5-6分：存在逻辑漏洞，需要修改
  - 1-4分：逻辑混乱，需要大幅修订

### 2. 角色一致性 (Character Consistency)
- **评估内容**：角色性格、行为、对话风格的一致性
- **权重**：25%
- **评分标准**：
  - 9-10分：角色形象鲜明，前后一致
  - 7-8分：角色基本一致，细节需完善
  - 5-6分：存在不一致问题
  - 1-4分：角色形象混乱

### 3. 语言质量 (Language Quality)
- **评估内容**：语法正确性、表达清晰度、词汇丰富性、句式变化、修辞手法
- **权重**：25%
- **评分标准**：
  - 9-10分：语言优美，表达精准
  - 7-8分：语言流畅，表达清晰
  - 5-6分：语言基本通顺，有改进空间
  - 1-4分：语言表达存在明显问题

### 4. 风格一致性 (Style Consistency)
- **评估内容**：叙述视角、语言风格、情感基调、文体特征
- **权重**：20%
- **评分标准**：
  - 9-10分：风格统一，特色鲜明
  - 7-8分：风格基本一致
  - 5-6分：风格偶有不一致
  - 1-4分：风格混乱，缺乏统一性

## 修订建议类型

### 1. 情节修订 (Plot Revision)
- **目标**：修复逻辑漏洞，优化情节发展
- **示例**：
  - 添加过渡情节
  - 修复因果关系
  - 调整情节节奏

### 2. 角色修订 (Character Revision)
- **目标**：保持角色一致性，完善角色设定
- **示例**：
  - 统一角色性格描述
  - 修正行为逻辑
  - 完善角色动机

### 3. 语言修订 (Language Revision)
- **目标**：提升语言质量和表达效果
- **示例**：
  - 修正语法错误
  - 丰富词汇表达
  - 优化句式结构

### 4. 风格修订 (Style Revision)
- **目标**：保持风格一致性
- **示例**：
  - 统一叙述视角
  - 调整语言风格
  - 保持情感基调

## 使用场景

### 1. 单章节质量检查
适用于对单个章节进行详细的质量评估，获取具体的改进建议。

### 2. 全书质量评估
对整部小说进行综合性质量评估，了解整体质量水平。

### 3. 智能修订优化
自动修订内容直到达到预期质量标准，减少人工修改工作量。

### 4. 批量章节对比
对多个章节进行质量对比，识别质量薄弱环节。

### 5. 质量趋势监控
跟踪创作过程中的质量变化，持续改进创作质量。

## 最佳实践

### 1. 设置合理的质量目标
- 新手作者：目标分数 6.0-7.0
- 有经验作者：目标分数 7.5-8.5
- 专业作者：目标分数 8.5-9.5

### 2. 分阶段质量检查
- 初稿完成后：基础质量检查
- 修改阶段：重点维度检查
- 定稿前：全面质量评估

### 3. 重视高优先级建议
- 优先处理"high"优先级的修订建议
- 关注影响整体评分的关键问题
- 保持角色和情节的一致性

### 4. 保持创作风格
- 在质量提升的同时保持个人风格
- 使用style_guide参数指定风格要求
- 避免过度修改导致风格丢失

## 技术特性

### 1. 异步处理
所有质量评估操作都支持异步处理，确保高性能。

### 2. 错误恢复
具备完善的错误处理机制，单个组件失败不影响整体功能。

### 3. 模块化设计
各个评估维度独立设计，便于扩展和维护。

### 4. 配置灵活
支持自定义质量阈值、修订参数等配置。

### 5. 测试覆盖
完整的单元测试覆盖，确保功能稳定性。

## 总结

质量评估系统提供了全面、智能、易用的小说质量评估和改进功能，能够有效帮助作者提升创作质量，实现了PRD文档中的多轮修订要求。通过多维度评估、智能修订建议和自动化改进流程，大大提升了小说创作的效率和质量。