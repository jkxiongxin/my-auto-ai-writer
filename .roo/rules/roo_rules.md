# AI智能小说生成器项目开发规范

## 项目概述

AI智能小说生成器是一个基于Python的智能小说生成系统，支持多LLM提供商、分层级大纲生成、角色系统和质量控制等核心功能。

## 目录结构规范

```
ai-novel-generator/
├── 📁 src/                         # 源代码目录
│   ├── 📁 core/                   # 核心业务逻辑模块
│   │   ├── __init__.py           # 核心模块导出
│   │   ├── concept_expander.py   # 概念扩展器
│   │   ├── strategy_selector.py  # 智能策略选择器
│   │   ├── outline_generator.py  # 分层级大纲生成器
│   │   ├── character_system.py   # 简化角色系统
│   │   ├── chapter_generator.py  # 分章节生成引擎
│   │   ├── consistency_checker.py # 基础一致性检查器
│   │   ├── quality_assessment.py # 质量评估系统
│   │   └── novel_generator.py    # 主小说生成器
│   ├── 📁 models/                 # 数据模型层
│   │   ├── __init__.py           # 模型模块导出
│   │   ├── database.py           # 数据库连接和会话管理
│   │   ├── novel_models.py       # 小说相关数据模型
│   │   │   ├── NovelProject      # 小说项目模型
│   │   │   ├── Chapter           # 章节模型
│   │   │   ├── Character         # 角色模型
│   │   │   ├── Outline           # 大纲模型
│   │   │   ├── GenerationTask    # 生成任务模型
│   │   │   └── QualityMetrics    # 质量指标模型
│   │   ├── user_models.py        # 用户相关模型
│   │   │   ├── User              # 用户模型
│   │   │   └── UserSession       # 用户会话模型
│   │   └── config_models.py      # 配置相关模型
│   │       ├── GenerationConfig  # 生成配置模型
│   │       ├── LLMProviderConfig # LLM提供商配置
│   │       └── QualityThresholds # 质量阈值配置
│   ├── 📁 api/                    # API接口层
│   │   ├── __init__.py           # API模块导出
│   │   ├── main.py               # FastAPI应用主入口
│   │   ├── 📁 routers/            # API路由模块
│   │   │   ├── __init__.py       # 路由模块导出
│   │   │   ├── health.py         # 健康检查路由
│   │   │   ├── generation.py     # 小说生成路由
│   │   │   ├── projects.py       # 项目管理路由
│   │   │   ├── quality.py        # 质量检查路由
│   │   │   └── export.py         # 导出功能路由
│   │   ├── 📁 middleware/         # 中间件
│   │   │   ├── __init__.py       # 中间件导出
│   │   │   ├── cors.py           # CORS中间件
│   │   │   ├── logging.py        # 日志中间件
│   │   │   ├── rate_limit.py     # 速率限制中间件
│   │   │   └── error_handler.py  # 错误处理中间件
│   │   ├── dependencies.py       # 依赖注入
│   │   └── schemas.py            # Pydantic数据模式
│   └── 📁 utils/                  # 工具模块
│       ├── __init__.py           # 工具模块导出
│       ├── config.py             # 配置管理系统 ✅
│       ├── llm_client.py         # 统一LLM客户端
│       ├── logger.py             # 日志系统
│       ├── cache.py              # 缓存管理
│       ├── validators.py         # 数据验证器
│       ├── text_processing.py    # 文本处理工具
│       ├── file_utils.py         # 文件操作工具
│       ├── monitoring.py         # 系统监控工具
│       └── 📁 providers/          # LLM提供商模块
│           ├── __init__.py       # 提供商模块导出
│           ├── base_provider.py  # 基础提供商抽象接口
│           ├── openai_client.py  # OpenAI客户端实现
│           ├── ollama_client.py  # Ollama客户端实现
│           ├── custom_client.py  # 自定义模型客户端
│           ├── router.py         # LLM智能路由器
│           └── fallback_manager.py # 降级和容错管理
├── 📁 tests/                      # 测试代码目录
│   ├── __init__.py               # 测试配置和标记
│   ├── conftest.py               # pytest配置和fixture
│   ├── 📁 unit/                   # 单元测试
│   │   ├── 📁 core/               # 核心模块单元测试
│   │   ├── 📁 models/             # 模型层单元测试
│   │   ├── 📁 api/                # API层单元测试
│   │   └── 📁 utils/              # 工具模块单元测试
│   ├── 📁 integration/            # 集成测试
│   │   ├── test_llm_integration.py # LLM集成测试
│   │   ├── test_api_integration.py # API集成测试
│   │   └── test_database_integration.py # 数据库集成测试
│   ├── 📁 performance/            # 性能测试
│   │   ├── test_generation_performance.py # 生成性能测试
│   │   ├── test_api_performance.py # API性能测试
│   │   └── test_concurrent_generation.py # 并发生成测试
│   ├── 📁 validation/             # 验证测试
│   │   ├── test_novel_quality.py # 小说质量验证
│   │   ├── test_consistency_check.py # 一致性检查验证
│   │   └── test_character_coherence.py # 角色一致性验证
│   ├── 📁 acceptance/             # 验收测试
│   │   ├── test_end_to_end_generation.py # 端到端生成测试
│   │   ├── test_user_scenarios.py # 用户场景测试
│   │   └── test_api_contracts.py # API契约测试
│   ├── 📁 fixtures/               # 测试数据和fixture
│   │   ├── sample_novels.py      # 示例小说数据
│   │   ├── mock_llm_responses.py # 模拟LLM响应
│   │   └── test_configurations.py # 测试配置
│   └── test_project_setup.py     # 项目设置验证测试 ✅
├── 📁 docs/                       # 项目文档目录
│   ├── api/                      # API文档
│   ├── architecture/             # 架构设计文档
│   ├── development/              # 开发指南
│   ├── deployment/               # 部署文档
│   └── user_guide/               # 用户指南
├── 📁 config/                     # 配置文件目录
│   ├── development.yaml          # 开发环境配置
│   ├── production.yaml           # 生产环境配置
│   ├── testing.yaml              # 测试环境配置
│   └── logging.yaml              # 日志配置
├── 📁 scripts/                    # 脚本文件目录
│   ├── setup.py                 # 项目设置脚本
│   ├── deploy.py                # 部署脚本
│   ├── migration.py             # 数据库迁移脚本
│   └── performance_test.py      # 性能测试脚本
├── 📁 data/                       # 数据文件目录
│   ├── 📁 samples/                # 样本数据
│   │   ├── sample_novels/        # 示例小说
│   │   ├── character_templates/  # 角色模板
│   │   └── prompt_templates/     # 提示词模板
│   ├── 📁 templates/              # 生成模板
│   │   ├── novel_templates/      # 小说模板
│   │   ├── chapter_templates/    # 章节模板
│   │   └── character_sheets/     # 角色表模板
│   ├── 📁 uploads/                # 用户上传文件
│   ├── 📁 exports/                # 导出文件
│   └── 📁 cache/                  # 缓存文件
├── 📄 pyproject.toml              # Poetry配置和项目元数据 ✅
├── 📄 poetry.lock                 # 依赖锁定文件 ✅
├── 📄 README.md                   # 项目说明文档 ✅
├── 📄 CHANGELOG.md                # 项目更新日志 ✅
├── 📄 LICENSE                     # 项目许可证
├── 📄 .env.example                # 环境变量模板 ✅
├── 📄 .gitignore                  # Git忽略配置 ✅
├── 📄 .pre-commit-config.yaml     # 代码质量钩子 ✅
├── 📄 Dockerfile                  # Docker构建文件
├── 📄 docker-compose.yml          # Docker编排配置
└── 📄 mkdocs.yml                  # 文档生成配置
```

