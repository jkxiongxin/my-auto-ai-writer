"""运行性能测试的脚本."""

import asyncio
import sys
import os
import time
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.monitoring import get_performance_monitor, get_concurrency_manager
from src.utils.performance_cache import get_smart_cache_manager
from src.utils.llm_client import get_universal_client
from src.core.novel_generator import NovelGenerator
from tests.performance.test_performance_optimization import TestPerformanceOptimization

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_performance_baseline_tests():
    """运行性能基准测试."""
    logger.info("=" * 60)
    logger.info("开始性能基准测试")
    logger.info("=" * 60)
    
    # 初始化性能监控
    monitor = get_performance_monitor()
    await monitor.start()
    
    try:
        # 创建测试实例
        test_instance = TestPerformanceOptimization()
        
        # 1. 生成速度基准测试
        logger.info("\n1. 生成速度基准测试")
        logger.info("-" * 30)
        await test_instance.test_generation_speed_benchmark()
        
        # 2. 内存使用优化测试
        logger.info("\n2. 内存使用优化测试")
        logger.info("-" * 30)
        await test_instance.test_memory_usage_optimization()
        
        # 3. 并发生成能力测试
        logger.info("\n3. 并发生成能力测试")
        logger.info("-" * 30)
        await test_instance.test_concurrent_generation_capacity()
        
        # 4. 缓存性能优化测试
        logger.info("\n4. 缓存性能优化测试")
        logger.info("-" * 30)
        await test_instance.test_cache_performance_optimization()
        
        # 5. 系统资源监控测试
        logger.info("\n5. 系统资源监控测试")
        logger.info("-" * 30)
        await test_instance.test_system_resource_monitoring()
        
        # 6. 性能回归测试
        logger.info("\n6. 性能回归测试")
        logger.info("-" * 30)
        await test_instance.test_performance_regression()
        
        logger.info("\n" + "=" * 60)
        logger.info("所有性能基准测试完成！")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"性能测试失败: {e}", exc_info=True)
        raise
    finally:
        await monitor.stop()


async def run_large_scale_test():
    """运行大规模生成测试."""
    logger.info("=" * 60)
    logger.info("开始大规模生成测试（10万字）")
    logger.info("=" * 60)
    
    # 初始化性能监控
    monitor = get_performance_monitor()
    await monitor.start()
    
    try:
        test_instance = TestPerformanceOptimization()
        await test_instance.test_large_scale_generation_performance()
        
        logger.info("\n" + "=" * 60)
        logger.info("大规模生成测试完成！")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"大规模测试失败: {e}", exc_info=True)
        raise
    finally:
        await monitor.stop()


async def run_performance_comparison():
    """运行性能对比测试（优化版 vs 基础版）."""
    logger.info("=" * 60)
    logger.info("开始性能对比测试")
    logger.info("=" * 60)
    
    # 测试数据
    test_cases = [
        {"input": "一个关于时间旅行的科幻故事", "words": 3000},
        {"input": "魔法学院的冒险故事", "words": 5000},
        {"input": "末世求生的故事", "words": 2000}
    ]
    
    results = {
        "optimized": [],
        "basic": []
    }
    
    # 测试优化版本
    logger.info("\n测试优化版本...")
    generator_optimized = NovelGenerator(enable_performance_optimization=True)
    
    for case in test_cases:
        logger.info(f"生成: {case['input']} ({case['words']} 字)")
        start_time = time.time()
        
        try:
            result = await generator_optimized.generate_novel_async(
                case["input"], case["words"]
            )
            generation_time = time.time() - start_time
            
            results["optimized"].append({
                "case": case,
                "time": generation_time,
                "words": result.get("metadata", {}).get("total_words", 0),
                "success": True
            })
            
            logger.info(f"完成: {generation_time:.2f}s, {result.get('metadata', {}).get('total_words', 0)} 字")
            
        except Exception as e:
            logger.error(f"优化版生成失败: {e}")
            results["optimized"].append({
                "case": case,
                "time": 0,
                "words": 0,
                "success": False,
                "error": str(e)
            })
    
    # 测试基础版本
    logger.info("\n测试基础版本...")
    generator_basic = NovelGenerator(enable_performance_optimization=False)
    
    for case in test_cases:
        logger.info(f"生成: {case['input']} ({case['words']} 字)")
        start_time = time.time()
        
        try:
            result = await generator_basic.generate_novel_async(
                case["input"], case["words"]
            )
            generation_time = time.time() - start_time
            
            results["basic"].append({
                "case": case,
                "time": generation_time,
                "words": result.get("metadata", {}).get("total_words", 0),
                "success": True
            })
            
            logger.info(f"完成: {generation_time:.2f}s, {result.get('metadata', {}).get('total_words', 0)} 字")
            
        except Exception as e:
            logger.error(f"基础版生成失败: {e}")
            results["basic"].append({
                "case": case,
                "time": 0,
                "words": 0,
                "success": False,
                "error": str(e)
            })
    
    # 分析结果
    logger.info("\n" + "=" * 60)
    logger.info("性能对比结果")
    logger.info("=" * 60)
    
    total_time_optimized = sum(r["time"] for r in results["optimized"] if r["success"])
    total_time_basic = sum(r["time"] for r in results["basic"] if r["success"])
    
    total_words_optimized = sum(r["words"] for r in results["optimized"] if r["success"])
    total_words_basic = sum(r["words"] for r in results["basic"] if r["success"])
    
    if total_time_basic > 0:
        time_improvement = (total_time_basic - total_time_optimized) / total_time_basic * 100
        speed_improvement = total_time_basic / total_time_optimized if total_time_optimized > 0 else float('inf')
    else:
        time_improvement = 0
        speed_improvement = 1
    
    logger.info(f"优化版总耗时: {total_time_optimized:.2f}s")
    logger.info(f"基础版总耗时: {total_time_basic:.2f}s")
    logger.info(f"时间改进: {time_improvement:.1f}%")
    logger.info(f"速度提升: {speed_improvement:.2f}x")
    logger.info(f"优化版总字数: {total_words_optimized}")
    logger.info(f"基础版总字数: {total_words_basic}")
    
    return results


