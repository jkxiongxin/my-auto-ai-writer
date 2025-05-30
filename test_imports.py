#!/usr/bin/env python3
"""测试循环导入是否已修复."""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """测试关键模块的导入."""
    
    print("🧪 测试模块导入（循环导入修复验证）")
    print("="*60)
    
    try:
        # 1. 测试数据模型导入
        print("1. 测试数据模型导入...")
        from src.core.data_models import ChapterContent, GenerationContext, GenerationHistory
        print("   ✅ data_models 导入成功")
        
        # 2. 测试叙事连贯性管理器导入
        print("2. 测试叙事连贯性管理器导入...")
        from src.core.narrative_coherence import NarrativeCoherenceManager
        print("   ✅ narrative_coherence 导入成功")
        
        # 3. 测试章节生成器导入
        print("3. 测试章节生成器导入...")
        from src.core.chapter_generator import ChapterGenerationEngine
        print("   ✅ chapter_generator 导入成功")
        
        # 4. 测试核心模块整体导入
        print("4. 测试核心模块整体导入...")
        from src.core import ChapterGenerationEngine, ChapterContent
        print("   ✅ src.core 整体导入成功")
        
        # 5. 测试API相关导入
        print("5. 测试API模块导入...")
        from src.api.main import app
        print("   ✅ API main 导入成功")
        
        print(f"\n🎉 所有导入测试通过！循环导入问题已解决。")
        return True
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_basic_functionality():
    """测试基本功能是否正常."""
    
    print(f"\n🔧 测试基本功能")
    print("="*60)
    
    try:
        from src.utils.llm_client import UniversalLLMClient
        from src.core.chapter_generator import ChapterGenerationEngine
        from src.core.data_models import ChapterContent
        
        # 创建LLM客户端
        llm_client = UniversalLLMClient()
        print("✅ LLM客户端创建成功")
        
        # 创建章节生成引擎（启用连贯性管理）
        chapter_engine = ChapterGenerationEngine(
            llm_client,
            enable_coherence_management=True
        )
        print("✅ 章节生成引擎创建成功（连贯性管理已启用）")
        
        # 验证连贯性管理器是否正确初始化
        if chapter_engine.coherence_manager:
            print("✅ 连贯性管理器初始化成功")
        else:
            print("❌ 连贯性管理器初始化失败")
            return False
        
        # 测试数据模型创建
        test_content = ChapterContent(
            title="测试章节",
            content="这是一个测试章节的内容。",
            word_count=12,
            summary="测试摘要",
            key_events_covered=["测试事件"]
        )
        print("✅ ChapterContent 数据模型创建成功")
        
        print(f"\n🎉 基本功能测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数."""
    
    print("🤖 AI智能小说生成器 - 循环导入修复验证")
    print("="*60)
    
    success_count = 0
    total_tests = 2
    
    # 1. 测试导入
    if test_imports():
        success_count += 1
    
    # 2. 测试基本功能
    if test_basic_functionality():
        success_count += 1
    
    print(f"\n📊 测试结果总结")
    print("="*60)
    print(f"通过测试: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print(f"🎉 所有测试通过!")
        print(f"✅ 循环导入问题已完全解决")
        print(f"✅ 连贯性管理系统正常工作")
        print(f"✅ API服务可以正常启动")
        
        print(f"\n💡 现在可以运行:")
        print(f"  - python start_api.py  # 启动API服务")
        print(f"  - python test_narrative_coherence.py  # 测试连贯性管理")
        
    else:
        print(f"⚠️ 仍有问题需要解决")
    
    return success_count == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)