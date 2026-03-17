import uuid
import hashlib
from datetime import datetime, timezone

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Task(Base):
    """监测任务"""
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200))
    brand_id: Mapped[str] = mapped_column(String(36), ForeignKey("brands.id"), index=True)
    question_set_id: Mapped[str] = mapped_column(String(36), ForeignKey("question_sets.id"))
    # 任务类型: once=单次, recurring=循环
    task_type: Mapped[str] = mapped_column(String(20), default="once")
    # 状态: pending, running, completed, failed, paused
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # 模型场景: mobile, pc, api
    model_scene: Mapped[str] = mapped_column(String(20), default="pc")
    # Provider 类型: api, browser_doubao, browser_deepseek
    provider_type: Mapped[str] = mapped_column(String(30), default="api")
    # 配置项 JSON: ip切换、隐私模式、提问轮次等
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    completed_questions: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class TaskResult(Base):
    """任务问答结果明细"""
    __tablename__ = "task_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), index=True)
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey("questions.id"))
    model_name: Mapped[str] = mapped_column(String(100), default="")
    model_version: Mapped[str] = mapped_column(String(50), default="")
    question_text: Mapped[str] = mapped_column(Text, default="")
    answer_text: Mapped[str] = mapped_column(Text, default="")
    sources: Mapped[dict] = mapped_column(JSON, default=list)  # 信息源列表
    provider_type: Mapped[str] = mapped_column(String(30), default="api")
    source_type: Mapped[str] = mapped_column(String(20), default="parsed")  # parsed | crawled
    ai_read_sources: Mapped[dict] = mapped_column(JSON, default=list)
    response_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    config_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CrawledPage(Base):
    """爬取的网页内容 — 每个 TaskResult 可关联多条"""
    __tablename__ = "crawled_pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_result_id: Mapped[str] = mapped_column(String(36), ForeignKey("task_results.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, default="")
    text_content: Mapped[str] = mapped_column(Text, default="")
    html_content: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    crawl_success: Mapped[bool] = mapped_column(Boolean, default=True)
    crawl_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
