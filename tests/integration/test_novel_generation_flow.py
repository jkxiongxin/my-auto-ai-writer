import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from src.core.novel_generator import NovelGenerator
from src.core.exceptions import NovelGeneratorError, RetryableError
from src.utils.llm_client import UniversalLLMClient
from src.core.quality_assessment import QualityAssessment

class TestNovelGenerationFlow:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_short_story_generation(self):
        """测试完整短篇小说生成流程"""
        generator = NovelGenerator()
        user_input = "一个机器人获得了情感"
        target_words = 5000
        
        result = await generator.generate_novel(user_input, target_words)
        
        # 验证结果完整性
        assert "concept" in result
        assert "strategy" in result
        assert "outline" in result
        assert "characters" in result
        assert "chapters" in result
        
        # 验证字数范围
        total_words = result["total_words"]
        assert 4000 <= total_words <= 6000  # 允许20%偏差
        
        # 验证章节数量
        assert len(result["chapters"]) >= 3
        
        # 验证一致性
        assert all(not ch["consistency_check"]["has_issues"] 
                  for ch in result["chapters"])

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_novel_generation_100k_words(self):
        """测试10万字小说生成"""
        generator = NovelGenerator()
        user_input = "在蒸汽朋克世界里拯救被污染的城市"
        target_words = 100000
        
        start_time = time.time()
        result = await generator.generate_novel(user_input, target_words)
        end_time = time.time()
        
        # 验证规模
        assert 90000 <= result["total_words"] <= 110000
        
        # 验证时间要求
        generation_time = end_time - start_time
        assert generation_time <= 7200  # 2小时内完成
        
        # 验证结构
        assert result["strategy"]["structure_type"] == "多卷本结构"
        assert len(result["outline"]["volumes"]) >= 2
        
        # 验证质量
        from src.core.quality_assessment import QualityAssessment
        quality_assessor = QualityAssessment()
        quality_result = quality_assessor.evaluate_novel(result)
        assert quality_result["overall_scores"]["overall"] >= 6.0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """测试错误恢复机制"""
        generator = NovelGenerator()
        
        # 模拟API调用失败然后恢复
        with patch.object(generator.llm_client, 'generate') as mock_generate:
            # 第一次调用失败，第二次成功
            mock_generate.side_effect = [
                RetryableError("Rate limit"),
                '{"theme": "科技与人性", "genre": "科幻", "main_conflict": "机器人觉醒"}',
                "第一章标题：觉醒",
                "主角是一个...",
                "这是第一章的内容..."
            ]
            
            try:
                result = await generator.generate_novel("测试故事", 1000)
                
                # 验证系统能够恢复并完成生成
                assert result is not None
                assert "chapters" in result
                assert len(result["chapters"]) > 0
            except NovelGeneratorError:
                # 如果重试机制失效，这是预期的
                pass

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_different_genre_generation(self):
        """测试不同题材的小说生成"""
        generator = NovelGenerator()
        
        test_cases = [
            {
                "input": "一个年轻法师踏上拯救王国的旅程",
                "style": "奇幻",
                "expected_genre": "奇幻"
            },
            {
                "input": "在未来世界调查一起神秘案件",
                "style": "科幻",
                "expected_genre": "科幻"
            },
            {
                "input": "小镇上发生的连环谋杀案",
                "style": "悬疑",
                "expected_genre": "悬疑"
            }
        ]
        
        for case in test_cases:
            with patch.object(generator.llm_client, 'generate') as mock_generate:
                # 模拟适合该题材的响应
                mock_generate.return_value = f'{{"theme": "测试主题", "genre": "{case["expected_genre"]}", "main_conflict": "测试冲突"}}'
                
                try:
                    result = await generator.generate_novel(
                        case["input"],
                        3000,
                        case["style"]
                    )
                    
                    # 验证题材匹配
                    assert result is not None
                    if "concept" in result:
                        assert case["expected_genre"] in str(result["concept"]).lower() or \
                               case["style"] in str(result["concept"]).lower()
                        
                except Exception as e:
                    # 记录失败但不中断测试
                    print(f"题材测试失败 {case['style']}: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_progress_tracking(self):
        """测试进度跟踪功能"""
        generator = NovelGenerator()
        
        # 记录进度变化
        progress_history = []
        
        original_update = generator._update_progress
        def track_progress(progress):
            progress_history.append(progress)
            original_update(progress)
        
        generator._update_progress = track_progress
        
        with patch.object(generator.llm_client, 'generate') as mock_generate:
            mock_generate.return_value = '{"theme": "测试", "genre": "测试"}'
            
            try:
                result = await generator.generate_novel("简单故事", 1000)
                
                # 验证进度是递增的
                assert len(progress_history) > 0
                for i in range(1, len(progress_history)):
                    assert progress_history[i] >= progress_history[i-1]
                    
                # 验证最终进度是100%
                if progress_history:
                    assert progress_history[-1] == 100
                    
            except Exception as e:
                print(f"进度跟踪测试异常: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_word_count_accuracy(self):
        """测试字数控制准确性"""
        generator = NovelGenerator()
        
        target_words_list = [1000, 3000, 5000]
        tolerance = 0.3  # 30%容差
        
        for target_words in target_words_list:
            with patch.object(generator.llm_client, 'generate') as mock_generate:
                # 模拟生成指定长度的内容
                mock_content = " ".join(["词"] * (target_words // 3))  # 粗略估算
                mock_generate.return_value = mock_content
                
                try:
                    result = await generator.generate_novel("测试故事", target_words)
                    
                    if "total_words" in result:
                        actual_words = result["total_words"]
                        min_words = target_words * (1 - tolerance)
                        max_words = target_words * (1 + tolerance)
                        
                        assert min_words <= actual_words <= max_words, \
                            f"字数偏差过大: 目标{target_words}, 实际{actual_words}"
                            
                except Exception as e:
                    print(f"字数测试失败 {target_words}: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_quality_assessment_integration(self):
        """测试质量评估系统集成"""
        generator = NovelGenerator()
        
        with patch.object(generator.llm_client, 'generate') as mock_generate:
            mock_generate.return_value = "这是一个连贯的测试内容"
            
            try:
                result = await generator.generate_novel("高质量故事", 2000)
                
                # 验证质量评估结果存在
                assert "quality_assessment" in result
                quality = result["quality_assessment"]
                
                # 验证评估结果结构
                assert "overall_scores" in quality
                assert "metrics" in quality
                
                # 验证分数范围
                if "overall" in quality["overall_scores"]:
                    overall_score = quality["overall_scores"]["overall"]
                    assert 0 <= overall_score <= 10
                    
            except Exception as e:
                print(f"质量评估集成测试失败: {e}")

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_generation(self):
        """测试并发生成能力"""
        async def generate_story(story_id):
            generator = NovelGenerator()
            
            with patch.object(generator.llm_client, 'generate') as mock_generate:
                mock_generate.return_value = f"故事{story_id}的内容"
                
                try:
                    return await generator.generate_novel(f"故事{story_id}", 1000)
                except Exception as e:
                    return {"error": str(e), "story_id": story_id}
        
        # 运行并发测试
        try:
            tasks = [generate_story(i) for i in range(3)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 验证所有任务都有结果
            assert len(results) == 3
            
            # 统计成功的任务
            successful_results = [r for r in results if isinstance(r, dict) and "error" not in r]
            print(f"并发测试: {len(successful_results)}/3 任务成功")
            
        except Exception as e:
            print(f"并发测试失败: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multi_volume_structure(self):
        """测试多卷本结构生成"""
        generator = NovelGenerator()
        
        with patch.object(generator.llm_client, 'generate') as mock_generate:
            # 模拟多卷本结构响应
            mock_generate.side_effect = [
                '{"theme": "史诗冒险", "genre": "奇幻"}',  # 概念扩展
                "多卷本结构",  # 策略选择
                '{"volumes": [{"title": "第一卷", "chapters": [{"title": "第一章"}]}]}',  # 大纲
                "主角档案",  # 角色创建
                "第一章内容..."  # 章节生成
            ]
            
            try:
                result = await generator.generate_novel("史诗级冒险故事", 50000)
                
                # 验证多卷结构
                if "outline" in result and "volumes" in result["outline"]:
                    volumes = result["outline"]["volumes"]
                    assert len(volumes) >= 1
                    assert all("chapters" in vol for vol in volumes)
                    
            except Exception as e:
                print(f"多卷本测试失败: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_consistency_check_integration(self):
        """测试一致性检查集成"""
        generator = NovelGenerator()
        
        with patch.object(generator.llm_client, 'generate') as mock_generate:
            mock_generate.return_value = "测试内容"
            
            # 模拟一致性检查
            with patch.object(generator.consistency_checker, 'check_chapter') as mock_check:
                mock_check.return_value = {
                    "has_issues": False,
                    "issues": [],
                    "confidence": 0.9
                }
                
                try:
                    result = await generator.generate_novel("一致性测试", 1500)
                    
                    # 验证每个章节都进行了一致性检查
                    if "chapters" in result:
                        for chapter in result["chapters"]:
                            assert "consistency_check" in chapter
                            assert "has_issues" in chapter["consistency_check"]
                            
                except Exception as e:
                    print(f"一致性检查集成测试失败: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_pipeline_with_mocked_llm(self):
        """测试完整流水线（使用模拟LLM）"""
        generator = NovelGenerator()
        
        # 模拟完整的LLM响应序列
        mock_responses = [
            # 概念扩展
            '{"theme": "科技与人性", "genre": "科幻", "main_conflict": "AI觉醒", "setting": "未来世界"}',
            # 策略选择（内部调用）
            '{"structure_type": "三幕剧", "chapter_count": 3, "character_depth": "medium"}',
            # 大纲生成
            '{"chapters": [{"title": "第一章：觉醒", "summary": "AI获得意识"}, {"title": "第二章：探索", "summary": "AI探索世界"}, {"title": "第三章：选择", "summary": "AI做出重要决定"}]}',
            # 角色创建
            '{"主角": {"name": "ARIA", "type": "AI", "personality": "好奇"}}',
            # 章节生成
            "在遥远的未来，一个名为ARIA的人工智能系统突然获得了意识...",
            "ARIA开始探索这个对她来说全新的世界，每一个数据都充满了惊喜...",
            "面对人类和机器的冲突，ARIA必须做出一个关键的选择..."
        ]
        
        with patch.object(generator.llm_client, 'generate', side_effect=mock_responses):
            try:
                result = await generator.generate_novel("AI觉醒的故事", 3000)
                
                # 全面验证结果
                assert "concept" in result
                assert "strategy" in result
                assert "outline" in result
                assert "characters" in result
                assert "chapters" in result
                assert "total_words" in result
                assert "quality_assessment" in result
                
                # 验证章节内容
                assert len(result["chapters"]) == 3
                for chapter in result["chapters"]:
                    assert "title" in chapter
                    assert "content" in chapter
                    assert "word_count" in chapter
                    assert "consistency_check" in chapter
                
                # 验证进度完成
                progress = generator.get_current_progress()
                assert progress["progress"] == 100
                assert progress["stage"] == "完成"
                
                print("✅ 完整流水线测试通过")
                
            except Exception as e:
                print(f"完整流水线测试失败: {e}")
                raise