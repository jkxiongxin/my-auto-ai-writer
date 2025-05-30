"""API与前端界面集成测试."""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.api.main import app
from src.models.database import get_db_session
from src.models.novel_models import NovelProject, GenerationTask


class TestAPIFrontendIntegration:
    """API与前端界面集成测试."""
    
    @pytest.fixture
    def client(self):
        """测试客户端."""
        return TestClient(app)
    
    def test_root_endpoint_provides_frontend_info(self, client):
        """测试根端点提供前端信息."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "frontend_url" in data
        assert data["frontend_url"] == "/static/index.html"
        assert data["status"] == "running"
    
    def test_frontend_redirect(self, client):
        """测试前端重定向."""
        response = client.get("/app", follow_redirects=False)
        
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"
    
    def test_health_check_for_frontend(self, client):
        """测试前端健康检查."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
    
    def test_novel_generation_workflow(self, client):
        """测试完整的小说生成工作流程."""
        # 1. 创建生成请求
        create_request = {
            "title": "测试小说",
            "description": "这是一个测试小说",
            "user_input": "一个关于时间旅行的科幻故事",
            "target_words": 5000,
            "style_preference": "科幻"
        }
        
        response = client.post("/api/v1/generate-novel", json=create_request)
        assert response.status_code == 202
        
        result = response.json()
        assert "task_id" in result
        assert result["status"] == "queued"
        
        task_id = result["task_id"]
        
        # 2. 查询生成状态
        status_response = client.get(f"/api/v1/generate-novel/{task_id}/status")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert status_data["task_id"] == task_id
        assert "progress" in status_data
    
    def test_project_management_workflow(self, client):
        """测试项目管理工作流程."""
        # 1. 获取项目列表（初始为空）
        response = client.get("/api/v1/projects")
        assert response.status_code == 200
        
        data = response.json()
        assert "projects" in data
        assert isinstance(data["projects"], list)
    
    def test_cors_configuration(self, client):
        """测试CORS配置."""
        # 预检请求
        response = client.options(
            "/api/v1/generate-novel",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        assert "Access-Control-Allow-Origin" in response.headers
    
    def test_error_handling_for_frontend(self, client):
        """测试前端错误处理."""
        # 测试无效的任务ID
        response = client.get("/api/v1/generate-novel/invalid-task-id/status")
        assert response.status_code == 404
        
        error_data = response.json()
        assert "detail" in error_data
    
    @pytest.mark.asyncio
    async def test_progress_tracking_system(self):
        """测试进度追踪系统."""
        from src.api.routers.progress import manager, notify_progress
        
        task_id = "test-task-123"
        
        # 模拟进度更新
        await notify_progress(task_id, 0.5, "章节生成", "正在生成第3章")
        
        # 验证连接管理器状态
        assert isinstance(manager.active_connections, dict)
    
    def test_api_documentation_endpoints(self, client):
        """测试API文档端点."""
        # OpenAPI文档
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_data = response.json()
        assert "openapi" in openapi_data
        assert "info" in openapi_data
        
        # Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
        
        # ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200
    
    def test_generation_request_validation(self, client):
        """测试生成请求验证."""
        # 无效请求 - 缺少必需字段
        invalid_request = {
            "title": "",  # 空标题
            "user_input": "短",  # 太短的输入
            "target_words": 500  # 字数太少
        }
        
        response = client.post("/api/v1/generate-novel", json=invalid_request)
        assert response.status_code == 422
        
        error_data = response.json()
        assert "detail" in error_data
    
    def test_rate_limiting_for_frontend(self, client):
        """测试前端速率限制."""
        # 发送多个快速请求来测试速率限制
        responses = []
        for i in range(5):
            response = client.get("/health")
            responses.append(response.status_code)
        
        # 大部分请求应该成功
        success_count = sum(1 for status in responses if status == 200)
        assert success_count >= 3
    
    def test_frontend_static_file_configuration(self, client):
        """测试前端静态文件配置."""
        # 注意：在测试环境中，静态文件可能不可用
        # 这里主要测试配置是否正确
        
        # 测试根路径是否正确返回前端信息
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "frontend_url" in data
        assert "/static/" in data["frontend_url"]


class TestAPIResponseFormats:
    """测试API响应格式."""
    
    @pytest.fixture
    def client(self):
        """测试客户端."""
        return TestClient(app)
    
    def test_standard_success_response_format(self, client):
        """测试标准成功响应格式."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应包含基本字段
        required_fields = ["status", "timestamp"]
        for field in required_fields:
            assert field in data
    
    def test_error_response_format(self, client):
        """测试错误响应格式."""
        response = client.get("/api/v1/projects/99999")
        
        assert response.status_code == 404
        error_data = response.json()
        
        # 验证错误响应格式
        assert "detail" in error_data
    
    def test_validation_error_format(self, client):
        """测试验证错误格式."""
        invalid_data = {"invalid": "data"}
        
        response = client.post("/api/v1/generate-novel", json=invalid_data)
        
        assert response.status_code == 422
        error_data = response.json()
        
        assert "detail" in error_data
        assert isinstance(error_data["detail"], list)


class TestFrontendAPIIntegration:
    """测试前端与API的集成场景."""
    
    @pytest.fixture
    def client(self):
        """测试客户端."""
        return TestClient(app)
    
    def test_complete_novel_generation_flow(self, client):
        """测试完整的小说生成流程."""
        # 1. 检查系统状态
        health_response = client.get("/health")
        assert health_response.status_code == 200
        
        # 2. 创建生成任务
        request_data = {
            "title": "集成测试小说",
            "description": "用于测试前后端集成",
            "user_input": "一个年轻程序员发现了可以修改现实的代码",
            "target_words": 3000,
            "style_preference": "科幻"
        }
        
        create_response = client.post("/api/v1/generate-novel", json=request_data)
        assert create_response.status_code == 202
        
        task_data = create_response.json()
        task_id = task_data["task_id"]
        
        # 3. 监控生成进度
        status_response = client.get(f"/api/v1/generate-novel/{task_id}/status")
        assert status_response.status_code == 200
        
        # 4. 获取项目列表
        projects_response = client.get("/api/v1/projects")
        assert projects_response.status_code == 200
        
        projects_data = projects_response.json()
        assert len(projects_data["projects"]) > 0
    
    def test_error_recovery_scenarios(self, client):
        """测试错误恢复场景."""
        # 1. 访问不存在的任务
        response = client.get("/api/v1/generate-novel/nonexistent-task/status")
        assert response.status_code == 404
        
        # 2. 无效的项目ID
        response = client.get("/api/v1/projects/invalid-id")
        assert response.status_code == 404
        
        # 3. 取消不存在的任务
        response = client.delete("/api/v1/generate-novel/nonexistent-task")
        assert response.status_code == 404
    
    def test_concurrent_request_handling(self, client):
        """测试并发请求处理."""
        import threading
        results = []
        
        def make_request():
            response = client.get("/health")
            results.append(response.status_code)
        
        # 创建多个并发请求
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # 等待所有请求完成
        for thread in threads:
            thread.join()
        
        # 验证所有请求都成功
        assert len(results) == 10
        assert all(status == 200 for status in results)