"""依赖注入模块."""

from typing import Optional

from fastapi import Depends, HTTPException, Header
from pydantic import ValidationError

from src.utils.llm_client import UniversalLLMClient
from src.utils.logger import get_logger
from src.models.user_models import User
from .schemas import CreateNovelProjectRequest

logger = get_logger(__name__)


async def get_llm_client() -> UniversalLLMClient:
    """获取LLM客户端实例."""
    
    try:
        client = UniversalLLMClient()
        
        # 检查是否有可用的提供商
        if not client.providers:
            raise HTTPException(
                status_code=503,
                detail="没有可用的LLM提供商，请检查配置"
            )
        
        # 尝试测试一个提供商的可用性
        try:
            test_results = await client.test_providers()
            healthy_providers = [name for name, result in test_results.items() if result.get('healthy', False)]
            
            if not healthy_providers:
                logger.warning("所有LLM提供商都不健康，但仍允许请求")
        except Exception as test_error:
            logger.warning(f"测试提供商健康状态失败: {test_error}")
        
        return client
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取LLM客户端失败: {e}")
        raise HTTPException(
            status_code=503,
            detail="LLM服务初始化失败"
        )


async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """获取当前用户（暂时返回None，后续实现认证）."""
    
    # TODO: 实现用户认证逻辑
    # 这里应该解析JWT token，验证用户身份
    
    if authorization:
        # 简单的token验证示例
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="无效的认证格式"
            )
        
        token = authorization[7:]  # 移除 "Bearer " 前缀
        
        # TODO: 验证token并获取用户信息
        # user = await verify_token(token)
        # return user
        
        logger.info(f"收到认证token: {token[:10]}...")
    
    # 暂时返回None，允许未认证访问
    return None


async def get_generation_service():
    """获取生成服务实例."""
    
    # TODO: 实现生成服务的依赖注入
    # 这里应该返回小说生成服务的实例
    
    from src.core.novel_generator import NovelGenerator
    
    try:
        # 这里应该从服务容器中获取实例
        # 暂时直接创建实例
        return NovelGenerator()
    except Exception as e:
        logger.error(f"获取生成服务失败: {e}")
        raise HTTPException(
            status_code=503,
            detail="生成服务不可用"
        )


def validate_generation_request() -> None:
    """验证生成请求参数（简化版本）."""
    # 这个依赖现在只是一个占位符
    # 实际的验证逻辑会在Pydantic模型层面和路由处理中进行
    pass


async def validate_request_data(request: CreateNovelProjectRequest) -> None:
    """验证生成请求数据."""
    
    try:
        # 验证用户输入长度
        if len(request.user_input.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="用户输入过短，至少需要10个字符"
            )
        
        if len(request.user_input.strip()) > 2000:
            raise HTTPException(
                status_code=400,
                detail="用户输入过长，最多2000个字符"
            )
        
        # 验证标题
        if len(request.title.strip()) < 1:
            raise HTTPException(
                status_code=400,
                detail="标题不能为空"
            )
        
        if len(request.title.strip()) > 200:
            raise HTTPException(
                status_code=400,
                detail="标题过长，最多200个字符"
            )
        
        # 验证目标字数
        if request.target_words < 1000:
            raise HTTPException(
                status_code=400,
                detail="目标字数不能少于1000字"
            )
        
        if request.target_words > 200000:
            raise HTTPException(
                status_code=400,
                detail="目标字数不能超过200000字"
            )
        
        # 验证描述长度
        if request.description and len(request.description) > 1000:
            raise HTTPException(
                status_code=400,
                detail="描述过长，最多1000个字符"
            )
        
        # 验证风格偏好
        valid_styles = [
            "科幻", "奇幻", "悬疑", "推理", "言情", "历史", "武侠",
            "现实主义", "青春", "都市", "军事", "穿越", "重生"
        ]
        
        if request.style_preference and request.style_preference not in valid_styles:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的风格类型，支持的风格: {', '.join(valid_styles)}"
            )
        
        logger.info("生成请求验证通过", extra={"title": request.title, "target_words": request.target_words})
        
    except HTTPException:
        raise
    except ValidationError as e:
        logger.warning(f"请求参数验证失败: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"请求参数无效: {str(e)}"
        )
    except Exception as e:
        logger.error(f"验证请求时发生错误: {e}")
        raise HTTPException(
            status_code=500,
            detail="请求验证失败"
        )


async def get_database_session():
    """获取数据库会话."""
    
    from src.models.database import get_db_session
    
    try:
        async with get_db_session() as session:
            yield session
    except Exception as e:
        logger.error(f"获取数据库会话失败: {e}")
        raise HTTPException(
            status_code=503,
            detail="数据库服务不可用"
        )


def require_auth(user: Optional[User] = Depends(get_current_user)) -> User:
    """要求用户认证的依赖."""
    
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="需要用户认证"
        )
    
    return user


def require_admin(user: User = Depends(require_auth)) -> User:
    """要求管理员权限的依赖."""
    
    # TODO: 检查用户是否为管理员
    # if not user.is_admin:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="需要管理员权限"
    #     )
    
    return user


async def validate_project_access(
    project_id: int,
    user: Optional[User] = Depends(get_current_user)
) -> int:
    """验证用户对项目的访问权限."""
    
    # TODO: 实现项目访问权限检查
    # 检查用户是否有权限访问指定项目
    
    if user is None:
        # 暂时允许未认证用户访问所有项目
        logger.info(f"未认证用户访问项目: {project_id}")
    else:
        logger.info(f"用户 {user.id} 访问项目: {project_id}")
    
    return project_id