"""测试模块."""

# 测试配置
TEST_CONFIG = {
    "database_url": "sqlite:///./test_ai_novel_generator.db",
    "mock_llm_responses": True,
    "skip_slow_tests": True,
    "test_data_dir": "tests/data",
    "fixtures_dir": "tests/fixtures",
}

# 测试标记说明
TEST_MARKERS = {
    "unit": "单元测试 - 快速执行的单元测试",
    "integration": "集成测试 - 测试模块间集成",
    "performance": "性能测试 - 测试系统性能",
    "validation": "验证测试 - 端到端功能验证",
    "slow": "慢速测试 - 执行时间较长的测试",
    "api": "API测试 - 测试REST API端点",
    "llm": "LLM测试 - 需要LLM提供商的测试",
    "database": "数据库测试 - 涉及数据库操作的测试",
}