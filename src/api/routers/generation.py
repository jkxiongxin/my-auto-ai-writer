"""小说生成路由."""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from src.utils.logger import get_logger
from src.utils.llm_client import UniversalLLMClient
from src.models.database import get_db_session
from src.models.novel_models import NovelProject, GenerationTask
from ..dependencies import get_llm_client, validate_generation_request
from ..schemas import (
    CreateNovelProjectRequest,
    NovelProjectResponse,
    GenerationStatusResponse,
    GenerationResultResponse,
)

logger = get_logger(__name__)

router = APIRouter()


@router.post("/generate-novel", response_model=NovelProjectResponse, status_code=202)
async def start_novel_generation(
    request: CreateNovelProjectRequest,
    background_tasks: BackgroundTasks,
    llm_client: UniversalLLMClient = Depends(get_llm_client),
    _: None = Depends(validate_generation_request),
) -> NovelProjectResponse:
    """启动小说生成任务."""
    
    try:
        # 验证请求数据
        from ..dependencies import validate_request_data
        await validate_request_data(request)
        
        # 创建项目记录
        async with get_db_session() as session:
            project = NovelProject(
                title=request.title,
                description=request.description,
                user_input=request.user_input,
                target_words=request.target_words,
                style_preference=request.style_preference,
                status="queued",
                progress=0.0,
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            
            project_id = project.id
        
        # 创建生成任务
        task_id = str(uuid.uuid4())
        
        async with get_db_session() as session:
            generation_task = GenerationTask(
                id=task_id,
                project_id=project_id,
                status="queued",
                progress=0.0,
                created_at=datetime.utcnow(),
            )
            session.add(generation_task)
            await session.commit()
        
        # 启动后台生成任务
        background_tasks.add_task(
            _generate_novel_background,
            project_id=project_id,
            task_id=task_id,
            llm_client=llm_client,
        )
        
        logger.info(f"小说生成任务已启动: project_id={project_id}, task_id={task_id}")
        
        return NovelProjectResponse(
            id=project_id,
            title=request.title,
            description=request.description,
            target_words=request.target_words,
            status="queued",
            progress=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            task_id=task_id,
        )
        
    except Exception as e:
        logger.error(f"启动小说生成失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"启动生成任务失败: {str(e)}"
        )


@router.get("/generate-novel/{task_id}/status", response_model=GenerationStatusResponse)
async def get_generation_status(task_id: str) -> GenerationStatusResponse:
    """获取生成任务状态."""
    
    try:
        async with get_db_session() as session:
            # 查询生成任务
            task = await session.get(GenerationTask, task_id)
            if not task:
                raise HTTPException(status_code=404, detail="生成任务未找到")
            
            # 查询项目信息
            project = await session.get(NovelProject, task.project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
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
        logger.error(f"获取生成状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取状态失败: {str(e)}"
        )


@router.get("/generate-novel/{task_id}/result", response_model=GenerationResultResponse)
async def get_generation_result(task_id: str) -> GenerationResultResponse:
    """获取生成结果."""
    
    try:
        async with get_db_session() as session:
            # 查询生成任务
            task = await session.get(GenerationTask, task_id)
            if not task:
                raise HTTPException(status_code=404, detail="生成任务未找到")
            
            if task.status != "completed":
                raise HTTPException(
                    status_code=400,
                    detail=f"任务尚未完成，当前状态: {task.status}"
                )
            
            # 查询项目和相关数据
            project = await session.get(NovelProject, task.project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            # 查询章节数量
            from sqlalchemy import select, func
            from src.models.novel_models import Chapter
            
            # 统计该项目的章节数量
            chapter_count_query = select(func.count(Chapter.id)).where(Chapter.project_id == task.project_id)
            chapter_count_result = await session.execute(chapter_count_query)
            actual_chapter_count = chapter_count_result.scalar() or 0
            
            return GenerationResultResponse(
                task_id=task_id,
                project_id=task.project_id,
                status=task.status,
                title=project.title,
                total_words=project.current_words or 0,
                chapter_count=actual_chapter_count,
                quality_score=task.quality_score,
                generation_time_seconds=task.generation_time_seconds,
                completed_at=task.completed_at,
                result_data=task.result_data or {},
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取生成结果失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取结果失败: {str(e)}"
        )


@router.delete("/generate-novel/{task_id}")
async def cancel_generation(task_id: str) -> Dict[str, str]:
    """取消生成任务."""
    
    try:
        async with get_db_session() as session:
            task = await session.get(GenerationTask, task_id)
            if not task:
                raise HTTPException(status_code=404, detail="生成任务未找到")
            
            if task.status in ["completed", "cancelled", "failed"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"任务已结束，无法取消，当前状态: {task.status}"
                )
            
            # 更新任务状态
            task.status = "cancelled"
            task.updated_at = datetime.utcnow()
            await session.commit()
            
            logger.info(f"生成任务已取消: task_id={task_id}")
            
            return {"message": "生成任务已取消", "task_id": task_id}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消生成任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"取消任务失败: {str(e)}"
        )


async def _generate_novel_background(
    project_id: int,
    task_id: str,
    llm_client: UniversalLLMClient,
) -> None:
    """后台小说生成任务 - 使用异步NovelGenerator."""
    
    start_time = datetime.utcnow()
    
    try:
        # 获取项目信息
        async with get_db_session() as session:
            project = await session.get(NovelProject, project_id)
            if not project:
                logger.error(f"项目未找到: project_id={project_id}")
                return
                
            # 更新任务状态为进行中
            task = await session.get(GenerationTask, task_id)
            task.status = "running"
            task.current_step = "初始化"
            task.updated_at = datetime.utcnow()
            await session.commit()
        
        logger.info(f"开始生成小说(异步模式): project_id={project_id}, title={project.title}")
        
        # 导入并创建异步小说生成器
        from src.core.novel_generator import NovelGenerator
        
        # 创建进度更新回调函数
        async def update_progress(step: str, progress: float):
            async with get_db_session() as session:
                task = await session.get(GenerationTask, task_id)
                if task.status == "cancelled":
                    raise asyncio.CancelledError("任务已被取消")
                
                task.current_step = step
                task.progress = progress / 100.0
                task.updated_at = datetime.utcnow()
                await session.commit()
                logger.info(f"生成进度: {step} ({progress:.1f}%)")
        
        # 创建小说生成器实例 - 确保使用配置中的PRIMARY_LLM_PROVIDER，并传递进度回调
        generator = NovelGenerator(llm_client, progress_callback=update_progress)
        
        # 调用实际的小说生成逻辑（不需要手动调用update_progress，generator内部会调用）
        novel_result = await generator.generate_novel(
            user_input=project.user_input,
            target_words=project.target_words,
            style_preference=project.style_preference
        )
        
        await update_progress("保存结果", 95)
        
        # 保存生成的章节到数据库
        from src.models.novel_models import Chapter, Character
        total_words = 0
        chapter_count = 0
        
        async with get_db_session() as session:
            logger.info(f"开始保存生成结果，novel_result keys: {list(novel_result.keys())}")
            
            # 保存角色信息
            if 'characters' in novel_result:
                characters_data = novel_result['characters']
                logger.info(f"保存角色信息，类型: {type(characters_data)}")
                
                # 处理不同的角色数据格式
                if isinstance(characters_data, dict):
                    # 如果是字典格式
                    if hasattr(characters_data, 'characters'):
                        # CharacterDatabase对象
                        char_dict = characters_data.characters
                    else:
                        # 普通字典
                        char_dict = characters_data
                    
                    for char_name, char_data in char_dict.items():
                        if hasattr(char_data, 'name'):
                            # Character对象
                            character = Character(
                                project_id=project_id,
                                name=char_data.name,
                                description=char_data.description or '',
                                importance=getattr(char_data, 'importance', 5),
                                profile=f"角色: {char_data.name}, 职业: {getattr(char_data, 'role', '未知')}, 动机: {getattr(char_data, 'motivation', '未知')}"
                            )
                        else:
                            # 字典格式
                            character = Character(
                                project_id=project_id,
                                name=char_name,
                                description=char_data.get('description', ''),
                                importance=char_data.get('importance', 5),
                                profile=str(char_data)
                            )
                        session.add(character)
                        logger.info(f"保存角色: {character.name}")
            
            # 保存章节内容
            if 'chapters' in novel_result:
                chapters_data = novel_result['chapters']
                logger.info(f"保存章节信息，章节数: {len(chapters_data)}, 类型: {type(chapters_data)}")
                
                for i, chapter_data in enumerate(chapters_data):
                    # 处理不同的章节数据格式
                    if hasattr(chapter_data, 'title'):
                        # ChapterContent对象
                        chapter = Chapter(
                            project_id=project_id,
                            chapter_number=i + 1,
                            title=chapter_data.title,
                            content=chapter_data.content,
                            word_count=chapter_data.word_count,
                            status='completed'
                        )
                        total_words += chapter_data.word_count
                    else:
                        # 字典格式
                        chapter = Chapter(
                            project_id=project_id,
                            chapter_number=i + 1,
                            title=chapter_data.get('title', f'第{i+1}章'),
                            content=chapter_data.get('content', ''),
                            word_count=chapter_data.get('word_count', 0),
                            status='completed'
                        )
                        total_words += chapter_data.get('word_count', 0)
                    
                    session.add(chapter)
                    chapter_count += 1
                    logger.info(f"保存章节: {chapter.title}, 字数: {chapter.word_count}")
            
            logger.info(f"提交数据库事务，总章节数: {chapter_count}, 总字数: {total_words}")
            await session.commit()
            logger.info("数据库事务提交成功")
        
        # 完成生成
        end_time = datetime.utcnow()
        generation_time = (end_time - start_time).total_seconds()
        
        # 获取质量评估结果
        quality_assessment = novel_result.get('quality_assessment', {})
        overall_score = quality_assessment.get('overall_scores', {}).get('overall', 8.0)
        
        async with get_db_session() as session:
            task = await session.get(GenerationTask, task_id)
            task.status = "completed"
            task.progress = 1.0
            task.current_step = "已完成"
            task.completed_at = end_time
            task.generation_time_seconds = generation_time
            task.quality_score = overall_score
            task.result_data = {
                "章节数": chapter_count,
                "总字数": total_words,
                "质量评分": overall_score,
                "概念扩展": "已完成",
                "大纲生成": "已完成",
                "角色创建": "已完成",
                "章节生成": "已完成",
                "质量评估": "已完成"
            }
            await session.commit()
            
            # 更新项目状态
            project = await session.get(NovelProject, project_id)
            project.status = "completed"
            project.progress = 1.0
            project.current_words = total_words
            project.updated_at = end_time
            await session.commit()
        
        logger.info(f"小说生成完成: project_id={project_id}, 章节数={chapter_count}, 总字数={total_words}, 耗时={generation_time:.2f}秒")
        
    except Exception as e:
        logger.error(f"生成小说时发生错误: {e}", exc_info=True)
        
        # 更新任务状态为失败
        try:
            async with get_db_session() as session:
                task = await session.get(GenerationTask, task_id)
                task.status = "failed"
                task.error_message = str(e)
                task.updated_at = datetime.utcnow()
                await session.commit()
                
                # 更新项目状态
                project = await session.get(NovelProject, project_id)
                project.status = "failed"
                project.updated_at = datetime.utcnow()
                await session.commit()
        except Exception as db_error:
            logger.error(f"更新失败状态时发生错误: {db_error}")