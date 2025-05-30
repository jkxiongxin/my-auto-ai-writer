#!/usr/bin/env python3
"""设置和测试自定义大模型接口的脚本."""

import os
import sys
import asyncio
from pathlib import Path
import json

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def create_custom_env_file():
    """创建自定义模型的环境配置文件."""
    
    print("🔧 配置自定义大模型接口")
    print("="*60)
    
    # 获取用户输入
    print("\n请输入您的自定义模型配置信息:")
    
    base_url = input("📡 模型API地址 (如: http://localhost:8080/v1): ").strip()
    if not base_url:
        print("❌ API地址不能为空")
        return False
    
    api_key = input("🔑 API密钥 (可选，如无需认证请直接回车): ").strip()
    model_name = input("🤖 模型名称 (如: llama2-7b-chat): ").strip()
    if not model_name:
        model_name = "custom-model"
    
    api_format = input("📋 API格式 (openai/custom，默认openai): ").strip().lower()
    if api_format not in ["openai", "custom"]:
        api_format = "openai"
    
    timeout = input("⏱️ 请求超时时间/秒 (默认300): ").strip()
    try:
        timeout = int(timeout) if timeout else 300
    except ValueError:
        timeout = 300
    
    # 创建.env文件内容
    env_content = f"""# AI智能小说生成器配置
# 自定义大模型配置

# =============================================================================
# 基本配置
# =============================================================================
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
LOG_FORMAT=json

# =============================================================================
# API服务配置
# =============================================================================
HOST=0.0.0.0
PORT=8000
API_RELOAD=true

# =============================================================================
# 数据库配置
# =============================================================================
DATABASE_URL=sqlite+aiosqlite:///./ai_novel_generator.db

# =============================================================================
# LLM提供商配置 ⭐ 重点配置
# =============================================================================
PRIMARY_LLM_PROVIDER=custom
FALLBACK_LLM_PROVIDERS=ollama

# =============================================================================
# 自定义模型配置 ⭐ 您的配置
# =============================================================================
CUSTOM_MODEL_BASE_URL={base_url}
CUSTOM_MODEL_API_KEY={api_key if api_key else "none"}
CUSTOM_MODEL_NAME={model_name}
CUSTOM_MODEL_TIMEOUT={timeout}
CUSTOM_MODEL_API_FORMAT={api_format}
CUSTOM_MODEL_AUTH_TYPE=bearer
CUSTOM_MODEL_MAX_TOKENS=4000
CUSTOM_MODEL_TEMPERATURE=0.7

# =============================================================================
# Ollama配置 (后备选项)
# =============================================================================
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2:7b-chat
OLLAMA_TIMEOUT=300

# =============================================================================
# 性能配置
# =============================================================================
MAX_CONCURRENT_GENERATIONS=2
GENERATION_TIMEOUT=3600
CHAPTER_GENERATION_TIMEOUT=600

# =============================================================================
# CORS配置
# =============================================================================
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=*

# =============================================================================
# 缓存配置
# =============================================================================
CACHE_ENABLED=true
REQUEST_CACHE_TTL=1800

# =============================================================================
# 日志配置
# =============================================================================
LOG_FILE=logs/ai_novel_generator.log
"""
    
    # 写入.env文件
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        print(f"\n✅ 配置文件已保存到 .env")
        print(f"📡 API地址: {base_url}")
        print(f"🤖 模型名称: {model_name}")
        print(f"📋 API格式: {api_format}")
        print(f"⏱️ 超时时间: {timeout}秒")
        return True
    except Exception as e:
        print(f"❌ 保存配置文件失败: {e}")
        return False