async def run_cache_warming_test():
    """运行缓存预热测试."""
    logger.info("=" * 60)
    logger.info("开始缓存预热测试")
    logger.info("=" * 60)
    
    cache_manager = get_smart_cache_manager()
    llm_client = get_universal_client()
    
    # 预热缓存
    logger.info("预热缓存...")
    await cache_manager.warmup_cache()
    
    # 测试常见请求
    common_prompts = [
        "一个关于机器人觉醒的科幻故事",
        "魔法世界的冒险",
        "现代都市的悬疑故事",
        "古代武侠的江湖恩怨",
        "未来世界的星际战争"
    ]
    
    # 第一轮请求（应该缓存未命中）
    logger.info("第一轮请求（缓存未命中）...")
    first_round_times = []
    
    for prompt in common_prompts:
        start_time = time.time()
        try:
            result = await llm_client.generate(prompt)
            request_time = time.time() - start_time
            first_round_times.append(request_time)
            logger.info(f"请求完成: {request_time:.2f}s")
        except Exception as e:
            logger.error(f"请求失败: {e}")
            first_round_times.append(0)
    
    # 第二轮请求（应该缓存命中）
    logger.info("第二轮请求（缓存命中）...")
    second_round_times = []
    
    for prompt in common_prompts:
        start_time = time.time()
        try:
            result = await llm_client.generate(prompt)
            request_time = time.time() - start_time
            second_round_times.append(request_time)
            logger.info(f"请求完成: {request_time:.2f}s")
        except Exception as e:
            logger.error(f"请求失败: {e}")
            second_round_times.append(0)
    
    # 分析缓存效果
    avg_first_round = sum(first_round_times) / len(first_round_times) if first_round_times else 0
    avg_second_round = sum(second_round_times) / len(second_round_times) if second_round_times else 0
    
    if avg_second_round > 0:
        cache_speedup = avg_first_round / avg_second_round
    else:
        cache_speedup = float('inf')
    
    logger.info("\n" + "=" * 60)
    logger.info("缓存预热测试结果")
    logger.info("=" * 60)
    logger.info(f"第一轮平均耗时: {avg_first_round:.2f}s")
    logger.info(f"第二轮平均耗时: {avg_second_round:.2f}s")
    logger.info(f"缓存加速比: {cache_speedup:.2f}x")
    
    # 获取缓存统计
    cache_stats = await cache_manager.get_cache_performance()
    logger.info(f"缓存统计: {cache_stats}")


async def main():
    """主函数."""
    logger.info("AI智能小说生成器 - 性能测试套件")
    logger.info("=" * 60)
    
    # 检查测试选项
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
    else:
        test_type = "all"
    
    try:
        if test_type == "baseline":
            await run_performance_baseline_tests()
        elif test_type == "large":
            await run_large_scale_test()
        elif test_type == "compare":
            await run_performance_comparison()
        elif test_type == "cache":
            await run_cache_warming_test()
        elif test_type == "all":
            await run_performance_baseline_tests()
            await run_performance_comparison()
            await run_cache_warming_test()
        else:
            logger.error(f"未知的测试类型: {test_type}")
            logger.info("可用的测试类型: baseline, large, compare, cache, all")
            sys.exit(1)
        
        logger.info("\n" + "=" * 60)
        logger.info("所有性能测试完成！")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试运行失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容性）
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 运行测试
    asyncio.run(main())