## 代码规范

### 1. Python代码规范

#### 1.1 代码格式化
- **工具**: Black (line-length=88)
- **导入排序**: isort (profile=black)
- **自动格式化**: 保存时自动运行

```python
# 示例：标准的导入顺序
# 标准库
import os
import sys
from typing import List, Dict, Optional, Union

# 第三方库
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String

# 本地导入
from src.core.novel_generator import NovelGenerator
from src.models.novel_models import NovelProject
from src.utils.config import settings
```

#### 1.2 类型注解
- **强制类型注解**: 所有函数参数和返回值必须有类型注解
- **工具**: MyPy静态类型检查
- **配置**: strict模式

```python
from typing import List, Dict, Optional, Union
from pydantic import BaseModel

class NovelProject(BaseModel):
    """小说项目模型."""
    
    id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    target_words: int = Field(default=10000, ge=1000, le=200000)
    style_preference: Optional[str] = None
    
    def validate_word_count(self) -> bool:
        """验证字数设置."""
        return 1000 <= self.target_words <= 200000

async def generate_novel(
    project: NovelProject,
    config: GenerationConfig
) -> Dict[str, Union[str, int, List[str]]]:
    """生成小说."""
    pass
```

#### 1.3 文档字符串
- **格式**: Google风格文档字符串
- **必需**: 所有公共函数、类、模块必须有文档字符串
- **内容**: 功能描述、参数说明、返回值、异常

