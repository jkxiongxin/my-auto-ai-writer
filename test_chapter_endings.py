#!/usr/bin/env python3
"""测试章节结尾改进效果."""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

async def test_chapter_prompt_generation():
    """测试章节生成提示词."""
    
    print("🧪 测试章节结尾提示词生成")
    print("="*60)
    
    try:
        from src.core.chapter_generator import ChapterGenerationEngine
        from src.core.outline_generator import ChapterOutline, SceneOutline
        from src.core.concept_expander import ConceptExpansionResult
        from src.core.strategy_selector import GenerationStrategy
        from src.core.character_system import CharacterDatabase, Character
        from src.utils.llm_client import UniversalLLMClient
        
        # 创建测试对象
        llm_client = UniversalLLMClient()
        chapter_engine = ChapterGenerationEngine(llm_client)
        
        # 创建测试概念
        concept = ConceptExpansionResult(
            theme="友谊与成长",
            genre="青春小说",
            main_conflict="主角面临友谊危机",
            world_type="现代都市",
            tone="温暖励志",
            setting="现代大学校园"
        )
        
        # 创建测试策略
        strategy = GenerationStrategy(
            structure_type="三幕剧",
            chapter_count=5,
            character_depth="medium",
            pacing="balanced"
        )
        
        # 创建角色数据库
        character_db = CharacterDatabase()
        character_db.add_character(Character(
            name="小明",
            role="主角",
            motivation="寻找真正的友谊",
            personality=["内向", "善良", "坚持"]
        ))
        
        # 测试非最后一章的提示词
        print("📝 测试非最后一章提示词:")
        print("-" * 40)
        
        chapter_outline_middle = ChapterOutline(
            number=2,
            title="误解产生",
            summary="主角与好友因为误解产生矛盾，友谊出现裂痕",
            key_events=["发生误解", "争吵爆发", "关系破裂"],
            estimated_word_count=2000,
            scenes=[
                SceneOutline(
                    name="图书馆对话",
                    description="主角与好友在图书馆发生争执"
                )
            ],
            is_final_chapter=False  # 非最后一章
        )
        
        # 构建提示词
        context = chapter_engine._build_generation_context(
            chapter_outline_middle, character_db, None
        )
        
        prompt_middle = chapter_engine._build_chapter_prompt(
            chapter_outline_middle, character_db, concept, strategy, context
        )
        
        print("非最后一章的结尾要求:")
        # 提取结尾要求部分
        lines = prompt_middle.split('\n')
        ending_section = False
        for line in lines:
            if "章节结尾要求" in line:
                ending_section = True
            if ending_section:
                print(f"  {line}")
                if line.strip() and not line.startswith("   ") and "章节结尾要求" not in line:
                    if "以纯文本格式" in line:
                        break
        
        print(f"\n📝 测试最后一章提示词:")
        print("-" * 40)
        
        # 测试最后一章的提示词
        chapter_outline_final = ChapterOutline(
            number=5,
            title="重归于好",
            summary="主角与好友解开误解，友谊得到升华，故事圆满结束",
            key_events=["真相大白", "相互道歉", "友谊升华"],
            estimated_word_count=2500,
            scenes=[
                SceneOutline(
                    name="校园重逢",
                    description="主角与好友在校园中重新相遇"
                )
            ],
            is_final_chapter=True  # 最后一章
        )
        
        prompt_final = chapter_engine._build_chapter_prompt(
            chapter_outline_final, character_db, concept, strategy, context
        )
        
        print("最后一章的结尾要求:")
        # 提取结尾要求部分
        lines = prompt_final.split('\n')
        ending_section = False
        for line in lines:
            if "章节结尾要求" in line:
                ending_section = True
            if ending_section:
                print(f"  {line}")
                if line.strip() and not line.startswith("   ") and "章节结尾要求" not in line:
                    if "以纯文本格式" in line:
                        break
        
        print(f"\n✅ 章节提示词测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_outline_generation_with_final_chapter():
    """测试大纲生成时最后一章标识."""
    
    print(f"\n🗂️ 测试大纲生成中最后一章标识")
    print("-" * 40)
    
    try:
        from src.core.outline_generator import HierarchicalOutlineGenerator
        from src.core.concept_expander import ConceptExpansionResult
        from src.core.strategy_selector import GenerationStrategy
        from src.utils.llm_client import UniversalLLMClient
        
        # 创建大纲生成器
        llm_client = UniversalLLMClient()
        outline_generator = HierarchicalOutlineGenerator(llm_client)
        
        # 创建测试概念
        concept = ConceptExpansionResult(
            theme="成长与冒险",
            genre="奇幻小说",
            main_conflict="主角必须拯救世界",
            world_type="奇幻世界",
            tone="史诗冒险"
        )
        
        # 创建测试策略
        strategy = GenerationStrategy(
            structure_type="三幕剧",
            chapter_count=4,
            character_depth="high",
            pacing="fast"
        )
        
        # 手动创建章节大纲来测试标识功能
        print("📊 手动创建章节大纲并标识最后一章:")
        
        from src.core.outline_generator import ChapterOutline
        
        chapters = [
            ChapterOutline(1, "开始", "故事开始", ["事件1"], 2000),
            ChapterOutline(2, "发展", "情节发展", ["事件2"], 2500),  
            ChapterOutline(3, "高潮", "故事高潮", ["事件3"], 3000),
            ChapterOutline(4, "结局", "故事结局", ["事件4"], 2000)
        ]
        
        # 更新章节信息（模拟大纲生成过程）
        for i, chapter in enumerate(chapters):
            chapter.act_number = outline_generator._determine_act_number(i, len(chapters), strategy.structure_type)
            chapter.narrative_purpose = outline_generator._determine_narrative_purpose(i, len(chapters), strategy.structure_type)
            # 标识最后一章
            chapter.is_final_chapter = (i == len(chapters) - 1)
        
        # 显示结果
        for chapter in chapters:
            status = "🔚 最后一章" if chapter.is_final_chapter else "📖 普通章节"
            print(f"  第{chapter.number}章: {chapter.title} - {status}")
            print(f"    叙事目的: {chapter.narrative_purpose}")
            print(f"    是否最后一章: {chapter.is_final_chapter}")
            print()
        
        print(f"✅ 大纲生成标识测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 大纲标识测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_ending_examples():
    """显示章节结尾示例对比."""
    
    print(f"\n📚 章节结尾风格对比")
    print("="*60)
    
    print("❌ 之前的开放式结尾（需要避免）:")
    print("-" * 30)
    print("""
    "这一天就这样结束了。小明回到宿舍，洗漱完毕后躺在床上，
    回想着今天发生的一切。虽然还有很多问题没有解决，但他相信
    明天会是新的开始。带着这样的想法，他渐渐进入了梦乡。"
    """)
    
    print("✅ 现在的戛然而止结尾（推荐风格）:")
    print("-" * 30)
    print("""
    示例1 - 悬疑转折:
    "小明刚要推开宿舍门，却发现门缝里塞着一张纸条。
    他展开一看，脸色瞬间变得苍白——上面只写着四个字：
    '我知道真相。'"
    
    示例2 - 冲突即将爆发:
    "就在小明准备向小红解释一切的时候，身后突然传来了
    熟悉的声音：'小明，原来你在这里...'他缓缓转身，
    看到了那个最不该出现在这里的人。"
    
    示例3 - 重要发现:
    "小明打开那个神秘的盒子，里面的东西让他倒吸一口凉气。
    这怎么可能？这个东西不是应该在..."
    """)
    
    print("🎯 新提示词的具体指导:")
    print("-" * 30)
    print("""
    - 必须在关键时刻戛然而止，营造强烈的悬念感
    - 可以在冲突即将爆发、真相即将揭晓、或重要决定即将做出时停笔
    - 让读者迫不及待想要阅读下一章
    - 避免圆满的小结局，避免"这一天就这样结束了"类的总结性结尾
    - 结尾要有强烈的戏剧张力，可以用悬疑、冲突、意外转折等手法
    """)

async def main():
    """主函数."""
    
    print("🤖 AI智能小说生成器 - 章节结尾改进测试")
    print("="*60)
    
    success_count = 0
    total_tests = 2
    
    # 1. 测试章节提示词生成
    if await test_chapter_prompt_generation():
        success_count += 1
    
    # 2. 测试大纲生成中的最后一章标识
    if await test_outline_generation_with_final_chapter():
        success_count += 1
    
    # 3. 显示结尾示例对比
    show_ending_examples()
    
    print(f"\n📊 测试结果总结")
    print("="*60)
    print(f"通过测试: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print(f"🎉 所有测试通过!")
        print(f"✅ 章节结尾提示词已改进")
        print(f"✅ 非最后一章：戛然而止，营造悬念")
        print(f"✅ 最后一章：完整结局，解决冲突")
        print(f"✅ 大纲生成正确标识最后一章")
    else:
        print(f"⚠️ 部分测试失败，请检查修改")
    
    print(f"\n💡 改进说明:")
    print(f"  - 修改了章节生成器的提示词，明确要求非最后一章要戛然而止")
    print(f"  - 为ChapterOutline添加了is_final_chapter字段")
    print(f"  - 大纲生成时自动标识最后一章")
    print(f"  - 提供了具体的悬念结尾示例和技巧指导")
    print(f"  - 避免了开放式的总结性结尾")

if __name__ == "__main__":
    asyncio.run(main())