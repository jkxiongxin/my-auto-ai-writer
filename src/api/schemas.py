"""API数据模式定义."""

from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field


# 请求模型
class CreateNovelProjectRequest(BaseModel):
    """创建小说项目请求模型."""
    
    title: str = Field(..., min_length=1, max_length=200, description="小说标题")
    description: Optional[str] = Field(None, max_length=1000, description="小说描述")
    user_input: str = Field(..., min_length=10, max_length=2000, description="用户创意输入")
    target_words: int = Field(..., ge=1000, le=200000, description="目标字数")
    style_preference: Optional[str] = Field(None, description="风格偏好")


class UpdateProjectRequest(BaseModel):
    """更新项目请求模型."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="小说标题")
    description: Optional[str] = Field(None, max_length=1000, description="小说描述")
    target_words: Optional[int] = Field(None, ge=1000, le=200000, description="目标字数")
    style_preference: Optional[str] = Field(None, description="风格偏好")


# 响应模型
class NovelProjectResponse(BaseModel):
    """小说项目响应模型."""
    
    id: int
    title: str
    description: Optional[str]
    target_words: int
    status: str
    progress: float = Field(ge=0, le=1, description="生成进度(0-1)")
    created_at: datetime
    updated_at: datetime
    current_words: Optional[int] = None
    style_preference: Optional[str] = None
    task_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """项目列表响应模型."""
    
    projects: List[NovelProjectResponse]
    total: int
    skip: int
    limit: int


class GenerationStatusResponse(BaseModel):
    """生成状态响应模型."""
    
    task_id: str
    project_id: int
    status: str
    progress: float = Field(ge=0, le=1)
    current_step: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class GenerationResultResponse(BaseModel):
    """生成结果响应模型."""
    
    task_id: str
    project_id: int
    status: str
    title: str
    total_words: int
    chapter_count: int
    quality_score: Optional[float] = None
    generation_time_seconds: Optional[float] = None
    completed_at: Optional[datetime] = None
    result_data: Dict[str, Any] = Field(default_factory=dict)


class ProjectStatisticsResponse(BaseModel):
    """项目统计响应模型."""
    
    project_id: int
    chapter_count: int
    character_count: int
    total_words: int
    target_words: int
    progress_percentage: float
    word_progress_percentage: float
    status: str
    created_at: datetime
    last_updated: datetime


class ChapterResponse(BaseModel):
    """章节响应模型."""
    
    id: int
    project_id: int
    chapter_number: int
    title: str
    word_count: int
    status: str
    created_at: datetime
    updated_at: datetime
    content: Optional[str] = None
    
    class Config:
        from_attributes = True


class CharacterResponse(BaseModel):
    """角色响应模型."""
    
    id: int
    project_id: int
    name: str
    importance: str
    description: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class QualityReportResponse(BaseModel):
    """质量报告响应模型."""
    
    project_id: int
    overall_score: float = Field(ge=0, le=10)
    coherence_score: float = Field(ge=0, le=10)
    consistency_issues: List[Dict[str, Any]]
    character_issues: List[Dict[str, Any]]
    plot_issues: List[Dict[str, Any]]
    suggestions: List[str]
    checked_at: str


class QualityMetricsResponse(BaseModel):
    """质量指标响应模型."""
    
    project_id: int
    metrics: Dict[str, Any]


# 错误响应模型
class ErrorResponse(BaseModel):
    """错误响应模型."""
    
    detail: str
    error_type: str
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationErrorResponse(ErrorResponse):
    """验证错误响应模型."""
    
    errors: List[Dict[str, Any]]


# 健康检查模型
class HealthCheckResponse(BaseModel):
    """健康检查响应模型."""
    
    status: str
    timestamp: datetime
    version: str
    uptime_seconds: float
    services: Dict[str, Any]


class DetailedHealthResponse(HealthCheckResponse):
    """详细健康检查响应模型."""
    
    system_info: Dict[str, Any]
    performance_metrics: Dict[str, Any]


# 配置模型
class GenerationConfigRequest(BaseModel):
    """生成配置请求模型."""
    
    temperature: float = Field(0.7, ge=0, le=1, description="生成温度")
    max_tokens: int = Field(2000, ge=100, le=4000, description="最大token数")
    provider: Optional[str] = Field(None, description="指定LLM提供商")
    model: Optional[str] = Field(None, description="指定模型")
    retry_count: int = Field(3, ge=1, le=10, description="重试次数")


class ExportConfigRequest(BaseModel):
    """导出配置请求模型."""
    
    format: str = Field("txt", description="导出格式")
    include_metadata: bool = Field(True, description="是否包含元数据")
    include_characters: bool = Field(True, description="是否包含角色信息")
    include_outline: bool = Field(True, description="是否包含大纲")
    split_chapters: bool = Field(False, description="是否分章节导出")


# 分页模型
class PaginationParams(BaseModel):
    """分页参数模型."""
    
    skip: int = Field(0, ge=0, description="跳过的记录数")
    limit: int = Field(100, ge=1, le=1000, description="返回的记录数")


class PaginatedResponse(BaseModel):
    """分页响应基础模型."""
    
    total: int
    skip: int
    limit: int
    has_more: bool
    
    @property
    def page_number(self) -> int:
        """当前页号（从1开始）."""
        return (self.skip // self.limit) + 1
    
    @property
    def total_pages(self) -> int:
        """总页数."""
        return (self.total + self.limit - 1) // self.limit


# 搜索模型
class SearchParams(BaseModel):
    """搜索参数模型."""
    
    query: Optional[str] = Field(None, min_length=1, max_length=100, description="搜索关键词")
    status: Optional[str] = Field(None, description="状态过滤")
    style: Optional[str] = Field(None, description="风格过滤")
    min_words: Optional[int] = Field(None, ge=0, description="最小字数")
    max_words: Optional[int] = Field(None, ge=0, description="最大字数")
    created_after: Optional[datetime] = Field(None, description="创建时间起始")
    created_before: Optional[datetime] = Field(None, description="创建时间结束")


# 批量操作模型
class BatchOperationRequest(BaseModel):
    """批量操作请求模型."""
    
    project_ids: List[int] = Field(..., min_items=1, max_items=100, description="项目ID列表")
    operation: str = Field(..., description="操作类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="操作参数")


class BatchOperationResponse(BaseModel):
    """批量操作响应模型."""
    
    total_requested: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]