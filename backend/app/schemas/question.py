from datetime import datetime

from pydantic import BaseModel


class QuestionSetCreate(BaseModel):
    brand_id: str
    name: str
    description: str = ""


class QuestionSetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class QuestionSetResponse(BaseModel):
    id: str
    brand_id: str
    name: str
    description: str
    question_count: int
    created_by: str
    created_at: datetime


class QuestionCreate(BaseModel):
    question_set_id: str
    content: str
    category: str = ""


class QuestionBatchCreate(BaseModel):
    question_set_id: str
    questions: list[dict]  # [{content, category}]


class QuestionResponse(BaseModel):
    id: str
    question_set_id: str
    content: str
    category: str
    sort_order: int
    created_at: datetime
