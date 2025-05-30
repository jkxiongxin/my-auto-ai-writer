"""小说生成专用日志管理器 - 记录提示词和模型响应."""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import uuid


@dataclass
class GenerationLogEntry:
    """生成日志条目."""
    timestamp: str
    step_type: str  # 步骤类型：concept_expansion, strategy_selection, outline_generation, character_creation, chapter_generation
    step_name: str  # 具体步骤名称
    prompt: str     # 发送给模型的提示词
    response: str   # 模型的响应
    model_info: Dict[str, Any] = field(default_factory=dict)  # 模型信息
    metadata: Dict[str, Any] = field(default_factory=dict)    # 附加元数据
    duration_ms: Optional[int] = None  # 执行时长（毫秒）
    token_usage: Dict[str, int] = field(default_factory=dict)  # Token使用情况
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式."""
        return asdict(self)


@dataclass
class NovelGenerationSession:
    """小说生成会话信息."""
    session_id: str
    novel_title: str
    start_time: str
    log_file_path: str
    status: str = "active"  # active, completed, failed
    total_entries: int = 0
    last_update: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式."""
        return asdict(self)


class GenerationLogger:
    """小说生成专用日志器.
    
    功能:
    1. 为每部小说创建独立的日志文件
    2. 记录完整的生成过程
    3. 保存提示词和模型响应
    4. 支持会话管理和检索
    """
    
    def __init__(self, log_base_dir: str = "logs/generation"):
        """初始化生成日志器.
        
        Args:
            log_base_dir: 日志基础目录
        """
        self.log_base_dir = Path(log_base_dir)
        self.log_base_dir.mkdir(parents=True, exist_ok=True)
        
        # 会话索引文件
        self.sessions_file = self.log_base_dir / "sessions.json"
        
        # 当前活跃会话
        self.current_session: Optional[NovelGenerationSession] = None
        
        # 创建标准Python日志器
        self.logger = logging.getLogger("generation_logger")
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            # 控制台输出handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        self.logger.info("生成日志器初始化完成")
    
    def start_novel_session(self, novel_title: str) -> str:
        """开始新的小说生成会话.
        
        Args:
            novel_title: 小说标题
            
        Returns:
            会话ID
        """
        # 生成会话ID
        session_id = str(uuid.uuid4())[:8]
        
        # 创建时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 清理小说标题（移除特殊字符）
        safe_title = self._sanitize_filename(novel_title)
        
        # 生成日志文件名
        log_filename = f"{safe_title}_{timestamp}_{session_id}.json"
        log_file_path = self.log_base_dir / log_filename
        
        # 创建会话信息
        self.current_session = NovelGenerationSession(
            session_id=session_id,
            novel_title=novel_title,
            start_time=datetime.now().isoformat(),
            log_file_path=str(log_file_path),
            status="active",
            total_entries=0,
            last_update=datetime.now().isoformat()
        )
        
        # 保存会话信息到索引
        self._save_session_index()
        
        # 初始化日志文件
        self._init_log_file()
        
        self.logger.info(f"开始新的小说生成会话: {novel_title} (ID: {session_id})")
        return session_id
    
    def log_generation_step(
        self,
        step_type: str,
        step_name: str,
        prompt: str,
        response: str,
        model_info: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        token_usage: Optional[Dict[str, int]] = None
    ):
        """记录生成步骤.
        
        Args:
            step_type: 步骤类型
            step_name: 步骤名称
            prompt: 提示词
            response: 模型响应
            model_info: 模型信息
            metadata: 元数据
            duration_ms: 执行时长
            token_usage: Token使用情况
        """
        if not self.current_session:
            self.logger.warning("没有活跃的生成会话，无法记录日志")
            return
        
        # 创建日志条目
        entry = GenerationLogEntry(
            timestamp=datetime.now().isoformat(),
            step_type=step_type,
            step_name=step_name,
            prompt=prompt,
            response=response,
            model_info=model_info or {},
            metadata=metadata or {},
            duration_ms=duration_ms,
            token_usage=token_usage or {}
        )
        
        # 保存到文件
        self._append_log_entry(entry)
        
        # 更新会话信息
        self.current_session.total_entries += 1
        self.current_session.last_update = datetime.now().isoformat()
        self._save_session_index()
        
        # 控制台日志
        self.logger.info(
            f"[{step_type}] {step_name} - "
            f"提示词: {len(prompt)} 字符, "
            f"响应: {len(response)} 字符"
        )
        
        if duration_ms:
            self.logger.info(f"执行时间: {duration_ms} ms")
        
        if token_usage:
            self.logger.info(f"Token使用: {token_usage}")
    
    def log_chapter_generation(
        self,
        chapter_number: int,
        chapter_title: str,
        prompt: str,
        response: str,
        coherence_context: Optional[Dict[str, Any]] = None,
        quality_score: Optional[float] = None,
        duration_ms: Optional[int] = None,
        token_usage: Optional[Dict[str, int]] = None
    ):
        """专门记录章节生成步骤.
        
        Args:
            chapter_number: 章节编号
            chapter_title: 章节标题
            prompt: 提示词
            response: 模型响应
            coherence_context: 连贯性上下文
            quality_score: 质量评分
            duration_ms: 执行时长
            token_usage: Token使用情况
        """
        metadata = {
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "coherence_context_size": len(coherence_context) if coherence_context else 0,
            "quality_score": quality_score
        }
        
        if coherence_context:
            metadata["coherence_context"] = coherence_context
        
        self.log_generation_step(
            step_type="chapter_generation",
            step_name=f"第{chapter_number}章: {chapter_title}",
            prompt=prompt,
            response=response,
            metadata=metadata,
            duration_ms=duration_ms,
            token_usage=token_usage
        )
    
    def log_error(
        self,
        step_type: str,
        step_name: str,
        error_message: str,
        prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """记录错误信息.
        
        Args:
            step_type: 步骤类型
            step_name: 步骤名称
            error_message: 错误信息
            prompt: 失败时的提示词
            metadata: 错误元数据
        """
        error_metadata = {
            "error": True,
            "error_message": error_message,
            **(metadata or {})
        }
        
        self.log_generation_step(
            step_type=step_type,
            step_name=f"[ERROR] {step_name}",
            prompt=prompt or "",
            response=f"ERROR: {error_message}",
            metadata=error_metadata
        )
        
        self.logger.error(f"[{step_type}] {step_name}: {error_message}")
    
    def complete_session(self, status: str = "completed"):
        """完成当前会话.
        
        Args:
            status: 完成状态 (completed, failed)
        """
        if not self.current_session:
            return
        
        self.current_session.status = status
        self.current_session.last_update = datetime.now().isoformat()
        
        # 保存会话摘要到日志文件
        self._finalize_log_file()
        
        # 更新会话索引
        self._save_session_index()
        
        self.logger.info(
            f"会话完成: {self.current_session.novel_title} "
            f"(状态: {status}, 总步骤: {self.current_session.total_entries})"
        )
        
        self.current_session = None
    
    def get_session_log(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话日志.
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话日志数据
        """
        sessions = self._load_sessions()
        session_info = next((s for s in sessions if s["session_id"] == session_id), None)
        
        if not session_info:
            return None
        
        log_file_path = Path(session_info["log_file_path"])
        if not log_file_path.exists():
            return None
        
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            return log_data
        except Exception as e:
            self.logger.error(f"读取会话日志失败: {e}")
            return None
    
    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """列出会话记录.
        
        Args:
            limit: 返回数量限制
            
        Returns:
            会话信息列表
        """
        sessions = self._load_sessions()
        # 按开始时间倒序排序
        sessions.sort(key=lambda x: x["start_time"], reverse=True)
        return sessions[:limit]
    
    def export_session_summary(self, session_id: str, output_file: Optional[str] = None) -> str:
        """导出会话摘要.
        
        Args:
            session_id: 会话ID
            output_file: 输出文件路径
            
        Returns:
            摘要文本
        """
        log_data = self.get_session_log(session_id)
        if not log_data:
            return "会话不存在或日志文件损坏"
        
        summary_lines = []
        summary_lines.append(f"小说生成摘要")
        summary_lines.append("=" * 50)
        summary_lines.append(f"小说标题: {log_data['session_info']['novel_title']}")
        summary_lines.append(f"会话ID: {session_id}")
        summary_lines.append(f"开始时间: {log_data['session_info']['start_time']}")
        summary_lines.append(f"完成状态: {log_data['session_info']['status']}")
        summary_lines.append(f"总步骤数: {len(log_data['entries'])}")
        summary_lines.append("")
        
        # 统计各步骤
        step_counts = {}
        for entry in log_data['entries']:
            step_type = entry['step_type']
            step_counts[step_type] = step_counts.get(step_type, 0) + 1
        
        summary_lines.append("步骤统计:")
        for step_type, count in step_counts.items():
            summary_lines.append(f"  - {step_type}: {count} 次")
        summary_lines.append("")
        
        # 详细步骤
        summary_lines.append("详细步骤:")
        for i, entry in enumerate(log_data['entries'], 1):
            summary_lines.append(f"{i}. [{entry['step_type']}] {entry['step_name']}")
            summary_lines.append(f"   时间: {entry['timestamp']}")
            summary_lines.append(f"   提示词长度: {len(entry['prompt'])} 字符")
            summary_lines.append(f"   响应长度: {len(entry['response'])} 字符")
            if entry.get('duration_ms'):
                summary_lines.append(f"   耗时: {entry['duration_ms']} ms")
            summary_lines.append("")
        
        summary_text = "\n".join(summary_lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(summary_text)
        
        return summary_text
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除特殊字符."""
        import re
        # 替换特殊字符为下划线
        safe_name = re.sub(r'[<>:"/\\|?*\s]', '_', filename)
        # 限制长度
        if len(safe_name) > 50:
            safe_name = safe_name[:50]
        return safe_name
    
    def _init_log_file(self):
        """初始化日志文件."""
        if not self.current_session:
            return
        
        log_structure = {
            "session_info": self.current_session.to_dict(),
            "entries": []
        }
        
        with open(self.current_session.log_file_path, 'w', encoding='utf-8') as f:
            json.dump(log_structure, f, ensure_ascii=False, indent=2)
    
    def _append_log_entry(self, entry: GenerationLogEntry):
        """追加日志条目到文件."""
        if not self.current_session:
            return
        
        log_file_path = Path(self.current_session.log_file_path)
        
        try:
            # 读取现有数据
            with open(log_file_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            # 添加新条目
            log_data['entries'].append(entry.to_dict())
            
            # 写回文件
            with open(log_file_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"写入日志条目失败: {e}")
    
    def _finalize_log_file(self):
        """完成日志文件."""
        if not self.current_session:
            return
        
        log_file_path = Path(self.current_session.log_file_path)
        
        try:
            # 读取现有数据
            with open(log_file_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            # 更新会话信息
            log_data['session_info'] = self.current_session.to_dict()
            
            # 添加摘要信息
            log_data['summary'] = {
                "total_entries": len(log_data['entries']),
                "step_types": list(set(entry['step_type'] for entry in log_data['entries'])),
                "total_prompt_chars": sum(len(entry['prompt']) for entry in log_data['entries']),
                "total_response_chars": sum(len(entry['response']) for entry in log_data['entries']),
                "completion_time": datetime.now().isoformat()
            }
            
            # 写回文件
            with open(log_file_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"完成日志文件失败: {e}")
    
    def _save_session_index(self):
        """保存会话索引."""
        if not self.current_session:
            return
        
        sessions = self._load_sessions()
        
        # 更新或添加当前会话
        session_dict = self.current_session.to_dict()
        updated = False
        for i, session in enumerate(sessions):
            if session['session_id'] == self.current_session.session_id:
                sessions[i] = session_dict
                updated = True
                break
        
        if not updated:
            sessions.append(session_dict)
        
        try:
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存会话索引失败: {e}")
    
    def _load_sessions(self) -> List[Dict[str, Any]]:
        """加载会话索引."""
        if not self.sessions_file.exists():
            return []
        
        try:
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载会话索引失败: {e}")
            return []


# 全局单例
_generation_logger = None

def get_generation_logger() -> GenerationLogger:
    """获取全局生成日志器实例."""
    global _generation_logger
    if _generation_logger is None:
        _generation_logger = GenerationLogger()
    return _generation_logger