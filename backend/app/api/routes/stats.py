from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.brand import Brand
from app.models.question import QuestionSet
from app.models.task import Task
from app.models.user import User

router = APIRouter()


@router.get("/dashboard")
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    brand_count = (await db.execute(select(func.count(Brand.id)))).scalar() or 0
    qs_count = (await db.execute(select(func.count(QuestionSet.id)))).scalar() or 0
    running = (await db.execute(select(func.count(Task.id)).where(Task.status == "running"))).scalar() or 0
    completed = (await db.execute(select(func.count(Task.id)).where(Task.status == "completed"))).scalar() or 0
    total_tasks = (await db.execute(select(func.count(Task.id)))).scalar() or 0
    return {
        "brand_count": brand_count,
        "question_set_count": qs_count,
        "running_tasks": running,
        "completed_tasks": completed,
        "total_tasks": total_tasks,
    }