```python
class ConceptExpander:
    """概念扩展器，将简单创意扩展为详细的小说概念.
    
    将用户输入的简单创意（如"机器人获得情感"）扩展为包含
    背景设定、人物关系、冲突设计等详细元素的完整小说概念。
    
    Attributes:
        llm_client: LLM客户端实例
        expansion_templates: 扩展模板集合
        quality_threshold: 质量阈值配置
    """
    
    def __init__(self, llm_client: UniversalLLMClient) -> None:
        """初始化概念扩展器.
        
        Args:
            llm_client: 统一LLM客户端实例
            
        Raises:
            ValueError: 当llm_client为None时抛出
        """
        pass
    
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
            LLMConnectionError: 当LLM连接失败时抛出
        """
        pass
```

#### 1.4 错误处理
- **自定义异常**: 每个模块定义特定的异常类
- **异常链**: 保持异常的原始堆栈信息
- **日志记录**: 所有异常都要记录到日志

```python
# src/core/exceptions.py
class NovelGeneratorError(Exception):
    """小说生成器基础异常."""
    pass

class ConceptExpansionError(NovelGeneratorError):
    """概念扩展异常."""
    pass

class LLMConnectionError(NovelGeneratorError):
    """LLM连接异常."""
    pass

# 使用示例
import logging
from src.core.exceptions import ConceptExpansionError

logger = logging.getLogger(__name__)

async def expand_concept(self, user_input: str) -> ConceptExpansionResult:
    """扩展概念."""
    try:
        result = await self._call_llm(user_input)
        return self._parse_result(result)
    except Exception as e:
        logger.error(f"概念扩展失败: {user_input}, 错误: {e}")
        raise ConceptExpansionError(f"无法扩展概念: {user_input}") from e
```

### 2. 测试规范

#### 2.1 测试结构
- **测试覆盖率**: 目标85%以上
- **测试分层**: 单元测试、集成测试、性能测试、验证测试、验收测试
- **命名规范**: `test_<功能>_<场景>_<预期结果>`

