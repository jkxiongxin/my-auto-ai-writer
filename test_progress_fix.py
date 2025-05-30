"""测试进度更新修复."""

import asyncio
import json
import aiohttp
from datetime import datetime

async def test_progress_updates():
    """测试进度更新修复."""
    
    base_url = "http://localhost:8000"
    
    # 测试数据
    test_request = {
        "title": "测试进度更新修复",
        "description": "测试生成过程中进度条正确更新",
        "user_input": "一个关于太空探险的故事，主角是一名勇敢的宇航员",
        "target_words": 2000,  # 较小的字数，便于快速测试
        "style_preference": "科幻"
    }
    
    print("🚀 开始测试进度更新修复...")
    
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
            
            # 2. 密集监控生成进度
            print("\n⏳ 密集监控生成进度...")
            max_attempts = 120  # 最多监控20分钟
            attempt = 0
            last_progress = -1
            last_step = ""
            progress_updates = []
            
            while attempt < max_attempts:
                await asyncio.sleep(5)  # 每5秒检查一次
                attempt += 1
                
                async with session.get(f"{base_url}/api/v1/generate-novel/{task_id}/status") as resp:
                    if resp.status == 200:
                        status_result = await resp.json()
                        status = status_result["status"]
                        progress = status_result["progress"]
                        current_step = status_result.get("current_step", "")
                        
                        # 检查进度是否有变化
                        if progress != last_progress or current_step != last_step:
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            progress_update = {
                                "time": timestamp,
                                "step": current_step,
                                "progress": progress * 100,
                                "status": status
                            }
                            progress_updates.append(progress_update)
                            
                            if progress > last_progress:
                                print(f"📈 [{timestamp}] 进度更新: {current_step} ({progress*100:.1f}%) - 状态: {status}")
                                last_progress = progress
                            elif current_step != last_step:
                                print(f"🔄 [{timestamp}] 阶段变更: {current_step} ({progress*100:.1f}%) - 状态: {status}")
                            
                            last_step = current_step
                        
                        if status == "completed":
                            print("✅ 生成完成!")
                            break
                        elif status in ["failed", "cancelled"]:
                            print(f"❌ 生成失败: {status}")
                            error_msg = status_result.get("error_message", "未知错误")
                            print(f"错误信息: {error_msg}")
                            break
                    else:
                        print(f"⚠️ 状态查询失败: {resp.status}")
            
            if attempt >= max_attempts:
                print("⏰ 等待超时，生成可能仍在进行中")
            
            # 3. 分析进度更新情况
            print(f"\n📊 进度更新分析:")
            print(f"  - 总计状态检查次数: {attempt}")
            print(f"  - 进度更新次数: {len(progress_updates)}")
            
            if len(progress_updates) > 1:
                print("✅ 进度更新正常 - 检测到多次进度变化")
                print("📈 进度变化详情:")
                for i, update in enumerate(progress_updates):
                    print(f"  {i+1}. [{update['time']}] {update['step']} - {update['progress']:.1f}%")
                
                # 检查进度是否有合理的递增
                progress_values = [update['progress'] for update in progress_updates]
                if len(progress_values) >= 2:
                    max_progress = max(progress_values)
                    min_progress = min(progress_values)
                    if max_progress > min_progress:
                        print(f"✅ 进度递增正常: {min_progress:.1f}% → {max_progress:.1f}%")
                    else:
                        print(f"⚠️ 进度似乎没有递增: {min_progress:.1f}% → {max_progress:.1f}%")
                
                # 检查阶段变化
                unique_steps = list(set(update['step'] for update in progress_updates))
                print(f"✅ 检测到 {len(unique_steps)} 个不同阶段: {', '.join(unique_steps)}")
                
            elif len(progress_updates) == 1:
                print("⚠️ 进度更新异常 - 只检测到一次进度变化")
                print(f"  唯一的进度: {progress_updates[0]}")
            else:
                print("❌ 进度更新失败 - 没有检测到任何进度变化")
            
            # 4. 获取最终结果
            if status == "completed":
                print(f"\n📋 获取最终结果...")
                async with session.get(f"{base_url}/api/v1/generate-novel/{task_id}/result") as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"📊 生成完成:")
                        print(f"  - 标题: {result['title']}")
                        print(f"  - 总字数: {result['total_words']}")
                        print(f"  - 章节数: {result['chapter_count']}")
                        print(f"  - 质量评分: {result['quality_score']}")
                        print(f"  - 生成时间: {result['generation_time_seconds']:.2f}秒")
                    else:
                        print(f"⚠️ 获取结果失败: {resp.status}")
    
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("📋 测试进度更新修复")
    print("=" * 50)
    asyncio.run(test_progress_updates())