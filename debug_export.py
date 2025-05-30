#!/usr/bin/env python3
"""调试导出内容为空的问题."""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

async def check_database_content():
    """检查数据库中的内容."""
    
    print("🔍 调试数据库内容")
    print("="*60)
    
    try:
        from src.models.database import get_db_session
        from src.models.novel_models import NovelProject, Chapter, Character, GenerationTask
        from sqlalchemy import select
        
        async with get_db_session() as session:
            # 1. 检查项目
            project_query = select(NovelProject).order_by(NovelProject.created_at.desc()).limit(5)
            project_result = await session.execute(project_query)
            projects = project_result.scalars().all()
            
            print(f"📚 最近的5个项目:")
            for i, project in enumerate(projects):
                print(f"  {i+1}. ID={project.id}, 标题='{project.title}', 状态={project.status}")
                print(f"      目标字数={project.target_words}, 当前字数={project.current_words}")
                print(f"      创建时间={project.created_at}")
                print()
            
            if not projects:
                print("  ❌ 没有找到任何项目")
                return
            
            # 选择最新的项目进行详细检查
            latest_project = projects[0]
            project_id = latest_project.id
            
            print(f"🔍 详细检查项目 ID={project_id}")
            print("-" * 40)
            
            # 2. 检查章节
            chapter_query = select(Chapter).where(
                Chapter.project_id == project_id
            ).order_by(Chapter.chapter_number)
            chapter_result = await session.execute(chapter_query)
            chapters = chapter_result.scalars().all()
            
            print(f"📖 项目章节 (共 {len(chapters)} 章):")
            if chapters:
                for chapter in chapters:
                    content_preview = (chapter.content[:50] + "...") if chapter.content and len(chapter.content) > 50 else (chapter.content or "无内容")
                    print(f"  第{chapter.chapter_number}章: {chapter.title}")
                    print(f"    字数: {chapter.word_count}, 状态: {chapter.status}")
                    print(f"    内容预览: {content_preview}")
                    print(f"    内容长度: {len(chapter.content) if chapter.content else 0}")
                    print()
            else:
                print("  ❌ 没有找到任何章节")
            
            # 3. 检查角色
            character_query = select(Character).where(
                Character.project_id == project_id
            ).order_by(Character.importance.desc())
            character_result = await session.execute(character_query)
            characters = character_result.scalars().all()
            
            print(f"👥 项目角色 (共 {len(characters)} 个):")
            if characters:
                for character in characters:
                    print(f"  {character.name}: 重要性={character.importance}")
                    print(f"    描述: {character.description}")
                    print()
            else:
                print("  ❌ 没有找到任何角色")
            
            # 4. 检查生成任务
            task_query = select(GenerationTask).where(
                GenerationTask.project_id == project_id
            ).order_by(GenerationTask.created_at.desc())
            task_result = await session.execute(task_query)
            tasks = task_result.scalars().all()
            
            print(f"⚙️ 项目任务 (共 {len(tasks)} 个):")
            if tasks:
                for task in tasks:
                    print(f"  任务ID: {task.id}")
                    print(f"    状态: {task.status}, 进度: {task.progress}")
                    print(f"    当前步骤: {task.current_step}")
                    print(f"    错误信息: {task.error_message}")
                    print(f"    结果数据: {task.result_data}")
                    print()
            else:
                print("  ❌ 没有找到任何任务")
            
            return project_id, len(chapters), len(characters)
            
    except Exception as e:
        print(f"❌ 检查数据库内容失败: {e}")
        import traceback
        traceback.print_exc()
        return None, 0, 0

