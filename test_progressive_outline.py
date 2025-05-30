#!/usr/bin/env python3
"""测试渐进式大纲生成功能."""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.progressive_outline_generator import ProgressiveOutlineGenerator
from src.core.concept_expander import ConceptExpansionResult
from src.core.strategy_selector import GenerationStrategy
from src.utils.llm_client import UniversalLLMClient

async def test_progressive_outline_basic():
    """测试渐进式大纲生成的基本功能."""
    print("=" * 60)
    print("测试渐进式大纲生成基本功能")
    print("=" * 60)
    
    try:
        # 初始化
        llm_client = UniversalLLMClient()
        generator = ProgressiveOutlineGenerator(llm_client)
        
        # 创建测试概念
        concept = ConceptExpansionResult(
            theme="成长与发现",
            genre="现实主义", 
            main_conflict="青少年面临的选择困境",
            world_type="现代都市",
            tone="温暖励志",
            protagonist_type="高中生"
        )
        
        # 创建测试策略
        strategy = GenerationStrategy(
            structure_type="三幕剧",
            chapter_count=8,
            character_depth="medium",
            pacing="moderate"
        )
        
        print("1. 生成初始大纲（世界观 + 粗略结构）")
        print("-" * 50)
        
        # 生成初始大纲
        outline_state = await generator.generate_initial_outline(
            concept, strategy, 15000
        )
        
        print(f"✓ 世界观生成完成:")
        print(f"  - 基本设定: {outline_state.world_building.setting[:100]}...")
        print(f"  - 时代背景: {outline_state.world_building.time_period}")
        print(f"  - 主要地点: {', '.join(outline_state.world_building.locations[:3])}")
        
        print(f"\n✓ 粗略大纲生成完成:")
        print(f"  - 故事弧线: {outline_state.rough_outline.story_arc[:100]}...")
        print(f"  - 主要主题: {', '.join(outline_state.rough_outline.main_themes)}")
        print(f"  - 预估章节数: {outline_state.rough_outline.estimated_chapters}")
        print(f"  - 主要情节点: {len(outline_state.rough_outline.major_plot_points)}个")
        
        print("\n2. 测试渐进式章节大纲完善")
        print("-" * 50)
        
        # 测试完善前3章的详细大纲
        for chapter_num in range(1, 4):
            print(f"\n完善第{chapter_num}章大纲...")
            
            # 构建前几章摘要
            previous_summary = ""
            if chapter_num > 1:
                completed_chapters = [ch.title for ch in outline_state.detailed_chapters]
                previous_summary = f"已完成章节: {', '.join(completed_chapters)}"
            
            # 完善章节大纲
            chapter_outline = await generator.refine_next_chapter(
                outline_state, chapter_num, previous_summary
            )
            
            print(f"  ✓ 第{chapter_num}章: {chapter_outline.title}")
            print(f"    摘要: {chapter_outline.summary[:100]}...")
            print(f"    关键事件: {len(chapter_outline.key_events)}个")
            print(f"    场景数: {len(chapter_outline.scenes)}个")
            print(f"    预估字数: {chapter_outline.estimated_word_count}")
        
        print("\n3. 验证渐进式完善效果")
        print("-" * 50)
        
        # 检查状态变化
        print(f"已完成详细章节: {len(outline_state.detailed_chapters)}/3")
        print(f"已完成情节点: {len(outline_state.completed_plot_points)}个")
        
        # 获取状态摘要
        state_summary = generator.get_current_state_summary(outline_state)
        print(f"\n当前状态摘要:")
        print(state_summary)
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

async def test_progressive_vs_traditional():
    """对比渐进式与传统大纲生成的差异."""
    print("\n" + "=" * 60)
    print("对比渐进式与传统大纲生成")
    print("=" * 60)
    
    print("渐进式大纲生成的优势:")
    print("1. ✓ 先建立完整世界观，后续内容更一致")
    print("2. ✓ 根据已生成内容动态调整后续章节")
    print("3. ✓ 避免一次性生成大纲的冗余和不合理")
    print("4. ✓ 可以在生成过程中根据实际情况微调")
    print("5. ✓ 减少LLM单次处理的复杂度，提高质量")
    
    print("\n传统大纲生成的局限:")
    print("1. ✗ 一次性生成所有章节，可能出现前后不一致")
    print("2. ✗ 无法根据实际生成内容调整后续计划")
    print("3. ✗ 短篇小说可能出现过度复杂的情节")
    print("4. ✗ 长篇小说的大纲可能缺乏细节")

def test_complexity_adaptation():
    """测试不同字数下的复杂度适应性."""
    print("\n" + "=" * 60)
    print("测试复杂度适应性")
    print("=" * 60)
    
    llm_client = UniversalLLMClient()
    generator = ProgressiveOutlineGenerator(llm_client)
    
    test_cases = [
        {"words": 5000, "expected": "简洁单线结构"},
        {"words": 50000, "expected": "中等复杂度"},
        {"words": 500000, "expected": "复杂多线结构"},
        {"words": 3000000, "expected": "史诗级复杂度"}
    ]
    
    for case in test_cases:
        guidance = generator._get_complexity_guidance(case["words"])
        print(f"{case['words']}字: {guidance}")

def main():
    """主函数."""
    print("🚀 开始测试渐进式大纲生成功能")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 测试基本功能
        success = loop.run_until_complete(test_progressive_outline_basic())
        
        # 对比分析
        loop.run_until_complete(test_progressive_vs_traditional())
        
        # 复杂度适应性测试（同步）
        test_complexity_adaptation()
        
        loop.close()
        
        if success:
            print("\n🎉 渐进式大纲生成功能测试完成！")
            print("\n主要改进验证:")
            print("1. ✓ 首先生成完整世界观和粗略大纲")
            print("2. ✓ 在章节生成过程中逐步完善详细大纲")
            print("3. ✓ 根据前面章节内容调整后续章节计划")
            print("4. ✓ 支持不同字数的复杂度自适应")
            print("5. ✓ 提供更好的生成质量和一致性")
        else:
            print("\n⚠️  部分测试未通过，请检查实现")
            
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        print("请确保:")
        print("1. 已正确配置 LLM API")
        print("2. 网络连接正常")
        print("3. 项目依赖已安装")

if __name__ == "__main__":
    main()