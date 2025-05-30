"""导出功能路由."""

import io
import zipfile
from datetime import datetime
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from src.utils.logger import get_logger
from src.models.database import get_db_session
from src.models.novel_models import NovelProject, Chapter, Character

logger = get_logger(__name__)

router = APIRouter()


@router.get("/projects/{project_id}/export")
async def export_project(
    project_id: int,
    format: str = Query("txt", description="导出格式: txt, docx, pdf, json"),
    include_metadata: bool = Query(True, description="是否包含元数据"),
    include_characters: bool = Query(True, description="是否包含角色信息"),
) -> StreamingResponse:
    """导出项目内容."""
    
    try:
        async with get_db_session() as session:
            # 检查项目是否存在
            project = await session.get(NovelProject, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            # 获取章节数据
            chapter_query = select(Chapter).where(
                Chapter.project_id == project_id
            ).order_by(Chapter.chapter_number)
            chapter_result = await session.execute(chapter_query)
            chapters = chapter_result.scalars().all()
            
            # 获取角色数据
            characters = []
            if include_characters:
                character_query = select(Character).where(
                    Character.project_id == project_id
                ).order_by(Character.importance.desc(), Character.name)
                character_result = await session.execute(character_query)
                characters = character_result.scalars().all()
            
            # 根据格式生成内容
            if format.lower() == "txt":
                content, content_type, filename = _export_as_txt(
                    project, chapters, characters, include_metadata
                )
            elif format.lower() == "json":
                content, content_type, filename = _export_as_json(
                    project, chapters, characters, include_metadata
                )
            elif format.lower() == "zip":
                content, content_type, filename = _export_as_zip(
                    project, chapters, characters, include_metadata
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的导出格式: {format}"
                )
            
            logger.info(f"项目导出完成: project_id={project_id}, format={format}")
            
            # 使用RFC5987标准编码文件名
            encoded_filename = quote(filename.encode('utf-8'))
            return StreamingResponse(
                io.BytesIO(content),
                media_type=content_type,
                headers={
                    "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出项目失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"导出失败: {str(e)}"
        )


@router.get("/projects/{project_id}/chapters/{chapter_id}/export")
async def export_chapter(
    project_id: int,
    chapter_id: int,
    format: str = Query("txt", description="导出格式: txt, json"),
) -> StreamingResponse:
    """导出单个章节."""
    
    try:
        async with get_db_session() as session:
            # 检查项目和章节
            project = await session.get(NovelProject, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            chapter = await session.get(Chapter, chapter_id)
            if not chapter or chapter.project_id != project_id:
                raise HTTPException(status_code=404, detail="章节未找到")
            
            # 生成内容
            if format.lower() == "txt":
                content = _format_chapter_as_txt(chapter)
                content_type = "text/plain; charset=utf-8"
                filename = f"chapter_{chapter.chapter_number}_{chapter.title}.txt"
            elif format.lower() == "json":
                import json
                content = json.dumps({
                    "id": chapter.id,
                    "chapter_number": chapter.chapter_number,
                    "title": chapter.title,
                    "content": chapter.content,
                    "word_count": chapter.word_count,
                    "status": chapter.status,
                    "created_at": chapter.created_at.isoformat() if chapter.created_at else None,
                    "updated_at": chapter.updated_at.isoformat() if chapter.updated_at else None,
                }, ensure_ascii=False, indent=2).encode('utf-8')
                content_type = "application/json"
                filename = f"chapter_{chapter.chapter_number}.json"
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的导出格式: {format}"
                )
            
            # 使用RFC5987标准编码文件名
            encoded_filename = quote(filename.encode('utf-8'))
            return StreamingResponse(
                io.BytesIO(content),
                media_type=content_type,
                headers={
                    "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出章节失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"导出章节失败: {str(e)}"
        )


def _export_as_txt(
    project,
    chapters,
    characters,
    include_metadata: bool
) -> tuple[bytes, str, str]:
    """导出为TXT格式."""
    
    lines = []
    
    # 标题
    lines.append(f"《{project.title}》")
    lines.append("=" * 50)
    lines.append("")
    
    # 元数据
    if include_metadata:
        lines.append("项目信息")
        lines.append("-" * 20)
        if project.description:
            lines.append(f"描述: {project.description}")
        lines.append(f"目标字数: {project.target_words}")
        lines.append(f"当前字数: {project.current_words or 0}")
        if project.style_preference:
            lines.append(f"风格: {project.style_preference}")
        lines.append(f"状态: {project.status}")
        lines.append(f"创建时间: {project.created_at}")
        lines.append("")
    
    # 角色信息
    if characters:
        lines.append("角色信息")
        lines.append("-" * 20)
        for character in characters:
            lines.append(f"【{character.name}】")
            if character.description:
                lines.append(f"  {character.description}")
            lines.append(f"  重要性: {character.importance}")
            lines.append("")
    
    # 正文内容
    if chapters:
        lines.append("正文内容")
        lines.append("=" * 50)
        lines.append("")
        
        logger.info(f"导出章节数量: {len(chapters)}")
        for chapter in chapters:
            logger.info(f"导出章节: 第{chapter.chapter_number}章 {chapter.title}, 内容长度: {len(chapter.content) if chapter.content else 0}")
            lines.append(f"第{chapter.chapter_number}章 {chapter.title}")
            lines.append("-" * 30)
            if chapter.content:
                lines.append(chapter.content)
            else:
                lines.append("（此章节暂无内容）")
                logger.warning(f"章节 {chapter.title} 内容为空")
            lines.append("")
            lines.append("")
    else:
        logger.warning("没有找到任何章节数据用于导出")
        lines.append("正文内容")
        lines.append("=" * 50)
        lines.append("")
        lines.append("（暂无章节内容）")
    
    content = "\n".join(lines).encode('utf-8')
    # 清理文件名中的特殊字符
    safe_title = "".join(c for c in project.title if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_title:
        safe_title = "novel"
    filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    return content, "text/plain; charset=utf-8", filename


def _export_as_json(
    project,
    chapters,
    characters,
    include_metadata: bool
) -> tuple[bytes, str, str]:
    """导出为JSON格式."""
    
    import json
    
    data = {
        "project": {
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "target_words": project.target_words,
            "current_words": project.current_words,
            "style_preference": project.style_preference,
            "status": project.status,
            "progress": project.progress,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        }
    }
    
    if include_metadata:
        data["export_info"] = {
            "exported_at": datetime.utcnow().isoformat(),
            "export_format": "json",
            "version": "1.0.0",
        }
    
    # 角色数据
    if characters:
        data["characters"] = [
            {
                "id": char.id,
                "name": char.name,
                "description": char.description,
                "importance": char.importance,
                "profile": char.profile,
                "created_at": char.created_at.isoformat() if char.created_at else None,
                "updated_at": char.updated_at.isoformat() if char.updated_at else None,
            }
            for char in characters
        ]
    
    # 章节数据
    if chapters:
        data["chapters"] = [
            {
                "id": chapter.id,
                "chapter_number": chapter.chapter_number,
                "title": chapter.title,
                "content": chapter.content,
                "word_count": chapter.word_count,
                "status": chapter.status,
                "created_at": chapter.created_at.isoformat() if chapter.created_at else None,
                "updated_at": chapter.updated_at.isoformat() if chapter.updated_at else None,
            }
            for chapter in chapters
        ]
    
    content = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
    # 清理文件名中的特殊字符
    safe_title = "".join(c for c in project.title if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_title:
        safe_title = "novel"
    filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    return content, "application/json", filename


def _export_as_zip(
    project,
    chapters,
    characters,
    include_metadata: bool
) -> tuple[bytes, str, str]:
    """导出为ZIP格式（包含多个文件）."""
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 添加项目信息文件
        if include_metadata:
            project_info = [
                f"项目名称: {project.title}",
                f"描述: {project.description or '无'}",
                f"目标字数: {project.target_words}",
                f"当前字数: {project.current_words or 0}",
                f"风格: {project.style_preference or '无'}",
                f"状态: {project.status}",
                f"创建时间: {project.created_at}",
                f"导出时间: {datetime.utcnow()}",
            ]
            zip_file.writestr("project_info.txt", "\n".join(project_info).encode('utf-8'))
        
        # 添加角色文件
        if characters:
            character_content = []
            for char in characters:
                character_content.append(f"【{char.name}】")
                character_content.append(f"重要性: {char.importance}")
                if char.description:
                    character_content.append(f"描述: {char.description}")
                if char.profile:
                    character_content.append(f"档案: {char.profile}")
                character_content.append("")
            
            zip_file.writestr("characters.txt", "\n".join(character_content).encode('utf-8'))
        
        # 添加章节文件
        if chapters:
            # 完整小说文件
            full_content = _export_as_txt(project, chapters, [], False)[0]
            zip_file.writestr("full_novel.txt", full_content)
            
            # 单独的章节文件
            for chapter in chapters:
                chapter_content = _format_chapter_as_txt(chapter)
                filename = f"chapters/chapter_{chapter.chapter_number:02d}_{chapter.title}.txt"
                zip_file.writestr(filename, chapter_content)
        
        # 添加JSON格式的完整数据
        json_content = _export_as_json(project, chapters, characters, include_metadata)[0]
        zip_file.writestr("full_data.json", json_content)
    
    zip_buffer.seek(0)
    content = zip_buffer.read()
    # 清理文件名中的特殊字符
    safe_title = "".join(c for c in project.title if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_title:
        safe_title = "novel"
    filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    
    return content, "application/zip", filename


def _format_chapter_as_txt(chapter) -> bytes:
    """格式化章节为TXT."""
    
    lines = []
    lines.append(f"第{chapter.chapter_number}章 {chapter.title}")
    lines.append("=" * 50)
    lines.append("")
    
    if chapter.content:
        lines.append(chapter.content)
    else:
        lines.append("（此章节暂无内容）")
    
    lines.append("")
    lines.append(f"字数: {chapter.word_count or 0}")
    lines.append(f"状态: {chapter.status}")
    
    return "\n".join(lines).encode('utf-8')


@router.get("/projects/{project_id}/content")
async def get_project_content(
    project_id: int,
    format: str = Query("txt", description="内容格式"),
) -> Response:
    """获取项目内容（预览模式，不下载）."""
    
    try:
        async with get_db_session() as session:
            project = await session.get(NovelProject, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            # 获取章节
            chapter_query = select(Chapter).where(
                Chapter.project_id == project_id
            ).order_by(Chapter.chapter_number)
            chapter_result = await session.execute(chapter_query)
            chapters = chapter_result.scalars().all()
            
            if format.lower() == "txt":
                content, content_type, _ = _export_as_txt(project, chapters, [], False)
                return Response(content=content, media_type=content_type)
            elif format.lower() == "json":
                content, content_type, _ = _export_as_json(project, chapters, [], False)
                return Response(content=content, media_type=content_type)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的格式: {format}"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目内容失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取内容失败: {str(e)}"
        )