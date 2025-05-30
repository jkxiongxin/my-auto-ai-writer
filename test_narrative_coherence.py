#!/usr/bin/env python3
"""测试叙事连贯性管理器."""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

async def test_coherence_management():
    """测试连贯性管理功能."""
    
    print("🧪 测试叙事连贯性管理系统")
    print("="*60)
    
    try:
        from src.core.narrative_coherence import NarrativeCoherenceManager
        from src.core.chapter_generator import ChapterGenerationEngine
        from src.core.data_models import ChapterContent
        from src.core.outline_generator import ChapterOutline, SceneOutline
        from src.core.concept_expander import ConceptExpansionResult
        from src.core.strategy_selector import GenerationStrategy
        from src.core.character_system import CharacterDatabase, Character
        from src.utils.llm_client import UniversalLLMClient
        
        # 创建测试对象
        llm_client = UniversalLLMClient()
        coherence_manager = NarrativeCoherenceManager(llm_client)
        chapter_engine = ChapterGenerationEngine(llm_client, enable_coherence_management=True)
        
        # 创建测试概念
        concept = ConceptExpansionResult(
            theme="友谊与成长",
            genre="青春小说",
            main_conflict="主角面临友谊危机，必须学会信任",
            world_type="现代都市",
            tone="温暖励志",
            setting="现代大学校园"
        )
        
        # 创建测试策略
        strategy = GenerationStrategy(
            structure_type="三幕剧",
            chapter_count=3,
            character_depth="high",
            pacing="balanced"
        )
        
        # 创建角色数据库
        character_db = CharacterDatabase()
        
        # 添加主要角色
        protagonist = Character(
            name="李小明",
            role="主角",
            motivation="寻找真正的友谊，克服内心的恐惧",
            personality=["内向", "善良", "坚持", "有些自卑"],
            background="来自小城市的大学新生，第一次离开家",
            relationships={}
        )
        character_db.add_character(protagonist)
        
        friend = Character(
            name="张小红", 
            role="好友",
            motivation="帮助朋友成长，维护友谊",
            personality=["开朗", "热心", "直率", "有时冲动"],
            background="本地学生，社交能力强",
            relationships={"李小明": "室友兼好友"}
        )
        character_db.add_character(friend)
        
        antagonist = Character(
            name="王小强",
            role="对手",
            motivation="证明自己的优越性",
            personality=["自信", "竞争", "有些自负"],
            background="富家子弟，学习优秀",
            relationships={"李小明": "竞争对手"}
        )
        character_db.add_character(antagonist)
        
        print("📝 测试连贯性上下文准备:")
        print("-" * 40)
        
        # 创建第一章大纲
        chapter1_outline = ChapterOutline(
            number=1,
            title="初来乍到",
            summary="李小明初入大学，与室友张小红相识，但因为性格差异产生误解",
            key_events=["入学报到", "遇见室友", "产生误解", "内心困惑"],
            estimated_word_count=2000,
            scenes=[
                SceneOutline(
                    name="宿舍相遇",
                    description="李小明与张小红第一次见面",
                    location="大学宿舍",
                    characters=["李小明", "张小红"]
                )
            ],
            is_final_chapter=False
        )
        
        # 测试第一章连贯性上下文（无前置章节）
        context1 = await coherence_manager.prepare_chapter_context(
            chapter1_outline, character_db, concept, []
        )
        
        print(f"第1章连贯性上下文要素: {len(context1)} 个")
        for key, value in context1.items():
            if value:
                print(f"  - {key}: {'有内容' if value else '无内容'}")
        
        # 模拟第一章内容
        chapter1_content = ChapterContent(
            title="初来乍到",
            content="""
李小明拖着行李箱走进宿舍楼，心里既兴奋又紧张。这是他第一次离开家乡的小城市，来到这座繁华的大都市读书。

推开宿舍门，他看到一个女孩正在整理床铺。女孩听到声音转过头来，露出一个灿烂的笑容。

"你好！我是张小红，你的室友。"女孩主动伸出手。

李小明有些拘谨地握了握手："我是李小明，请多关照。"

"不用这么客气啦！"张小红爽朗地笑道，"我来帮你整理东西吧。"

李小明连忙摆手："不用不用，我自己来就好。"

张小红的笑容僵了一下，但很快恢复正常："好吧，那你慢慢收拾。"

房间里一时陷入了尴尬的沉默。李小明暗自懊恼，自己是不是太冷淡了？但他就是不知道该怎么和这样热情的人相处。

就在这时，门外传来了敲门声...
            """.strip(),
            word_count=245,
            summary="李小明入学与室友张小红相识，但因为性格差异产生了初步的误解",
            key_events_covered=["入学报到", "遇见室友", "产生误解"]
        )
        
        # 分析第一章连贯性
        print(f"\n📊 分析第1章连贯性:")
        print("-" * 40)
        
        coherence_analysis1 = await coherence_manager.analyze_coherence(
            chapter1_content, [], character_db
        )
        
        print(f"连贯性总分: {coherence_analysis1.coherence_score:.2f}")
        print(f"角色一致性: {coherence_analysis1.character_consistency:.2f}")
        print(f"情节一致性: {coherence_analysis1.plot_consistency:.2f}")
        print(f"时间线一致性: {coherence_analysis1.timeline_consistency:.2f}")
        
        if coherence_analysis1.issues_found:
            print("发现的问题:")
            for issue in coherence_analysis1.issues_found:
                print(f"  - {issue}")
        
        if coherence_analysis1.suggestions:
            print("改进建议:")
            for suggestion in coherence_analysis1.suggestions:
                print(f"  - {suggestion}")
        
        # 创建第二章大纲
        chapter2_outline = ChapterOutline(
            number=2,
            title="深入了解",
            summary="李小明和张小红通过一次意外事件加深了解，开始建立真正的友谊",
            key_events=["图书馆相遇", "共同解决问题", "友谊萌芽", "互相理解"],
            estimated_word_count=2200,
            scenes=[
                SceneOutline(
                    name="图书馆偶遇",
                    description="两人在图书馆意外相遇，一起解决问题",
                    location="大学图书馆",
                    characters=["李小明", "张小红"]
                )
            ],
            is_final_chapter=False
        )
        
        # 测试第二章连贯性上下文（有前置章节）
        print(f"\n📝 测试第2章连贯性上下文（有前置章节）:")
        print("-" * 40)
        
        context2 = await coherence_manager.prepare_chapter_context(
            chapter2_outline, character_db, concept, [chapter1_content]
        )
        
        print(f"第2章连贯性上下文要素: {len(context2)} 个")
        for key, value in context2.items():
            if value:
                print(f"  - {key}: {'有内容' if value else '无内容'}")
        
        # 显示连贯性指导内容
        if "coherence_guidelines" in context2:
            print(f"\n连贯性指导原则:")
            for guideline in context2["coherence_guidelines"][:3]:
                print(f"  - {guideline}")
        
        if "transition_info" in context2 and context2["transition_info"]:
            transition = context2["transition_info"]
            print(f"\n章节转换信息:")
            print(f"  - 时间间隔: {transition.get('time_gap', '未指定')}")
            print(f"  - 地点变化: {transition.get('location_change', False)}")
            print(f"  - 情绪转变: {transition.get('mood_shift', '未指定')}")
        
        # 测试连贯性管理器状态
        print(f"\n📈 连贯性管理器状态:")
        print("-" * 40)
        
        summary = coherence_manager.get_coherence_summary()
        print(f"已处理章节数: {summary['chapters_processed']}")
        print(f"活跃情节线索: {summary['active_plot_threads']}")
        print(f"角色状态记录: {summary['character_states']}")
        print(f"世界事实记录: {summary['world_facts']}")
        print(f"转换记录: {summary['transitions_tracked']}")
        
        print(f"\n✅ 连贯性管理测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_chapter_generation_with_coherence():
    """测试带连贯性管理的章节生成."""
    
    print(f"\n🔗 测试带连贯性管理的章节生成")
    print("="*60)
    
    try:
        from src.core.chapter_generator import ChapterGenerationEngine
        from src.core.data_models import ChapterContent
        from src.core.outline_generator import ChapterOutline, SceneOutline
        from src.core.concept_expander import ConceptExpansionResult
        from src.core.strategy_selector import GenerationStrategy
        from src.core.character_system import CharacterDatabase, Character
        from src.utils.llm_client import UniversalLLMClient
        
        # 创建测试对象
        llm_client = UniversalLLMClient()
        
        # 创建启用连贯性管理的章节生成引擎
        chapter_engine = ChapterGenerationEngine(
            llm_client,
            enable_coherence_management=True
        )
        
        print("✅ 已启用连贯性管理的章节生成引擎")
        
        # 验证连贯性管理器是否正确初始化
        if chapter_engine.coherence_manager:
            print("✅ 连贯性管理器已正确初始化")
        else:
            print("❌ 连贯性管理器初始化失败")
            return False
        
        # 模拟章节生成过程中的连贯性检查
        print("\n📝 模拟连贯性检查流程:")
        print("-" * 40)
        
        # 创建简单的测试数据
        concept = ConceptExpansionResult(
            theme="冒险与成长",
            genre="奇幻小说",
            main_conflict="主角必须拯救世界",
            world_type="魔法世界",
            tone="史诗冒险"
        )
        
        strategy = GenerationStrategy(
            structure_type="三幕剧",
            chapter_count=3,
            character_depth="medium",
            pacing="fast"
        )
        
        character_db = CharacterDatabase()
        character_db.add_character(Character(
            name="艾伦",
            role="主角",
            motivation="拯救世界，保护朋友",
            personality=["勇敢", "善良", "坚定"]
        ))
        
        chapter_outline = ChapterOutline(
            number=1,
            title="冒险开始",
            summary="艾伦接受了拯救世界的使命",
            key_events=["接受使命", "获得魔法剑", "踏上旅程"],
            estimated_word_count=1500,
            scenes=[
                SceneOutline(
                    name="村庄告别",
                    description="艾伦告别家乡踏上冒险之旅"
                )
            ],
            is_final_chapter=False
        )
        
        # 测试连贯性上下文准备
        coherence_context = await chapter_engine.coherence_manager.prepare_chapter_context(
            chapter_outline, character_db, concept, []
        )
        
        print(f"连贯性上下文准备完成: {len(coherence_context)} 个要素")
        
        # 测试连贯性指导生成
        guidance = chapter_engine._build_coherence_guidance(coherence_context)
        
        if guidance:
            print(f"生成连贯性指导: {len(guidance)} 字符")
            print(f"指导内容预览: {guidance[:100]}...")
        else:
            print("连贯性指导为空（第一章正常现象）")
        
        print(f"\n✅ 连贯性集成测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_coherence_features():
    """展示连贯性管理功能特性."""
    
    print(f"\n📚 叙事连贯性管理系统特性")
    print("="*60)
    
    print("🎯 核心功能:")
    print("  1. 角色状态追踪 - 确保角色行为一致性")
    print("  2. 情节线索管理 - 维护故事情节的连贯性")
    print("  3. 世界设定一致性 - 保持世界观的统一")
    print("  4. 章节转换分析 - 确保章节间自然衔接")
    print("  5. 连贯性评分 - 量化评估章节质量")
    
    print(f"\n🔧 技术特性:")
    print("  - 自动叙事状态更新")
    print("  - 智能转换分析")
    print("  - 多维度连贯性检查")
    print("  - 个性化指导生成")
    print("  - 历史状态管理")
    
    print(f"\n📈 质量保证:")
    print("  - 角色一致性检查")
    print("  - 情节逻辑验证")
    print("  - 时间线连贯性")
    print("  - 世界设定统一性")
    print("  - 情绪基调转换")
    
    print(f"\n🚀 使用优势:")
    print("  ✅ 显著提升章节间连贯性")
    print("  ✅ 减少角色性格不一致问题")
    print("  ✅ 自动维护情节线索")
    print("  ✅ 智能生成连贯性指导")
    print("  ✅ 支持大型长篇小说创作")

async def main():
    """主函数."""
    
    print("🤖 AI智能小说生成器 - 叙事连贯性管理测试")
    print("="*60)
    
    success_count = 0
    total_tests = 2
    
    # 1. 测试连贯性管理器核心功能
    if await test_coherence_management():
        success_count += 1
    
    # 2. 测试章节生成集成
    if await test_chapter_generation_with_coherence():
        success_count += 1
    
    # 3. 展示功能特性
    show_coherence_features()
    
    print(f"\n📊 测试结果总结")
    print("="*60)
    print(f"通过测试: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print(f"🎉 所有测试通过!")
        print(f"✅ 连贯性管理系统已成功实现")
        print(f"✅ 章节生成引擎已集成连贯性管理")
        print(f"✅ 支持多维度连贯性分析")
        print(f"✅ 自动生成连贯性指导")
    else:
        print(f"⚠️ 部分测试失败，请检查修改")
    
    print(f"\n💡 使用说明:")
    print(f"  - 创建ChapterGenerationEngine时设置enable_coherence_management=True")
    print(f"  - 系统会自动管理章节间的连贯性")
    print(f"  - 每次生成后会更新叙事状态")
    print(f"  - 为下一章提供连贯性指导")
    print(f"  - 支持连贯性评分和问题检测")

if __name__ == "__main__":
    asyncio.run(main())