async def test_export_api(project_id: int):
    """测试导出API."""
    
    print(f"\n🚀 测试导出API (项目ID={project_id})")
    print("-" * 40)
    
    try:
        from src.api.routers.export import export_project
        from fastapi import Request
        from unittest.mock import Mock
        
        # 模拟导出请求
        formats = ["txt", "json"]
        
        for format_type in formats:
            print(f"📄 测试 {format_type.upper()} 格式导出...")
            
            try:
                # 直接调用导出函数
                from src.models.database import get_db_session
                from src.models.novel_models import NovelProject, Chapter, Character
                from sqlalchemy import select
                from src.api.routers.export import _export_as_txt, _export_as_json
                
                async with get_db_session() as session:
                    # 获取项目
                    project = await session.get(NovelProject, project_id)
                    if not project:
                        print(f"  ❌ 项目不存在")
                        continue
                    
                    # 获取章节
                    chapter_query = select(Chapter).where(
                        Chapter.project_id == project_id
                    ).order_by(Chapter.chapter_number)
                    chapter_result = await session.execute(chapter_query)
                    chapters = chapter_result.scalars().all()
                    
                    # 获取角色
                    character_query = select(Character).where(
                        Character.project_id == project_id
                    ).order_by(Character.importance.desc())
                    character_result = await session.execute(character_query)
                    characters = character_result.scalars().all()
                    
                    # 测试导出函数
                    if format_type == "txt":
                        content, content_type, filename = _export_as_txt(
                            project, chapters, characters, True
                        )
                    else:
                        content, content_type, filename = _export_as_json(
                            project, chapters, characters, True
                        )
                    
                    print(f"  ✅ 导出成功:")
                    print(f"    文件名: {filename}")
                    print(f"    内容类型: {content_type}")
                    print(f"    内容大小: {len(content)} 字节")
                    
                    # 显示内容预览
                    if format_type == "txt":
                        content_str = content.decode('utf-8')
                        preview = content_str[:200] + "..." if len(content_str) > 200 else content_str
                        print(f"    内容预览: {preview}")
                    
                    if len(content) == 0:
                        print(f"    ⚠️ 警告: 导出内容为空!")
                    
            except Exception as e:
                print(f"  ❌ {format_type.upper()} 导出失败: {e}")
                import traceback
                traceback.print_exc()
            
            print()
        
    except Exception as e:
        print(f"❌ 测试导出API失败: {e}")
        import traceback
        traceback.print_exc()

async def test_chapter_content():
    """检查章节内容的详细情况."""
    
    print(f"\n🔬 详细检查章节内容")
    print("-" * 40)
    
    try:
        from src.models.database import get_db_session
        from src.models.novel_models import Chapter
        from sqlalchemy import select
        
        async with get_db_session() as session:
            # 获取最近的10个章节
            chapter_query = select(Chapter).order_by(Chapter.created_at.desc()).limit(10)
            chapter_result = await session.execute(chapter_query)
            chapters = chapter_result.scalars().all()
            
            print(f"📖 最近的10个章节:")
            for i, chapter in enumerate(chapters):
                print(f"  {i+1}. 项目ID={chapter.project_id}, 第{chapter.chapter_number}章: {chapter.title}")
                print(f"      状态: {chapter.status}")
                print(f"      字数: {chapter.word_count}")
                
                if chapter.content:
                    print(f"      内容长度: {len(chapter.content)} 字符")
                    # 显示前100个字符
                    preview = chapter.content[:100] + "..." if len(chapter.content) > 100 else chapter.content
                    print(f"      内容预览: {preview}")
                else:
                    print(f"      ❌ 内容为空!")
                
                print(f"      创建时间: {chapter.created_at}")
                print()
            
            if not chapters:
                print("  ❌ 没有找到任何章节")
        
    except Exception as e:
        print(f"❌ 检查章节内容失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主函数."""
    
    print("🤖 AI智能小说生成器 - 导出问题调试")
    print("="*60)
    
    # 1. 检查数据库内容
    project_id, chapter_count, character_count = await check_database_content()
    
    if project_id is None:
        print("❌ 无法获取项目信息，退出调试")
        return
    
    # 2. 检查章节内容详情
    await test_chapter_content()
    
    # 3. 测试导出API
    if project_id:
        await test_export_api(project_id)
    
    print(f"\n📊 调试总结:")
    print("="*60)
    print(f"检查的项目ID: {project_id}")
    print(f"章节数量: {chapter_count}")
    print(f"角色数量: {character_count}")
    
    if chapter_count == 0:
        print(f"\n🔍 可能的问题:")
        print(f"  1. 小说生成过程中没有正确保存章节到数据库")
        print(f"  2. 生成过程中发生了错误，导致数据没有提交")
        print(f"  3. 数据库事务回滚了")
        print(f"  4. 生成的数据结构与预期不符")
        
        print(f"\n💡 建议:")
        print(f"  1. 检查生成日志中的错误信息")
        print(f"  2. 确认生成任务是否成功完成")
        print(f"  3. 检查NovelGenerator返回的数据结构")
        print(f"  4. 验证数据库保存逻辑")
    else:
        print(f"✅ 数据库中有章节数据，检查导出逻辑")

if __name__ == "__main__":
    asyncio.run(main())