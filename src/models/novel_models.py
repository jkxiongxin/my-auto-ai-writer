"""小说相关数据模型."""

from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class NovelProject(Base):
    """小说项目模型."""
    
    __tablename__ = 'novel_projects'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    user_input = Column(Text, nullable=False)
    target_words = Column(Integer, nullable=False)
    current_words = Column(Integer, default=0)
    style_preference = Column(String(100))
    status = Column(String(50), default="queued", index=True)
    progress = Column(Float, default=0.0)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    chapters = relationship("Chapter", back_populates="project", cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="project", cascade="all, delete-orphan")
    outlines = relationship("Outline", back_populates="project", cascade="all, delete-orphan")
    generation_tasks = relationship("GenerationTask", back_populates="project", cascade="all, delete-orphan")
    quality_metrics = relationship("QualityMetrics", back_populates="project", cascade="all, delete-orphan")


class Chapter(Base):
    """章节模型."""
    
    __tablename__ = 'chapters'
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('novel_projects.id'), nullable=False, index=True)
    chapter_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    word_count = Column(Integer, default=0)
    status = Column(String(50), default="draft")
    
    # 元数据
    outline_summary = Column(Text)
    key_events = Column(JSON)
    involved_characters = Column(JSON)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    project = relationship("NovelProject", back_populates="chapters")


class Character(Base):
    """角色模型."""
    
    __tablename__ = 'characters'
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('novel_projects.id'), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    importance = Column(String(50), default="secondary")  # main, secondary, minor
    description = Column(Text)
    
    # 角色档案
    profile = Column(JSON)  # 包含外貌、性格、背景等信息
    
    # 一致性追踪
    mentioned_chapters = Column(JSON)  # 出现的章节列表
    character_arc = Column(Text)  # 角色发展弧线
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    project = relationship("NovelProject", back_populates="characters")


class Outline(Base):
    """大纲模型."""
    
    __tablename__ = 'outlines'
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('novel_projects.id'), nullable=False, index=True)
    outline_type = Column(String(50), default="hierarchical")  # hierarchical, linear, three_act
    level = Column(Integer, default=1)  # 1=主大纲, 2=章节大纲, 3=段落大纲
    
    # 大纲内容
    title = Column(String(200))
    summary = Column(Text, nullable=False)
    structure_data = Column(JSON)  # 结构化大纲数据
    
    # 排序和层级
    parent_id = Column(Integer, ForeignKey('outlines.id'))
    sort_order = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    project = relationship("NovelProject", back_populates="outlines")
    children = relationship("Outline", backref="parent", remote_side="Outline.id")


class GenerationTask(Base):
    """生成任务模型."""
    
    __tablename__ = 'generation_tasks'
    
    id = Column(String(36), primary_key=True)  # UUID
    project_id = Column(Integer, ForeignKey('novel_projects.id'), nullable=False, index=True)
    
    # 任务状态
    status = Column(String(50), default="queued", index=True)  # queued, running, completed, failed, cancelled
    progress = Column(Float, default=0.0)
    current_step = Column(String(100))
    
    # 时间信息
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    estimated_completion = Column(DateTime)
    
    # 结果信息
    generation_time_seconds = Column(Float)
    quality_score = Column(Float)
    error_message = Column(Text)
    result_data = Column(JSON)
    
    # 配置信息
    generation_config = Column(JSON)
    
    # 关系
    project = relationship("NovelProject", back_populates="generation_tasks")


class QualityMetrics(Base):
    """质量指标模型."""
    
    __tablename__ = 'quality_metrics'
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('novel_projects.id'), nullable=False, index=True)
    
    # 质量分数
    overall_score = Column(Float, default=0.0)
    coherence_score = Column(Float, default=0.0)
    character_consistency_score = Column(Float, default=0.0)
    plot_consistency_score = Column(Float, default=0.0)
    writing_quality_score = Column(Float, default=0.0)
    
    # 详细指标
    metrics_data = Column(JSON)  # 详细的质量指标数据
    
    # 问题统计
    total_issues = Column(Integer, default=0)
    critical_issues = Column(Integer, default=0)
    warning_issues = Column(Integer, default=0)
    
    # 建议和修复
    suggestions = Column(JSON)
    auto_fixes_applied = Column(JSON)
    
    # 检查信息
    checked_at = Column(DateTime, default=func.now())
    check_version = Column(String(50))  # 质量检查器版本
    
    # 关系
    project = relationship("NovelProject", back_populates="quality_metrics")