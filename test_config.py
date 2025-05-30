#!/usr/bin/env python3
"""测试配置加载."""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.utils.config import settings
    print("✅ 配置加载成功!")
    print(f"📊 主要LLM提供商: {settings.primary_llm_provider}")
    print(f"🔄 后备LLM提供商: {settings.fallback_llm_providers}")
    print(f"🌐 数据库URL: {settings.database_url}")
    print(f"🔧 调试模式: {settings.debug}")
    print(f"📝 日志级别: {settings.log_level}")
    print(f"🎯 CORS来源: {settings.cors_origins}")
    
except Exception as e:
    print(f"❌ 配置加载失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)