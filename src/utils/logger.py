"""日志系统配置."""

import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import structlog
from structlog.stdlib import BoundLogger

from .config import settings


def setup_logging(log_level: str = "INFO") -> None:
    """设置结构化日志."""
    
    # 确保日志目录存在
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 清除现有的处理器
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建格式化器
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 配置控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(console_formatter)
    
    # 配置文件处理器
    log_file = log_dir / settings.log_file.split('/')[-1]  # 获取文件名部分
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(file_formatter)
    
    # 配置根日志器
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # 配置structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            _add_timestamp,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            _get_renderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # 记录日志系统启动
    logger = logging.getLogger(__name__)
    logger.info("日志系统初始化完成")
    logger.info(f"日志级别: {log_level}")
    logger.info(f"控制台输出: 启用")
    logger.info(f"文件输出: {log_file}")


def _add_timestamp(_, __, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """添加时间戳到日志."""
    event_dict["timestamp"] = datetime.utcnow().isoformat()
    return event_dict


def _get_renderer():
    """获取日志渲染器."""
    try:
        if settings.log_format == "json":
            # 使用支持中文的JSON渲染器
            return structlog.processors.JSONRenderer(ensure_ascii=False)
        else:
            return structlog.dev.ConsoleRenderer()
    except Exception:
        # 如果配置未加载，使用控制台渲染器
        return structlog.dev.ConsoleRenderer()


def get_logger(name: str) -> BoundLogger:
    """获取结构化日志器."""
    return structlog.get_logger(name)


# 确保日志系统初始化
try:
    setup_logging(settings.log_level)
except Exception:
    # 如果设置未加载，使用默认配置
    setup_logging("INFO")

# 导出默认logger实例
logger = get_logger(__name__)