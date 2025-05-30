#!/usr/bin/env python3
"""测试同步小说生成功能."""

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_sync_generation():
    """测试同步小说生成."""
    
    print("🧪 测试同步小说生成功能")
    print("="*60)
    
    try:
        # 导入相关模块
        from src.core.sync_novel_generator import SyncNovelGenerator
        from src.utils.llm_client import UniversalLLMClient
        
        print("✅ 模块导入成功")
        
        # 创建LLM客户端
        print("\n📡 创建LLM客户端...")
        llm_client = UniversalLLMClient()
        
        # 创建同步生成器
        print("🔧 创建同步生成器...")
        generator = SyncNovelGenerator(llm_client)
        
        # 设置进度回调
        def progress_callback(step: str, progress: float):
            print(f"📊 进度更新: {step} - {progress:.1f}%")
        
        generator.set_progress_callback(progress_callback)
        
        # 测试参数
        test_input = "一个关于人工智能觉醒的科幻故事"
        target_words = 1000
        style_preference = "科幻"
        
        print(f"\n📚 开始生成测试小说...")
        print(f"💭 创意: {test_input}")
        print(f"🎯 目标字数: {target_words}")
        print(f"🎨 风格: {style_preference}")
        print("-" * 60)
        
        start_time = time.time()
        
        # 执行同步生成
        result = generator.generate_novel(
            user_input=test_input,
            target_words=target_words,
            style_preference=style_preference
        )
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        print("-" * 60)
        print(f"🎉 生成完成! 耗时: {generation_time:.2f}秒")
        
        # 显示结果统计
        if result:
            print(f"\n📊 生成结果统计:")
            print(f"  总字数: {result.get('total_words', 0)}")
            print(f"  章节数: {len(result.get('chapters', []))}")
            print(f"  角色数: {len(result.get('characters', {}))}")
            
            # 显示概念信息
            concept = result.get('concept')
            if concept:
                print(f"\n💡 概念信息:")
                print(f"  主题: {concept.theme}")
                print(f"  核心冲突: {concept.core_conflict}")
            
            # 显示章节信息
            chapters = result.get('chapters', [])
            if chapters:
                print(f"\n📖 章节信息:")
                for i, chapter in enumerate(chapters[:3]):  # 只显示前3章
                    title = chapter.get('title', f'第{i+1}章')
                    word_count = chapter.get('word_count', 0)
                    print(f"  {i+1}. {title} ({word_count}字)")
                    
                    # 显示部分内容
                    content = chapter.get('content', '')
                    if content:
                        preview = content[:100] + '...' if len(content) > 100 else content
                        print(f"     预览: {preview}")
                
                if len(chapters) > 3:
                    print(f"  ... 还有 {len(chapters) - 3} 章")
            
            # 显示质量评估
            quality = result.get('quality_assessment', {})
            if quality:
                overall_scores = quality.get('overall_scores', {})
                overall_score = overall_scores.get('overall', 0)
                print(f"\n⭐ 质量评估: {overall_score:.1f}/10")
            
            print(f"\n✅ 同步生成测试成功!")
            return True
        else:
            print(f"\n❌ 生成结果为空")
            return False
            
    except Exception as e:
        print(f"\n❌ 同步生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sync_wrapper():
    """测试同步包装器功能."""
    
    print("\n🔧 测试同步包装器...")
    
    try:
        from src.core.sync_wrapper import sync_llm_call, SyncLLMClient
        from src.utils.llm_client import UniversalLLMClient
        
        # 创建异步客户端
        async_client = UniversalLLMClient()
        
        # 测试同步包装器
        print("📡 测试同步LLM调用...")
        
        # 简单测试生成
        result = sync_llm_call(
            async_client.generate,
            prompt="请说'测试成功'",
            max_tokens=10
        )
        
        print(f"✅ 同步调用成功: {result[:50]}...")
        
        # 测试同步客户端包装器
        print("🔄 测试同步客户端包装器...")
        sync_client = SyncLLMClient(async_client)
        
        result2 = sync_client.generate(
            prompt="请说'包装器测试成功'",
            max_tokens=10
        )
        
        print(f"✅ 同步客户端测试成功: {result2[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 同步包装器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数."""
    
    print("🤖 AI智能小说生成器 - 同步执行测试")
    print("="*60)
    
    # 测试同步包装器
    wrapper_success = test_sync_wrapper()
    
    if wrapper_success:
        # 测试同步生成
        generation_success = test_sync_generation()
        
        if generation_success:
            print(f"\n🎉 所有同步测试通过!")
            print(f"📝 说明: 所有LLM调用现在都是单线程阻塞串型执行")
        else:
            print(f"\n⚠️ 同步包装器正常，但生成功能有问题")
    else:
        print(f"\n❌ 同步包装器测试失败")
    
    print(f"\n📖 技术说明:")
    print(f"  • 使用 ThreadPoolExecutor 避免阻塞事件循环")
    print(f"  • 每个LLM调用都在独立线程中串型执行") 
    print(f"  • 避免并发调用可能导致的问题")
    print(f"  • 保持API响应性的同时确保生成的可靠性")

if __name__ == "__main__":
    main()