"""
Celery task: execute monitoring task — iterate questions, call LLM, save results.

Supports both API providers (OpenAI) and browser providers (Doubao/DeepSeek).
Uses SQLAlchemy sync session (Celery is synchronous).
"""
import hashlib
import time
import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.celery_app import celery_app
from app.core.database import get_sync_db
from app.models.task import Task, TaskResult, CrawledPage
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
BROWSER_QUESTION_DELAY = 3.0


def get_provider(task):
    """Factory: create the appropriate LLM provider based on task.provider_type."""
    pt = task.provider_type or "api"
    if pt == "api":
        return OpenAIProvider()
    elif pt.startswith("browser_"):
        platform = pt.replace("browser_", "")  # "doubao" or "deepseek"
        from app.services.session_manager import get_session_manager
        mgr = get_session_manager()
        session = mgr.acquire(platform)
        if not session:
            raise RuntimeError(f"No active browser session for {platform}. Create and authenticate one first.")
        user_data_dir = session["user_data_dir"]
        if platform == "doubao":
            from app.services.llm.doubao_provider import DoubaoProvider
            return DoubaoProvider(user_data_dir=user_data_dir, headless=True)
        elif platform == "deepseek":
            from app.services.llm.deepseek_provider import DeepSeekProvider
            return DeepSeekProvider(user_data_dir=user_data_dir, headless=True)
        else:
            raise RuntimeError(f"Unknown browser platform: {platform}")
    else:
        raise RuntimeError(f"Unknown provider_type: {pt}")


def _save_crawled_pages(db, task_result_id: str, crawled_sources) -> int:
    """Save crawled page content to crawled_pages table. Returns count saved."""
    saved = 0
    for source in crawled_sources:
        text_content = getattr(source, "text_content", "") or ""
        html_content = getattr(source, "html_content", "") or ""
        content_hash = hashlib.sha256(
            (text_content or html_content or source.url).encode()
        ).hexdigest()

        page = CrawledPage(
            id=str(uuid.uuid4()),
            task_result_id=task_result_id,
            url=source.url,
            title=getattr(source, "title", "") or "",
            text_content=text_content,
            html_content=html_content,
            content_hash=content_hash,
            word_count=len(text_content.split()) if text_content else 0,
            crawl_success=getattr(source, "success", True),
            crawl_error=getattr(source, "error", None) or None,
        )
        db.add(page)
        saved += 1
    return saved


