#!/usr/bin/env python3
"""测试速率限制豁免功能."""

import sys
import asyncio
import aiohttp
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

async def test_rate_limit_exemption():
    """测试速率限制豁免功能."""
    
    print("🧪 测试速率限制豁免功能")
    print("="*60)
    
    # API基础URL
    base_url = "http://localhost:8000"
    
    # 需要测试的豁免路径
    exempt_paths = [
        "/health/ping",                    # 健康检查
        "/api/v1/progress/active",         # 活跃任务查询
        "/api/v1/progress/test-task/status", # 任务状态查询（测试路径）
    ]
    
    # 需要测试的限制路径
    limited_paths = [
        "/api/v1/generate-novel",          # 小说生成（受限制）
        "/api/v1/export/1?format=txt",     # 导出功能（受限制）
    ]
    
    async with aiohttp.ClientSession() as session:
        
        # 1. 测试豁免路径 - 频繁调用不应该被限制
        print("📝 测试豁免路径（频繁调用应该不被限制）:")
        print("-" * 40)
        
        for path in exempt_paths:
            url = f"{base_url}{path}"
            success_count = 0
            error_count = 0
            
            print(f"测试路径: {path}")
            
            # 快速连续请求10次
            for i in range(10):
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            success_count += 1
                        elif response.status == 404:
                            # 404说明路径不存在，但没有被速率限制
                            success_count += 1
                        elif response.status == 429:
                            error_count += 1
                            print(f"  ❌ 第{i+1}次请求被速率限制 (429)")
                        else:
                            print(f"  ⚠️ 第{i+1}次请求返回状态码: {response.status}")
                        
                        # 检查是否有豁免标记
                        if response.headers.get("X-RateLimit-Exempt") == "true":
                            print(f"  ✅ 第{i+1}次请求已豁免速率限制")
                        
                except Exception as e:
                    error_count += 1
                    print(f"  ❌ 第{i+1}次请求失败: {e}")
                
                # 很短的间隔
                await asyncio.sleep(0.1)
            
            print(f"  结果: 成功 {success_count}/10, 失败 {error_count}/10")
            
            if error_count == 0:
                print(f"  ✅ 路径 {path} 正确豁免了速率限制")
            else:
                print(f"  ❌ 路径 {path} 可能没有正确豁免")
            print()
        
        # 2. 测试限制路径 - 应该触发速率限制
        print("📝 测试限制路径（频繁调用应该被限制）:")
        print("-" * 40)
        
        for path in limited_paths:
            url = f"{base_url}{path}"
            success_count = 0
            rate_limited_count = 0
            
            print(f"测试路径: {path}")
            
            # 快速连续请求15次，应该触发速率限制
            for i in range(15):
                try:
                    async with session.post(url, json={"test": "data"}) if "generate" in path else session.get(url) as response:
                        if response.status == 429:
                            rate_limited_count += 1
                            print(f"  ✅ 第{i+1}次请求被正确限制 (429)")
                        else:
                            success_count += 1
                            print(f"  📝 第{i+1}次请求成功 ({response.status})")
                        
                        # 检查速率限制头
                        limit = response.headers.get("X-RateLimit-Limit")
                        remaining = response.headers.get("X-RateLimit-Remaining")
                        if limit and remaining:
                            print(f"     限制: {limit}, 剩余: {remaining}")
                            
                except Exception as e:
                    print(f"  ⚠️ 第{i+1}次请求异常: {e}")
                
                # 很短的间隔
                await asyncio.sleep(0.1)
            
            print(f"  结果: 成功 {success_count}/15, 被限制 {rate_limited_count}/15")
            
            if rate_limited_count > 0:
                print(f"  ✅ 路径 {path} 正确触发了速率限制")
            else:
                print(f"  ⚠️ 路径 {path} 可能没有触发速率限制（可能是其他原因）")
            print()

async def test_websocket_exemption():
    """测试WebSocket连接豁免."""
    
    print("🔌 测试WebSocket连接豁免:")
    print("-" * 40)
    
    try:
        import websockets
        
        ws_url = "ws://localhost:8000/api/v1/ws/progress/test-task"
        
        print(f"尝试连接WebSocket: {ws_url}")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print("✅ WebSocket连接成功（没有被速率限制）")
                
                # 发送心跳测试
                await websocket.send("ping")
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"✅ 心跳测试成功: {response}")
                
        except Exception as e:
            print(f"⚠️ WebSocket连接失败: {e}")
            print("   这可能是因为服务未启动或任务不存在，而不是速率限制问题")
            
    except ImportError:
        print("⚠️ 未安装websockets库，跳过WebSocket测试")
        print("   安装: pip install websockets")

def test_rate_limiter_logic():
    """测试速率限制器逻辑."""
    
    print("⚙️ 测试速率限制器逻辑:")
    print("-" * 40)
    
    try:
        from src.api.middleware.rate_limit import RateLimiter
        
        # 创建测试限制器
        limiter = RateLimiter(max_requests=3, window_seconds=10)
        
        client_id = "test_client"
        
        print("测试基本限制功能:")
        
        # 应该允许前3个请求
        for i in range(3):
            allowed = limiter.is_allowed(client_id)
            remaining = limiter.get_remaining_requests(client_id)
            print(f"  请求 {i+1}: 允许={allowed}, 剩余={remaining}")
        
        # 第4个请求应该被拒绝
        allowed = limiter.is_allowed(client_id)
        remaining = limiter.get_remaining_requests(client_id)
        print(f"  请求 4: 允许={allowed}, 剩余={remaining}")
        
        if not allowed:
            print("✅ 速率限制器正确拒绝了超限请求")
        else:
            print("❌ 速率限制器没有正确工作")
        
        # 获取重置时间
        reset_time = limiter.get_reset_time(client_id)
        print(f"  重置时间: {reset_time}")
        
    except Exception as e:
        print(f"❌ 速率限制器逻辑测试失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主函数."""
    
    print("🤖 AI智能小说生成器 - 速率限制豁免测试")
    print("="*60)
    
    # 1. 测试速率限制器逻辑
    test_rate_limiter_logic()
    
    print("\n" + "="*60)
    
    # 2. 测试API速率限制豁免
    try:
        await test_rate_limit_exemption()
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        print("请确保API服务正在运行: python start_api.py")
    
    print("\n" + "="*60)
    
    # 3. 测试WebSocket豁免
    try:
        await test_websocket_exemption()
    except Exception as e:
        print(f"❌ WebSocket测试失败: {e}")
    
    print("\n" + "="*60)
    
    print("📊 测试总结:")
    print("✅ 修改了速率限制中间件，为以下路径提供豁免:")
    print("   - /api/v1/progress/* (所有进度查询接口)")
    print("   - /api/v1/ws/progress/* (WebSocket进度连接)")
    print("   - /health/* (健康检查接口)")
    print("   - WebSocket升级请求自动豁免")
    print()
    print("📝 豁免说明:")
    print("   - 进度查询接口需要频繁调用，不应被限制")
    print("   - WebSocket连接用于实时进度推送，不应被限制")
    print("   - 健康检查和状态查询是轻量级操作")
    print("   - 生成和导出接口仍然受到速率限制保护")
    print()
    print("🔧 如需调整:")
    print("   - 修改 src/api/middleware/rate_limit.py 中的 exempt_paths")
    print("   - 调整各类接口的速率限制参数")

if __name__ == "__main__":
    asyncio.run(main())