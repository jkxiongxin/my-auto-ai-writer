"""用户相关数据模型."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    """用户模型."""
    
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # 用户信息
    full_name = Column(String(100))
    avatar_url = Column(String(500))
    bio = Column(Text)
    
    # 状态
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    
    # 偏好设置
    preferences = Column(JSON)  # 用户偏好配置
    
    # 统计信息
    total_projects = Column(Integer, default=0)
    total_words_generated = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime)


class UserSession(Base):
    """用户会话模型."""
    
    __tablename__ = 'user_sessions'
    
    id = Column(String(36), primary_key=True)  # Session ID
    user_id = Column(Integer, nullable=False, index=True)
    
    # 会话信息
    token_hash = Column(String(255), nullable=False, unique=True)
    device_info = Column(String(500))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # 状态
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    last_accessed_at = Column(DateTime, default=func.now())