def run_monitoring_task(task_id: str) -> dict:
    """Core execution logic — testable without Celery decorator."""
    logger.info(f"[Task {task_id}] Starting execution")

    with get_sync_db() as db:
        # 1. Load task
        task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
        if not task:
            logger.error(f"[Task {task_id}] Not found")
            return {"status": "error", "message": "Task not found"}

        # 2. Create provider
        try:
            llm = get_provider(task)
        except RuntimeError as e:
            task.status = "failed"
            task.finished_at = datetime.now(timezone.utc)
            db.commit()
            return {"status": "failed", "message": str(e)}

        is_browser = (task.provider_type or "api").startswith("browser_")
        delay = BROWSER_QUESTION_DELAY if is_browser else INTER_QUESTION_DELAY

        # 3. Load questions
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

        # 4. Find already-completed question IDs (for resume)
        completed_ids = set(
            row[0] for row in db.execute(
                select(TaskResult.question_id).where(TaskResult.task_id == task_id)
            ).all()
        )

        # 5. Update task: started
        total = len(questions)
        task.status = "running"
        task.total_questions = total
        task.completed_questions = len(completed_ids)
        if not task.started_at:
            task.started_at = datetime.now(timezone.utc)
        db.commit()

        system_prompt = SCENE_PROMPTS.get(task.model_scene, SCENE_PROMPTS["pc"])
        completed_count = len(completed_ids)
        provider_type = task.provider_type or "api"

        # 6. Execute questions — batch path for browser, sequential for API
        from app.services.llm.browser_base import BaseBrowserProvider, BrowserLLMResponse

        # Filter unanswered questions
        unanswered = [q for q in questions if q.id not in completed_ids]

        if isinstance(llm, BaseBrowserProvider) and unanswered:
            # --- Browser batch path: single browser session for all questions ---
            questions_data = [{"question": q.content, "question_id": str(q.id)} for q in unanswered]
            logger.info(f"[Task {task_id}] Browser batch: {len(questions_data)} questions")

            batch_results = llm.chat_batch(questions_data)

            for q, resp in zip(unanswered, batch_results):
                answer_text = resp.content
                model_name = resp.model or ""
                source_type = "crawled"
                ai_read_sources = resp.ai_read_sources
                response_time_ms = resp.response_time_ms
                sources = [{"url": s.url, "title": s.title, "text_snippet": (getattr(s, "text_content", "") or "")[:500]} for s in resp.crawled_sources if s.success]

                result_id = str(uuid.uuid4())
                result = TaskResult(
                    id=result_id,
                    task_id=task_id,
                    question_id=q.id,
                    model_name=model_name,
                    model_version="",
                    question_text=q.content,
                    answer_text=answer_text,
                    sources=sources,
                    provider_type=provider_type,
                    source_type=source_type,
                    ai_read_sources=ai_read_sources,
                    response_time_ms=response_time_ms,
                    config_snapshot=task.config or {},
                )
                db.add(result)

                # Save full crawled page content
                if resp.crawled_sources:
                    saved = _save_crawled_pages(db, result_id, resp.crawled_sources)
                    logger.info(f"[Task {task_id}] Saved {saved} crawled pages for q={q.id}")

                completed_count += 1
                task.completed_questions = completed_count
                task.progress = int(completed_count / total * 100) if total > 0 else 100
                db.commit()

                logger.info(
                    f"[Task {task_id}] {completed_count}/{total} "
                    f"({task.progress}%) q={q.id} {response_time_ms}ms provider={provider_type}"
                )
        else:
            # --- API sequential path (unchanged) ---
            for q in unanswered:
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
                source_type = "parsed"
                ai_read_sources = []
                response_time_ms = 0
                resp = None

                try:
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": q.content},
                    ]
                    resp = llm.chat(messages)
                    answer_text = resp.content
                    model_name = resp.model

                    if isinstance(resp, BrowserLLMResponse):
                        source_type = "crawled"
                        ai_read_sources = resp.ai_read_sources
                        response_time_ms = resp.response_time_ms
                        sources = [{"url": s.url, "title": s.title, "text_snippet": (getattr(s, "text_content", "") or "")[:500]} for s in resp.crawled_sources if s.success]
                    else:
                        sources = parse_sources(answer_text)
                except Exception as e:
                    answer_text = f"[ERROR] {e}"
                    logger.warning(f"[Task {task_id}] Question {q.id} failed: {e}")

                duration_ms = int((time.time() - start_ms) * 1000)

                # Write result
                result_id = str(uuid.uuid4())
                result = TaskResult(
                    id=result_id,
                    task_id=task_id,
                    question_id=q.id,
                    model_name=model_name,
                    model_version="",
                    question_text=q.content,
                    answer_text=answer_text,
                    sources=sources,
                    provider_type=provider_type,
                    source_type=source_type,
                    ai_read_sources=ai_read_sources,
                    response_time_ms=response_time_ms,
                    config_snapshot=task.config or {},
                )
                db.add(result)

                # Save crawled pages (browser responses only)
                if resp and isinstance(resp, BrowserLLMResponse) and resp.crawled_sources:
                    _save_crawled_pages(db, result_id, resp.crawled_sources)

                # Update progress
                completed_count += 1
                task.completed_questions = completed_count
                task.progress = int(completed_count / total * 100) if total > 0 else 100
                db.commit()

                logger.info(
                    f"[Task {task_id}] {completed_count}/{total} "
                    f"({task.progress}%) q={q.id} {duration_ms}ms provider={provider_type}"
                )

                if completed_count < total:
                    time.sleep(delay)

        # 7. Mark completed
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