async def test_custom_model():
    """测试自定义模型连接."""
    
    print("\n🧪 测试自定义模型连接...")
    print("-" * 40)
    
    try:
        # 导入相关模块
        from src.utils.llm_client import UniversalLLMClient
        from src.utils.providers.router import TaskType
        
        # 创建客户端
        client = UniversalLLMClient()
        
        # 测试提供商健康状态
        print("1. 检查提供商状态...")
        provider_stats = await client.test_providers()
        
        for provider_name, status in provider_stats.items():
            health_icon = "✅" if status.get('healthy', False) else "❌"
            print(f"   {health_icon} {provider_name}: {status.get('error', '正常')}")
        
        # 测试简单生成
        print("\n2. 测试文本生成...")
        test_prompt = "请用一句话介绍人工智能的概念。"
        
        try:
            result = await client.generate(
                prompt=test_prompt,
                task_type=TaskType.GENERAL,
                preferred_provider="custom",
                max_tokens=100,
                temperature=0.7
            )
            
            print(f"✅ 生成成功!")
            print(f"📝 提示词: {test_prompt}")
            print(f"🤖 回复: {result[:200]}{'...' if len(result) > 200 else ''}")
            
            return True
            
        except Exception as e:
            print(f"❌ 生成测试失败: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_novel_generation():
    """测试小说生成功能."""
    
    print("\n📚 测试小说生成功能...")
    print("-" * 40)
    
    try:
        from src.core.novel_generator import NovelGenerator
        from src.utils.llm_client import UniversalLLMClient
        
        # 创建生成器
        llm_client = UniversalLLMClient()
        generator = NovelGenerator(llm_client)
        
        # 测试概念扩展
        print("1. 测试概念扩展...")
        test_input = "一个关于时间旅行的科幻故事"
        
        try:
            concept = await generator.concept_expander.expand_concept(
                user_input=test_input,
                target_words=1000,
                style_preference="科幻"
            )
            
            print(f"✅ 概念扩展成功!")
            print(f"📖 主题: {concept.theme}")
            print(f"🎯 核心冲突: {concept.core_conflict}")
            
            return True
            
        except Exception as e:
            print(f"❌ 概念扩展失败: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 小说生成测试失败: {e}")
        return False

def show_usage_guide():
    """显示使用指南."""
    
    print("\n📖 自定义模型使用指南")
    print("="*60)
    
    print("""
🎯 支持的API格式:

1. OpenAI兼容格式 (推荐):
   - 适用于大多数开源模型 (如 vLLM, FastChat, Ollama等)
   - 请求格式: POST /v1/chat/completions
   - 响应格式: OpenAI标准格式

2. 自定义格式:
   - 适用于特殊API接口
   - 可配置请求和响应格式

🔧 常见模型部署工具配置:

1. vLLM:
   python -m vllm.entrypoints.openai.api_server \\
     --model your-model-path \\
     --host 0.0.0.0 \\
     --port 8080

2. FastChat:
   python -m fastchat.serve.openai_api_server \\
     --host 0.0.0.0 \\
     --port 8080

3. Ollama:
   ollama serve
   # 默认端口: 11434

🚀 启动步骤:

1. 配置环境变量: python setup_custom_model.py
2. 测试连接: python test_logging.py  
3. 启动服务: python start_api.py
4. 访问界面: http://localhost:8000/app

💡 故障排除:

- 连接超时: 检查网络和防火墙设置
- 认证失败: 确认API密钥正确
- 格式错误: 检查API格式配置
- 生成失败: 查看日志文件排查具体错误

📁 相关文件:
- .env: 环境配置
- logs/ai_novel_generator.log: 运行日志
- .env.custom_model_example: 配置示例
""")

def main():
    """主函数."""
    
    print("🤖 AI智能小说生成器 - 自定义模型配置工具")
    print("="*60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--guide":
        show_usage_guide()
        return
    
    # 1. 配置环境文件
    if not create_custom_env_file():
        return
    
    # 2. 测试连接
    print(f"\n🔍 开始测试配置...")
    
    try:
        # 测试自定义模型
        success = asyncio.run(test_custom_model())
        
        if success:
            print(f"\n🎉 自定义模型配置成功!")
            
            # 测试概念扩展
            concept_success = asyncio.run(test_novel_generation())
            
            if concept_success:
                print(f"\n✅ 所有测试通过! 您可以开始使用AI小说生成器了。")
                print(f"\n🚀 启动命令: python start_api.py")
                print(f"🌐 访问地址: http://localhost:8000/app")
            else:
                print(f"\n⚠️ 基础连接正常，但小说生成功能可能需要调试")
        else:
            print(f"\n❌ 配置有问题，请检查您的API设置")
            
    except KeyboardInterrupt:
        print(f"\n👋 配置已中断")
    except Exception as e:
        print(f"\n❌ 配置过程中发生错误: {e}")

if __name__ == "__main__":
    main()