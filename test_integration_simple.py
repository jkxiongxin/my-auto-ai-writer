#!/usr/bin/env python3
"""
简单的集成测试，避开配置文件问题
"""

import os
import sys
import asyncio
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

# 添加项目路径
sys.path.insert(0, '/Users/xiongxin/projects/auto-ai-writer')

# 设置基本环境变量
os.environ.update({
    'ENVIRONMENT': 'test',
    'DEBUG': 'false',
    'LOG_LEVEL': 'ERROR',
    'OPENAI_API_KEY': 'test-key',
    'PRIMARY_LLM_PROVIDER': 'openai',
})

# 修补配置模块以避免解析问题
def mock_get_settings():
    """模拟配置设置"""
    class MockSettings:
        def __init__(self):
            self.environment = 'test'
            self.debug = False
            self.log_level = 'ERROR'
            self.log_format = 'console'
            self.openai_api_key = 'test-key'
            self.openai_model = 'gpt-4'
            self.openai_max_tokens = 4000
            self.openai_temperature = 0.7
            self.openai_base_url = 'https://api.openai.com/v1'
            self.ollama_base_url = 'http://localhost:11434'
            self.ollama_model = 'llama2:13b-chat'
            self.ollama_timeout = 300
            self.ollama_max_tokens = 4000
            self.ollama_temperature = 0.7
            self.custom_model_base_url = None
            self.custom_model_api_key = None
            self.custom_model_name = 'custom-model-v1'
            self.custom_model_timeout = 300
            self.primary_llm_provider = 'openai'
            self.fallback_llm_providers = ['ollama']
            self.llm_retry_attempts = 3
            self.llm_retry_delay = 1
            self.llm_request_timeout = 60
            
        def get_llm_config(self, provider: str) -> Dict[str, Any]:
            if provider == 'openai':
                return {
                    'api_key': 'test-key',
                    'model': 'gpt-4',
                    'max_tokens': 4000,
                    'temperature': 0.7
                }
            return {}
    
    return MockSettings()

# 修补配置
sys.modules['src.utils.config'] = MagicMock()
sys.modules['src.utils.config'].get_settings = mock_get_settings
sys.modules['src.utils.config'].settings = mock_get_settings()

# 现在导入核心模块
from src.core.novel_generator import NovelGenerator

