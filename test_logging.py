#!/usr/bin/env python3
"""测试日志系统."""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_logging():
    """测试日志功能."""
    
    print("🧪 测试日志系统...")
    
    try:
        # 导入日志模块
        from src.utils.logger import get_logger, setup_logging
        
        print("✅ 日志模块导入成功")
        
        # 重新设置日志（确保使用最新配置）
        setup_logging("DEBUG")
        
        # 获取测试日志器
        logger = get_logger("test_logging")
        
        print("\n📝 测试各种日志级别...")
        
        # 测试各种日志级别
        logger.debug("这是一个调试消息", component="测试", action="调试")
        logger.info("这是一个信息消息", component="测试", action="信息", status="正常")
        logger.warning("这是一个警告消息", component="测试", action="警告", reason="测试警告")
        logger.error("这是一个错误消息", component="测试", action="错误", error_code=500)
        
        # 测试中文字符
        logger.info("测试中文字符显示", 
                   项目名称="AI智能小说生成器",
                   状态="运行中", 
                   描述="这是一个包含中文的日志消息")
        
        # 测试异常日志
        try:
            raise ValueError("这是一个测试异常")
        except Exception as e:
            logger.error("捕获到异常", error=str(e), exc_info=True)
        
        print("✅ 日志测试完成")
        
        # 检查日志文件
        log_file = Path("logs/ai_novel_generator.log")
        if log_file.exists():
            print(f"📁 日志文件存在: {log_file}")
            print(f"📏 日志文件大小: {log_file.stat().st_size} 字节")
            
            # 读取最后几行日志
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    print("\n📖 最后5行日志:")
                    for line in lines[-5:]:
                        print(f"  {line.strip()}")
        else:
            print("❌ 日志文件不存在")
        
    except Exception as e:
        print(f"❌ 日志测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数."""
    print("🧪 AI智能小说生成器日志系统测试")
    print("="*50)
    
    test_logging()
    
    print("\n🎉 日志测试完成!")

if __name__ == "__main__":
    main()