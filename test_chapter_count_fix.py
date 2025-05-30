"""测试章节数量显示修复."""

import asyncio
import json
import aiohttp
from datetime import datetime

async def test_chapter_count_fix():
    """测试章节数量显示修复."""
    
    base_url = "http://localhost:8000"
    
    # 测试数据
    test_request = {
        "title": "测试章节数量修复",
        "description": "测试章节数量在result接口中正确显示",
        "user_input": "一个关于机器人获得情感的故事",
        "target_words": 3000,
        "style_preference": "科幻"
    }
    
    print("🚀 开始测试章节数量修复...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # 1. 启动生成任务
            print("\n📝 启动小说生成任务...")
            async with session.post(
                f"{base_url}/api/v1/generate-novel",
                json=test_request,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status != 202:
                    error_text = await resp.text()
                    print(f"❌ 启动任务失败: {resp.status} - {error_text}")
                    return
                
                result = await resp.json()
                task_id = result["task_id"]
                project_id = result["id"]
                print(f"✅ 任务已启动: task_id={task_id}, project_id={project_id}")
            
            # 2. 监控生成进度
            print("\n⏳ 监控生成进度...")
            max_attempts = 60  # 最多等待10分钟
            attempt = 0
            
            while attempt < max_attempts:
                await asyncio.sleep(10)  # 每10秒检查一次
                attempt += 1
                
                async with session.get(f"{base_url}/api/v1/generate-novel/{task_id}/status") as resp:
                    if resp.status == 200:
                        status_result = await resp.json()
                        status = status_result["status"]
                        progress = status_result["progress"]
                        current_step = status_result.get("current_step", "")
                        
                        print(f"📊 进度: {status} - {current_step} ({progress*100:.1f}%)")
                        
                        if status == "completed":
                            print("✅ 生成完成!")
                            break
                        elif status in ["failed", "cancelled"]:
                            print(f"❌ 生成失败: {status}")
                            error_msg = status_result.get("error_message", "未知错误")
                            print(f"错误信息: {error_msg}")
                            return
                    else:
                        print(f"⚠️ 状态查询失败: {resp.status}")
            
            if attempt >= max_attempts:
                print("⏰ 等待超时，生成可能仍在进行中")
                return
            
            # 3. 获取生成结果并验证章节数量
            print("\n📋 获取生成结果...")
            async with session.get(f"{base_url}/api/v1/generate-novel/{task_id}/result") as resp:
                if resp.status == 200:
                    result = await resp.json()
                    
                    print("\n📊 生成结果:")
                    print(f"  - 任务ID: {result['task_id']}")
                    print(f"  - 项目ID: {result['project_id']}")
                    print(f"  - 状态: {result['status']}")
                    print(f"  - 标题: {result['title']}")
                    print(f"  - 总字数: {result['total_words']}")
                    print(f"  - 章节数: {result['chapter_count']}")  # 关键字段
                    print(f"  - 质量评分: {result['quality_score']}")
                    print(f"  - 生成时间: {result['generation_time_seconds']:.2f}秒")
                    
                    # 显示详细结果数据
                    result_data = result.get('result_data', {})
                    print(f"  - 详细数据:")
                    for key, value in result_data.items():
                        print(f"    * {key}: {value}")
                    
                    # 验证修复
                    api_chapter_count = result['chapter_count']
                    result_data_chapter_count = result_data.get('章节数', 0)
                    
                    print(f"\n🔍 章节数量验证:")
                    print(f"  - API返回的chapter_count: {api_chapter_count}")
                    print(f"  - result_data中的章节数: {result_data_chapter_count}")
                    
                    if api_chapter_count > 0 and api_chapter_count == result_data_chapter_count:
                        print("✅ 修复成功！章节数量现在正确显示了")
                    elif api_chapter_count == 0:
                        print("❌ 修复失败：API仍然返回章节数为0")
                    else:
                        print(f"⚠️ 数据不一致：API({api_chapter_count}) != result_data({result_data_chapter_count})")
                        
                else:
                    error_text = await resp.text()
                    print(f"❌ 获取结果失败: {resp.status} - {error_text}")
            
            # 4. 验证数据库中的章节记录
            print(f"\n🗄️ 检查数据库章节记录 (project_id: {project_id})...")
            async with session.get(f"{base_url}/api/v1/projects/{project_id}/chapters") as resp:
                if resp.status == 200:
                    chapters = await resp.json()
                    if isinstance(chapters, list):
                        print(f"✅ 数据库中实际存储了 {len(chapters)} 个章节")
                        for i, chapter in enumerate(chapters[:3]):  # 只显示前3个章节
                            print(f"  - 章节{i+1}: {chapter.get('title', '无标题')} ({chapter.get('word_count', 0)}字)")
                    else:
                        print(f"✅ 数据库中有章节记录: {chapters}")
                else:
                    print(f"⚠️ 无法获取章节列表: {resp.status}")
    
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("📋 测试章节数量修复")
    print("=" * 50)
    asyncio.run(test_chapter_count_fix())