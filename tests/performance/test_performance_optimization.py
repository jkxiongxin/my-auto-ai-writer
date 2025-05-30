"""性能优化测试模块."""

import asyncio
import time
import pytest
import psutil
import os
from typing import List, Dict, Any
import logging

from src.core.novel_generator import NovelGenerator
from src.core.quality_assessment import QualityAssessment
from src.utils.monitoring import get_performance_monitor, get_concurrency_manager
from src.utils.performance_cache import get_smart_cache_manager
from src.utils.llm_client import get_universal_client

logger = logging.getLogger(__name__)


class TestPerformanceOptimization:
    """性能优化测试类."""
    
    @pytest.fixture(autouse=True)
    async def setup_monitoring(self):
        """设置监控."""
        monitor = get_performance_monitor()
        await monitor.start()
        yield
        await monitor.stop()
    
    @pytest.mark.performance
    async def test_generation_speed_benchmark(self):
        """测试生成速度基准."""
        generator = NovelGenerator()
        
        # 测试不同规模的生成速度
        test_cases = [
            {"words": 1000, "max_time": 300, "description": "短篇故事"},     # 5分钟
            {"words": 5000, "max_time": 900, "description": "中篇故事"},     # 15分钟
            {"words": 10000, "max_time": 1800, "description": "长篇故事"},   # 30分钟
        ]
        
        results = []
        
        for case in test_cases:
            logger.info(f"开始测试: {case['description']} ({case['words']} 字)")
            
            start_time = time.time()
            result = await generator.generate_novel_async(
                f"测试{case['description']}", 
                case["words"]
            )
            end_time = time.time()
            
            generation_time = end_time - start_time
            actual_words = result.get("total_words", 0)
            words_per_minute = actual_words / (generation_time / 60) if generation_time > 0 else 0
            
            # 验证时间要求
            assert generation_time <= case["max_time"], \
                f"{case['description']} 生成时间超限: {generation_time:.2f}s > {case['max_time']}s"
            
            # 验证字数要求
            assert actual_words >= case["words"] * 0.8, \
                f"{case['description']} 字数不足: {actual_words} < {case['words'] * 0.8}"
            
            # 验证生成速度（至少每分钟100字）
            assert words_per_minute >= 100, \
                f"{case['description']} 生成速度过慢: {words_per_minute:.1f} 字/分钟"
            
            results.append({
                "description": case["description"],
                "target_words": case["words"],
                "actual_words": actual_words,
                "generation_time": generation_time,
                "words_per_minute": words_per_minute,
                "efficiency": actual_words / generation_time
            })
            
            logger.info(
                f"{case['description']} 完成: "
                f"{actual_words} 字, {generation_time:.2f}s, "
                f"{words_per_minute:.1f} 字/分钟"
            )
        
        # 记录性能基准
        logger.info("性能基准测试结果:")
        for result in results:
            logger.info(f"  {result}")
    
    @pytest.mark.performance
    async def test_memory_usage_optimization(self):
        """测试内存使用优化."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        generator = NovelGenerator()
        
        # 生成多个中等规模的小说
        novels = []
        for i in range(3):
            logger.info(f"生成第 {i+1} 个小说")
            
            result = await generator.generate_novel_async(
                f"大型史诗小说 {i+1}", 
                20000  # 2万字
            )
            novels.append(result)
            
            # 检查内存使用
            current_memory = process.memory_info().rss
            memory_increase = current_memory - initial_memory
            
            logger.info(f"当前内存增长: {memory_increase / 1024 / 1024:.1f} MB")
        
        # 最终内存检查
        peak_memory = process.memory_info().rss
        total_memory_increase = peak_memory - initial_memory
        
        # 验证内存使用合理（小于1GB）
        assert total_memory_increase < 1024 * 1024 * 1024, \
            f"内存使用过多: {total_memory_increase / 1024 / 1024:.1f} MB"
        
        # 验证生成的小说质量
        total_words = sum(novel.get("total_words", 0) for novel in novels)
        assert total_words >= 50000, f"总字数不足: {total_words}"
        
        logger.info(f"内存优化测试完成，总内存增长: {total_memory_increase / 1024 / 1024:.1f} MB")
    
    @pytest.mark.performance
    async def test_concurrent_generation_capacity(self):
        """测试并发生成能力."""
        generator = NovelGenerator()
        concurrency_manager = get_concurrency_manager()
        
        # 测试不同并发级别
        concurrent_levels = [2, 3, 5]
        
        for level in concurrent_levels:
            logger.info(f"测试并发级别: {level}")
            
            async def generate_story(story_id: int) -> Dict[str, Any]:
                """生成单个故事."""
                return await generator.generate_novel_async(
                    f"并发测试故事 {story_id}", 
                    2000  # 2000字
                )
            
            # 执行并发生成
            start_time = time.time()
            tasks = [generate_story(i) for i in range(level)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # 验证结果
            successful_results = [r for r in results if not isinstance(r, Exception)]
            failed_results = [r for r in results if isinstance(r, Exception)]
            
            # 记录失败的任务
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"并发任务 {i} 失败: {result}")
            
            # 验证成功率
            success_rate = len(successful_results) / len(results)
            assert success_rate >= 0.8, \
                f"并发级别 {level} 成功率过低: {success_rate:.1%}"
            
            # 验证并发效率（并发应该比串行快）
            total_time = end_time - start_time
            estimated_serial_time = level * 120  # 假设每个任务2分钟
            efficiency = estimated_serial_time / total_time if total_time > 0 else 0
            
            assert efficiency >= 1.5, \
                f"并发级别 {level} 效率提升不足: {efficiency:.1f}x"
            
            # 验证生成质量
            total_words = sum(
                result.get("total_words", 0) 
                for result in successful_results
            )
            expected_words = len(successful_results) * 1600  # 允许20%偏差
            assert total_words >= expected_words, \
                f"并发级别 {level} 总字数不足: {total_words} < {expected_words}"
            
            # 获取并发统计
            concurrency_stats = await concurrency_manager.get_concurrency_stats()
            
            logger.info(
                f"并发级别 {level} 完成: "
                f"成功率 {success_rate:.1%}, "
                f"效率 {efficiency:.1f}x, "
                f"总耗时 {total_time:.1f}s, "
                f"总字数 {total_words}"
            )
            
            logger.debug(f"并发统计: {concurrency_stats}")
            
            # 短暂休息，避免资源争用
            await asyncio.sleep(2)
    
    @pytest.mark.performance
    async def test_cache_performance_optimization(self):
        """测试缓存性能优化."""
        cache_manager = get_smart_cache_manager()
        llm_client = get_universal_client()
        
        # 预热缓存
        await cache_manager.warmup_cache()
        
        # 测试相同请求的缓存效果
        test_prompt = "一个关于人工智能觉醒的科幻故事"
        
        # 第一次请求（缓存未命中）
        start_time = time.time()
        result1 = await llm_client.generate(test_prompt)
        first_request_time = time.time() - start_time
        
        # 第二次请求（应该命中缓存）
        start_time = time.time()
        result2 = await llm_client.generate(test_prompt)
        second_request_time = time.time() - start_time
        
        # 验证缓存命中
        assert result1 == result2, "缓存结果不一致"
        
        # 验证缓存带来的性能提升
        cache_speedup = first_request_time / second_request_time if second_request_time > 0 else float('inf')
        assert cache_speedup >= 10, \
            f"缓存性能提升不足: {cache_speedup:.1f}x"
        
        # 测试批量请求的缓存效果
        prompts = [
            f"测试提示词 {i}: {test_prompt}" 
            for i in range(5)
        ]
        
        # 第一次批量请求
        start_time = time.time()
        batch_results1 = await llm_client.generate_batch(prompts)
        first_batch_time = time.time() - start_time
        
        # 第二次批量请求（应该大部分命中缓存）
        start_time = time.time()
        batch_results2 = await llm_client.generate_batch(prompts)
        second_batch_time = time.time() - start_time
        
        # 验证批量缓存效果
        batch_cache_speedup = first_batch_time / second_batch_time if second_batch_time > 0 else float('inf')
        assert batch_cache_speedup >= 5, \
            f"批量缓存性能提升不足: {batch_cache_speedup:.1f}x"
        
        # 获取缓存统计
        cache_stats = await cache_manager.get_cache_performance()
        
        logger.info(
            f"缓存性能测试完成: "
            f"单次加速 {cache_speedup:.1f}x, "
            f"批量加速 {batch_cache_speedup:.1f}x"
        )
        logger.debug(f"缓存统计: {cache_stats}")
    
    @pytest.mark.performance
    async def test_system_resource_monitoring(self):
        """测试系统资源监控."""
        monitor = get_performance_monitor()
        generator = NovelGenerator()
        
        # 开始监控
        initial_metrics = await monitor.get_current_metrics()
        
        # 执行资源密集型任务
        async with monitor.track_request("intensive_generation") as metrics:
            result = await generator.generate_novel_async(
                "资源密集型测试小说", 
                15000  # 15000字
            )
            
            # 记录token使用（如果可用）
            if hasattr(metrics, 'tokens_used'):
                metrics.tokens_used = result.get("total_words", 0) * 1.3  # 估算
        
        # 获取最终指标
        final_metrics = await monitor.get_current_metrics()
        performance_summary = await monitor.get_performance_summary()
        
        # 验证监控数据
        assert performance_summary["status"] == "healthy", \
            "系统状态不健康"
        
        assert performance_summary["cpu_percent"] < 90, \
            f"CPU使用率过高: {performance_summary['cpu_percent']:.1f}%"
        
        assert performance_summary["memory_percent"] < 90, \
            f"内存使用率过高: {performance_summary['memory_percent']:.1f}%"
        
        # 验证生成质量
        assert result.get("total_words", 0) >= 12000, \
            "生成字数不足"
        
        logger.info(f"资源监控测试完成: {performance_summary}")
    
    @pytest.mark.performance
    async def test_performance_regression(self):
        """性能回归测试."""
        generator = NovelGenerator()
        
        # 性能基准（这些数值应该基于实际测量调整）
        performance_baselines = {
            "short_story_time": 300,      # 短篇5分钟
            "medium_story_time": 900,     # 中篇15分钟  
            "words_per_minute": 100,      # 每分钟至少100字
            "memory_limit_mb": 500,       # 内存限制500MB
            "cache_hit_ratio": 0.7,       # 缓存命中率70%
        }
        
        # 测试短篇生成性能
        start_time = time.time()
        short_result = await generator.generate_novel_async("性能回归测试短篇", 3000)
        short_time = time.time() - start_time
        
        assert short_time <= performance_baselines["short_story_time"], \
            f"短篇生成时间超过基准: {short_time:.1f}s > {performance_baselines['short_story_time']}s"
        
        # 测试生成速度
        words_per_minute = short_result.get("total_words", 0) / (short_time / 60)
        assert words_per_minute >= performance_baselines["words_per_minute"], \
            f"生成速度低于基准: {words_per_minute:.1f} < {performance_baselines['words_per_minute']}"
        
        # 测试内存使用
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        assert memory_mb <= performance_baselines["memory_limit_mb"], \
            f"内存使用超过基准: {memory_mb:.1f}MB > {performance_baselines['memory_limit_mb']}MB"
        
        # 测试缓存性能
        cache_manager = get_smart_cache_manager()
        cache_stats = await cache_manager.get_cache_performance()
        
        if "llm_cache" in cache_stats and "hit_ratio" in cache_stats["llm_cache"]:
            hit_ratio = cache_stats["llm_cache"]["hit_ratio"]
            if hit_ratio > 0:  # 只有在有缓存数据时才验证
                assert hit_ratio >= performance_baselines["cache_hit_ratio"], \
                    f"缓存命中率低于基准: {hit_ratio:.2f} < {performance_baselines['cache_hit_ratio']}"
        
        logger.info(
            f"性能回归测试通过: "
            f"时间 {short_time:.1f}s, "
            f"速度 {words_per_minute:.1f} 字/分钟, "
            f"内存 {memory_mb:.1f}MB"
        )
    
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_large_scale_generation_performance(self):
        """大规模生成性能测试."""
        generator = NovelGenerator()
        
        # 测试10万字小说生成
        logger.info("开始大规模生成性能测试（10万字）")
        
        start_time = time.time()
        result = await generator.generate_novel_async(
            "大规模性能测试史诗小说：一个平凡少年成长为传奇英雄的冒险故事", 
            100000
        )
        end_time = time.time()
        
        generation_time = end_time - start_time
        total_words = result.get("total_words", 0)
        
        # 验证时间要求（2小时内）
        assert generation_time <= 7200, \
            f"大规模生成时间超限: {generation_time:.1f}s > 7200s"
        
        # 验证字数要求
        assert 95000 <= total_words <= 110000, \
            f"大规模生成字数不符: {total_words} 不在 [95000, 110000] 范围内"
        
        # 验证平均生成速度
        words_per_minute = total_words / (generation_time / 60)
        assert words_per_minute >= 50, \
            f"大规模生成平均速度过慢: {words_per_minute:.1f} 字/分钟"
        
        # 验证质量
        quality_assessor = QualityAssessment()
        quality_result = await quality_assessor.evaluate_novel_async(result)
        overall_score = quality_result.get("overall_scores", {}).get("overall", 0)
        
        assert overall_score >= 7.0, \
            f"大规模生成质量不达标: {overall_score:.1f} < 7.0"
        
        # 获取性能统计
        monitor = get_performance_monitor()
        performance_summary = await monitor.get_performance_summary()
        
        logger.info(
            f"大规模生成性能测试完成: "
            f"{total_words} 字, {generation_time:.1f}s, "
            f"{words_per_minute:.1f} 字/分钟, "
            f"质量评分 {overall_score:.1f}"
        )
        
        logger.info(f"系统性能摘要: {performance_summary}")


# 性能基准数据收集函数
async def collect_performance_baseline():
    """收集性能基准数据."""
    logger.info("开始收集性能基准数据")
    
    test_instance = TestPerformanceOptimization()
    
    # 收集各种场景的性能数据
    baseline_data = {
        "timestamp": time.time(),
        "test_results": {}
    }
    
    try:
        # 小规模生成基准
        await test_instance.test_generation_speed_benchmark()
        baseline_data["test_results"]["speed_benchmark"] = "completed"
        
        # 内存使用基准
        await test_instance.test_memory_usage_optimization()
        baseline_data["test_results"]["memory_optimization"] = "completed"
        
        # 并发能力基准
        await test_instance.test_concurrent_generation_capacity()
        baseline_data["test_results"]["concurrent_capacity"] = "completed"
        
        logger.info("性能基准数据收集完成")
        return baseline_data
        
    except Exception as e:
        logger.error(f"性能基准数据收集失败: {e}")
        raise


if __name__ == "__main__":
    # 运行性能基准收集
    asyncio.run(collect_performance_baseline())