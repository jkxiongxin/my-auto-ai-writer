"""综合测试：验证章节生成和连贯性分析修复."""

import asyncio
import logging
from src.core.novel_generator import NovelGenerator
from src.utils.llm_client import UniversalLLMClient

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_chapter_generation_with_coherence():
    """测试带连贯性分析的章节生成."""
    try:
        # 创建LLM客户端和生成器
        llm_client = UniversalLLMClient()
        generator = NovelGenerator(llm_client)
        
        # 测试参数
        user_input = "一个关于程序员调试bug却发现AI觉醒的故事"
        target_words = 2000  # 较小的字数以快速测试
        
        logger.info("开始测试带连贯性分析的章节生成...")
        
        # 生成小说（只生成前两章）
        result = await generator.generate_novel(
            user_input=user_input,
            target_words=target_words,
            style_preference="科幻",
            use_progressive_outline=True
        )
        
        logger.info("✅ 章节生成测试成功！")
        logger.info(f"总字数: {result.get('total_words', 0)}")
        logger.info(f"章节数: {len(result.get('chapters', []))}")
        
        # 验证章节数据结构
        chapters = result.get('chapters', [])
        for i, chapter in enumerate(chapters):
            logger.info(f"第{i+1}章: {chapter['title']} ({chapter['word_count']}字)")
            
            # 验证一致性检查结果
            consistency = chapter.get('consistency_check', {})
            logger.info(f"  一致性评分: {consistency.get('overall_score', 'N/A')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 章节生成测试失败: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

async def test_coherence_manager_standalone():
    """独立测试连贯性管理器."""
    try:
        from src.core.narrative_coherence import NarrativeCoherenceManager
        from src.core.data_models import ChapterContent
        from src.core.character_system import CharacterDatabase, Character
        from src.core.outline_generator import ChapterOutline
        from src.core.concept_expander import ConceptExpansionResult
        
        logger.info("测试连贯性管理器...")
        
        # 创建测试数据
        llm_client = UniversalLLMClient()
        coherence_manager = NarrativeCoherenceManager(llm_client)
        
        # 创建测试章节
        test_chapter = ChapterContent(
            title="测试章节",
            content="这是一个测试章节的内容。角色张三在办公室里调试代码。",
            word_count=50,
            summary="测试章节摘要",
            key_events_covered=["调试代码"],
            character_developments={},
            consistency_notes=[]
        )
        
        # 创建测试角色数据库
        character_db = CharacterDatabase()
        test_character = Character(
            name="张三",
            role="程序员",
            age=30,
            personality=["认真", "专注"],
            background="资深程序员，有10年开发经验",
            goals=["解决技术难题", "提升编程技能"],
            skills=["Python", "调试", "算法"],
            appearance="中等身材，戴眼镜",
            motivation="解决技术问题"
        )
        character_db.add_character(test_character)
        
        # 创建测试概念
        concept = ConceptExpansionResult(
            theme="技术与人性",
            genre="科幻",
            main_conflict="程序员与AI觉醒的冲突",
            world_type="现代都市",
            tone="严肃"
        )
        
        # 创建测试章节大纲
        chapter_outline = ChapterOutline(
            number=2,
            title="深入调试",
            summary="继续调试过程",
            key_events=["发现异常"],
            estimated_word_count=1000
        )
        
        # 测试连贯性分析
        logger.info("测试连贯性分析...")
        analysis = await coherence_manager.analyze_coherence(
            test_chapter, [test_chapter], character_db
        )
        
        logger.info(f"连贯性评分: {analysis.coherence_score}")
        logger.info(f"发现的问题: {len(analysis.issues_found)}")
        
        # 测试上下文准备
        logger.info("测试上下文准备...")
        context = await coherence_manager.prepare_chapter_context(
            chapter_outline, character_db, concept, [test_chapter]
        )
        
        logger.info(f"上下文要素数量: {len(context)}")
        
        logger.info("✅ 连贯性管理器测试成功！")
        return True
        
    except Exception as e:
        logger.error(f"❌ 连贯性管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数."""
    print("🧪 综合修复验证测试")
    print("=" * 50)
    
    # 测试1: 独立连贯性管理器
    print("\n1. 测试独立连贯性管理器...")
    coherence_test = await test_coherence_manager_standalone()
    
    # 测试2: 完整章节生成（如果连贯性测试通过）
    if coherence_test:
        print("\n2. 测试完整章节生成流程...")
        generation_test = await test_chapter_generation_with_coherence()
    else:
        print("\n2. ⏭️  跳过完整生成测试（连贯性测试失败）")
        generation_test = False
    
    # 结果总结
    print("\n" + "=" * 50)
    print("📊 综合测试结果:")
    print(f"连贯性管理器: {'✅ 通过' if coherence_test else '❌ 失败'}")
    print(f"完整章节生成: {'✅ 通过' if generation_test else '❌ 失败'}")
    
    if coherence_test and generation_test:
        print("\n🎉 所有修复验证成功！")
        print("✅ 原始错误 'dict object has no attribute summary' 已解决")
        print("✅ 连贯性分析相关错误已解决") 
    elif coherence_test:
        print("\n⚠️ 部分修复成功，连贯性问题已解决")
    else:
        print("\n⚠️ 仍有问题需要解决")

if __name__ == "__main__":
    asyncio.run(main())