"""质量检查路由."""

from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.utils.logger import get_logger
from src.models.database import get_db_session
from src.models.novel_models import NovelProject, Chapter, Character
from src.core.quality_integration import EnhancedQualityChecker, QualityIntegrationError
from src.core.character_system import Character as CoreCharacter
from src.utils.llm_client import UniversalLLMClient
from ..schemas import QualityReportResponse, QualityMetricsResponse
from ..dependencies import get_llm_client

logger = get_logger(__name__)

router = APIRouter()


class QualityCheckRequest(BaseModel):
    """质量检查请求模型."""
    
    project_id: int
    check_types: List[str] = ["consistency", "coherence", "character", "plot", "language", "style"]
    include_suggestions: bool = True
    style_guide: Optional[str] = None


class IntelligentRevisionRequest(BaseModel):
    """智能修订请求模型."""
    
    project_id: int
    target_score: float = 8.0
    max_iterations: int = 3
    style_guide: Optional[str] = None


class BatchQualityCheckRequest(BaseModel):
    """批量质量检查请求模型."""
    
    project_id: int
    chapter_ids: Optional[List[int]] = None  # 如果为None则检查所有章节
    style_guide: Optional[str] = None


class EnhancedQualityReportResponse(BaseModel):
    """增强质量报告响应模型."""
    
    project_id: int
    overall_score: float
    grade: str
    assessment_time: str
    word_count: int
    chapter_count: int
    character_count: int
    quality_dimensions: Dict[str, Any]
    consistency: Dict[str, Any]
    revision_suggestions: List[Dict[str, Any]]
    summary: str
    recommendations: List[str]


class IntelligentRevisionResponse(BaseModel):
    """智能修订响应模型."""
    
    project_id: int
    original_score: float
    final_score: float
    improvement: float
    iterations_performed: int
    revision_history: List[Dict[str, Any]]
    final_report: Dict[str, Any]


class BatchQualityReportResponse(BaseModel):
    """批量质量报告响应模型."""
    
    project_id: int
    chapter_reports: List[Dict[str, Any]]
    overall_statistics: Dict[str, Any]


