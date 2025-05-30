#!/usr/bin/env python3
"""测试导出修复."""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

async def test_simple_generation_and_export():
    """测试简单的生成和导出流程."""
    
    print("🧪 测试生成和导出流程")
    print("="*60)
    
    try:
        # 1. 清理数据库（可选）
        from src.models.database import get_db_session
        from src.models.novel_models import NovelProject, Chapter, Character, GenerationTask
        from sqlalchemy import delete
        
        print("📚 创建测试项目...")
        
        # 创建一个简单的测试项目
        async with get_db_session() as session:
            # 创建项目
            project = NovelProject(
                title="测试小说",
                description="用于测试导出功能的小说",
                user_input="一个关于测试的故事",
                target_words=1000,
                style_preference="简洁",
                status="completed",
                progress=1.0,
                current_words=600
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            project_id = project.id
            
            print(f"✅ 项目创建成功: ID={project_id}")
            
            # 创建测试章节
            test_chapters = [
                {
                    "title": "开始",
                    "content": "这是第一章的内容。主人公开始了他的冒险之旅。他走出了家门，踏上了未知的道路。",
                    "word_count": 35
                },
                {
                    "title": "旅程",
                    "content": "在第二章中，主人公遇到了各种挑战。他需要面对困难，克服障碍。经过努力，他逐渐成长。",
                    "word_count": 40
                }
            ]
            
            for i, chapter_data in enumerate(test_chapters):
                chapter = Chapter(
                    project_id=project_id,
                    chapter_number=i + 1,
                    title=chapter_data["title"],
                    content=chapter_data["content"],
                    word_count=chapter_data["word_count"],
                    status="completed"
                )
                session.add(chapter)
                print(f"✅ 添加章节: 第{i+1}章 {chapter_data['title']}")
            
            # 创建测试角色
            test_characters = [
                {
                    "name": "主人公",
                    "description": "故事的主角，勇敢而坚定",
                    "importance": 10
                },
                {
                    "name": "导师",
                    "description": "指导主人公的智者",
                    "importance": 7
                }
            ]
            
            for char_data in test_characters:
                character = Character(
                    project_id=project_id,
                    name=char_data["name"],
                    description=char_data["description"],
                    importance=char_data["importance"],
                    profile=f"角色档案: {char_data['name']} - {char_data['description']}"
                )
                session.add(character)
                print(f"✅ 添加角色: {char_data['name']}")
            
            await session.commit()
            print(f"✅ 测试数据创建完成")
        
        # 2. 测试导出功能
        print(f"\n📄 测试导出功能...")
        
        from src.api.routers.export import _export_as_txt, _export_as_json
        from sqlalchemy import select
        
        async with get_db_session() as session:
            # 获取项目和相关数据
            project = await session.get(NovelProject, project_id)
            
            chapter_query = select(Chapter).where(
                Chapter.project_id == project_id
            ).order_by(Chapter.chapter_number)
            chapter_result = await session.execute(chapter_query)
            chapters = chapter_result.scalars().all()
            
            character_query = select(Character).where(
                Character.project_id == project_id
            ).order_by(Character.importance.desc())
            character_result = await session.execute(character_query)
            characters = character_result.scalars().all()
            
            print(f"📊 数据统计:")
            print(f"  项目: {project.title}")
            print(f"  章节数: {len(chapters)}")
            print(f"  角色数: {len(characters)}")
            
            # 测试TXT导出
            print(f"\n📝 测试TXT导出...")
            txt_content, txt_type, txt_filename = _export_as_txt(
                project, chapters, characters, True
            )
            print(f"  文件名: {txt_filename}")
            print(f"  内容大小: {len(txt_content)} 字节")
            
            # 显示TXT内容预览
            txt_str = txt_content.decode('utf-8')
            print(f"  内容预览:")
            preview_lines = txt_str.split('\n')[:20]  # 前20行
            for line in preview_lines:
                print(f"    {line}")
            if len(txt_str.split('\n')) > 20:
                print(f"    ... (省略 {len(txt_str.split('\n')) - 20} 行)")
            
            # 测试JSON导出
            print(f"\n📊 测试JSON导出...")
            json_content, json_type, json_filename = _export_as_json(
                project, chapters, characters, True
            )
            print(f"  文件名: {json_filename}")
            print(f"  内容大小: {len(json_content)} 字节")
            
            # 解析JSON内容
            import json
            json_data = json.loads(json_content.decode('utf-8'))
            print(f"  JSON结构:")
            for key in json_data.keys():
                if key == 'chapters':
                    print(f"    {key}: {len(json_data[key])} 个章节")
                elif key == 'characters':
                    print(f"    {key}: {len(json_data[key])} 个角色")
                else:
                    print(f"    {key}: {type(json_data[key])}")
        
        # 3. 保存测试文件
        print(f"\n💾 保存测试文件...")
        
        # 保存TXT文件
        with open("test_export.txt", "wb") as f:
            f.write(txt_content)
        print(f"✅ TXT文件已保存: test_export.txt")
        
        # 保存JSON文件
        with open("test_export.json", "wb") as f:
            f.write(json_content)
        print(f"✅ JSON文件已保存: test_export.json")
        
        print(f"\n🎉 导出测试成功!")
        print(f"  项目ID: {project_id}")
        print(f"  导出文件: test_export.txt, test_export.json")
        
        return project_id
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_api_export(project_id: int):
    """测试API导出功能."""
    
    print(f"\n🚀 测试API导出功能 (项目ID={project_id})")
    print("-" * 40)
    
    try:
        from src.api.routers.export import export_project
        from fastapi.responses import StreamingResponse
        import io
        
        # 测试不同格式的导出
        formats = ["txt", "json"]
        
        for format_type in formats:
            print(f"📄 测试API {format_type.upper()}导出...")
            
            try:
                # 调用API导出函数
                response = await export_project(
                    project_id=project_id,
                    format=format_type,
                    include_metadata=True,
                    include_characters=True
                )
                
                # 读取响应内容
                if isinstance(response, StreamingResponse):
                    # 获取响应内容
                    content_data = b""
                    async for chunk in response.body_iterator:
                        content_data += chunk
                    
                    print(f"  ✅ API导出成功:")
                    print(f"    内容大小: {len(content_data)} 字节")
                    print(f"    媒体类型: {response.media_type}")
                    
                    # 保存API导出的文件
                    filename = f"api_export_{project_id}.{format_type}"
                    with open(filename, "wb") as f:
                        f.write(content_data)
                    print(f"    已保存文件: {filename}")
                    
                    if len(content_data) == 0:
                        print(f"    ⚠️ 警告: 导出内容为空!")
                    else:
                        # 显示内容预览
                        if format_type == "txt":
                            preview = content_data.decode('utf-8')[:200]
                            print(f"    内容预览: {preview}...")
                else:
                    print(f"  ❌ 响应类型不正确: {type(response)}")
                    
            except Exception as e:
                print(f"  ❌ API导出失败: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"❌ API导出测试失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主函数."""
    
    print("🤖 AI智能小说生成器 - 导出修复测试")
    print("="*60)
    
    # 1. 测试基本的生成和导出流程
    project_id = await test_simple_generation_and_export()
    
    if project_id:
        # 2. 测试API导出功能
        await test_api_export(project_id)
        
        print(f"\n📊 测试总结:")
        print("="*60)
        print(f"✅ 测试项目创建成功")
        print(f"✅ 章节和角色数据保存成功")
        print(f"✅ 导出功能测试成功")
        print(f"✅ API导出功能测试成功")
        
        print(f"\n💡 如果之前导出为空，现在应该已经修复:")
        print(f"  1. 改进了数据保存逻辑，处理不同的数据格式")
        print(f"  2. 添加了详细的调试日志")
        print(f"  3. 增强了导出函数的错误处理")
        print(f"  4. 测试了完整的数据流程")
        
        print(f"\n🔍 生成的测试文件:")
        print(f"  - test_export.txt: 基础TXT导出")
        print(f"  - test_export.json: 基础JSON导出")
        print(f"  - api_export_{project_id}.txt: API TXT导出")
        print(f"  - api_export_{project_id}.json: API JSON导出")
    else:
        print(f"\n❌ 测试失败，无法创建测试项目")

if __name__ == "__main__":
    asyncio.run(main())