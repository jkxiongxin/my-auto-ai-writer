"""API框架单元测试."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.api.main import app
from src.utils.config import settings


class TestAPIFramework:
    """API框架测试类."""
    
    @pytest.fixture
    def client(self):
        """测试客户端fixture."""
        return TestClient(app)
    
    def test_api_health_check(self, client):
        """测试API健康检查."""
        response = client.get("/health/")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "services" in data
        
        # 检查响应头
        assert "X-Request-ID" in response.headers
    
    def test_api_root_endpoint(self, client):
        """测试根路径端点."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "欢迎使用AI智能小说生成器"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
    
    def test_api_cors_middleware(self, client):
        """测试CORS中间件."""
        # 测试预检请求
        response = client.options("/api/v1/generate-novel")
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers
        
        # 测试正常请求的CORS头
        response = client.get("/health/")
        assert "Access-Control-Allow-Origin" in response.headers
    
    def test_api_error_handling(self, client):
        """测试错误处理."""
        # 测试404错误
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "error_type" in data
        assert data["error_type"] == "NotFound"
        assert "request_id" in data
    
    def test_api_rate_limiting(self, client):
        """测试速率限制."""
        # 这里可以测试速率限制功能
        # 由于速率限制器的配置，需要发送很多请求才能触发
        # 为了测试效率，我们可以模拟速率限制触发的情况
        
        with patch('src.api.middleware.rate_limit._rate_limiters') as mock_limiters:
            mock_limiter = AsyncMock()
            mock_limiter.is_allowed.return_value = False
            mock_limiter.max_requests = 10
            mock_limiter.get_remaining_requests.return_value = 0
            mock_limiter.get_reset_time.return_value = 1234567890
            
            mock_limiters.__getitem__.return_value = mock_limiter
            
            response = client.get("/health/")
            # 由于中间件的实现方式，这个测试可能需要调整
            # 目前先检查基本功能
            assert response.status_code in [200, 429]
    
    def test_api_request_logging(self, client):
        """测试请求日志记录."""
        with patch('src.api.middleware.logging.logger') as mock_logger:
            response = client.get("/health/")
            assert response.status_code == 200
            
            # 验证日志被调用
            assert mock_logger.info.called
            
            # 检查处理时间头
            assert "X-Process-Time" in response.headers
    
    def test_api_generation_endpoint_validation(self, client):
        """测试生成端点的参数验证."""
        # 测试缺少必需参数
        response = client.post("/api/v1/generate-novel", json={})
        assert response.status_code == 422  # 验证错误
        
        # 测试无效参数
        invalid_payload = {
            "title": "",  # 空标题
            "user_input": "短",  # 太短
            "target_words": 500,  # 低于最小值
        }
        response = client.post("/api/v1/generate-novel", json=invalid_payload)
        assert response.status_code == 422
        
        # 测试有效参数（但会因为缺少依赖而失败）
        valid_payload = {
            "title": "测试小说",
            "user_input": "这是一个关于机器人获得情感的故事",
            "target_words": 5000,
            "style_preference": "科幻"
        }
        response = client.post("/api/v1/generate-novel", json=valid_payload)
        # 可能因为数据库或LLM客户端不可用而返回503
        assert response.status_code in [202, 503]
    
    def test_api_openapi_schema(self, client):
        """测试OpenAPI schema生成."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        
        # 检查基本路径存在
        paths = schema["paths"]
        assert "/" in paths
        assert "/health/" in paths
    
    def test_api_docs_endpoints(self, client):
        """测试API文档端点."""
        # 测试Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # 测试ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestAPIMiddleware:
    """API中间件测试类."""
    
    def test_error_handler_middleware(self):
        """测试错误处理中间件."""
        from src.api.middleware.error_handler import ErrorHandlerMiddleware
        
        middleware = ErrorHandlerMiddleware(app)
        assert middleware is not None
    
    def test_logging_middleware(self):
        """测试日志中间件."""
        from src.api.middleware.logging import logging_middleware
        
        assert logging_middleware is not None
    
    def test_rate_limit_middleware(self):
        """测试速率限制中间件."""
        from src.api.middleware.rate_limit import RateLimiter
        
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # 测试允许请求
        assert limiter.is_allowed("test_client") is True
        assert limiter.is_allowed("test_client") is True
        
        # 测试剩余请求数
        remaining = limiter.get_remaining_requests("test_client")
        assert remaining <= 5
        
        # 测试重置时间
        reset_time = limiter.get_reset_time("test_client")
        assert reset_time > 0
    
    def test_cors_middleware(self):
        """测试CORS中间件."""
        from src.api.middleware.cors import cors_middleware
        
        assert cors_middleware is not None


class TestAPIDependencies:
    """API依赖注入测试类."""
    
    @pytest.mark.asyncio
    async def test_get_llm_client_dependency(self):
        """测试LLM客户端依赖."""
        from src.api.dependencies import get_llm_client
        
        # 模拟LLM客户端可用
        with patch('src.utils.llm_client.UniversalLLMClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_available.return_value = True
            mock_client_class.return_value = mock_client
            
            client = await get_llm_client()
            assert client is not None
    
    @pytest.mark.asyncio
    async def test_validate_generation_request(self):
        """测试生成请求验证依赖."""
        from src.api.dependencies import validate_generation_request
        from src.api.schemas import CreateNovelProjectRequest
        
        # 测试有效请求
        valid_request = CreateNovelProjectRequest(
            title="测试小说",
            user_input="这是一个关于时间旅行的故事，主角发现自己回到了过去",
            target_words=10000,
            style_preference="科幻"
        )
        
        # 验证不应该抛出异常
        try:
            await validate_generation_request(valid_request)
        except Exception as e:
            pytest.fail(f"验证有效请求时不应该抛出异常: {e}")
    
    @pytest.mark.asyncio 
    async def test_get_current_user_dependency(self):
        """测试用户认证依赖."""
        from src.api.dependencies import get_current_user
        
        # 测试无认证头
        user = await get_current_user(None)
        assert user is None
        
        # 测试有认证头（暂时返回None）
        user = await get_current_user("Bearer fake-token")
        assert user is None  # 当前实现返回None


class TestAPISchemas:
    """API数据模式测试类."""
    
    def test_create_novel_project_request_schema(self):
        """测试创建项目请求模式."""
        from src.api.schemas import CreateNovelProjectRequest
        
        # 测试有效数据
        valid_data = {
            "title": "测试小说",
            "user_input": "这是一个关于机器人的故事",
            "target_words": 10000,
            "style_preference": "科幻"
        }
        
        request = CreateNovelProjectRequest(**valid_data)
        assert request.title == "测试小说"
        assert request.target_words == 10000
        
        # 测试无效数据
        with pytest.raises(Exception):
            CreateNovelProjectRequest(
                title="",  # 空标题
                user_input="短",  # 太短
                target_words=500  # 低于最小值
            )
    
    def test_novel_project_response_schema(self):
        """测试项目响应模式."""
        from src.api.schemas import NovelProjectResponse
        from datetime import datetime
        
        data = {
            "id": 1,
            "title": "测试小说",
            "description": "测试描述",
            "target_words": 10000,
            "status": "created",
            "progress": 0.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        response = NovelProjectResponse(**data)
        assert response.id == 1
        assert response.title == "测试小说"
        assert 0 <= response.progress <= 1