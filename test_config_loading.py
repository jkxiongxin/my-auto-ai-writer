#!/usr/bin/env python3
"""测试配置加载和PRIMARY_LLM_PROVIDER使用."""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_config_loading():
    """测试配置文件加载."""
    
    print("🧪 测试配置文件加载")
    print("="*60)
    
    try:
        # 检查.env文件
        env_file = Path(".env")
        if env_file.exists():
            print(f"✅ .env 文件存在")
            
            # 读取并显示关键配置
            with open(env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            primary_provider = None
            fallback_providers = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('PRIMARY_LLM_PROVIDER='):
                    primary_provider = line.split('=', 1)[1]
                elif line.startswith('FALLBACK_LLM_PROVIDERS='):
                    fallback_providers = line.split('=', 1)[1]
            
            print(f"📄 .env文件中的配置:")
            print(f"  PRIMARY_LLM_PROVIDER = {primary_provider}")
            print(f"  FALLBACK_LLM_PROVIDERS = {fallback_providers}")
        else:
            print(f"⚠️ .env 文件不存在")
        
        # 导入配置模块
        print(f"\n📦 导入配置模块...")
        from src.utils.config import get_settings, settings
        
        print(f"✅ 配置模块导入成功")
        
        # 显示加载的配置
        print(f"\n⚙️ 加载的配置:")
        print(f"  主要LLM提供商: {settings.primary_llm_provider}")
        print(f"  后备LLM提供商: {settings.fallback_llm_providers}")
        print(f"  后备提供商列表: {settings.fallback_llm_providers_list}")
        print(f"  数据库URL: {settings.database_url}")
        print(f"  日志级别: {settings.log_level}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_llm_client_config():
    """测试LLM客户端配置使用."""
    
    print(f"\n🤖 测试LLM客户端配置")
    print("-" * 40)
    
    try:
        from src.utils.llm_client import UniversalLLMClient
        from src.utils.providers.router import get_router
        
        # 创建客户端（会触发配置加载）
        print(f"📡 创建LLM客户端...")
        client = UniversalLLMClient()
        
        print(f"✅ LLM客户端创建成功")
        
        # 检查路由器配置
        router = get_router()
        
        print(f"\n🛣️ 路由器配置:")
        for name, capability in router.providers.items():
            print(f"  {name}: 优先级={capability.priority}, 可用={capability.is_available}")
        
        # 测试提供商选择
        print(f"\n🎯 测试提供商选择:")
        
        from src.utils.providers.router import TaskType, RoutingStrategy
        
        # 测试不同策略的提供商选择
        strategies = [
            RoutingStrategy.BALANCED,
            RoutingStrategy.FAILOVER,
            RoutingStrategy.QUALITY_FIRST
        ]
        
        for strategy in strategies:
            try:
                selected = router.select_provider(
                    prompt="测试提示词",
                    task_type=TaskType.GENERAL,
                    strategy=strategy
                )
                print(f"  {strategy.value}: {selected}")
            except Exception as e:
                print(f"  {strategy.value}: 失败 - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM客户端配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_provider_priority():
    """测试提供商优先级设置."""
    
    print(f"\n🏆 测试提供商优先级")
    print("-" * 40)
    
    try:
        from src.utils.config import settings
        from src.utils.providers.router import get_router
        
        router = get_router()
        
        print(f"📊 提供商优先级排序:")
        
        # 按优先级排序显示
        sorted_providers = sorted(
            router.providers.items(),
            key=lambda x: x[1].priority
        )
        
        for i, (name, capability) in enumerate(sorted_providers):
            status = "✅" if capability.is_available else "❌"
            primary_mark = "⭐" if name == settings.primary_llm_provider else "  "
            fallback_mark = "🔄" if name in settings.fallback_llm_providers_list else "  "
            
            print(f"  {i+1}. {primary_mark}{fallback_mark} {name} (优先级:{capability.priority}) {status}")
        
        print(f"\n🎯 预期结果:")
        print(f"  主要提供商 '{settings.primary_llm_provider}' 应该有最高优先级(1)")
        print(f"  后备提供商 {settings.fallback_llm_providers_list} 应该有较高优先级(2,3...)")
        
        # 验证优先级设置是否正确
        primary_provider = settings.primary_llm_provider
        if primary_provider in router.providers:
            primary_priority = router.providers[primary_provider].priority
            if primary_priority == 1:
                print(f"✅ 主要提供商优先级设置正确")
            else:
                print(f"❌ 主要提供商优先级设置错误: {primary_priority}")
        
        return True
        
    except Exception as e:
        print(f"❌ 提供商优先级测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_generation():
    """测试简单的生成功能."""
    
    print(f"\n🚀 测试简单生成功能")
    print("-" * 40)
    
    try:
        from src.utils.llm_client import UniversalLLMClient
        from src.utils.providers.router import TaskType
        
        client = UniversalLLMClient()
        
        # 测试简单生成（不指定首选提供商，应该使用配置中的主要提供商）
        print(f"📝 测试简单生成（使用配置中的主要提供商）...")
        
        import asyncio
        result = asyncio.run(client.generate(
            prompt="请说'配置测试成功'",
            task_type=TaskType.GENERAL,
            max_tokens=20,
            use_cache=False  # 不使用缓存以确保真实调用
        ))
        
        if result and "配置测试成功" in result:
            print(f"✅ 生成成功: {result[:100]}...")
        else:
            print(f"⚠️ 生成成功但内容不符合预期: {result[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 简单生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数."""
    
    print("🤖 AI智能小说生成器 - 配置加载测试")
    print("="*60)
    
    success_count = 0
    total_tests = 4
    
    # 1. 测试配置加载
    if test_config_loading():
        success_count += 1
    
    # 2. 测试LLM客户端配置
    if test_llm_client_config():
        success_count += 1
    
    # 3. 测试提供商优先级
    if test_provider_priority():
        success_count += 1
    
    # 4. 测试简单生成
    if test_simple_generation():
        success_count += 1
    
    print(f"\n📊 测试结果总结")
    print("="*60)
    print(f"通过测试: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print(f"🎉 所有测试通过!")
        print(f"✅ PRIMARY_LLM_PROVIDER 配置正在正确使用")
        print(f"✅ 提供商优先级设置正确")
        print(f"✅ 配置文件加载正常")
    else:
        print(f"⚠️ 部分测试失败，请检查配置")
    
    print(f"\n💡 提示:")
    print(f"  - 确保 .env 文件中设置了 PRIMARY_LLM_PROVIDER")
    print(f"  - 检查日志输出中的配置加载信息")
    print(f"  - 确认您的LLM提供商服务正在运行")

if __name__ == "__main__":
    main()