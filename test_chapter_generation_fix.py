"""测试章节生成修复."""

import asyncio
import logging
from src.core.novel_generator import NovelGenerator
from src.utils.llm_client import UniversalLLMClient

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_simple_generation():
    """测试简单的小说生成."""
    try:
        # 创建LLM客户端和生成器
        llm_client = UniversalLLMClient()
        generator = NovelGenerator(llm_client)
        
        # 测试参数
        user_input = "一个关于程序员发现AI有自我意识的科幻故事"
        target_words = 3000
        
        logger.info("开始测试小说生成...")
        
        # 生成小说
        result = await generator.generate_novel(
            user_input=user_input,
            target_words=target_words,
            style_preference="科幻",
            use_progressive_outline=True
        )
        
        logger.info("✅ 小说生成成功！")
        logger.info(f"总字数: {result.get('total_words', 0)}")
        logger.info(f"章节数: {len(result.get('chapters', []))}")
        
        # 显示章节信息
        for i, chapter in enumerate(result.get('chapters', [])[:2]):
            logger.info(f"第{i+1}章: {chapter['title']} ({chapter['word_count']}字)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        return False

async def test_data_model_compatibility():
    """测试数据模型兼容性."""
    try:
        from src.core.data_models import ChapterContent
        from src.core.chapter_generator import ChapterGenerationEngine
        from src.utils.llm_client import UniversalLLMClient
        
        logger.info("测试ChapterContent对象创建...")
        
        # 创建测试章节对象
        chapter = ChapterContent(
            title="测试章节",
            content="这是一个测试章节的内容。",
            word_count=50,
            summary="测试章节摘要",
            key_events_covered=["测试事件"],
            character_developments={},
            consistency_notes=[]
        )
        
        logger.info(f"✅ ChapterContent对象创建成功: {chapter.title}")
        logger.info(f"摘要属性访问: {chapter.summary}")
        
        # 测试章节列表
        previous_chapters = [chapter]
        logger.info(f"✅ 章节列表创建成功，包含 {len(previous_chapters)} 个章节")
        logger.info(f"最后一章摘要: {previous_chapters[-1].summary}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据模型测试失败: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        return False

async def main():
    """主测试函数."""
    print("🧪 章节生成修复测试")
    print("=" * 50)
    
    # 测试1: 数据模型兼容性
    print("\n1. 测试数据模型兼容性...")
    model_test = await test_data_model_compatibility()
    
    if not model_test:
        print("❌ 数据模型测试失败，跳过完整生成测试")
        return
    
    # 测试2: 完整生成流程
    print("\n2. 测试完整生成流程...")
    generation_test = await test_simple_generation()
    
    # 结果总结
    print("\n" + "=" * 50)
    print("📊 测试结果:")
    print(f"数据模型兼容性: {'✅ 通过' if model_test else '❌ 失败'}")
    print(f"完整生成流程: {'✅ 通过' if generation_test else '❌ 失败'}")
    
    if model_test and generation_test:
        print("\n🎉 所有测试通过！章节生成bug已修复。")
    else:
        print("\n⚠️ 仍有测试失败，需要进一步调试。")

if __name__ == "__main__":
    asyncio.run(main())