from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.question import Question, QuestionSet
from app.models.user import User
from app.schemas.question import (
    QuestionBatchCreate,
    QuestionCreate,
    QuestionResponse,
    QuestionSetCreate,
    QuestionSetResponse,
    QuestionSetUpdate,
)

router = APIRouter()


# --- Question Sets ---

@router.get("/sets", response_model=list[QuestionSetResponse])
async def list_question_sets(
    brand_id: str = Query("", description="按品牌筛选"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(QuestionSet).order_by(QuestionSet.created_at.desc())
    if brand_id:
        q = q.where(QuestionSet.brand_id == brand_id)
    result = await db.execute(q)
    return [QuestionSetResponse.model_validate(qs, from_attributes=True) for qs in result.scalars().all()]


@router.post("/sets", response_model=QuestionSetResponse, status_code=status.HTTP_201_CREATED)
async def create_question_set(body: QuestionSetCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    qs = QuestionSet(**body.model_dump(), created_by=user.id)
    db.add(qs)
    await db.commit()
    await db.refresh(qs)
    return QuestionSetResponse.model_validate(qs, from_attributes=True)


@router.put("/sets/{set_id}", response_model=QuestionSetResponse)
async def update_question_set(set_id: str, body: QuestionSetUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(QuestionSet).where(QuestionSet.id == set_id))
    qs = result.scalar_one_or_none()
    if not qs:
        raise HTTPException(status_code=404, detail="Question set not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(qs, k, v)
    await db.commit()
    await db.refresh(qs)
    return QuestionSetResponse.model_validate(qs, from_attributes=True)


@router.delete("/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question_set(set_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(QuestionSet).where(QuestionSet.id == set_id))
    qs = result.scalar_one_or_none()
    if not qs:
        raise HTTPException(status_code=404, detail="Question set not found")
    await db.delete(qs)
    await db.commit()


# --- Questions ---

@router.get("", response_model=list[QuestionResponse])
async def list_questions(
    question_set_id: str = Query(..., description="问题集ID"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Question).where(Question.question_set_id == question_set_id).order_by(Question.sort_order)
    result = await db.execute(q)
    return [QuestionResponse.model_validate(qn, from_attributes=True) for qn in result.scalars().all()]


@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(body: QuestionCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    question = Question(**body.model_dump())
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return QuestionResponse.model_validate(question, from_attributes=True)


@router.post("/batch", response_model=list[QuestionResponse], status_code=status.HTTP_201_CREATED)
async def batch_create_questions(body: QuestionBatchCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    questions = []
    for i, q_data in enumerate(body.questions):
        question = Question(question_set_id=body.question_set_id, content=q_data["content"], category=q_data.get("category", ""), sort_order=i)
        db.add(question)
        questions.append(question)
    await db.commit()
    for q in questions:
        await db.refresh(q)
    return [QuestionResponse.model_validate(q, from_attributes=True) for q in questions]


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(question_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    await db.delete(question)
    await db.commit()