```python
# tests/unit/core/test_concept_expander.py
import pytest
from unittest.mock import AsyncMock, Mock
from src.core.concept_expander import ConceptExpander
from src.core.exceptions import ConceptExpansionError

class TestConceptExpander:
    """概念扩展器单元测试."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """模拟LLM客户端fixture."""
        return AsyncMock()
    
    @pytest.fixture
    def concept_expander(self, mock_llm_client):
        """概念扩展器fixture."""
        return ConceptExpander(mock_llm_client)
    
    async def test_expand_concept_success_simple_input(self, concept_expander):
        """测试概念扩展成功_简单输入_返回完整概念."""
        # Given
        user_input = "机器人获得了情感"
        target_words = 10000
        
        # When
        result = await concept_expander.expand_concept(user_input, target_words)
        
        # Then
        assert result.expanded_concept is not None
        assert len(result.expanded_concept) > len(user_input)
        assert result.confidence_score >= 0.7
    
    async def test_expand_concept_failure_empty_input_raises_error(self, concept_expander):
        """测试概念扩展失败_空输入_抛出异常."""
        # Given
        user_input = ""
        target_words = 10000
        
        # When & Then
        with pytest.raises(ConceptExpansionError, match="输入不能为空"):
            await concept_expander.expand_concept(user_input, target_words)
```

#### 2.2 测试标记
- **pytest标记**: 用于分类和选择性运行测试

```python
import pytest

# 单元测试标记
@pytest.mark.unit
def test_basic_functionality():
    pass

# 集成测试标记
@pytest.mark.integration
def test_llm_integration():
    pass

# 性能测试标记
@pytest.mark.performance
def test_generation_speed():
    pass

# 慢速测试标记
@pytest.mark.slow
def test_large_novel_generation():
    pass

# LLM依赖测试标记
@pytest.mark.llm
def test_openai_connection():
    pass
```

#### 2.3 Mock和Fixture
- **数据隔离**: 每个测试使用独立的测试数据
- **外部依赖**: 所有外部依赖都要Mock
- **可重用性**: 通用fixture定义在conftest.py

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock
from src.utils.config import Settings

@pytest.fixture
def test_settings():
    """测试配置fixture."""
    return Settings(
        database_url="sqlite:///:memory:",
        openai_api_key="test-key",
        cache_enabled=False
    )

@pytest.fixture
def mock_llm_response():
    """模拟LLM响应fixture."""
    return {
        "content": "这是一个关于机器人的故事...",
        "usage": {"total_tokens": 150},
        "model": "gpt-4-turbo"
    }
```

### 3. API设计规范

#### 3.1 接口定义规范
设计API接口时需遵循以下规范：

1. **RESTful设计原则**:
   - 资源使用复数名词（如`/projects`）
   - HTTP方法正确使用：GET（查询）、POST（创建）、PUT（更新）、DELETE（删除）
   - 使用标准HTTP状态码（200成功、201创建、400错误请求、404未找到等）

2. **版本控制**:
   - API版本包含在路径中（如`/api/v1/projects`）
   - 使用语义化版本控制（Semantic Versioning）

3. **端点命名**:
   - 路径使用小写和连字符（kebab-case）
   - 嵌套资源使用路径参数（如`/projects/{project_id}/chapters`）

4. **请求/响应模型**:
   - 所有API输入输出使用Pydantic模型
   - 请求模型：验证输入数据并生成OpenAPI文档
   - 响应模型：确保输出格式一致，隐藏敏感数据
   - 使用Field添加额外元数据（描述、示例等）

5. **分页和过滤**:
   - 列表端点支持分页（`skip`和`limit`参数）
   - 支持字段过滤（`fields`参数）
   - 支持排序（`sort`参数）

6. **错误处理**:
   - 使用标准错误响应格式
   - 包含错误代码、消息和详情
   - 全局异常处理器捕获所有异常

7. **文档**:
   - 使用OpenAPI自动生成文档
   - 所有端点添加操作摘要和描述
   - 为复杂操作添加示例

```python
# src/api/routers/projects.py 示例
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional

router = APIRouter(prefix="/api/v1/projects", tags=["项目管理"])

@router.post(
    "/",
    status_code=201,
    response_model=NovelProjectResponse,
    summary="创建新项目",
    description="创建一个新的小说生成项目"
)
async def create_project(
    project: CreateNovelProjectRequest,
    current_user: User = Depends(get_current_user)
) -> NovelProjectResponse:
    pass

