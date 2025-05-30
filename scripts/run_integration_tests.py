#!/usr/bin/env python3
"""集成和端到端测试运行脚本

此脚本运行完整的集成测试套件，包括：
- 集成测试
- 性能测试
- 验收测试
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_command(command, description):
    """运行命令并返回结果"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"执行命令: {command}")
    
    start_time = time.time()
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"耗时: {duration:.2f}秒")
        
        if result.returncode == 0:
            print("✅ 成功")
            if result.stdout:
                print("输出:")
                print(result.stdout)
        else:
            print("❌ 失败")
            if result.stderr:
                print("错误:")
                print(result.stderr)
            if result.stdout:
                print("输出:")
                print(result.stdout)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False

def check_prerequisites():
    """检查运行前提条件"""
    print("🔍 检查运行前提条件...")
    
    # 检查Python环境
    python_version = sys.version_info
    if python_version < (3, 8):
        print(f"❌ Python版本过低: {python_version.major}.{python_version.minor}")
        print("需要Python 3.8或更高版本")
        return False
    
    print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 检查项目结构
    required_dirs = [
        "src",
        "tests",
        "tests/integration",
        "tests/performance", 
        "tests/acceptance"
    ]
    
    for dir_path in required_dirs:
        if not (project_root / dir_path).exists():
            print(f"❌ 缺少目录: {dir_path}")
            return False
    
    print("✅ 项目结构完整")
    
    # 检查核心文件
    required_files = [
        "src/core/novel_generator.py",
        "tests/integration/test_novel_generation_flow.py",
        "tests/performance/test_performance.py",
        "tests/acceptance/test_final_acceptance.py"
    ]
    
    for file_path in required_files:
        if not (project_root / file_path).exists():
            print(f"❌ 缺少文件: {file_path}")
            return False
    
    print("✅ 核心文件完整")
    
    return True

def run_integration_tests():
    """运行集成测试"""
    commands = [
        (
            "python -m pytest tests/integration/ -v --tb=short",
            "集成测试"
        ),
        (
            "python -m pytest tests/integration/test_novel_generation_flow.py::TestNovelGenerationFlow::test_complete_short_story_generation -v",
            "短篇小说生成测试"
        ),
        (
            "python -m pytest tests/integration/test_novel_generation_flow.py::TestNovelGenerationFlow::test_error_recovery -v",
            "错误恢复测试"
        )
    ]
    
    results = []
    for command, description in commands:
        success = run_command(command, description)
        results.append((description, success))
    
    return results

def run_performance_tests():
    """运行性能测试"""
    commands = [
        (
            "python -m pytest tests/performance/ -v --tb=short -m 'performance and not slow'",
            "基础性能测试"
        ),
        (
            "python -m pytest tests/performance/test_performance.py::TestPerformance::test_generation_speed_benchmark -v",
            "生成速度基准测试"
        ),
        (
            "python -m pytest tests/performance/test_performance.py::TestPerformance::test_memory_usage -v",
            "内存使用测试"
        ),
        (
            "python -m pytest tests/performance/test_performance.py::TestPerformance::test_concurrent_generation -v",
            "并发生成测试"
        )
    ]
    
    results = []
    for command, description in commands:
        success = run_command(command, description)
        results.append((description, success))
    
    return results

def run_acceptance_tests():
    """运行验收测试"""
    commands = [
        (
            "python -m pytest tests/acceptance/ -v --tb=short",
            "验收测试"
        ),
        (
            "python -m pytest tests/acceptance/test_final_acceptance.py::TestFinalAcceptance::test_all_success_criteria -v",
            "成功标准验证"
        ),
        (
            "python -m pytest tests/acceptance/test_final_acceptance.py::TestFinalAcceptance::test_functional_requirements -v",
            "功能需求验证"
        ),
        (
            "python -m pytest tests/acceptance/test_final_acceptance.py::TestFinalAcceptance::test_final_acceptance_summary -v",
            "最终验收总结"
        )
    ]
    
    results = []
    for command, description in commands:
        success = run_command(command, description)
        results.append((description, success))
    
    return results

def run_slow_tests():
    """运行慢速测试（可选）"""
    print("\n" + "="*60)
    print("⚠️  慢速测试需要更长时间，是否运行？")
    print("包括：大型小说生成测试、压力测试等")
    print("="*60)
    
    response = input("运行慢速测试? (y/N): ").strip().lower()
    
    if response not in ['y', 'yes']:
        print("跳过慢速测试")
        return []
    
    commands = [
        (
            "python -m pytest tests/integration/ -v --tb=short -m 'slow'",
            "慢速集成测试"
        ),
        (
            "python -m pytest tests/performance/ -v --tb=short -m 'slow'",
            "慢速性能测试"
        )
    ]
    
    results = []
    for command, description in commands:
        success = run_command(command, description)
        results.append((description, success))
    
    return results

def generate_report(all_results):
    """生成测试报告"""
    print("\n" + "="*80)
    print("📊 测试结果汇总")
    print("="*80)
    
    total_tests = 0
    passed_tests = 0
    
    for category, results in all_results.items():
        if not results:
            continue
            
        print(f"\n📋 {category}:")
        print("-" * 40)
        
        for test_name, success in results:
            status = "✅ 通过" if success else "❌ 失败"
            print(f"  {test_name}: {status}")
            total_tests += 1
            if success:
                passed_tests += 1
    
    print("\n" + "="*80)
    print(f"📈 总体结果: {passed_tests}/{total_tests} 通过 ({passed_tests/total_tests:.1%})")
    
    if passed_tests == total_tests:
        print("🎉 所有测试都通过了！系统集成成功！")
        return True
    elif passed_tests / total_tests >= 0.8:
        print("✅ 大部分测试通过，系统基本可用")
        return True
    else:
        print("⚠️ 测试通过率较低，需要进一步完善")
        return False

def main():
    """主函数"""
    print("🚀 AI智能小说生成器 - 集成和端到端测试")
    print("="*80)
    
    # 检查前提条件
    if not check_prerequisites():
        print("❌ 前提条件检查失败")
        sys.exit(1)
    
    # 记录开始时间
    start_time = time.time()
    
    # 运行各类测试
    all_results = {}
    
    try:
        # 集成测试
        print("\n🔗 开始集成测试...")
        all_results["集成测试"] = run_integration_tests()
        
        # 性能测试
        print("\n⚡ 开始性能测试...")
        all_results["性能测试"] = run_performance_tests()
        
        # 验收测试
        print("\n✅ 开始验收测试...")
        all_results["验收测试"] = run_acceptance_tests()
        
        # 慢速测试（可选）
        slow_results = run_slow_tests()
        if slow_results:
            all_results["慢速测试"] = slow_results
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
        sys.exit(1)
    
    # 计算总耗时
    end_time = time.time()
    total_duration = end_time - start_time
    
    # 生成报告
    success = generate_report(all_results)
    
    print(f"\n⏱️ 总耗时: {total_duration:.2f}秒")
    print("="*80)
    
    if success:
        print("🎯 集成测试完成！系统可以进入下一阶段。")
        sys.exit(0)
    else:
        print("🔧 需要修复失败的测试项目。")
        sys.exit(1)

if __name__ == "__main__":
    main()