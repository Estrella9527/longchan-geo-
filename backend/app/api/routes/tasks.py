from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.task import Task, TaskResult
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse, TaskResultResponse

router = APIRouter()


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    brand_id: str = Query("", description="按品牌筛选"),
    task_status: str = Query("", description="按状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Task).order_by(Task.created_at.desc())
    if brand_id:
        q = q.where(Task.brand_id == brand_id)
    if task_status:
        q = q.where(Task.status == task_status)
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return [TaskResponse.model_validate(t, from_attributes=True) for t in result.scalars().all()]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    task = Task(**body.model_dump(), created_by=user.id)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return TaskResponse.model_validate(task, from_attributes=True)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task, from_attributes=True)


@router.post("/{task_id}/start", response_model=TaskResponse)
async def start_task(task_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in ("pending", "paused", "failed"):
        raise HTTPException(status_code=400, detail=f"Cannot start task in {task.status} status")
    # Dispatch to Celery worker
    from app.tasks.execute_task import execute_monitoring_task
    celery_result = execute_monitoring_task.delay(task_id)
    task.status = "running"
    await db.commit()
    await db.refresh(task)
    return TaskResponse.model_validate(task, from_attributes=True)


@router.post("/{task_id}/pause", response_model=TaskResponse)
async def pause_task(task_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "running":
        raise HTTPException(status_code=400, detail="Task is not running")
    task.status = "paused"
    await db.commit()
    await db.refresh(task)
    return TaskResponse.model_validate(task, from_attributes=True)


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Task already {task.status}")
    task.status = "cancelled"
    await db.commit()
    await db.refresh(task)
    return TaskResponse.model_validate(task, from_attributes=True)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()


# --- Task Results ---

@router.get("/{task_id}/results", response_model=list[TaskResultResponse])
async def list_task_results(
    task_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(TaskResult).where(TaskResult.task_id == task_id).order_by(TaskResult.created_at.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return [TaskResultResponse.model_validate(r, from_attributes=True) for r in result.scalars().all()]
