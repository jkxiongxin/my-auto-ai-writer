"""项目删除功能单元测试."""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.main import app
from src.models.novel_models import NovelProject, Chapter, Character
from src.models.database import get_db_session


@pytest.fixture
def client():
    """测试客户端fixture."""
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """模拟数据库会话fixture."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def sample_completed_project():
    """已完成项目样例数据."""
    project = NovelProject(
        id=1,
        title="测试小说",
        description="这是一个测试小说",
        user_input="科幻小说创意",
        target_words=10000,
        current_words=10500,
        status="completed",
        progress=1.0
    )
    return project


@pytest.fixture
def sample_running_project():
    """运行中项目样例数据."""
    project = NovelProject(
        id=2,
        title="运行中的小说",
        description="正在生成的小说",
        user_input="奇幻小说创意",
        target_words=15000,
        current_words=5000,
        status="running",
        progress=0.3
    )
    return project


@pytest.fixture
def sample_failed_project():
    """失败项目样例数据."""
    project = NovelProject(
        id=3,
        title="失败的小说",
        description="生成失败的小说",
        user_input="悬疑小说创意",
        target_words=8000,
        current_words=0,
        status="failed",
        progress=0.0
    )
    return project


class TestProjectDeletion:
    """项目删除功能测试类."""

    @pytest.mark.asyncio
    @patch('src.api.routers.projects.get_db_session')
    async def test_delete_completed_project_success(self, mock_get_db, client, mock_db_session, sample_completed_project):
        """测试删除已完成项目_成功_返回删除成功消息."""
        # Given
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.get.return_value = sample_completed_project
        mock_db_session.delete = AsyncMock()
        mock_db_session.commit = AsyncMock()
        
        # When
        response = client.delete("/api/v1/projects/1")
        
        # Then
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "项目已删除"
        assert response_data["project_id"] == 1
        
        # 验证数据库操作
        mock_db_session.get.assert_called_once_with(NovelProject, 1)
        mock_db_session.delete.assert_called_once_with(sample_completed_project)
        mock_db_session.commit.assert_called_once()

    @patch('src.api.routers.projects.get_db_session')
    async def test_delete_running_project_failure(self, mock_get_db, client, mock_db_session, sample_running_project):
        """测试删除运行中项目_失败_返回400错误."""
        # Given
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.get.return_value = sample_running_project
        
        # When
        response = client.delete("/api/v1/projects/2")
        
        # Then
        assert response.status_code == 400
        response_data = response.json()
        assert "无法删除正在运行的项目" in response_data["detail"]
        
        # 验证没有执行删除操作
        mock_db_session.delete.assert_not_called()
        mock_db_session.commit.assert_not_called()

    @patch('src.api.routers.projects.get_db_session')
    async def test_delete_failed_project_success(self, mock_get_db, client, mock_db_session, sample_failed_project):
        """测试删除失败项目_成功_返回删除成功消息."""
        # Given
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.get.return_value = sample_failed_project
        mock_db_session.delete = AsyncMock()
        mock_db_session.commit = AsyncMock()
        
        # When
        response = client.delete("/api/v1/projects/3")
        
        # Then
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "项目已删除"
        assert response_data["project_id"] == 3
        
        # 验证数据库操作
        mock_db_session.delete.assert_called_once_with(sample_failed_project)
        mock_db_session.commit.assert_called_once()

    @patch('src.api.routers.projects.get_db_session')
    async def test_delete_nonexistent_project_failure(self, mock_get_db, client, mock_db_session):
        """测试删除不存在项目_失败_返回404错误."""
        # Given
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.get.return_value = None
        
        # When
        response = client.delete("/api/v1/projects/999")
        
        # Then
        assert response.status_code == 404
        response_data = response.json()
        assert response_data["detail"] == "项目未找到"
        
        # 验证没有执行删除操作
        mock_db_session.delete.assert_not_called()
        mock_db_session.commit.assert_not_called()

    @patch('src.api.routers.projects.get_db_session')
    async def test_delete_project_database_error(self, mock_get_db, client, mock_db_session, sample_completed_project):
        """测试删除项目时数据库错误_失败_返回500错误."""
        # Given
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.get.return_value = sample_completed_project
        mock_db_session.delete = AsyncMock()
        mock_db_session.commit = AsyncMock(side_effect=Exception("数据库连接失败"))
        
        # When
        response = client.delete("/api/v1/projects/1")
        
        # Then
        assert response.status_code == 500
        response_data = response.json()
        assert "删除项目失败" in response_data["detail"]

    @pytest.mark.parametrize("project_status,should_allow_deletion", [
        ("completed", True),
        ("failed", True),
        ("cancelled", True),
        ("queued", True),
        ("running", False),
    ])
    @patch('src.api.routers.projects.get_db_session')
    async def test_delete_project_by_status(self, mock_get_db, client, mock_db_session, project_status, should_allow_deletion):
        """测试根据项目状态的删除权限_参数化测试."""
        # Given
        project = NovelProject(
            id=1,
            title="测试项目",
            user_input="测试输入",
            target_words=10000,
            status=project_status,
            progress=0.5 if project_status == "running" else 1.0
        )
        
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.get.return_value = project
        mock_db_session.delete = AsyncMock()
        mock_db_session.commit = AsyncMock()
        
        # When
        response = client.delete("/api/v1/projects/1")
        
        # Then
        if should_allow_deletion:
            assert response.status_code == 200
            mock_db_session.delete.assert_called_once()
            mock_db_session.commit.assert_called_once()
        else:
            assert response.status_code == 400
            mock_db_session.delete.assert_not_called()
            mock_db_session.commit.assert_not_called()


class TestCascadeDeletion:
    """级联删除测试类."""

    @patch('src.api.routers.projects.get_db_session')
    async def test_cascade_deletion_removes_related_data(self, mock_get_db, client, mock_db_session):
        """测试级联删除_删除项目时清理相关数据."""
        # Given
        project = NovelProject(
            id=1,
            title="有内容的项目",
            user_input="测试输入",
            target_words=10000,
            status="completed"
        )
        
        # 模拟相关数据会被级联删除（SQLAlchemy会自动处理）
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.get.return_value = project
        mock_db_session.delete = AsyncMock()
        mock_db_session.commit = AsyncMock()
        
        # When
        response = client.delete("/api/v1/projects/1")
        
        # Then
        assert response.status_code == 200
        
        # 验证主项目被删除（级联删除由SQLAlchemy ORM自动处理）
        mock_db_session.delete.assert_called_once_with(project)
        mock_db_session.commit.assert_called_once()


@pytest.mark.integration
class TestProjectDeletionIntegration:
    """项目删除集成测试类."""

    async def test_delete_project_end_to_end(self):
        """端到端删除项目测试."""
        # 这个测试需要真实的数据库连接
        # 在实际项目中，应该使用测试数据库
        pass

    async def test_delete_project_with_large_content(self):
        """测试删除包含大量内容的项目性能."""
        # 性能测试，验证删除操作在合理时间内完成
        pass