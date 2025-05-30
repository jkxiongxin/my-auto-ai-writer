"""数据库模块单元测试."""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.models.database import (
    Base,
    DatabaseManager,
    create_tables,
    get_database_session,
)
from src.models.novel_models import (
    NovelProject,
    Chapter,
    Character,
    Outline,
    GenerationTask,
    QualityMetrics,
)


class TestDatabaseSchema:
    """测试数据库表结构."""

    @pytest.fixture
    def temp_database(self) -> Generator[str, None, None]:
        """创建临时数据库."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            temp_db_path = temp_file.name
        
        yield f"sqlite:///{temp_db_path}"
        
        # 清理临时文件
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)

    def test_database_tables_creation(self, temp_database: str) -> None:
        """测试数据库表创建."""
        # 创建数据库引擎
        engine = create_engine(temp_database)
        
        # 创建表
        create_tables(engine)
        
        # 验证表是否创建成功
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='novel_projects'"))
            assert result.fetchone() is not None, "novel_projects表未创建"
            
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='chapters'"))
            assert result.fetchone() is not None, "chapters表未创建"
            
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='characters'"))
            assert result.fetchone() is not None, "characters表未创建"

    def test_novel_project_model_fields(self) -> None:
        """测试小说项目模型字段."""
        # 验证NovelProject模型有必要的字段
        required_fields = [
            "id", "title", "description", "user_input", 
            "target_words", "style_preference", "status", 
            "progress", "created_at", "updated_at"
        ]
        
        for field in required_fields:
            assert hasattr(NovelProject, field), f"NovelProject缺少字段: {field}"

    def test_chapter_model_fields(self) -> None:
        """测试章节模型字段."""
        required_fields = [
            "id", "project_id", "chapter_number", "title", 
            "content", "word_count", "status", "created_at", "updated_at"
        ]
        
        for field in required_fields:
            assert hasattr(Chapter, field), f"Chapter缺少字段: {field}"

    def test_character_model_fields(self) -> None:
        """测试角色模型字段."""
        required_fields = [
            "id", "project_id", "name", "profile", 
            "created_at", "updated_at"
        ]
        
        for field in required_fields:
            assert hasattr(Character, field), f"Character缺少字段: {field}"


class TestDatabaseManager:
    """测试数据库管理器."""

    @pytest.fixture
    def temp_database(self) -> Generator[str, None, None]:
        """创建临时数据库."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            temp_db_path = temp_file.name
        
        yield f"sqlite:///{temp_db_path}"
        
        # 清理临时文件
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)

    def test_database_manager_initialization(self, temp_database: str) -> None:
        """测试数据库管理器初始化."""
        manager = DatabaseManager(temp_database)
        
        assert manager.database_url == temp_database
        assert manager.engine is not None
        assert manager.session_factory is not None

    def test_database_session_creation(self, temp_database: str) -> None:
        """测试数据库会话创建."""
        manager = DatabaseManager(temp_database)
        
        with manager.get_session() as session:
            assert session is not None
            # 验证会话可以执行查询
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1

    def test_get_database_session_function(self, temp_database: str) -> None:
        """测试数据库会话获取函数."""
        # 设置临时数据库URL
        original_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = temp_database
        
        try:
            session = next(get_database_session())
            assert session is not None
            session.close()
        finally:
            # 恢复环境变量
            if original_url:
                os.environ["DATABASE_URL"] = original_url
            elif "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]


class TestDatabaseOperations:
    """测试数据库操作."""

    @pytest.fixture
    def temp_database_session(self) -> Generator:
        """创建临时数据库会话."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            temp_db_path = temp_file.name
        
        database_url = f"sqlite:///{temp_db_path}"
        engine = create_engine(database_url)
        create_tables(engine)
        
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        yield session
        
        session.close()
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)

    def test_create_novel_project(self, temp_database_session) -> None:
        """测试创建小说项目."""
        project = NovelProject(
            title="测试小说",
            description="这是一个测试小说",
            user_input="一个关于机器人的故事",
            target_words=10000,
            style_preference="科幻"
        )
        
        temp_database_session.add(project)
        temp_database_session.commit()
        
        # 验证项目已保存
        saved_project = temp_database_session.query(NovelProject).filter_by(title="测试小说").first()
        assert saved_project is not None
        assert saved_project.title == "测试小说"
        assert saved_project.target_words == 10000

    def test_create_chapter_with_project_relationship(self, temp_database_session) -> None:
        """测试创建章节并关联到项目."""
        # 先创建项目
        project = NovelProject(
            title="测试小说",
            user_input="测试输入",
            target_words=5000
        )
        temp_database_session.add(project)
        temp_database_session.commit()
        
        # 创建章节
        chapter = Chapter(
            project_id=project.id,
            chapter_number=1,
            title="第一章",
            content="这是第一章的内容...",
            word_count=500
        )
        temp_database_session.add(chapter)
        temp_database_session.commit()
        
        # 验证关系
        saved_chapter = temp_database_session.query(Chapter).filter_by(title="第一章").first()
        assert saved_chapter is not None
        assert saved_chapter.project_id == project.id
        assert saved_chapter.project.title == "测试小说"

    def test_create_character_with_project_relationship(self, temp_database_session) -> None:
        """测试创建角色并关联到项目."""
        # 先创建项目
        project = NovelProject(
            title="测试小说",
            user_input="测试输入",
            target_words=5000
        )
        temp_database_session.add(project)
        temp_database_session.commit()
        
        # 创建角色
        character = Character(
            project_id=project.id,
            name="主角",
            profile={
                "age": 25,
                "personality": "勇敢",
                "background": "普通学生"
            }
        )
        temp_database_session.add(character)
        temp_database_session.commit()
        
        # 验证关系
        saved_character = temp_database_session.query(Character).filter_by(name="主角").first()
        assert saved_character is not None
        assert saved_character.project_id == project.id
        assert saved_character.project.title == "测试小说"
        assert saved_character.profile["age"] == 25


if __name__ == "__main__":
    pytest.main([__file__])