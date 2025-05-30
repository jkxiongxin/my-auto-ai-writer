#!/usr/bin/env python
"""启动API服务器脚本."""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import uvicorn
from src.utils.config import settings
from src.utils.logger import setup_logging, get_logger

# 设置日志
setup_logging(settings.log_level)
logger = get_logger(__name__)


def main():
    """启动API服务器主函数."""
    
    logger.info("正在启动AI小说生成器API服务...")
    logger.info(f"环境: {settings.environment}")
    logger.info(f"主机: {settings.host}:{settings.port}")
    logger.info(f"调试模式: {settings.debug}")
    
    try:
        uvicorn.run(
            "src.api.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level="info" if not settings.debug else "debug",
            access_log=True,
        )
    except KeyboardInterrupt:
        logger.info("服务器已停止")
    except Exception as e:
        logger.error(f"启动服务器失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()