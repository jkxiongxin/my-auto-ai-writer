"""项目设置测试 - 验证项目结构和依赖安装."""

import os
import sys
from pathlib import Path

import pytest


class TestProjectSetup:
    """测试项目基础设置."""

    def test_project_structure(self) -> None:
        """测试项目结构完整性."""
        # 获取项目根目录
        project_root = Path(__file__).parent.parent
        
        # 验证主要目录存在
        required_dirs = [
            "src/core",
            "src/models", 
            "src/api",
            "src/utils",
            "src/utils/providers",
            "tests/unit",
            "tests/integration",
            "tests/performance",
            "tests/validation",
            "tests/acceptance",
            "docs",
            "config",
            "scripts",
            "data/samples",
            "data/templates",
        ]
        
        for dir_path in required_dirs:
            full_path = project_root / dir_path
            assert full_path.exists(), f"目录不存在: {dir_path}"
            assert full_path.is_dir(), f"路径不是目录: {dir_path}"

    def test_required_files_exist(self) -> None:
        """测试必需文件存在."""
        project_root = Path(__file__).parent.parent
        
        required_files = [
            "pyproject.toml",
            "README.md",
            ".gitignore",
            ".env.example",
            ".pre-commit-config.yaml",
            "src/__init__.py",
            "src/core/__init__.py",
            "src/models/__init__.py",
            "src/api/__init__.py",
            "src/utils/__init__.py",
            "src/utils/providers/__init__.py",
        ]
        
        for file_path in required_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"文件不存在: {file_path}"
            assert full_path.is_file(), f"路径不是文件: {file_path}"

    def test_dependencies_installed(self) -> None:
        """测试依赖项正确安装."""
        # 测试主要依赖包是否可以导入
        try:
            import fastapi
            import pydantic
            import sqlalchemy
            import pytest
            import httpx
            import uvicorn
        except ImportError as e:
            pytest.fail(f"依赖包导入失败: {e}")

    def test_python_version(self) -> None:
        """测试Python版本要求."""
        assert sys.version_info >= (3, 11), f"需要Python 3.11+，当前版本: {sys.version}"

    def test_src_module_importable(self) -> None:
        """测试src模块可以导入."""
        # 添加src到Python路径
        project_root = Path(__file__).parent.parent
        src_path = project_root / "src"
        
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        # 测试各个模块可以导入
        try:
            import src
            # 暂时注释掉具体模块导入，因为还没有实现
            # import src.core
            # import src.models
            # import src.api
            # import src.utils
        except ImportError as e:
            pytest.fail(f"src模块导入失败: {e}")

    def test_project_metadata(self) -> None:
        """测试项目元数据."""
        project_root = Path(__file__).parent.parent
        
        # 测试pyproject.toml存在且格式正确
        pyproject_path = project_root / "pyproject.toml"
        assert pyproject_path.exists()
        
        # 读取并验证基本内容
        content = pyproject_path.read_text(encoding="utf-8")
        assert "ai-novel-generator" in content
        assert "fastapi" in content
        assert "pytest" in content

    def test_environment_template(self) -> None:
        """测试环境变量模板文件."""
        project_root = Path(__file__).parent.parent
        env_example_path = project_root / ".env.example"
        
        assert env_example_path.exists()
        content = env_example_path.read_text(encoding="utf-8")
        
        # 验证包含必要的配置项
        required_vars = [
            "OPENAI_API_KEY",
            "OLLAMA_BASE_URL", 
            "DATABASE_URL",
            "SECRET_KEY",
        ]
        
        for var in required_vars:
            assert var in content, f"环境变量模板缺少: {var}"

    def test_gitignore_configuration(self) -> None:
        """测试Git忽略文件配置."""
        project_root = Path(__file__).parent.parent
        gitignore_path = project_root / ".gitignore"
        
        assert gitignore_path.exists()
        content = gitignore_path.read_text(encoding="utf-8")
        
        # 验证包含重要的忽略规则
        important_ignores = [
            "__pycache__/",
            "*.py[cod]",  # 更现代的Python字节码文件模式
            ".env",
            "*.db",
            ".coverage",
            "dist/",
            "build/",
        ]
        
        for ignore_pattern in important_ignores:
            assert ignore_pattern in content, f"gitignore缺少规则: {ignore_pattern}"

    @pytest.mark.slow
    def test_pre_commit_hooks_installable(self) -> None:
        """测试pre-commit钩子可以安装."""
        project_root = Path(__file__).parent.parent
        precommit_path = project_root / ".pre-commit-config.yaml"
        
        assert precommit_path.exists()
        content = precommit_path.read_text(encoding="utf-8")
        
        # 验证包含基本的钩子
        expected_hooks = [
            "black",
            "flake8", 
            "mypy",
            "isort",
        ]
        
        for hook in expected_hooks:
            assert hook in content, f"pre-commit配置缺少钩子: {hook}"


if __name__ == "__main__":
    pytest.main([__file__])