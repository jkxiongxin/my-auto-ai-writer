#!/usr/bin/env python3
"""测试API接口."""

import asyncio
import json
import sys
from pathlib import Path

import httpx

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

API_BASE_URL = "http://localhost:8000"

async def test_api():
    """测试API功能."""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🔍 测试API功能...")
        
        # 1. 测试健康检查
        print("\n1. 测试健康检查...")
        try:
            response = await client.get(f"{API_BASE_URL}/health")
            print(f"健康检查状态: {response.status_code}")
            if response.status_code == 200:
                print("✅ 健康检查通过")
                print(f"响应: {response.json()}")
            else:
                print(f"❌ 健康检查失败: {response.text}")
        except Exception as e:
            print(f"❌ 健康检查请求失败: {e}")
        
        # 2. 测试小说生成接口
        print("\n2. 测试小说生成接口...")
        
        test_request = {
            "title": "测试小说",
            "description": "这是一个用于测试API的小说项目",
            "user_input": "写一个关于时间旅行的科幻故事，主角是一名年轻的物理学家",
            "target_words": 5000,
            "style_preference": "科幻"
        }
        
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/generate-novel",
                json=test_request
            )
            print(f"生成请求状态: {response.status_code}")
            
            if response.status_code == 202:
                print("✅ 生成请求成功")
                result = response.json()
                print(f"任务ID: {result.get('task_id')}")
                print(f"项目ID: {result.get('id')}")
                
                # 测试状态查询
                task_id = result.get('task_id')
                if task_id:
                    print(f"\n3. 测试状态查询...")
                    status_response = await client.get(
                        f"{API_BASE_URL}/api/v1/generate-novel/{task_id}/status"
                    )
                    print(f"状态查询: {status_response.status_code}")
                    if status_response.status_code == 200:
                        print("✅ 状态查询成功")
                        status_data = status_response.json()
                        print(f"当前状态: {status_data.get('status')}")
                        print(f"进度: {status_data.get('progress', 0) * 100:.1f}%")
                    else:
                        print(f"❌ 状态查询失败: {status_response.text}")
            else:
                print(f"❌ 生成请求失败: {response.text}")
                
        except Exception as e:
            print(f"❌ 生成请求异常: {e}")
        
        # 3. 测试项目列表
        print("\n4. 测试项目列表...")
        try:
            response = await client.get(f"{API_BASE_URL}/api/v1/projects")
            print(f"项目列表状态: {response.status_code}")
            if response.status_code == 200:
                print("✅ 项目列表获取成功")
                projects_data = response.json()
                project_count = len(projects_data.get('projects', []))
                print(f"项目数量: {project_count}")
            else:
                print(f"❌ 项目列表获取失败: {response.text}")
        except Exception as e:
            print(f"❌ 项目列表请求异常: {e}")
        
        # 4. 测试API文档
        print("\n5. 测试API文档...")
        try:
            response = await client.get(f"{API_BASE_URL}/openapi.json")
            print(f"OpenAPI文档状态: {response.status_code}")
            if response.status_code == 200:
                print("✅ API文档可访问")
                openapi_data = response.json()
                print(f"API标题: {openapi_data.get('info', {}).get('title')}")
                print(f"API版本: {openapi_data.get('info', {}).get('version')}")
                print(f"路径数量: {len(openapi_data.get('paths', {}))}")
            else:
                print(f"❌ API文档不可访问: {response.text}")
        except Exception as e:
            print(f"❌ API文档请求异常: {e}")

def main():
    """主函数."""
    print("🧪 AI智能小说生成器API测试")
    print("="*50)
    
    try:
        asyncio.run(test_api())
        print("\n🎉 API测试完成!")
    except KeyboardInterrupt:
        print("\n👋 测试已中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")

if __name__ == "__main__":
    main()