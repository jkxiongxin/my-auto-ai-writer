"""API路由模块."""

from .health import router as health_router
from .generation import router as generation_router
from .projects import router as project_router
from .quality import router as quality_router
from .export import router as export_router

__all__ = [
    "health_router",
    "generation_router", 
    "project_router",
    "quality_router",
    "export_router",
]