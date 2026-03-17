from datetime import datetime

from pydantic import BaseModel


class TaskCreate(BaseModel):
    name: str
    brand_id: str
    question_set_id: str
    task_type: str = "once"  # once | recurring
    model_scene: str = "pc"  # mobile | pc | api
    provider_type: str = "api"  # api | browser_doubao | browser_deepseek
    config: dict = {}


class TaskResponse(BaseModel):
    id: str
    name: str
    brand_id: str
    question_set_id: str
    task_type: str
    status: str
    model_scene: str
    provider_type: str = "api"
    config: dict
    progress: int
    total_questions: int
    completed_questions: int
    created_by: str
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class TaskResultResponse(BaseModel):
    id: str
    task_id: str
    question_id: str
    model_name: str
    model_version: str
    question_text: str
    answer_text: str
    sources: list | dict
    provider_type: str = "api"
    source_type: str = "parsed"
    ai_read_sources: list = []
    response_time_ms: int = 0
    created_at: datetime


class CrawledPageResponse(BaseModel):
    id: str
    task_result_id: str
    url: str
    title: str
    text_content: str
    word_count: int
    crawl_success: bool
    crawl_error: str | None = None
    crawled_at: datetime
