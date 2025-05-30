"""测试JSON解析修复."""

import asyncio
import logging
from src.core.narrative_coherence import NarrativeCoherenceManager
from src.core.data_models import ChapterContent
from src.core.character_system import CharacterDatabase, Character
from src.utils.llm_client import UniversalLLMClient

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_json_parsing_resilience():
    """测试JSON解析的容错性."""
    try:
        logger.info("测试JSON解析容错性...")
        
        # 创建LLM客户端和连贯性管理器
        llm_client = UniversalLLMClient()
        coherence_manager = NarrativeCoherenceManager(llm_client)
        
        # 创建测试章节
        test_chapter = ChapterContent(
            title="测试章节",
            content="这是一个测试章节的内容。角色张三在办公室里调试代码，突然发现了异常现象。",
            word_count=50,
            summary="测试章节摘要",
            key_events_covered=["调试代码"],
            character_developments={},
            consistency_notes=[]
        )
        
        # 创建角色数据库
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
        
        # 测试连贯性分析（这可能触发JSON解析错误）
        logger.info("测试连贯性分析...")
        analysis = await coherence_manager.analyze_coherence(
            test_chapter, [test_chapter], character_db
        )
        
        logger.info(f"✅ 连贯性分析完成: 评分 {analysis.coherence_score}")
        logger.info(f"角色一致性: {analysis.character_consistency}")
        logger.info(f"情节一致性: {analysis.plot_consistency}")
        logger.info(f"发现问题: {len(analysis.issues_found)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ JSON解析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数."""
    print("🧪 JSON解析容错性测试")
    print("=" * 40)
    
    # 测试JSON解析容错性
    print("\n测试JSON解析容错性...")
    json_test = await test_json_parsing_resilience()
    
    # 结果总结
    print("\n" + "=" * 40)
    print("📊 测试结果:")
    print(f"JSON解析容错性: {'✅ 通过' if json_test else '❌ 失败'}")
    
    if json_test:
        print("\n🎉 JSON解析修复验证成功！")
        print("✅ 连贯性分析不再因JSON解析错误而中断")
    else:
        print("\n⚠️ 仍需要进一步修复")

if __name__ == "__main__":
    asyncio.run(main())