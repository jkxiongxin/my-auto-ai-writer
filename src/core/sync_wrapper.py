"""异步转同步包装器 - 将异步LLM调用转换为同步阻塞调用"""

import asyncio
import threading
import time
from typing import Any, Callable, TypeVar
from concurrent.futures import ThreadPoolExecutor
from src.utils.logger import logger

T = TypeVar('T')

# 全局速率限制状态
_last_llm_call_time = 0.0


def sync_llm_call(async_func: Callable[..., Any], *args, **kwargs) -> Any:
    """
    将异步LLM调用转换为同步阻塞调用，包含速率限制
    
    Args:
        async_func: 异步函数
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        函数执行结果
        
    Raises:
        Exception: 异步函数抛出的任何异常
    """
    try:
        # 应用速率限制
        _apply_rate_limit()
        
        # 尝试获取当前事件循环
        try:
            loop = asyncio.get_running_loop()
            # 如果在事件循环中，使用线程池执行
            logger.debug("在事件循环中，使用线程池执行异步调用")
            return _run_in_thread(async_func, *args, **kwargs)
        except RuntimeError:
            # 没有运行的事件循环，创建新的
            logger.debug("没有运行的事件循环，创建新的事件循环")
            return asyncio.run(async_func(*args, **kwargs))
    except Exception as e:
        logger.error(f"同步LLM调用失败: {e}")
        raise


def _apply_rate_limit():
    """应用速率限制，确保LLM调用间隔合理"""
    global _last_llm_call_time
    
    # 从配置获取速率限制
    try:
        from src.utils.config import get_settings
        settings = get_settings()
        rate_limit_delay = settings.llm_rate_limit_delay
    except Exception:
        # 如果无法获取配置，使用默认值
        rate_limit_delay = 10.0
    
    current_time = time.time()
    time_since_last_call = current_time - _last_llm_call_time
    
    if time_since_last_call < rate_limit_delay:
        wait_time = rate_limit_delay - time_since_last_call
        logger.info(f"同步速率限制: 等待 {wait_time:.2f} 秒后继续")
        time.sleep(wait_time)
    
    _last_llm_call_time = time.time()


def _run_in_thread(async_func: Callable, *args, **kwargs) -> Any:
    """
    在新线程中运行异步函数
    
    Args:
        async_func: 异步函数
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        函数执行结果
    """
    result = None
    exception = None
    
    def thread_target():
        nonlocal result, exception
        try:
            # 在新线程中创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(async_func(*args, **kwargs))
            finally:
                loop.close()
        except Exception as e:
            exception = e
    
    # 创建并启动线程
    thread = threading.Thread(target=thread_target)
    thread.start()
    thread.join()
    
    # 检查是否有异常
    if exception:
        raise exception
    
    return result


class SyncLLMClient:
    """同步LLM客户端包装器"""
    
    def __init__(self, llm_client):
        """
        初始化同步LLM客户端
        
        Args:
            llm_client: 异步LLM客户端实例
        """
        self.llm_client = llm_client
    
    def generate(self, *args, **kwargs) -> str:
        """同步生成文本"""
        return sync_llm_call(self.llm_client.generate, *args, **kwargs)
    
    def test_providers(self) -> dict:
        """同步测试提供商"""
        return sync_llm_call(self.llm_client.test_providers)
    
    def get_available_providers(self) -> list:
        """同步获取可用提供商"""
        return sync_llm_call(self.llm_client.get_available_providers)


def make_sync(async_obj):
    """
    将异步对象的方法转换为同步方法
    
    Args:
        async_obj: 异步对象实例
        
    Returns:
        包装后的同步对象
    """
    class SyncWrapper:
        def __init__(self, obj):
            self._obj = obj
        
        def __getattr__(self, name):
            attr = getattr(self._obj, name)
            if asyncio.iscoroutinefunction(attr):
                def sync_method(*args, **kwargs):
                    return sync_llm_call(attr, *args, **kwargs)
                return sync_method
            else:
                return attr
    
    return SyncWrapper(async_obj)


# 便捷函数
def run_sync(coro, timeout=None):
    """
    运行协程并返回结果（同步方式）
    
    Args:
        coro: 协程对象
        timeout: 超时时间（秒）
        
    Returns:
        协程执行结果
    """
    try:
        # 尝试获取当前事件循环
        loop = asyncio.get_running_loop()
        # 在事件循环中，使用线程池
        return _run_coro_in_thread(coro, timeout)
    except RuntimeError:
        # 没有运行的事件循环，直接运行
        if timeout:
            return asyncio.wait_for(coro, timeout=timeout)
        else:
            return asyncio.run(coro)


def _run_coro_in_thread(coro, timeout=None):
    """在新线程中运行协程"""
    result = None
    exception = None
    
    def thread_target():
        nonlocal result, exception
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                if timeout:
                    result = loop.run_until_complete(
                        asyncio.wait_for(coro, timeout=timeout)
                    )
                else:
                    result = loop.run_until_complete(coro)
            finally:
                loop.close()
        except Exception as e:
            exception = e
    
    thread = threading.Thread(target=thread_target)
    thread.start()
    thread.join()
    
    if exception:
        raise exception
    
    return result