@router.post("/projects/{project_id}/enhanced-quality-check", response_model=EnhancedQualityReportResponse)
async def enhanced_quality_check(
    project_id: int,
    request: QualityCheckRequest = None,
    llm_client: UniversalLLMClient = Depends(get_llm_client)
) -> EnhancedQualityReportResponse:
    """执行增强质量检查."""
    
    try:
        async with get_db_session() as session:
            # 检查项目是否存在
            project = await session.get(NovelProject, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            # 获取项目数据
            chapters, characters = await _get_project_data(project_id, session)
            
            if not chapters:
                raise HTTPException(status_code=400, detail="项目没有章节内容")
            
            # 创建增强质量检查器
            quality_checker = EnhancedQualityChecker(llm_client)
            
            # 合并所有章节内容进行检查
            full_content = "\n\n".join([chapter.content for chapter in chapters if chapter.content])
            
            # 转换角色格式
            core_characters = _convert_to_core_characters(characters)
            
            # 创建章节信息
            chapter_info = {
                "title": f"{project.title} - 完整内容",
                "chapter_count": len(chapters),
                "key_events": [],  # 可以从章节中提取
                "previous_events": [],
                "characters_involved": [char.name for char in characters],
                "setting": "小说世界"
            }
            
            # 执行全面质量检查
            report = await quality_checker.comprehensive_quality_check(
                content=full_content,
                characters=core_characters,
                chapter_info=chapter_info,
                style_guide=request.style_guide if request else None,
                include_suggestions=request.include_suggestions if request else True
            )
            
            logger.info(f"增强质量检查完成: project_id={project_id}")
            
            return EnhancedQualityReportResponse(
                project_id=project_id,
                **report
            )
            
    except HTTPException:
        raise
    except QualityIntegrationError as e:
        logger.error(f"质量检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"增强质量检查失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"增强质量检查失败: {str(e)}"
        )


@router.post("/projects/{project_id}/intelligent-revision", response_model=IntelligentRevisionResponse)
async def intelligent_revision(
    project_id: int,
    request: IntelligentRevisionRequest,
    llm_client: UniversalLLMClient = Depends(get_llm_client)
) -> IntelligentRevisionResponse:
    """执行智能修订."""
    
    try:
        async with get_db_session() as session:
            # 检查项目是否存在
            project = await session.get(NovelProject, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            # 获取项目数据
            chapters, characters = await _get_project_data(project_id, session)
            
            if not chapters:
                raise HTTPException(status_code=400, detail="项目没有章节内容")
            
            # 创建增强质量检查器
            quality_checker = EnhancedQualityChecker(llm_client)
            
            # 合并所有章节内容
            full_content = "\n\n".join([chapter.content for chapter in chapters if chapter.content])
            original_content = full_content
            
            # 转换角色格式
            core_characters = _convert_to_core_characters(characters)
            
            # 创建章节信息
            chapter_info = {
                "title": f"{project.title} - 智能修订",
                "chapter_count": len(chapters),
                "key_events": [],
                "previous_events": [],
                "characters_involved": [char.name for char in characters],
                "setting": "小说世界"
            }
            
            # 获取原始分数
            original_metrics = await quality_checker.quality_system.assess_quality(
                original_content, core_characters, chapter_info
            )
            
            # 执行智能修订
            revised_content, revision_history, final_report = await quality_checker.intelligent_revision(
                content=full_content,
                characters=core_characters,
                chapter_info=chapter_info,
                target_score=request.target_score,
                max_iterations=request.max_iterations,
                style_guide=request.style_guide
            )
            
            # TODO: 保存修订后的内容到数据库
            # 这里需要根据实际需求决定是否自动保存修订结果
            
            improvement = final_report["overall_score"] - original_metrics.overall_score
            
            logger.info(f"智能修订完成: project_id={project_id}, improvement={improvement}")
            
            return IntelligentRevisionResponse(
                project_id=project_id,
                original_score=original_metrics.overall_score,
                final_score=final_report["overall_score"],
                improvement=improvement,
                iterations_performed=len(revision_history),
                revision_history=revision_history,
                final_report=final_report
            )
            
    except HTTPException:
        raise
    except QualityIntegrationError as e:
        logger.error(f"智能修订失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"智能修订失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"智能修订失败: {str(e)}"
        )


@router.post("/projects/{project_id}/batch-quality-check", response_model=BatchQualityReportResponse)
async def batch_quality_check(
    project_id: int,
    request: BatchQualityCheckRequest,
    llm_client: UniversalLLMClient = Depends(get_llm_client)
) -> BatchQualityReportResponse:
    """执行批量质量检查."""
    
    try:
        async with get_db_session() as session:
            # 检查项目是否存在
            project = await session.get(NovelProject, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            # 获取项目数据
            chapters, characters = await _get_project_data(project_id, session)
            
            if not chapters:
                raise HTTPException(status_code=400, detail="项目没有章节内容")
            
            # 过滤章节（如果指定了特定章节）
            if request.chapter_ids:
                chapters = [ch for ch in chapters if ch.id in request.chapter_ids]
            
            # 创建增强质量检查器
            quality_checker = EnhancedQualityChecker(llm_client)
            
            # 转换角色格式
            core_characters = _convert_to_core_characters(characters)
            
            # 准备批量检查数据
            contents = []
            chapter_infos = []
            
            for chapter in chapters:
                if chapter.content:
                    contents.append(chapter.content)
                    chapter_infos.append({
                        "title": chapter.title,
                        "chapter_number": chapter.chapter_number,
                        "key_events": [],  # 可以从章节中提取
                        "previous_events": [],
                        "characters_involved": [char.name for char in characters],
                        "setting": "小说世界"
                    })
            
            # 执行批量质量检查
            chapter_reports = await quality_checker.batch_quality_check(
                contents=contents,
                characters=core_characters,
                chapter_infos=chapter_infos,
                style_guide=request.style_guide
            )
            
            # 计算整体统计
            overall_statistics = _calculate_batch_statistics(chapter_reports)
            
            logger.info(f"批量质量检查完成: project_id={project_id}, chapters={len(chapter_reports)}")
            
            return BatchQualityReportResponse(
                project_id=project_id,
                chapter_reports=chapter_reports,
                overall_statistics=overall_statistics
            )
            
    except HTTPException:
        raise
    except QualityIntegrationError as e:
        logger.error(f"批量质量检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"批量质量检查失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"批量质量检查失败: {str(e)}"
        )


@router.get("/projects/{project_id}/quality-trends")
async def get_quality_trends(
    project_id: int,
    llm_client: UniversalLLMClient = Depends(get_llm_client)
) -> Dict[str, Any]:
    """获取质量趋势分析."""
    
    try:
        async with get_db_session() as session:
            # 检查项目是否存在
            project = await session.get(NovelProject, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            # TODO: 从数据库获取历史质量报告
            # 这里需要实现质量报告的存储和检索机制
            historical_reports = []
            
            # 创建增强质量检查器
            quality_checker = EnhancedQualityChecker(llm_client)
            
            # 分析质量趋势
            trends = quality_checker.get_quality_trends(historical_reports)
            
            return {
                "project_id": project_id,
                "trends": trends
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取质量趋势失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取质量趋势失败: {str(e)}"
        )


# 保留原有的基础质量检查接口以保持兼容性
@router.post("/projects/{project_id}/quality-check", response_model=QualityReportResponse)
async def check_project_quality(
    project_id: int,
    request: QualityCheckRequest = None,
) -> QualityReportResponse:
    """执行项目质量检查（兼容性接口）."""
    
    try:
        async with get_db_session() as session:
            # 检查项目是否存在
            project = await session.get(NovelProject, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            if project.status != "completed":
                raise HTTPException(
                    status_code=400,
                    detail="只能对已完成的项目进行质量检查"
                )
            
            # 执行基础质量检查（保持原有逻辑）
            quality_report = await _perform_legacy_quality_check(project_id, session)
            
            logger.info(f"基础质量检查完成: project_id={project_id}")
            
            return quality_report
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"基础质量检查失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"基础质量检查失败: {str(e)}"
        )


@router.get("/projects/{project_id}/quality-metrics", response_model=QualityMetricsResponse)
async def get_quality_metrics(project_id: int) -> QualityMetricsResponse:
    """获取项目质量指标（兼容性接口）."""
    
    try:
        async with get_db_session() as session:
            project = await session.get(NovelProject, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="项目未找到")
            
            # 计算质量指标
            metrics = await _calculate_quality_metrics(project_id, session)
            
            return QualityMetricsResponse(
                project_id=project_id,
                metrics=metrics,
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取质量指标失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取质量指标失败: {str(e)}"
        )


# 辅助函数

async def _get_project_data(project_id: int, session) -> tuple:
    """获取项目数据."""
    from sqlalchemy import select
    
    # 获取章节
    chapter_query = select(Chapter).where(Chapter.project_id == project_id)
    chapter_result = await session.execute(chapter_query)
    chapters = chapter_result.scalars().all()
    
    # 获取角色
    character_query = select(Character).where(Character.project_id == project_id)
    character_result = await session.execute(character_query)
    characters = character_result.scalars().all()
    
    return chapters, characters


def _convert_to_core_characters(db_characters) -> Dict[str, CoreCharacter]:
    """转换数据库角色到核心角色格式."""
    core_characters = {}
    
    for db_char in db_characters:
        try:
            # 解析角色档案
            profile = db_char.profile or {}
            
            core_char = CoreCharacter(
                name=db_char.name,
                role=db_char.importance,  # 使用importance作为role
                age=profile.get("age", 25),
                personality=profile.get("personality", ["未定义"]),
                background=profile.get("background", db_char.description or ""),
                goals=profile.get("goals", ["未定义"]),
                skills=profile.get("skills", []),
                appearance=profile.get("appearance", ""),
                motivation=profile.get("motivation", "")
            )
            
            core_characters[db_char.name] = core_char
        except Exception as e:
            logger.warning(f"转换角色 {db_char.name} 失败: {e}")
            # 创建基础角色
            core_char = CoreCharacter(
                name=db_char.name,
                role=db_char.importance,
                age=25,
                personality=["未定义"],
                background=db_char.description or "",
                goals=["未定义"],
                skills=[],
                appearance="",
                motivation=""
            )
            core_characters[db_char.name] = core_char
    
    return core_characters


def _calculate_batch_statistics(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算批量检查的整体统计."""
    if not reports:
        return {}
    
    scores = [report.get("overall_score", 0) for report in reports]
    
    return {
        "total_chapters": len(reports),
        "average_score": round(sum(scores) / len(scores), 2),
        "highest_score": max(scores),
        "lowest_score": min(scores),
        "score_distribution": {
            "A (9.0+)": len([s for s in scores if s >= 9.0]),
            "B (7.5-8.9)": len([s for s in scores if 7.5 <= s < 9.0]),
            "C (6.0-7.4)": len([s for s in scores if 6.0 <= s < 7.5]),
            "D (4.0-5.9)": len([s for s in scores if 4.0 <= s < 6.0]),
            "F (<4.0)": len([s for s in scores if s < 4.0])
        }
    }


# 以下是保持兼容性的原有函数

async def _perform_legacy_quality_check(project_id: int, session) -> QualityReportResponse:
    """执行传统质量检查."""
    
    # 获取项目数据
    from sqlalchemy import select
    
    # 获取章节
    chapter_query = select(Chapter).where(Chapter.project_id == project_id)
    chapter_result = await session.execute(chapter_query)
    chapters = chapter_result.scalars().all()
    
    # 获取角色
    character_query = select(Character).where(Character.project_id == project_id)
    character_result = await session.execute(character_query)
    characters = character_result.scalars().all()
    
    # 执行各项检查
    consistency_issues = _check_consistency(chapters, characters)
    coherence_score = _check_coherence(chapters)
    character_issues = _check_character_consistency(chapters, characters)
    plot_issues = _check_plot_logic(chapters)
    
    # 计算总体分数
    overall_score = _calculate_overall_score(
        consistency_issues, coherence_score, character_issues, plot_issues
    )
    
    # 生成建议
    suggestions = _generate_improvement_suggestions(
        consistency_issues, character_issues, plot_issues, coherence_score
    )
    
    return QualityReportResponse(
        project_id=project_id,
        overall_score=overall_score,
        coherence_score=coherence_score,
        consistency_issues=consistency_issues,
        character_issues=character_issues,
        plot_issues=plot_issues,
        suggestions=suggestions,
        checked_at=f"{project_id}_quality_check",  # 简化实现
    )


async def _calculate_quality_metrics(project_id: int, session) -> Dict[str, Any]:
    """计算质量指标."""
    
    from sqlalchemy import select, func
    
    # 基础统计
    chapter_query = select(func.count(), func.avg(Chapter.word_count)).where(
        Chapter.project_id == project_id
    )
    chapter_result = await session.execute(chapter_query)
    chapter_count, avg_chapter_words = chapter_result.one()
    
    character_query = select(func.count()).where(
        Character.project_id == project_id
    )
    character_result = await session.execute(character_query)
    character_count = character_result.scalar()
    
    # 计算指标
    metrics = {
        "chapter_count": chapter_count or 0,
        "character_count": character_count or 0,
        "avg_chapter_words": round(avg_chapter_words or 0, 2),
        "structure_score": _calculate_structure_score(chapter_count or 0),
        "character_density": _calculate_character_density(character_count or 0, chapter_count or 0),
        "estimated_readability": 7.5,  # 模拟可读性分数
        "genre_consistency": 8.0,  # 模拟题材一致性
        "pacing_score": 7.8,  # 模拟节奏分数
    }
    
    return metrics


def _check_consistency(chapters: List, characters: List) -> List[Dict[str, Any]]:
    """检查一致性问题."""
    
    issues = []
    
    # 简化的一致性检查
    if len(chapters) == 0:
        issues.append({
            "type": "structure",
            "severity": "high",
            "description": "项目没有章节内容",
            "location": "project",
        })
    
    if len(characters) == 0:
        issues.append({
            "type": "character",
            "severity": "medium", 
            "description": "项目没有定义角色",
            "location": "project",
        })
    
    # 检查章节标题重复
    chapter_titles = [ch.title for ch in chapters if ch.title]
    if len(chapter_titles) != len(set(chapter_titles)):
        issues.append({
            "type": "structure",
            "severity": "medium",
            "description": "存在重复的章节标题",
            "location": "chapters",
        })
    
    return issues


def _check_coherence(chapters: List) -> float:
    """检查连贯性."""
    
    if not chapters:
        return 0.0
    
    # 简化的连贯性评分
    base_score = 7.0
    
    # 章节数量适中加分
    if 3 <= len(chapters) <= 20:
        base_score += 0.5
    
    # 章节字数相对均匀加分
    if chapters:
        word_counts = [ch.word_count for ch in chapters if ch.word_count]
        if word_counts:
            avg_words = sum(word_counts) / len(word_counts)
            variance = sum((w - avg_words) ** 2 for w in word_counts) / len(word_counts)
            if variance < (avg_words * 0.3) ** 2:  # 字数差异不大
                base_score += 0.5
    
    return min(base_score, 10.0)


def _check_character_consistency(chapters: List, characters: List) -> List[Dict[str, Any]]:
    """检查角色一致性."""
    
    issues = []
    
    # 检查是否有主要角色
    main_characters = [ch for ch in characters if ch.importance == "main"]
    if not main_characters:
        issues.append({
            "type": "character",
            "severity": "high",
            "description": "缺少主要角色定义",
            "character": None,
        })
    
    # 检查角色名称长度
    for character in characters:
        if len(character.name) < 2:
            issues.append({
                "type": "character",
                "severity": "medium",
                "description": "角色名称过短",
                "character": character.name,
            })
    
    return issues


def _check_plot_logic(chapters: List) -> List[Dict[str, Any]]:
    """检查情节逻辑."""
    
    issues = []
    
    # 检查章节顺序
    chapter_numbers = [ch.chapter_number for ch in chapters]
    expected_numbers = list(range(1, len(chapters) + 1))
    
    if sorted(chapter_numbers) != expected_numbers:
        issues.append({
            "type": "structure",
            "severity": "high",
            "description": "章节编号不连续或重复",
            "location": "chapter_numbering",
        })
    
    # 检查极短章节
    for chapter in chapters:
        if chapter.word_count and chapter.word_count < 500:
            issues.append({
                "type": "content",
                "severity": "low",
                "description": f"章节 '{chapter.title}' 字数过少 ({chapter.word_count} 字)",
                "location": f"chapter_{chapter.chapter_number}",
            })
    
    return issues


def _calculate_overall_score(
    consistency_issues: List,
    coherence_score: float,
    character_issues: List,
    plot_issues: List,
) -> float:
    """计算总体分数."""
    
    base_score = 10.0
    
    # 扣除一致性问题分数
    for issue in consistency_issues:
        if issue["severity"] == "high":
            base_score -= 1.5
        elif issue["severity"] == "medium":
            base_score -= 1.0
        else:
            base_score -= 0.5
    
    # 扣除角色问题分数
    for issue in character_issues:
        if issue["severity"] == "high":
            base_score -= 1.0
        elif issue["severity"] == "medium":
            base_score -= 0.7
        else:
            base_score -= 0.3
    
    # 扣除情节问题分数
    for issue in plot_issues:
        if issue["severity"] == "high":
            base_score -= 1.2
        elif issue["severity"] == "medium":
            base_score -= 0.8
        else:
            base_score -= 0.4
    
    # 连贯性分数权重
    base_score = (base_score + coherence_score) / 2
    
    return max(0.0, min(10.0, base_score))


def _generate_improvement_suggestions(
    consistency_issues: List,
    character_issues: List,
    plot_issues: List,
    coherence_score: float,
) -> List[str]:
    """生成改进建议."""
    
    suggestions = []
    
    # 基于问题类型生成建议
    if any(issue["severity"] == "high" for issue in consistency_issues):
        suggestions.append("建议检查和修复高严重性的一致性问题")
    
    if any(issue["type"] == "character" for issue in character_issues):
        suggestions.append("建议完善角色设定和描述")
    
    if any(issue["type"] == "structure" for issue in plot_issues):
        suggestions.append("建议检查章节结构和编号")
    
    if coherence_score < 7.0:
        suggestions.append("建议提高章节间的连贯性")
    
    if coherence_score < 6.0:
        suggestions.append("建议重新审视整体故事逻辑")
    
    # 通用建议
    if not suggestions:
        suggestions.append("整体质量良好，可考虑细节优化")
    
    return suggestions


def _calculate_structure_score(chapter_count: int) -> float:
    """计算结构分数."""
    
    if chapter_count == 0:
        return 0.0
    elif 1 <= chapter_count <= 3:
        return 6.0  # 短篇
    elif 4 <= chapter_count <= 10:
        return 8.0  # 中篇
    elif 11 <= chapter_count <= 30:
        return 9.0  # 长篇
    else:
        return 7.0  # 超长篇，可能结构复杂


def _calculate_character_density(character_count: int, chapter_count: int) -> float:
    """计算角色密度分数."""
    
    if chapter_count == 0:
        return 0.0
    
    density = character_count / chapter_count
    
    if 0.5 <= density <= 2.0:
        return 9.0  # 理想密度
    elif 0.3 <= density <= 3.0:
        return 7.5  # 可接受密度
    else:
        return 6.0  # 密度过高或过低