@router.get(
    "/",
    response_model=List[NovelProjectResponse],
    summary="获取项目列表",
    description="分页获取所有小说项目"
)
async def list_projects(
    skip: int = Query(0, ge=0, description="跳过的项目数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回的项目数量"),
    status: Optional[str] = Query(None, description="项目状态过滤"),
    search: Optional[str] = Query(None, description="搜索关键词")
) -> List[NovelProjectResponse]:
    pass

@router.get(
    "/{project_id}",
    response_model=NovelProjectResponse,
    summary="获取项目详情",
    description="获取指定ID的小说项目详细信息"
)
async def get_project(
    project_id: int,
    fields: Optional[str] = Query(None, description="返回字段过滤（逗号分隔）")
) -> NovelProjectResponse:
    pass
```

#### 3.2 请求/响应模型规范
请求和响应模型设计需遵循：

1. **请求模型**:
   - 命名：`<操作><资源>Request`（如`CreateProjectRequest`）
   - 字段：只包含客户端可提供的参数
   - 验证：使用Pydantic验证器确保数据完整性

2. **响应模型**:
   - 命名：`<资源>Response`（如`ProjectResponse`）
   - 字段：只包含客户端需要的数据
   - 安全：排除敏感字段（如数据库ID、内部状态）

3. **通用模式**:
   - 分页响应：包含数据列表和元数据（总数、页码等）
   - 错误响应：包含错误代码、消息和可选详情
   - 操作结果：包含操作状态和结果数据

```python
# src/api/schemas.py 示例
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""
    data: List[T]
    total: int
    skip: int
    limit: int

class ErrorResponse(BaseModel):
    """错误响应模型"""
    error_code: str
    message: str
    detail: Optional[str] = None

class SuccessResponse(BaseModel, Generic[T]):
    """操作成功响应"""
    status: str = "success"
    data: T
```

### 4. 数据库规范

#### 4.1 数据模型定义规范
数据模型是系统核心，设计时需遵循以下规范：

1. **命名规范**:
   - 表名和列名使用蛇形命名法（snake_case）
   - 表名使用复数形式（例如`novel_projects`）
   - 关联表名使用两个表名的单数形式按字母顺序连接（例如`character_chapter`）

2. **字段类型**:
   - 根据数据特性选择最小但足够的类型（如短字符串用`String(50)`，长文本用`Text`）
   - 布尔值使用`Boolean`类型，不用整数代替
   - 日期时间使用`DateTime`类型，统一使用UTC时间

3. **主键和外键**:
   - 每个表必须有主键，命名为`id`，类型为整数或UUID
   - 外键字段命名为`<关联表名单数>_id`（例如`project_id`）
   - 明确定义外键约束和级联规则

4. **索引规范**:
   - 主键自动创建索引
   - 经常查询的字段（如`created_at`, `status`）应创建索引
   - 避免过度索引，尤其对频繁更新的表

5. **默认值**:
   - 为字段设置合理默认值（如`created_at`默认为当前时间，`status`默认为初始状态）

6. **关系定义**:
   - 一对多关系：在"多"方使用外键，在"一"方定义关系
   - 多对多关系：使用关联表，并在两个模型中定义多对多关系
   - 使用`back_populates`参数明确双向关系

7. **数据验证**:
   - 在模型层进行基本数据验证（如非空约束、长度约束）
   - 使用`CheckConstraint`进行复杂约束（如状态字段取值范围）

```python
# src/models/novel_models.py 示例
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

class NovelProject(Base):
    """小说项目模型."""
    
    __tablename__ = 'novel_projects'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    # 使用server_default设置数据库端默认值
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # 一对多关系：一个项目有多个章节
    chapters = relationship("Chapter", back_populates="project", cascade="all, delete-orphan")

class Chapter(Base):
    """章节模型."""
    
    __tablename__ = 'chapters'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    project_id = Column(Integer, ForeignKey('novel_projects.id'), nullable=False)
    
    # 定义反向关系
    project = relationship("NovelProject", back_populates="chapters")
