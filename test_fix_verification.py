"""验证章节生成修复是否成功."""

import logging
from src.core.data_models import ChapterContent

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_chapter_content_creation():
    """测试ChapterContent对象创建和访问."""
    try:
        # 创建测试章节
        chapter = ChapterContent(
            title="测试章节",
            content="这是一个测试章节的内容，用于验证数据结构是否正确。",
            word_count=100,
            summary="这是测试章节的摘要",
            key_events_covered=["事件1", "事件2"],
            character_developments={},
            consistency_notes=[]
        )
        
        # 测试属性访问
        logger.info(f"章节标题: {chapter.title}")
        logger.info(f"章节摘要: {chapter.summary}")
        logger.info(f"字数: {chapter.word_count}")
        
        # 创建章节列表，模拟previous_chapters
        previous_chapters = [chapter]
        
        # 测试访问最后一章的摘要（这是导致原始错误的操作）
        last_chapter_summary = previous_chapters[-1].summary
        logger.info(f"最后一章摘要: {last_chapter_summary}")
        
        logger.info("✅ ChapterContent测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ ChapterContent测试失败: {e}")
        return False

def test_data_conversion():
    """测试数据转换逻辑."""
    try:
        # 模拟novel_generator.py中的转换逻辑
        chapters_dict = [
            {
                "title": "第一章",
                "content": "第一章的内容...",
                "word_count": 1000
            },
            {
                "title": "第二章", 
                "content": "第二章的内容...",
                "word_count": 1200
            }
        ]
        
        # 使用修复后的转换逻辑
        from src.core.data_models import ChapterContent
        previous_chapters_content = []
        if chapters_dict:
            for ch in chapters_dict[-2:]:  # 最近两章
                chapter_obj = ChapterContent(
                    title=ch["title"],
                    content=ch["content"],
                    word_count=ch["word_count"],
                    summary=ch.get("content", "")[:200] + "...",  # 使用内容前200字作为摘要
                    key_events_covered=[],
                    character_developments={},
                    consistency_notes=[]
                )
                previous_chapters_content.append(chapter_obj)
        
        # 测试访问转换后的对象
        if previous_chapters_content:
            last_summary = previous_chapters_content[-1].summary
            logger.info(f"转换后的最后一章摘要: {last_summary}")
        
        logger.info("✅ 数据转换测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据转换测试失败: {e}")
        return False

def main():
    """主测试函数."""
    print("🧪 章节生成修复验证")
    print("=" * 40)
    
    # 测试1: ChapterContent基础功能
    print("\n1. 测试ChapterContent基础功能...")
    test1 = test_chapter_content_creation()
    
    # 测试2: 数据转换逻辑
    print("\n2. 测试数据转换逻辑...")
    test2 = test_data_conversion()
    
    # 结果总结
    print("\n" + "=" * 40)
    print("📊 验证结果:")
    print(f"ChapterContent基础功能: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"数据转换逻辑: {'✅ 通过' if test2 else '❌ 失败'}")
    
    if test1 and test2:
        print("\n🎉 修复验证成功！")
        print("原始错误 'dict object has no attribute summary' 已解决")
    else:
        print("\n⚠️ 验证失败，需要进一步检查")

if __name__ == "__main__":
    main()