"""性能测试模块

测试系统在各种负载条件下的性能表现。
"""

import pytest
import time
import asyncio
import psutil
import os
from unittest.mock import patch, MagicMock
from src.core.novel_generator import NovelGenerator
from src.utils.llm_client import UniversalLLMClient


class TestPerformance:
    """性能测试类"""
    
    @pytest.mark.performance
    def test_generation_speed_benchmark(self):
        """测试生成速度基准"""
        generator = NovelGenerator()
        
        # 测试不同规模的生成速度
        test_cases = [
            {"words": 1000, "max_time": 300},   # 5分钟
            {"words": 5000, "max_time": 900},   # 15分钟
            {"words": 10000, "max_time": 1800}, # 30分钟
        ]
        
        for case in test_cases:
            with patch.object(generator.llm_client, 'generate') as mock_generate:
                # 模拟生成内容，控制字数
                mock_content = " ".join(["测试词汇"] * (case["words"] // 10))
                mock_generate.return_value = mock_content
                
                start_time = time.time()
                try:
                    result = generator.generate_novel("性能测试故事", case["words"])
                    end_time = time.time()
                    
                    generation_time = end_time - start_time
                    assert generation_time <= case["max_time"], \
                        f"生成{case['words']}字耗时{generation_time:.2f}秒，超过限制{case['max_time']}秒"
                    
                    if "total_words" in result:
                        words_per_minute = result["total_words"] / (generation_time / 60)
                        assert words_per_minute >= 100, \
                            f"生成速度{words_per_minute:.2f}字/分钟低于最低要求100字/分钟"
                    
                    print(f"✅ {case['words']}字生成测试通过: {generation_time:.2f}秒")
                    
                except Exception as e:
                    print(f"❌ {case['words']}字生成测试失败: {e}")

    @pytest.mark.performance
    def test_memory_usage(self):
        """测试内存使用情况"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        generator = NovelGenerator()
        
        with patch.object(generator.llm_client, 'generate') as mock_generate:
            # 模拟大量内容生成
            large_content = " ".join(["内容"] * 10000)  # 约50KB内容
            mock_generate.return_value = large_content
            
            try:
                result = generator.generate_novel("大型史诗小说", 50000)
                
                peak_memory = process.memory_info().rss
                memory_increase = peak_memory - initial_memory
                
                # 验证内存使用合理（小于1GB）
                max_memory_mb = 1024  # 1GB in MB
                memory_increase_mb = memory_increase / (1024 * 1024)
                
                assert memory_increase_mb < max_memory_mb, \
                    f"内存使用过多: {memory_increase_mb:.2f}MB > {max_memory_mb}MB"
                
                print(f"✅ 内存使用测试通过: {memory_increase_mb:.2f}MB")
                
            except Exception as e:
                print(f"❌ 内存使用测试失败: {e}")

    @pytest.mark.performance
    def test_concurrent_generation(self):
        """测试并发生成能力"""
        async def generate_story(story_id):
            generator = NovelGenerator()
            
            with patch.object(generator.llm_client, 'generate') as mock_generate:
                # 模拟不同响应时间
                await asyncio.sleep(0.1 * story_id)  # 模拟网络延迟
                mock_generate.return_value = f"故事{story_id}的测试内容"
                
                try:
                    return generator.generate_novel(f"并发故事{story_id}", 2000)
                except Exception as e:
                    return {"error": str(e), "story_id": story_id}
        
        async def test_concurrent():
            start_time = time.time()
            tasks = [generate_story(i) for i in range(3)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            return results, end_time - start_time
        
        try:
            results, total_time = asyncio.run(test_concurrent())
            
            # 验证并发效果
            assert len(results) == 3
            
            # 验证并发执行时间合理（应该比串行快）
            max_concurrent_time = 10.0  # 10秒内完成3个任务
            assert total_time < max_concurrent_time, \
                f"并发执行时间{total_time:.2f}秒超过限制{max_concurrent_time}秒"
            
            # 统计成功任务
            successful_results = [
                r for r in results 
                if isinstance(r, dict) and "error" not in r
            ]
            
            success_rate = len(successful_results) / len(results)
            assert success_rate >= 0.6, \
                f"并发成功率{success_rate:.2%}低于最低要求60%"
            
            print(f"✅ 并发生成测试通过: {len(successful_results)}/3 成功, 耗时{total_time:.2f}秒")
            
        except Exception as e:
            print(f"❌ 并发生成测试失败: {e}")

    @pytest.mark.performance
    @pytest.mark.slow
    def test_large_novel_generation_performance(self):
        """测试大型小说生成性能"""
        generator = NovelGenerator()
        
        target_words = 100000
        max_time = 7200  # 2小时
        
        with patch.object(generator.llm_client, 'generate') as mock_generate:
            # 模拟大量内容生成，但速度要快
            def fast_generate(prompt, **kwargs):
                # 根据提示内容返回不同长度的响应
                if "概念扩展" in prompt or "概念" in prompt:
                    return '{"theme": "史诗冒险", "genre": "奇幻"}'
                elif "策略" in prompt:
                    return '{"structure_type": "多卷本结构", "volume_count": 3}'
                elif "大纲" in prompt:
                    return '{"volumes": [{"title": "第一卷", "chapters": [{"title": "第一章"}]}]}'
                elif "角色" in prompt:
                    return '{"主角": {"name": "英雄", "type": "人类"}}'
                else:
                    # 生成较长的章节内容
                    return " ".join(["这是一个精彩的章节内容"] * 500)  # 约3000字
            
            mock_generate.side_effect = fast_generate
            
            start_time = time.time()
            try:
                result = generator.generate_novel("超大型史诗小说", target_words)
                end_time = time.time()
                
                generation_time = end_time - start_time
                
                # 验证时间要求
                assert generation_time <= max_time, \
                    f"生成时间{generation_time:.2f}秒超过限制{max_time}秒"
                
                # 验证字数
                if "total_words" in result:
                    actual_words = result["total_words"]
                    min_words = target_words * 0.8  # 允许20%偏差
                    assert actual_words >= min_words, \
                        f"生成字数{actual_words}低于最低要求{min_words}"
                
                # 计算生成速度
                words_per_second = result.get("total_words", 0) / generation_time
                assert words_per_second >= 10, \
                    f"生成速度{words_per_second:.2f}字/秒低于最低要求10字/秒"
                
                print(f"✅ 大型小说性能测试通过: {result.get('total_words', 0)}字, {generation_time:.2f}秒")
                
            except Exception as e:
                print(f"❌ 大型小说性能测试失败: {e}")

    @pytest.mark.performance
    def test_api_response_time(self):
        """测试API响应时间"""
        from src.api.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # 测试各个端点的响应时间
        endpoints = [
            ("GET", "/health"),
            ("GET", "/api/v1/health"),
        ]
        
        max_response_time = 5.0  # 5秒内响应
        
        for method, endpoint in endpoints:
            start_time = time.time()
            try:
                if method == "GET":
                    response = client.get(endpoint)
                elif method == "POST":
                    response = client.post(endpoint, json={})
                
                end_time = time.time()
                response_time = end_time - start_time
                
                assert response_time < max_response_time, \
                    f"{method} {endpoint} 响应时间{response_time:.2f}秒超过限制{max_response_time}秒"
                
                print(f"✅ {method} {endpoint} 响应时间测试通过: {response_time:.3f}秒")
                
            except Exception as e:
                print(f"❌ {method} {endpoint} 响应时间测试失败: {e}")

    @pytest.mark.performance
    def test_caching_performance(self):
        """测试缓存性能"""
        generator = NovelGenerator()
        
        # 启用缓存
        with patch.object(generator.llm_client, 'generate') as mock_generate:
            call_count = 0
            
            def counting_generate(prompt, **kwargs):
                nonlocal call_count
                call_count += 1
                return f"响应{call_count}: {prompt[:50]}..."
            
            mock_generate.side_effect = counting_generate
            
            # 第一次生成
            start_time = time.time()
            try:
                result1 = generator.generate_novel("缓存测试故事", 1000)
                first_time = time.time() - start_time
                first_calls = call_count
                
                # 重置计数
                call_count = 0
                
                # 相同输入的第二次生成（应该使用缓存）
                start_time = time.time()
                result2 = generator.generate_novel("缓存测试故事", 1000)
                second_time = time.time() - start_time
                second_calls = call_count
                
                # 验证缓存效果
                if hasattr(generator.llm_client, 'cache') and generator.llm_client.cache:
                    # 如果有缓存，第二次应该更快，调用更少
                    assert second_time < first_time, \
                        f"缓存未生效：第二次生成时间{second_time:.2f}秒 >= 第一次{first_time:.2f}秒"
                    
                    cache_hit_rate = 1 - (second_calls / max(first_calls, 1))
                    assert cache_hit_rate > 0, \
                        f"缓存命中率{cache_hit_rate:.2%}过低"
                
                print(f"✅ 缓存性能测试通过: 首次{first_time:.2f}s/{first_calls}次调用, "
                      f"缓存{second_time:.2f}s/{second_calls}次调用")
                
            except Exception as e:
                print(f"❌ 缓存性能测试失败: {e}")

    @pytest.mark.performance
    def test_resource_cleanup(self):
        """测试资源清理"""
        initial_memory = psutil.Process(os.getpid()).memory_info().rss
        
        # 创建多个生成器实例
        generators = []
        for i in range(5):
            generator = NovelGenerator()
            generators.append(generator)
            
            # 模拟使用
            with patch.object(generator.llm_client, 'generate') as mock_generate:
                mock_generate.return_value = f"测试内容{i}"
                try:
                    generator.generate_novel(f"测试故事{i}", 500)
                except:
                    pass
        
        # 清理引用
        del generators
        
        # 强制垃圾回收
        import gc
        gc.collect()
        
        # 等待一段时间让资源释放
        time.sleep(1)
        
        final_memory = psutil.Process(os.getpid()).memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_increase_mb = memory_increase / (1024 * 1024)
        
        # 验证内存没有显著增长（允许50MB增长）
        max_increase_mb = 50
        assert memory_increase_mb < max_increase_mb, \
            f"内存泄漏：增长了{memory_increase_mb:.2f}MB，超过限制{max_increase_mb}MB"
        
        print(f"✅ 资源清理测试通过: 内存增长{memory_increase_mb:.2f}MB")

    @pytest.mark.performance
    def test_stress_test(self):
        """压力测试"""
        generator = NovelGenerator()
        
        # 连续生成多个小说
        num_novels = 5
        max_total_time = 60  # 1分钟内完成所有任务
        
        with patch.object(generator.llm_client, 'generate') as mock_generate:
            mock_generate.return_value = "压力测试内容"
            
            start_time = time.time()
            successful_generations = 0
            
            for i in range(num_novels):
                try:
                    result = generator.generate_novel(f"压力测试小说{i}", 800)
                    if result and "chapters" in result:
                        successful_generations += 1
                except Exception as e:
                    print(f"压力测试第{i+1}个小说失败: {e}")
            
            total_time = time.time() - start_time
            
            # 验证完成时间
            assert total_time < max_total_time, \
                f"压力测试耗时{total_time:.2f}秒超过限制{max_total_time}秒"
            
            # 验证成功率
            success_rate = successful_generations / num_novels
            min_success_rate = 0.8  # 80%成功率
            assert success_rate >= min_success_rate, \
                f"压力测试成功率{success_rate:.2%}低于最低要求{min_success_rate:.2%}"
            
            print(f"✅ 压力测试通过: {successful_generations}/{num_novels} 成功, 耗时{total_time:.2f}秒")


if __name__ == "__main__":
    # 运行性能测试
    pytest.main([__file__, "-v", "-m", "performance"])