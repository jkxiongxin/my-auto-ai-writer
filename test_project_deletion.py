"""测试项目删除功能的脚本."""

import asyncio
import aiohttp
import json
from datetime import datetime

API_BASE_URL = 'http://localhost:8000'

async def create_test_project(session, title, status="completed"):
    """创建测试项目."""
    project_data = {
        "title": title,
        "description": f"测试项目 - {title}",
        "user_input": "这是一个用于测试删除功能的项目",
        "target_words": 5000,
        "style_preference": "科幻"
    }
    
    # 直接插入数据库而不是通过生成API
    # 这里模拟创建已完成的项目
    print(f"创建测试项目: {title} (状态: {status})")
    return {"id": 999, "title": title, "status": status}  # 模拟返回

async def test_delete_completed_project():
    """测试删除已完成项目."""
    async with aiohttp.ClientSession() as session:
        print("=== 测试删除已完成项目 ===")
        
        # 1. 获取项目列表
        try:
            async with session.get(f"{API_BASE_URL}/api/v1/projects") as response:
                if response.status == 200:
                    data = await response.json()
                    projects = data.get('projects', [])
                    completed_projects = [p for p in projects if p['status'] == 'completed']
                    
                    if completed_projects:
                        project = completed_projects[0]
                        project_id = project['id']
                        project_title = project['title']
                        
                        print(f"找到已完成项目: ID={project_id}, 标题='{project_title}'")
                        
                        # 2. 尝试删除项目
                        async with session.delete(f"{API_BASE_URL}/api/v1/projects/{project_id}") as delete_response:
                            if delete_response.status == 200:
                                result = await delete_response.json()
                                print(f"✅ 删除成功: {result}")
                            else:
                                error_data = await delete_response.json()
                                print(f"❌ 删除失败: {delete_response.status} - {error_data}")
                    else:
                        print("⚠️ 没有找到已完成的项目用于测试")
                else:
                    print(f"❌ 获取项目列表失败: {response.status}")
                    
        except aiohttp.ClientError as e:
            print(f"❌ 网络错误: {e}")
        except Exception as e:
            print(f"❌ 意外错误: {e}")

async def test_delete_running_project():
    """测试删除运行中项目（应该失败）."""
    async with aiohttp.ClientSession() as session:
        print("\n=== 测试删除运行中项目（应该被拒绝） ===")
        
        try:
            async with session.get(f"{API_BASE_URL}/api/v1/projects") as response:
                if response.status == 200:
                    data = await response.json()
                    projects = data.get('projects', [])
                    running_projects = [p for p in projects if p['status'] == 'running']
                    
                    if running_projects:
                        project = running_projects[0]
                        project_id = project['id']
                        project_title = project['title']
                        
                        print(f"找到运行中项目: ID={project_id}, 标题='{project_title}'")
                        
                        # 尝试删除（应该失败）
                        async with session.delete(f"{API_BASE_URL}/api/v1/projects/{project_id}") as delete_response:
                            if delete_response.status == 400:
                                error_data = await delete_response.json()
                                print(f"✅ 正确拒绝删除运行中项目: {error_data['detail']}")
                            else:
                                print(f"❌ 意外结果: {delete_response.status}")
                    else:
                        print("⚠️ 没有找到运行中的项目用于测试")
                        
        except Exception as e:
            print(f"❌ 错误: {e}")

async def test_delete_nonexistent_project():
    """测试删除不存在的项目."""
    async with aiohttp.ClientSession() as session:
        print("\n=== 测试删除不存在的项目 ===")
        
        fake_project_id = 999999
        
        try:
            async with session.delete(f"{API_BASE_URL}/api/v1/projects/{fake_project_id}") as response:
                if response.status == 404:
                    error_data = await response.json()
                    print(f"✅ 正确返回404: {error_data['detail']}")
                else:
                    print(f"❌ 意外状态码: {response.status}")
                    
        except Exception as e:
            print(f"❌ 错误: {e}")

async def test_api_health():
    """测试API健康状态."""
    async with aiohttp.ClientSession() as session:
        print("=== 检查API健康状态 ===")
        
        try:
            async with session.get(f"{API_BASE_URL}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ API服务正常: {health_data}")
                    return True
                else:
                    print(f"❌ API服务异常: {response.status}")
                    return False
                    
        except aiohttp.ClientError:
            print("❌ 无法连接到API服务，请确保API服务正在运行")
            return False

async def main():
    """主测试函数."""
    print("🧪 项目删除功能测试")
    print("=" * 50)
    
    # 检查API服务状态
    if not await test_api_health():
        print("\n⚠️ API服务不可用，请先启动API服务:")
        print("  python start_api.py")
        return
    
    print()
    
    # 运行测试
    await test_delete_completed_project()
    await test_delete_running_project() 
    await test_delete_nonexistent_project()
    
    print("\n" + "=" * 50)
    print("🎉 测试完成！")
    
    print("\n📝 测试说明:")
    print("1. ✅ 应该能够删除已完成(completed)的项目")
    print("2. ❌ 不应该能够删除运行中(running)的项目")
    print("3. ❌ 删除不存在的项目应该返回404")
    print("4. 前端界面现在为已完成项目显示删除按钮")
    print("5. 删除已完成项目需要二次确认")

def print_frontend_testing_guide():
    """打印前端测试指南."""
    print("\n🌐 前端测试指南:")
    print("=" * 30)
    print("1. 在浏览器中打开: frontend/index.html")
    print("2. 切换到 '我的项目' 页面")
    print("3. 对于已完成的项目，现在应该看到:")
    print("   - [查看] [导出] [删除] 三个按钮")
    print("4. 点击删除按钮时会有:")
    print("   - 详细的警告确认对话框")
    print("   - 要求输入 '确认删除' 的二次确认")
    print("5. 删除成功后项目列表会自动刷新")

if __name__ == "__main__":
    asyncio.run(main())
    print_frontend_testing_guide()