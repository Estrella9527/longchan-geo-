"""
Celery task: execute monitoring task — iterate questions, call LLM, save results.

Uses SQLAlchemy sync session (Celery is synchronous).
"""
import time
import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.celery_app import celery_app
from app.core.database import get_sync_db
from app.models.task import Task, TaskResult
from app.models.question import Question
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.source_parser import parse_sources

logger = logging.getLogger(__name__)

SCENE_PROMPTS = {
    "pc": "你是一个普通用户，正在电脑浏览器上搜索信息。请回答以下问题并注明信息来源。",
    "mobile": "你是手机用户，快速搜索。请简洁回答并列出信息来源。",
    "api": "请回答以下问题并提供信息来源和引用链接。",
}

INTER_QUESTION_DELAY = 1.0


def run_monitoring_task(task_id: str) -> dict:
    """Core execution logic — testable without Celery decorator."""
    logger.info(f"[Task {task_id}] Starting execution")
    llm = OpenAIProvider()

    with get_sync_db() as db:
        # 1. Load task
        task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
        if not task:
            logger.error(f"[Task {task_id}] Not found")
            return {"status": "error", "message": "Task not found"}

        # 2. Load questions
        questions = db.execute(
            select(Question)
            .where(Question.question_set_id == task.question_set_id)
            .order_by(Question.sort_order)
        ).scalars().all()

        if not questions:
            task.status = "completed"
            task.finished_at = datetime.now(timezone.utc)
            db.commit()
            return {"status": "completed", "message": "No questions"}

        # 3. Find already-completed question IDs (for resume)
        completed_ids = set(
            row[0] for row in db.execute(
                select(TaskResult.question_id).where(TaskResult.task_id == task_id)
            ).all()
        )

        # 4. Update task: started
        total = len(questions)
        task.status = "running"
        task.total_questions = total
        task.completed_questions = len(completed_ids)
        if not task.started_at:
            task.started_at = datetime.now(timezone.utc)
        db.commit()

        system_prompt = SCENE_PROMPTS.get(task.model_scene, SCENE_PROMPTS["pc"])
        completed_count = len(completed_ids)

        # 5. Iterate questions
        for q in questions:
            if q.id in completed_ids:
                continue

            # Check if paused/cancelled
            db.refresh(task)
            if task.status in ("paused", "cancelled"):
                logger.info(f"[Task {task_id}] {task.status}, stopping")
                return {"status": task.status}

            # Call LLM
            start_ms = time.time()
            answer_text = ""
            sources = []
            model_name = ""
            error_msg = None

            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": q.content},
                ]
                resp = llm.chat(messages)
                answer_text = resp.content
                model_name = resp.model
                sources = parse_sources(answer_text)
            except Exception as e:
                error_msg = str(e)
                answer_text = f"[ERROR] {error_msg}"
                logger.warning(f"[Task {task_id}] Question {q.id} failed: {e}")

            duration_ms = int((time.time() - start_ms) * 1000)

            # Write result
            result = TaskResult(
                id=str(uuid.uuid4()),
                task_id=task_id,
                question_id=q.id,
                model_name=model_name,
                model_version="",
                question_text=q.content,
                answer_text=answer_text,
                sources=sources,
                config_snapshot=task.config or {},
            )
            db.add(result)

            # Update progress
            completed_count += 1
            task.completed_questions = completed_count
            task.progress = int(completed_count / total * 100) if total > 0 else 100
            db.commit()

            logger.info(
                f"[Task {task_id}] {completed_count}/{total} "
                f"({task.progress}%) q={q.id} {duration_ms}ms"
            )

            if completed_count < total:
                time.sleep(INTER_QUESTION_DELAY)

        # 6. Mark completed
        task.status = "completed"
        task.finished_at = datetime.now(timezone.utc)
        task.progress = 100
        db.commit()
        logger.info(f"[Task {task_id}] Completed ({completed_count}/{total})")
        return {"status": "completed", "completed": completed_count, "total": total}


@celery_app.task(bind=True, name="app.tasks.execute_monitoring_task")
def execute_monitoring_task(self, task_id: str):
    """Celery task wrapper."""
    try:
        return run_monitoring_task(task_id)
    except Exception as e:
        logger.exception(f"[Task {task_id}] Failed: {e}")
        # Mark task as failed
        try:
            with get_sync_db() as db:
                task = db.execute(
                    select(Task).where(Task.id == task_id)
                ).scalar_one_or_none()
                if task:
                    task.status = "failed"
                    task.finished_at = datetime.now(timezone.utc)
                    db.commit()
        except Exception:
            pass
        return {"status": "failed", "message": str(e)}
