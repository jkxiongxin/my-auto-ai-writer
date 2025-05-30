#!/usr/bin/env python3
"""启动API服务器."""

import os
import sys
import subprocess
from pathlib import Path

# 确保我们在正确的目录
project_root = Path(__file__).parent
os.chdir(project_root)

# 添加项目根目录到Python路径
sys.path.insert(0, str(project_root))

def main():
    """主函数."""
    print("🚀 正在启动AI智能小说生成器API服务...")
    print("="*60)
    
    # 首先测试配置
    print("🔍 检查配置...")
    try:
        result = subprocess.run([sys.executable, "test_config.py"],
                              capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ 配置检查失败: {e}")
        print("错误输出:", e.stderr)
        return 1
    
    # 测试日志系统
    print("\n📝 检查日志系统...")
    try:
        result = subprocess.run([sys.executable, "test_logging.py"],
                              capture_output=True, text=True, check=True)
        print("✅ 日志系统正常")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ 日志系统检查失败: {e}")
        print("但继续启动...")
    
    # 启动API服务器
    print("\n🌐 启动API服务器...")
    print("访问地址:")
    print("  - API文档: http://localhost:8000/docs")
    print("  - 前端界面: http://localhost:8000/app")
    print("  - 健康检查: http://localhost:8000/health")
    print("\n📁 日志文件: logs/ai_novel_generator.log")
    print("按 Ctrl+C 停止服务器")
    print("="*60)
    
    try:
        # 使用uvicorn启动服务器
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "src.api.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--log-level", "info"
        ], check=True)
        
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())