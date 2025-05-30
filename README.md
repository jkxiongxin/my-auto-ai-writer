# AI智能小说生成器 (AI Novel Generator)

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tested with pytest](https://img.shields.io/badge/tested%20with-pytest-0A9EDC.svg)](https://github.com/pytest-dev/pytest)
[![Coverage](https://img.shields.io/badge/coverage-85%25+-green.svg)](https://github.com/pytest-dev/pytest-cov)

## 项目概述

AI智能小说生成器是一个概念验证（POC）项目，旨在验证超大规模小说生成技术的可行性。系统支持生成1万字到10万字的智能小说，具备多LLM提供商支持、智能策略选择、分层级大纲生成等核心功能。

## 核心功能

- 🚀 **概念扩展模块**: 将简单创意扩展为详细的小说概念
- 🎯 **智能策略选择器**: 根据字数和类型选择最优生成策略
- 📋 **渐进式大纲生成器**: 先建立世界观，在生成过程中逐步完善大纲
- 🔗 **无缝章节衔接**: 智能分析上章结尾，生成流畅的章节过渡
- 👥 **简化角色系统**: 创建和管理角色档案与关系
- ✍️ **分章节生成引擎**: 高质量的章节内容生成
- 🔍 **基础一致性检查器**: 确保内容的逻辑一致性
- 📊 **多字数分级支持**: 支持1千字到1千万字的小说生成

## 技术栈

- **后端**: Python 3.11+ + FastAPI
- **数据库**: SQLite (POC阶段)
- **前端**: React + TypeScript
- **测试**: pytest + coverage
- **LLM**: 多提供商支持（OpenAI GPT-4 Turbo + Ollama + 自定义模型）

## 快速开始

### 环境要求

- Python 3.11+
- Poetry (依赖管理)
- Git

### 安装依赖

```bash
# 克隆仓库
git clone <repository-url>
cd ai-novel-generator

# 安装Poetry (如果未安装)
curl -sSL https://install.python-poetry.org | python3 -

# 安装项目依赖
poetry install

# 激活虚拟环境
poetry shell
```

### 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件，添加API密钥
nano .env
```

**必需的环境变量配置：**

```bash
# OpenAI API配置（推荐）
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview

# Ollama配置（可选，本地模型）
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2:13b-chat

# 自定义模型配置（可选）
CUSTOM_MODEL_BASE_URL=http://localhost:7860
CUSTOM_MODEL_NAME=gemini-2.0-flash

# 系统配置
LLM_RATE_LIMIT_DELAY=1.0
LLM_MAX_RETRIES=3
LOG_LEVEL=INFO
```

**LLM提供商配置说明：**

1. **OpenAI GPT-4** (推荐新手使用)
   - 需要 OpenAI API Key
   - 最稳定，质量最高
   - 需要付费使用

2. **Ollama** (本地运行)
   - 免费使用，数据隐私
   - 需要本地安装 Ollama
   - 安装命令：`curl -fsSL https://ollama.ai/install.sh | sh`
   - 拉取模型：`ollama pull llama2:13b-chat`

3. **自定义模型**
   - 支持兼容 OpenAI API 的任何服务
   - 可以是本地部署的模型服务
   - 如 Text Generation WebUI、vLLM 等

### 运行测试

```bash
# 运行所有测试
poetry run pytest

# 运行特定类型的测试
poetry run pytest -m unit
poetry run pytest -m integration

# 生成测试覆盖率报告
poetry run pytest --cov=src --cov-report=html
```

### 启动系统

**方法一：使用便捷启动脚本**

```bash
# 启动API服务器
python start_api.py

# 或者使用poetry
poetry run python start_api.py
```

**方法二：手动启动FastAPI服务器**

```bash
# 启动FastAPI开发服务器
poetry run uvicorn src.api.main:app --reload --port 8000

# 生产环境启动
poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 访问系统

启动成功后，您可以通过以下方式访问系统：

**1. Web前端界面**
```
http://localhost:8000
```
- 提供友好的用户界面
- 支持小说生成、进度监控、结果查看
- 支持导出为多种格式（TXT、DOCX、PDF）

**2. API文档界面**
```
http://localhost:8000/docs
```
- Swagger UI 自动生成的API文档
- 支持在线测试所有API接口
- 查看详细的请求/响应格式

**3. 替代API文档**
```
http://localhost:8000/redoc
```
- ReDoc 风格的API文档
- 更清晰的文档展示

**4. 健康检查**
```
http://localhost:8000/health
```
- 检查系统运行状态
- 查看各个LLM提供商的可用性

### 使用示例

**通过Web界面使用：**
1. 访问 `http://localhost:8000`
2. 在文本框中输入创意，如："一个机器人获得了情感"
3. 设置目标字数（1000-10000000字）
4. 选择风格偏好（可选）
5. 点击"开始生成"
6. 在进度页面监控生成过程
7. 生成完成后查看和下载结果

**通过API使用：**
```bash
# 发起生成请求
curl -X POST "http://localhost:8000/api/v1/generate-novel" \
     -H "Content-Type: application/json" \
     -d '{
       "user_input": "一个机器人获得了情感",
       "target_words": 10000,
       "style_preference": "科幻"
     }'

# 查询生成进度
curl "http://localhost:8000/api/v1/projects/{project_id}/status"

# 获取生成结果
curl "http://localhost:8000/api/v1/projects/{project_id}/result"
```

## 项目结构

```
ai-novel-generator/
├── src/                    # 源代码目录
│   ├── core/              # 核心业务逻辑
│   ├── models/            # 数据模型
│   ├── api/               # API接口
│   └── utils/             # 工具模块
├── tests/                 # 测试代码
│   ├── unit/             # 单元测试
│   ├── integration/      # 集成测试
│   └── performance/      # 性能测试
├── docs/                  # 项目文档
├── config/                # 配置文件
└── data/                  # 数据文件
```

## 开发指南

### 代码规范

项目采用严格的代码质量标准：

```bash
# 代码格式化
poetry run black src tests

# 代码规范检查
poetry run flake8 src tests

# 类型检查
poetry run mypy src

# 安全检查
poetry run bandit -r src
```

### 测试驱动开发

项目采用TDD开发流程：

1. **红色阶段**: 编写失败的测试用例
2. **绿色阶段**: 编写最少代码使测试通过
3. **重构阶段**: 优化代码结构和性能
4. **验证阶段**: 确保所有测试仍然通过

### 提交代码

```bash
# 安装pre-commit钩子
poetry run pre-commit install

# 运行所有质量检查
poetry run pre-commit run --all-files

# 提交代码
git add .
git commit -m "feat: 添加新功能"
git push
```

## 故障排除

### 常见问题和解决方案

**1. 启动失败 - 端口被占用**
```bash
# 检查端口占用
lsof -i :8000

# 使用不同端口启动
poetry run uvicorn src.api.main:app --reload --port 8001
```

**2. LLM提供商连接失败**
```bash
# 检查环境变量配置
cat .env

# 测试OpenAI连接
python -c "
import openai
openai.api_key = 'your_api_key'
print(openai.Model.list())
"

# 测试Ollama连接
curl http://localhost:11434/api/tags
```

**3. 依赖安装问题**
```bash
# 清理并重新安装
poetry env remove python
poetry install

# 或使用pip安装
pip install -r requirements.txt
```

**4. 生成过程中断**
```bash
# 查看日志
tail -f logs/ai_novel_generator.log

# 检查系统资源
htop
df -h
```

**5. 前端页面无法访问**
- 确保API服务器已启动
- 检查防火墙设置
- 尝试使用 `127.0.0.1:8000` 而不是 `localhost:8000`

### 性能优化建议

**1. 提高生成速度**
```bash
# 使用更快的LLM模型
OPENAI_MODEL=gpt-3.5-turbo-1106

# 增加并发数（需要更多资源）
LLM_CONCURRENT_REQUESTS=3

# 启用缓存
ENABLE_LLM_CACHE=true
```

**2. 降低成本**
```bash
# 使用本地Ollama模型（免费）
PRIMARY_LLM_PROVIDER=ollama

# 或使用较便宜的模型
OPENAI_MODEL=gpt-3.5-turbo
```

## API 使用示例

### Python SDK 使用

```python
import httpx
import asyncio

async def generate_novel():
    # 创建生成请求
    payload = {
        "user_input": "一个机器人获得了情感",
        "target_words": 10000,
        "style_preference": "科幻",
        "use_progressive_outline": True  # 使用渐进式大纲生成
    }

    # 发送请求
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/generate-novel",
            json=payload
        )
        project_id = response.json()["project_id"]
        print(f"生成任务已启动，项目ID: {project_id}")

        # 轮询生成状态
        while True:
            status_response = await client.get(
                f"http://localhost:8000/api/v1/projects/{project_id}/status"
            )
            status = status_response.json()
            
            print(f"进度: {status['progress']}% - {status['stage']}")
            
            if status["status"] == "completed":
                print("生成完成！")
                break
            elif status["status"] == "failed":
                print(f"生成失败: {status.get('error', '未知错误')}")
                break
                
            await asyncio.sleep(5)  # 等待5秒后再次查询

        # 获取结果
        result_response = await client.get(
            f"http://localhost:8000/api/v1/projects/{project_id}/result"
        )
        result = result_response.json()
        print(f"生成的小说总字数: {result['total_words']}")

# 运行示例
asyncio.run(generate_novel())
```

### cURL 使用示例

```bash
# 1. 发起生成请求
PROJECT_ID=$(curl -s -X POST "http://localhost:8000/api/v1/generate-novel" \
     -H "Content-Type: application/json" \
     -d '{
       "user_input": "一个机器人获得了情感",
       "target_words": 10000,
       "style_preference": "科幻"
     }' | jq -r '.project_id')

echo "项目ID: $PROJECT_ID"

# 2. 监控生成进度
while true; do
  STATUS=$(curl -s "http://localhost:8000/api/v1/projects/$PROJECT_ID/status" | jq -r '.status')
  PROGRESS=$(curl -s "http://localhost:8000/api/v1/projects/$PROJECT_ID/status" | jq -r '.progress')
  echo "状态: $STATUS, 进度: $PROGRESS%"
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  
  sleep 5
done

# 3. 获取生成结果
curl -s "http://localhost:8000/api/v1/projects/$PROJECT_ID/result" | jq '.'

# 4. 导出为文件
curl -s "http://localhost:8000/api/v1/projects/$PROJECT_ID/export?format=txt" \
     -o "generated_novel.txt"
```

## 性能指标

- **生成速度**: 10万字作品≤2小时
- **内容质量**: 连贯性≥7.5/10，角色一致性≥80%
- **系统性能**: API响应时间<5秒，支持≥3个并发任务
- **测试覆盖率**: ≥85%

## 贡献指南

我们欢迎社区贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 编写测试用例
4. 实现功能代码
5. 确保所有测试通过
6. 提交更改 (`git commit -m 'Add amazing feature'`)
7. 推送分支 (`git push origin feature/amazing-feature`)
8. 创建Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系我们

- 项目维护者: AI Novel Generator Team
- 邮箱: team@ai-novel-generator.com
- 项目主页: [GitHub Repository](https://github.com/your-org/ai-novel-generator)

## 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解版本更新历史。