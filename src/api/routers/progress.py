"""进度追踪路由."""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from src.utils.logger import get_logger
from src.models.database import get_db_session
from src.models.novel_models import GenerationTask
from ..schemas import GenerationStatusResponse

logger = get_logger(__name__)

router = APIRouter()


class ProgressUpdate(BaseModel):
    """进度更新模型."""
    task_id: str
    progress: float
    current_step: str
    message: Optional[str] = None


class ConnectionManager:
    """WebSocket连接管理器."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """接受新连接."""
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)
        logger.info(f"新WebSocket连接: task_id={task_id}")
    
    def disconnect(self, websocket: WebSocket, task_id: str):
        """断开连接."""
        if task_id in self.active_connections:
            self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
        logger.info(f"WebSocket连接断开: task_id={task_id}")
    
    async def send_progress_update(self, task_id: str, data: dict):
        """发送进度更新."""
        if task_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(data)
                except Exception as e:
                    logger.error(f"发送WebSocket消息失败: {e}")
                    dead_connections.append(connection)
            
            # 清理死连接
            for dead_connection in dead_connections:
                self.disconnect(dead_connection, task_id)


# 全局连接管理器
manager = ConnectionManager()


@router.websocket("/ws/progress/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str):
    """WebSocket进度实时推送."""
    await manager.connect(websocket, task_id)
    
    try:
        # 发送当前状态
        async with get_db_session() as session:
            task = await session.get(GenerationTask, task_id)
            if task:
                await websocket.send_json({
                    "type": "status",
                    "task_id": task_id,
                    "status": task.status,
                    "progress": task.progress,
                    "current_step": task.current_step,
                    "updated_at": task.updated_at.isoformat() if task.updated_at else None
                })
        
        # 保持连接活跃
        while True:
            try:
                # 等待客户端消息（心跳包）
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket处理消息失败: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, task_id)


@router.post("/progress/{task_id}/update")
async def update_progress(task_id: str, update: ProgressUpdate) -> Dict[str, str]:
    """更新任务进度（内部API）."""
    
    try:
        async with get_db_session() as session:
            task = await session.get(GenerationTask, task_id)
            if not task:
                raise HTTPException(status_code=404, detail="任务未找到")
            
            # 更新进度
            task.progress = update.progress
            task.current_step = update.current_step
            await session.commit()
            
            # 通过WebSocket推送更新
            await manager.send_progress_update(task_id, {
                "type": "progress",
                "task_id": task_id,
                "progress": update.progress,
                "current_step": update.current_step,
                "message": update.message
            })
            
            logger.info(f"进度更新: {task_id} - {update.current_step} ({update.progress*100:.1f}%)")
            
            return {"message": "进度更新成功"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新进度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新进度失败: {str(e)}")


@router.get("/progress/{task_id}/status", response_model=GenerationStatusResponse)
async def get_task_status(task_id: str) -> GenerationStatusResponse:
    """获取任务状态（REST API）."""
    
    try:
        async with get_db_session() as session:
            task = await session.get(GenerationTask, task_id)
            if not task:
                raise HTTPException(status_code=404, detail="任务未找到")
            
            return GenerationStatusResponse(
                task_id=task_id,
                project_id=task.project_id,
                status=task.status,
                progress=task.progress,
                current_step=task.current_step,
                estimated_completion=task.estimated_completion,
                error_message=task.error_message,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.get("/progress/active")
async def get_active_tasks() -> Dict[str, List[str]]:
    """获取活跃任务列表."""
    
    try:
        async with get_db_session() as session:
            from sqlalchemy import select
            
            # 查询运行中的任务
            result = await session.execute(
                select(GenerationTask.id)
                .where(GenerationTask.status.in_(["queued", "running"]))
            )
            active_task_ids = [row[0] for row in result.fetchall()]
            
            # 获取有WebSocket连接的任务
            connected_task_ids = list(manager.active_connections.keys())
            
            return {
                "active_tasks": active_task_ids,
                "connected_tasks": connected_task_ids,
                "total_active": len(active_task_ids),
                "total_connected": len(connected_task_ids)
            }
            
    except Exception as e:
        logger.error(f"获取活跃任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取活跃任务失败: {str(e)}")


# 提供给生成器使用的进度更新函数
async def notify_progress(task_id: str, progress: float, step: str, message: str = None):
    """通知进度更新（供后台任务调用）."""
    try:
        await manager.send_progress_update(task_id, {
            "type": "progress",
            "task_id": task_id,
            "progress": progress,
            "current_step": step,
            "message": message,
            "timestamp": str(datetime.utcnow())
        })
        
        # 同时更新数据库
        async with get_db_session() as session:
            task = await session.get(GenerationTask, task_id)
            if task:
                task.progress = progress
                task.current_step = step
                await session.commit()
                
    except Exception as e:
        logger.error(f"通知进度更新失败: {e}")


# 导出进度管理器供其他模块使用
__all__ = ["router", "manager", "notify_progress"]