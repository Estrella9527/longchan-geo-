from datetime import datetime

from pydantic import BaseModel


class TaskCreate(BaseModel):
    name: str
    brand_id: str
    question_set_id: str
    task_type: str = "once"  # once | recurring
    model_scene: str = "pc"  # mobile | pc | api
    config: dict = {}


class TaskResponse(BaseModel):
    id: str
    name: str
    brand_id: str
    question_set_id: str
    task_type: str
    status: str
    model_scene: str
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
    created_at: datetime
