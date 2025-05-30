"""项目管理路由."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.utils.logger import get_logger
from src.models.database import get_db_session
from src.models.novel_models import NovelProject, Chapter, Character
from ..dependencies import get_current_user
from ..schemas import (
    NovelProjectResponse,
    ProjectListResponse,
    UpdateProjectRequest,
    ProjectStatisticsResponse,
    ChapterResponse,
    CharacterResponse,
)

logger = get_logger(__name__)

router = APIRouter()


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    skip: int = Query(0, ge=0, description="跳过的项目数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回的项目数量"),
    status: Optional[str] = Query(None, description="项目状态过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    # current_user = Depends(get_current_user),  # 暂时注释掉用户认证
) -> ProjectListResponse:
    """获取项目列表."""
    
    try:
        async with get_db_session() as session:
            # 构建查询
            query = select(NovelProject)
            
            # 状态过滤
            if status:
                query = query.where(NovelProject.status == status)
            
            # 搜索过滤
            if search:
                search_pattern = f"%{search}%"
                query = query.where(
                    (NovelProject.title.ilike(search_pattern)) |
                    (NovelProject.description.ilike(search_pattern)) |
                    (NovelProject.user_input.ilike(search_pattern))
                )
            
            # 计算总数
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total = total_result.scalar()
            
            # 分页和排序
            query = query.order_by(NovelProject.updated_at.desc())
            query = query.offset(skip).limit(limit)
            
            # 执行查询
            result = await session.execute(query)
            projects = result.scalars().all()
            
            # 转换为响应模型
            project_responses = [
                NovelProjectResponse(
                    id=project.id,
                    title=project.title,
                    description=project.description,
                    target_words=project.target_words,
                    status=project.status,
                    progress=project.progress,
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                )
                for project in projects
            ]
            
            return ProjectListResponse(
                projects=project_responses,
                total=total,
                skip=skip,
                limit=limit,
            )
            
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取项目列表失败: {str(e)}"
        )


@router.get("/projects/{project_id}", response_model=NovelProjectResponse)
async def get_project(
    project_id: int,
    # current_user = Depends(get_current_user),  # 暂时注释掉用户认证
) -> NovelProjectResponse:
    """获取指定项目详情."""
    
    try:
        async with get_db_session() as session:
            project = await session.get(NovelProject, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            return NovelProjectResponse(
                id=project.id,
                title=project.title,
                description=project.description,
                target_words=project.target_words,
                status=project.status,
                progress=project.progress,
                created_at=project.created_at,
                updated_at=project.updated_at,
                current_words=project.current_words,
                style_preference=project.style_preference,
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取项目详情失败: {str(e)}"
        )


@router.put("/projects/{project_id}", response_model=NovelProjectResponse)
async def update_project(
    project_id: int,
    request: UpdateProjectRequest,
    # current_user = Depends(get_current_user),  # 暂时注释掉用户认证
) -> NovelProjectResponse:
    """更新项目信息."""
    
    try:
        async with get_db_session() as session:
            project = await session.get(NovelProject, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            # 更新字段
            if request.title is not None:
                project.title = request.title
            if request.description is not None:
                project.description = request.description
            if request.target_words is not None:
                project.target_words = request.target_words
            if request.style_preference is not None:
                project.style_preference = request.style_preference
            
            project.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(project)
            
            return NovelProjectResponse(
                id=project.id,
                title=project.title,
                description=project.description,
                target_words=project.target_words,
                status=project.status,
                progress=project.progress,
                created_at=project.created_at,
                updated_at=project.updated_at,
                current_words=project.current_words,
                style_preference=project.style_preference,
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新项目失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"更新项目失败: {str(e)}"
        )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    # current_user = Depends(get_current_user),  # 暂时注释掉用户认证
) -> dict:
    """删除项目."""
    
    try:
        async with get_db_session() as session:
            project = await session.get(NovelProject, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            # 检查项目状态 - 只禁止删除正在运行的项目
            if project.status == "running":
                raise HTTPException(
                    status_code=400,
                    detail="无法删除正在运行的项目，请先停止生成任务"
                )
            
            await session.delete(project)
            await session.commit()
            
            logger.info(f"项目已删除: project_id={project_id}")
            
            return {"message": "项目已删除", "project_id": project_id}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除项目失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"删除项目失败: {str(e)}"
        )


@router.get("/projects/{project_id}/statistics", response_model=ProjectStatisticsResponse)
async def get_project_statistics(
    project_id: int,
    # current_user = Depends(get_current_user),  # 暂时注释掉用户认证
) -> ProjectStatisticsResponse:
    """获取项目统计信息."""
    
    try:
        async with get_db_session() as session:
            project = await session.get(NovelProject, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            # 查询章节统计
            chapter_query = select(func.count(), func.sum(Chapter.word_count)).where(
                Chapter.project_id == project_id
            )
            chapter_result = await session.execute(chapter_query)
            chapter_count, total_words = chapter_result.one()
            
            # 查询角色统计
            character_query = select(func.count()).where(
                Character.project_id == project_id
            )
            character_result = await session.execute(character_query)
            character_count = character_result.scalar()
            
            # 计算进度统计
            progress_percentage = round(project.progress * 100, 2)
            word_progress = round((total_words or 0) / project.target_words * 100, 2) if project.target_words > 0 else 0
            
            return ProjectStatisticsResponse(
                project_id=project_id,
                chapter_count=chapter_count or 0,
                character_count=character_count or 0,
                total_words=total_words or 0,
                target_words=project.target_words,
                progress_percentage=progress_percentage,
                word_progress_percentage=word_progress,
                status=project.status,
                created_at=project.created_at,
                last_updated=project.updated_at,
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目统计失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取项目统计失败: {str(e)}"
        )


@router.get("/projects/{project_id}/chapters", response_model=List[ChapterResponse])
async def get_project_chapters(
    project_id: int,
    # current_user = Depends(get_current_user),  # 暂时注释掉用户认证
) -> List[ChapterResponse]:
    """获取项目的章节列表."""
    
    try:
        async with get_db_session() as session:
            # 检查项目是否存在
            project = await session.get(NovelProject, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            # 查询章节
            query = select(Chapter).where(
                Chapter.project_id == project_id
            ).order_by(Chapter.chapter_number)
            
            result = await session.execute(query)
            chapters = result.scalars().all()
            
            return [
                ChapterResponse(
                    id=chapter.id,
                    project_id=chapter.project_id,
                    chapter_number=chapter.chapter_number,
                    title=chapter.title,
                    word_count=chapter.word_count,
                    status=chapter.status,
                    created_at=chapter.created_at,
                    updated_at=chapter.updated_at,
                )
                for chapter in chapters
            ]
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目章节失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取项目章节失败: {str(e)}"
        )


@router.get("/projects/{project_id}/characters", response_model=List[CharacterResponse])
async def get_project_characters(
    project_id: int,
    # current_user = Depends(get_current_user),  # 暂时注释掉用户认证
) -> List[CharacterResponse]:
    """获取项目的角色列表."""
    
    try:
        async with get_db_session() as session:
            # 检查项目是否存在
            project = await session.get(NovelProject, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            # 查询角色
            query = select(Character).where(
                Character.project_id == project_id
            ).order_by(Character.importance.desc(), Character.name)
            
            result = await session.execute(query)
            characters = result.scalars().all()
            
            return [
                CharacterResponse(
                    id=character.id,
                    project_id=character.project_id,
                    name=character.name,
                    importance=character.importance,
                    description=character.description,
                    created_at=character.created_at,
                    updated_at=character.updated_at,
                )
                for character in characters
            ]
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目角色失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取项目角色失败: {str(e)}"
        )