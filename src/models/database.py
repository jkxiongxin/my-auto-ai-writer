"""数据库连接和会话管理."""

import asyncio
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """数据库模型基类."""
    pass


# 创建异步数据库引擎
engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的异步上下文管理器."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database() -> None:
    """初始化数据库."""
    try:
        logger.info("正在初始化数据库...")
        
        # 创建所有表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # 测试连接
        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
            
        logger.info("数据库初始化完成")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


async def close_database() -> None:
    """关闭数据库连接."""
    try:
        await engine.dispose()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接时发生错误: {e}")


# 依赖注入函数
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI依赖注入：获取数据库会话."""
    async with get_db_session() as session:
        yield session