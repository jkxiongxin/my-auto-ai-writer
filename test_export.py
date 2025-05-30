#!/usr/bin/env python3
"""测试导出功能."""

import asyncio
import sys
from pathlib import Path

import httpx

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

API_BASE_URL = "http://localhost:8000"

async def test_export():
    """测试导出功能."""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🧪 测试导出功能...")
        
        # 1. 首先创建一个测试项目
        print("\n1. 创建测试项目...")
        test_request = {
            "title": "测试导出项目",
            "description": "这是一个用于测试导出功能的项目",
            "user_input": "创建一个简单的测试小说用于导出功能验证",
            "target_words": 1000,
            "style_preference": "科幻"
        }
        
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/generate-novel",
                json=test_request
            )
            
            if response.status_code != 202:
                print(f"❌ 创建项目失败: {response.text}")
                return
            
            result = response.json()
            project_id = result.get('id')
            print(f"✅ 项目创建成功: ID={project_id}")
            
        except Exception as e:
            print(f"❌ 创建项目异常: {e}")
            return
        
        # 等待一下让任务有时间处理
        print("⏳ 等待生成任务处理...")
        await asyncio.sleep(3)
        
        # 2. 测试不同格式的导出
        formats = ["txt", "json", "zip"]
        
        for fmt in formats:
            print(f"\n2.{formats.index(fmt)+1} 测试{fmt.upper()}格式导出...")
            
            try:
                response = await client.get(
                    f"{API_BASE_URL}/api/v1/projects/{project_id}/export?format={fmt}"
                )
                
                print(f"导出状态: {response.status_code}")
                
                if response.status_code == 200:
                    print("✅ 导出成功")
                    print(f"Content-Type: {response.headers.get('content-type')}")
                    print(f"Content-Disposition: {response.headers.get('content-disposition')}")
                    print(f"内容大小: {len(response.content)} 字节")
                    
                    # 保存文件进行验证
                    filename = f"test_export_{project_id}.{fmt}"
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    print(f"文件已保存: {filename}")
                    
                else:
                    print(f"❌ 导出失败: {response.text}")
                    
            except Exception as e:
                print(f"❌ 导出{fmt}格式异常: {e}")
        
        # 3. 测试内容预览
        print(f"\n3. 测试内容预览...")
        
        try:
            response = await client.get(
                f"{API_BASE_URL}/api/v1/projects/{project_id}/content?format=txt"
            )
            
            if response.status_code == 200:
                print("✅ 内容预览成功")
                content = response.content.decode('utf-8')
                print(f"预览内容（前200字符）:\n{content[:200]}...")
            else:
                print(f"❌ 内容预览失败: {response.text}")
                
        except Exception as e:
            print(f"❌ 内容预览异常: {e}")
        
        print(f"\n🎉 导出测试完成!")

def main():
    """主函数."""
    print("🧪 AI智能小说生成器导出功能测试")
    print("="*50)
    
    try:
        asyncio.run(test_export())
    except KeyboardInterrupt:
        print("\n👋 测试已中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")

if __name__ == "__main__":
    main()