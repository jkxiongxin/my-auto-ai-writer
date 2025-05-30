#!/usr/bin/env python3
"""API和前端界面演示脚本."""

import asyncio
import json
import time
from pathlib import Path
import subprocess
import webbrowser
from typing import Dict, Any

import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text


console = Console()

API_BASE_URL = "http://localhost:8000"
FRONTEND_URL = f"{API_BASE_URL}/app"


class APIFrontendDemo:
    """API和前端界面演示类."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.current_task_id = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def check_api_health(self) -> bool:
        """检查API服务健康状态."""
        try:
            response = await self.client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                health_data = response.json()
                console.print(f"✅ API服务运行正常: {health_data['status']}")
                return True
            else:
                console.print(f"❌ API服务异常: HTTP {response.status_code}")
                return False
        except Exception as e:
            console.print(f"❌ 无法连接到API服务: {e}")
            return False
    
    async def demonstrate_novel_generation(self) -> Dict[str, Any]:
        """演示小说生成功能."""
        console.print("\n" + "="*60)
        console.print("🎭 演示小说生成功能")
        console.print("="*60)
        
        # 生成请求数据
        request_data = {
            "title": "时空漂流者",
            "description": "一个关于时间旅行和自我发现的科幻冒险故事",
            "user_input": "一名年轻的物理学家意外发现了时间旅行的秘密，但每次穿越都会带来意想不到的后果",
            "target_words": 5000,
            "style_preference": "科幻"
        }
        
        console.print("📝 创建生成请求...")
        console.print(Panel(json.dumps(request_data, indent=2, ensure_ascii=False), title="生成参数"))
        
        try:
            response = await self.client.post(
                f"{API_BASE_URL}/api/v1/generate-novel",
                json=request_data
            )
            
            if response.status_code != 202:
                console.print(f"❌ 创建生成任务失败: {response.text}")
                return {}
            
            result = response.json()
            self.current_task_id = result["task_id"]
            
            console.print(f"✅ 生成任务已创建: {self.current_task_id}")
            
            # 监控生成进度
            await self.monitor_generation_progress()
            
            return result
            
        except Exception as e:
            console.print(f"❌ 生成失败: {e}")
            return {}
    
    async def monitor_generation_progress(self):
        """监控生成进度."""
        if not self.current_task_id:
            return
        
        console.print("\n📊 监控生成进度...")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("正在生成小说...", total=None)
            
            while True:
                try:
                    response = await self.client.get(
                        f"{API_BASE_URL}/api/v1/generate-novel/{self.current_task_id}/status"
                    )
                    
                    if response.status_code != 200:
                        console.print(f"❌ 获取进度失败: {response.text}")
                        break
                    
                    status_data = response.json()
                    progress_percent = status_data["progress"] * 100
                    current_step = status_data["current_step"] or "处理中"
                    
                    progress.update(
                        task,
                        description=f"[green]{current_step}[/green] ({progress_percent:.1f}%)"
                    )
                    
                    if status_data["status"] in ["completed", "failed", "cancelled"]:
                        progress.update(task, description=f"[yellow]状态: {status_data['status']}[/yellow]")
                        break
                    
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    console.print(f"❌ 监控进度时出错: {e}")
                    break
        
        # 获取最终结果
        await self.get_generation_result()
    
    async def get_generation_result(self):
        """获取生成结果."""
        if not self.current_task_id:
            return
        
        try:
            response = await self.client.get(
                f"{API_BASE_URL}/api/v1/generate-novel/{self.current_task_id}/result"
            )
            
            if response.status_code == 200:
                result = response.json()
                console.print("\n🎉 生成完成!")
                
                # 创建结果表格
                table = Table(title="生成结果")
                table.add_column("项目", style="cyan")
                table.add_column("值", style="green")
                
                table.add_row("小说标题", result["title"])
                table.add_row("总字数", f"{result['total_words']:,}")
                table.add_row("章节数", str(result["chapter_count"]))
                table.add_row("质量评分", f"{result.get('quality_score', 'N/A')}")
                table.add_row("生成时间", f"{result.get('generation_time_seconds', 0):.1f}秒")
                
                console.print(table)
                
            else:
                console.print(f"❌ 获取结果失败: {response.text}")
                
        except Exception as e:
            console.print(f"❌ 获取结果时出错: {e}")
    
    async def demonstrate_project_management(self):
        """演示项目管理功能."""
        console.print("\n" + "="*60)
        console.print("📁 演示项目管理功能")
        console.print("="*60)
        
        try:
            response = await self.client.get(f"{API_BASE_URL}/api/v1/projects")
            
            if response.status_code != 200:
                console.print(f"❌ 获取项目列表失败: {response.text}")
                return
            
            data = response.json()
            projects = data.get("projects", [])
            
            if not projects:
                console.print("📋 暂无项目")
                return
            
            # 创建项目表格
            table = Table(title=f"项目列表 (共 {len(projects)} 个)")
            table.add_column("ID", style="cyan")
            table.add_column("标题", style="green")
            table.add_column("状态", style="yellow")
            table.add_column("目标字数", style="blue")
            table.add_column("当前字数", style="magenta")
            table.add_column("创建时间", style="white")
            
            for project in projects:
                table.add_row(
                    str(project["id"]),
                    project["title"][:30] + "..." if len(project["title"]) > 30 else project["title"],
                    project["status"],
                    f"{project['target_words']:,}",
                    f"{project.get('current_words', 0):,}",
                    project["created_at"][:19].replace("T", " ")
                )
            
            console.print(table)
            
        except Exception as e:
            console.print(f"❌ 项目管理演示失败: {e}")
    
    async def demonstrate_api_documentation(self):
        """演示API文档功能."""
        console.print("\n" + "="*60)
        console.print("📚 演示API文档功能")
        console.print("="*60)
        
        try:
            # 检查OpenAPI文档
            response = await self.client.get(f"{API_BASE_URL}/openapi.json")
            
            if response.status_code == 200:
                openapi_data = response.json()
                console.print(f"✅ OpenAPI文档可用")
                console.print(f"   - 版本: {openapi_data['info']['version']}")
                console.print(f"   - 标题: {openapi_data['info']['title']}")
                console.print(f"   - 路径数量: {len(openapi_data['paths'])}")
                
                # 列出主要端点
                console.print("\n📋 主要API端点:")
                for path, methods in openapi_data["paths"].items():
                    for method in methods.keys():
                        console.print(f"   {method.upper()} {path}")
            
            console.print(f"\n🌐 Swagger UI: {API_BASE_URL}/docs")
            console.print(f"🌐 ReDoc: {API_BASE_URL}/redoc")
            
        except Exception as e:
            console.print(f"❌ API文档演示失败: {e}")
    
    def demonstrate_frontend_interface(self):
        """演示前端界面."""
        console.print("\n" + "="*60)
        console.print("🖥️  演示前端界面")
        console.print("="*60)
        
        console.print(f"🌐 前端界面地址: {FRONTEND_URL}")
        console.print(f"📁 静态文件地址: {API_BASE_URL}/static/")
        
        # 尝试打开浏览器
        try:
            console.print("🚀 正在打开浏览器...")
            webbrowser.open(FRONTEND_URL)
            console.print("✅ 浏览器已打开")
        except Exception as e:
            console.print(f"❌ 无法自动打开浏览器: {e}")
            console.print(f"请手动访问: {FRONTEND_URL}")
    
    async def run_complete_demo(self):
        """运行完整演示."""
        console.print(Panel.fit(
            "[bold green]AI智能小说生成器[/bold green]\n"
            "[blue]API与前端界面完整演示[/blue]",
            title="🎭 演示程序"
        ))
        
        # 1. 检查API健康状态
        console.print("\n🔍 检查API服务状态...")
        if not await self.check_api_health():
            console.print("❌ API服务不可用，请先启动API服务")
            return
        
        # 2. 演示API文档
        await self.demonstrate_api_documentation()
        
        # 3. 演示项目管理
        await self.demonstrate_project_management()
        
        # 4. 演示前端界面
        self.demonstrate_frontend_interface()
        
        # 5. 询问是否进行小说生成演示
        console.print("\n" + "="*60)
        response = console.input("是否进行小说生成演示？(这可能需要几分钟) [y/N]: ")
        if response.lower() in ['y', 'yes', '是']:
            await self.demonstrate_novel_generation()
            await self.demonstrate_project_management()  # 再次显示项目列表
        
        console.print("\n🎉 演示完成!")
        console.print(f"💡 您可以继续在浏览器中体验完整功能: {FRONTEND_URL}")


def check_api_server():
    """检查API服务器是否运行."""
    try:
        import requests
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def start_api_server():
    """启动API服务器."""
    console.print("🚀 正在启动API服务器...")
    
    # 检查是否已经运行
    if check_api_server():
        console.print("✅ API服务器已在运行")
        return True
    
    try:
        # 启动API服务器
        subprocess.Popen([
            "python", "-m", "uvicorn",
            "src.api.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ], cwd=Path(__file__).parent.parent)
        
        # 等待服务器启动
        console.print("⏳ 等待服务器启动...")
        for i in range(30):  # 最多等待30秒
            time.sleep(1)
            if check_api_server():
                console.print("✅ API服务器启动成功")
                return True
            console.print(f"⏳ 等待中... ({i+1}/30)")
        
        console.print("❌ API服务器启动超时")
        return False
        
    except Exception as e:
        console.print(f"❌ 启动API服务器失败: {e}")
        return False


async def main():
    """主函数."""
    console.print("🎭 AI智能小说生成器 - API与前端演示")
    console.print("="*60)
    
    # 检查API服务器
    if not check_api_server():
        console.print("⚠️  API服务器未运行")
        response = console.input("是否自动启动API服务器? [Y/n]: ")
        if response.lower() not in ['n', 'no', '否']:
            if not start_api_server():
                console.print("❌ 无法启动API服务器，请手动启动后重试")
                console.print("启动命令: uvicorn src.api.main:app --reload")
                return
        else:
            console.print("请手动启动API服务器后重试")
            console.print("启动命令: uvicorn src.api.main:app --reload")
            return
    
    # 运行演示
    async with APIFrontendDemo() as demo:
        await demo.run_complete_demo()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n👋 演示已取消")
    except Exception as e:
        console.print(f"\n❌ 演示过程中发生错误: {e}")