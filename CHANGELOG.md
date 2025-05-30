# 更新日志

所有项目的重要更改都将记录在此文件中。

本格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

## [0.2.0] - 2025-05-29

### 新增
- 实现系统集成与端到端测试
  - 添加`NovelGenerator`核心类协调所有模块
  - 创建集成测试`test_novel_generation_flow.py`
  - 实现带重试机制的章节生成
  - 添加进度跟踪功能

## [0.1.0] - 2025-05-29

### 新增
- 项目初始化完成
- 基础目录结构建立
- 测试驱动开发环境配置
- 多模块架构设计
- 配置管理系统
- 项目文档模板

### 技术规格
- Python 3.11+ 支持
- FastAPI Web 框架
- SQLite 数据库 (POC 阶段)
- pytest 测试框架
- Poetry 依赖管理
- 多 LLM 提供商支持架构

### 项目结构
```
ai-novel-generator/
├── src/                    # 源代码目录
│   ├── core/              # 核心业务逻辑
│   ├── models/            # 数据模型
│   ├── api/               # API接口
│   ├── utils/             # 工具模块
│   └── utils/providers/   # LLM提供商
├── tests/                 # 测试代码
│   ├── unit/             # 单元测试
│   ├── integration/      # 集成测试
│   ├── performance/      # 性能测试
│   ├── validation/       # 验证测试
│   └── acceptance/       # 验收测试
├── docs/                  # 项目文档
├── config/                # 配置文件
├── scripts/               # 脚本文件
└── data/                  # 数据文件
    ├── samples/          # 样本数据
    └── templates/        # 模板文件
```

### 开发环境
- ✅ Poetry 安装和配置
- ✅ 虚拟环境创建
- ✅ 依赖包安装
- ✅ 代码质量工具配置
- ✅ 测试框架配置
- ✅ 项目结构验证测试

### 下一步计划
1. 实现概念扩展模块 (ConceptExpander)
2. 实现策略选择器 (StrategySelector)
3. 实现多 LLM 提供商集成
4. 数据库模型设计和实现
5. API 基础框架开发

---

### 提交约定

本项目使用以下提交消息约定：

- `feat:` 新功能
- `fix:` 错误修复
- `docs:` 文档更新
- `style:` 代码格式化（不影响代码含义的更改）
- `refactor:` 代码重构
- `test:` 添加或修改测试
- `chore:` 构建过程或辅助工具的变动