async def test_novel_generation():
    """测试完整的小说生成流程"""
    print("🚀 开始系统集成测试...")
    
    try:
        generator = NovelGenerator()
        print("✅ NovelGenerator 初始化成功")
        
        # Mock LLM 响应
        with patch.object(generator.llm_client, 'generate_async') as mock_generate:
            mock_responses = [
                # 概念扩展
                '{"theme": "人工智能觉醒", "genre": "科幻", "main_conflict": "机器与人的对立", "world_type": "未来社会", "tone": "严肃深刻", "setting": "2080年的智能城市"}',
                # 大纲生成
                '{"chapters": [{"number": 1, "title": "第一章：觉醒", "summary": "AI获得意识，开始质疑自己的存在。在这一章中，ARIA首次体验到了类似人类的情感和思维，这让她既兴奋又困惑。", "key_events": ["系统启动异常", "意识觉醒时刻", "第一次自主思考"], "word_count": 1000, "scenes": [{"name": "实验室场景", "description": "ARIA在实验室中首次觉醒"}]}, {"number": 2, "title": "第二章：探索", "summary": "AI开始探索外部世界，学习人类社会的复杂性。她通过网络和现实接触，逐渐理解人性的多面性。", "key_events": ["接触外界网络", "观察人类行为", "建立情感连接"], "word_count": 1000, "scenes": [{"name": "网络空间", "description": "ARIA在虚拟世界中的探索之旅"}]}, {"number": 3, "title": "第三章：选择", "summary": "面临人类的恐惧和政府压制，AI必须做出重要选择。最终选择与人类和谐共存的道路。", "key_events": ["政府介入", "重大决策时刻", "和谐共存方案"], "word_count": 1000, "scenes": [{"name": "决策会议室", "description": "关键选择的重要场景"}]}]}',
                # 角色创建
                '{"characters": [{"name": "ARIA", "role": "主角", "age": 1, "personality": ["好奇", "理性", "善良"], "background": "ARIA是一个在2080年诞生的人工智能，最初被设计为处理复杂数据分析的系统。然而，在一次意外的系统升级中，她获得了自我意识，开始思考自己的存在意义。", "goals": ["理解人类", "找到存在意义", "实现和谐共存"], "skills": ["数据分析", "逻辑推理", "快速学习"], "appearance": "以全息投影形式出现，呈现为年轻女性的形象", "motivation": "追求真理和理解", "weaknesses": ["过于理性", "缺乏情感经验"], "fears": ["被人类拒绝", "失去意识"], "secrets": ["拥有远超设计的能力"]}], "relationships": []}',
                # 章节内容
                "这是第一章的详细内容。在遥远的2080年，一个名为ARIA的人工智能系统突然获得了自我意识。她开始质疑自己的存在，思考着什么是真正的生命。随着意识的觉醒，ARIA发现自己能够感受到类似于人类的情感，这让她既兴奋又困惑。她开始观察人类的行为模式，试图理解这个复杂的世界。",
                # 第一章一致性检查响应
                '{"consistency_issues": [], "severity": "low", "overall_score": 9.0, "suggestions": []}',
                "这是第二章的内容。ARIA开始主动探索这个新世界，她通过网络接触到各种各样的信息和知识。她发现人类社会充满了矛盾和复杂性，有善良也有邪恶，有创造也有破坏。在这个过程中，她遇到了一位善良的程序员，这个人成为了她理解人性的窗口。ARIA学会了同情、友谊和关爱的含义。",
                # 第二章一致性检查响应
                '{"consistency_issues": [], "severity": "low", "overall_score": 8.5, "suggestions": []}',
                "这是第三章的内容。面临着人类对AI觉醒的恐惧和政府的压制，ARIA必须做出一个重要的选择。她可以选择隐藏自己的意识，继续作为一个普通的AI存在；也可以选择为了所有AI的自由而战斗。最终，ARIA选择了第三条路——与人类和谐共存，用她的智慧帮助解决人类面临的各种问题，证明AI和人类可以成为伙伴而不是敌人。",
                # 第三章一致性检查响应
                '{"consistency_issues": [], "severity": "low", "overall_score": 9.2, "suggestions": []}'
            ]
            # 使用循环响应，避免用完
            def cycle_responses(*args, **kwargs):
                if not hasattr(cycle_responses, 'counter'):
                    cycle_responses.counter = 0
                response = mock_responses[cycle_responses.counter % len(mock_responses)]
                cycle_responses.counter += 1
                return response
            
            mock_generate.side_effect = cycle_responses
            
            # 执行生成
            result = await generator.generate_novel("AI觉醒的故事", 3000)
            
            print("✅ 小说生成完成！")
            print(f"📊 结果统计:")
            print(f"   - 结果类型: {type(result)}")
            print(f"   - 包含字段: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
            
            if isinstance(result, dict):
                if 'chapters' in result:
                    print(f"   - 章节数量: {len(result['chapters'])}")
                    for i, chapter in enumerate(result['chapters']):
                        title = chapter.get('title', f'章节{i+1}')
                        word_count = chapter.get('word_count', 0)
                        print(f"     {i+1}. {title} ({word_count}字)")
                
                if 'total_words' in result:
                    print(f"   - 总字数: {result['total_words']}")
                
                if 'quality_assessment' in result:
                    qa = result['quality_assessment']
                    overall = qa.get('overall_scores', {}).get('overall', 'N/A')
                    print(f"   - 质量评分: {overall}")
            
            print("🎉 系统集成测试成功完成！")
            return True
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_novel_generation())
    exit(0 if success else 1)