```

### 5. 配置管理规范

#### 5.1 环境配置
- **Pydantic Settings**: 使用Pydantic进行配置管理
- **环境变量**: 支持从环境变量读取配置
- **配置验证**: 启动时验证配置有效性

```python
# src/utils/config.py (已实现)
from pydantic import BaseSettings, Field
from typing import List

class Settings(BaseSettings):
    """应用程序配置."""
    
    # 数据库配置
    database_url: str = Field(env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # LLM配置
    openai_api_key: str = Field(env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo", env="OPENAI_MODEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

### 6. 中间件使用规范

#### 6.1 通用中间件使用方法
中间件是处理请求和响应的重要组件，遵循以下规范：

1. **注册顺序**: 中间件的注册顺序很重要，按照以下顺序添加：
   - 错误处理中间件（最外层）
   - CORS中间件
   - 日志中间件
   - 速率限制中间件
   - 自定义业务中间件

2. **标准中间件**:
   ```python
   # FastAPI应用注册中间件
   app = FastAPI()
   
   # 错误处理中间件（最外层）
   app.middleware("http")(error_handler_middleware)
   
   # CORS中间件
   app.add_middleware(
       CORSMiddleware,
       allow_origins=settings.allowed_origins,
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   
   # 日志中间件
   app.middleware("http")(logging_middleware)
   
   # 速率限制中间件
   app.middleware("http")(rate_limit_middleware)
   ```

3. **自定义中间件结构**:
   ```python
   async def custom_middleware(request: Request, call_next) -> Response:
       # 请求前处理
       start_time = time.time()
       request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
       
       # 设置请求ID到state
       request.state.request_id = request_id
       
       try:
           # 调用下一个中间件或路由处理
           response = await call_next(request)
       except Exception as exc:
           # 异常处理
           logger.error(f"请求处理异常: {exc}", exc_info=True)
           response = JSONResponse(
               status_code=500,
               content={"error": "Internal server error"}
           )
       
       # 响应后处理
       process_time = time.time() - start_time
       response.headers["X-Process-Time"] = str(process_time)
       response.headers["X-Request-ID"] = request_id
       
       return response
   ```

4. **中间件最佳实践**:
   - **轻量处理**: 中间件应保持轻量，避免阻塞操作
   - **异步支持**: 所有中间件必须支持异步
   - **错误处理**: 捕获并适当处理异常，避免中断请求
   - **上下文传递**: 使用`request.state`传递上下文信息
   - **性能监控**: 记录请求处理时间

#### 6.2 项目内置中间件
项目已实现以下通用中间件：

1. **错误处理中间件 (`error_handler.py`)**:
   - 全局捕获异常
   - 生成标准化错误响应
   - 记录错误日志
   - 保留原始堆栈信息

2. **日志中间件 (`logging.py`)**:
   - 记录请求和响应信息
   - 包含请求ID、处理时间
   - 结构化日志输出
   - 敏感信息过滤

3. **速率限制中间件 (`rate_limit.py`)**:
   - 基于IP和端点的限流
   - 可配置的速率限制
   - 支持突发请求处理
   - 返回标准化的限流响应

4. **CORS中间件 (`cors.py`)**:
   - 跨域资源共享支持
   - 可配置的允许来源
   - 预检请求处理
   - 安全头设置

### 7. 日志规范

#### 7.1 结构化日志
- **格式**: JSON格式结构化日志
- **级别**: DEBUG、INFO、WARNING、ERROR、CRITICAL
- **上下文**: 包含请求ID、用户ID等上下文信息

```python
# src/utils/logger.py
import logging
import structlog
from typing import Dict, Any

def setup_logging(log_level: str = "INFO") -> None:
    """设置结构化日志."""
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> structlog.BoundLogger:
    """获取结构化日志器."""
    return structlog.get_logger(name)

# 使用示例
logger = get_logger(__name__)

async def generate_chapter(project_id: int, chapter_number: int):
    """生成章节."""
    logger.info(
        "开始生成章节",
        project_id=project_id,
        chapter_number=chapter_number,
        action="chapter_generation_start"
    )
    
    try:
        # 生成逻辑
        result = await _do_generation()
        
        logger.info(
            "章节生成成功",
            project_id=project_id,
            chapter_number=chapter_number,
            word_count=result.word_count,
            action="chapter_generation_success"
        )
        
    except Exception as e:
        logger.error(
            "章节生成失败",
            project_id=project_id,
            chapter_number=chapter_number,
            error=str(e),
            action="chapter_generation_error"
        )
        raise
```

### 7. 性能规范

#### 7.1 异步编程
- **异步优先**: 所有I/O操作使用异步
- **并发控制**: 限制并发数量防止资源耗尽
- **超时处理**: 所有外部调用设置超时

```python
import asyncio
from typing import List
import aiohttp
from contextlib import asynccontextmanager

class LLMClient:
    """异步LLM客户端."""
    
    def __init__(self, max_concurrent: int = 3):
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def generate_text(
        self,
        prompt: str,
        timeout: int = 60
    ) -> str:
        """生成文本."""
        async with self.semaphore:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                    # API调用逻辑
                    pass
            except asyncio.TimeoutError:
                raise LLMTimeoutError(f"LLM调用超时: {timeout}秒")
```

### 8. 安全规范

#### 8.1 输入验证
- **Pydantic验证**: 所有输入使用Pydantic验证
- **SQL注入防护**: 使用ORM和参数化查询
- **XSS防护**: 输出时进行HTML转义

```python
from pydantic import BaseModel, validator
import html

class UserInput(BaseModel):
    """用户输入验证."""
    
    content: str
    
    @validator('content')
    def validate_content(cls, v):
        """验证内容安全性."""
        # 长度限制
        if len(v) > 10000:
            raise ValueError('内容过长')
        
        # HTML转义
        v = html.escape(v)
        
        # 恶意内容检查
        forbidden_patterns = ['<script>', 'javascript:', 'onload=']
        for pattern in forbidden_patterns:
            if pattern.lower() in v.lower():
                raise ValueError('内容包含不安全字符')
        
        return v
```

## Git提交规范

### 提交消息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 提交类型
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式化（不影响功能）
- `refactor`: 代码重构
- `test`: 添加或修改测试
- `chore`: 构建工具或依赖更新
- `perf`: 性能优化

### 示例提交
```bash
feat(core): 实现概念扩展器模块

- 添加ConceptExpander类，支持用户创意扩展
- 实现多风格模板支持（科幻、奇幻、现实主义）
- 集成质量评估和一致性检查
- 添加完整的单元测试和集成测试

Closes #123
```

## 开发工作流

### 1. 功能开发流程
1. **创建功能分支**: `git checkout -b feature/concept-expander`
2. **编写测试**: 先写测试，后写实现 (TDD)
3. **实现功能**: 按照代码规范实现功能
4. **运行测试**: 确保所有测试通过
5. **代码审查**: 提交PR进行代码审查
6. **合并代码**: 审查通过后合并到主分支

### 2. 质量检查
```bash
# 代码格式化
poetry run black src tests

# 导入排序
poetry run isort src tests

# 类型检查
poetry run mypy src

# 代码规范检查
poetry run flake8 src tests

# 安全检查
poetry run bandit -r src

# 运行测试
poetry run pytest

# 测试覆盖率
poetry run pytest --cov=src --cov-report=html
```

### 3. 版本发布
1. **更新CHANGELOG.md**
2. **更新版本号** (pyproject.toml)
3. **创建发布标签**: `git tag v0.1.0`
4. **推送标签**: `git push origin v0.1.0`

这些规范确保了代码质量、团队协作效率和项目的长期可维护性。所有开发人员都应该严格遵循这些规范。