"""Unit tests for task execution logic.

Note: conftest.py mocks celery and app.celery_app before this module is imported.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.services.llm.base import LLMResponse


def _make_session(task, questions, completed_question_ids=None):
    """Create a mock sync DB session."""
    session = MagicMock()
    completed_question_ids = completed_question_ids or []
    call_count = [0]

    def mock_execute(stmt):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.scalar_one_or_none.return_value = task
        elif call_count[0] == 2:
            result.scalars.return_value.all.return_value = questions
        elif call_count[0] == 3:
            result.all.return_value = [(qid,) for qid in completed_question_ids]
        else:
            result.scalar_one_or_none.return_value = task
        return result

    session.execute = mock_execute
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    return session


def _make_task():
    task = MagicMock()
    task.id = "task-1"
    task.question_set_id = "qs-1"
    task.model_scene = "pc"
    task.config = {}
    task.status = "running"
    task.started_at = None
    task.progress = 0
    task.total_questions = 0
    task.completed_questions = 0
    return task


def _make_questions():
    q1 = MagicMock(id="q-1", content="什么是GEO?", sort_order=1)
    q2 = MagicMock(id="q-2", content="品牌推荐?", sort_order=2)
    return [q1, q2]


def _wrap_ctx(session):
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=session)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


@patch("app.tasks.execute_task.time.sleep")
@patch("app.tasks.execute_task.OpenAIProvider")
@patch("app.tasks.execute_task.get_sync_db")
def test_normal_completion(mock_get_db, mock_provider_cls, mock_sleep):
    task = _make_task()
    session = _make_session(task, _make_questions())
    mock_get_db.return_value = _wrap_ctx(session)

    provider = MagicMock()
    provider.chat.return_value = LLMResponse(
        content="GEO是品牌优化。参考 https://example.com",
        model="gpt-4o-mini", usage={}, raw_response={},
    )
    mock_provider_cls.return_value = provider

    from app.tasks.execute_task import run_monitoring_task
    result = run_monitoring_task("task-1")

    assert result["status"] == "completed"
    assert result["completed"] == 2
    assert result["total"] == 2
    assert task.status == "completed"
    assert task.progress == 100
    assert provider.chat.call_count == 2


@patch("app.tasks.execute_task.time.sleep")
@patch("app.tasks.execute_task.OpenAIProvider")
@patch("app.tasks.execute_task.get_sync_db")
def test_pause_stops_execution(mock_get_db, mock_provider_cls, mock_sleep):
    task = _make_task()
    session = _make_session(task, _make_questions())
    mock_get_db.return_value = _wrap_ctx(session)

    refresh_count = [0]

    def refresh_side_effect(obj):
        refresh_count[0] += 1
        if refresh_count[0] >= 2:
            task.status = "paused"
    session.refresh = refresh_side_effect

    provider = MagicMock()
    provider.chat.return_value = LLMResponse(
        content="Answer", model="gpt-4o-mini", usage={}, raw_response={},
    )
    mock_provider_cls.return_value = provider

    from app.tasks.execute_task import run_monitoring_task
    result = run_monitoring_task("task-1")

    assert result["status"] == "paused"
    # First question processed, second stopped by pause
    assert provider.chat.call_count == 1


@patch("app.tasks.execute_task.OpenAIProvider")
@patch("app.tasks.execute_task.get_sync_db")
def test_task_not_found(mock_get_db, mock_provider_cls):
    session = MagicMock()
    session.execute = MagicMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    mock_get_db.return_value = _wrap_ctx(session)

    from app.tasks.execute_task import run_monitoring_task
    result = run_monitoring_task("nonexistent")

    assert result["status"] == "error"


@patch("app.tasks.execute_task.time.sleep")
@patch("app.tasks.execute_task.OpenAIProvider")
@patch("app.tasks.execute_task.get_sync_db")
def test_llm_error_continues(mock_get_db, mock_provider_cls, mock_sleep):
    task = _make_task()
    session = _make_session(task, _make_questions())
    mock_get_db.return_value = _wrap_ctx(session)

    provider = MagicMock()
    provider.chat.side_effect = [
        Exception("API timeout"),
        LLMResponse(content="OK", model="gpt-4o-mini"),
    ]
    mock_provider_cls.return_value = provider

    from app.tasks.execute_task import run_monitoring_task
    result = run_monitoring_task("task-1")

    assert result["status"] == "completed"
    assert result["completed"] == 2
    assert provider.chat.call_count == 2


@patch("app.tasks.execute_task.time.sleep")
@patch("app.tasks.execute_task.OpenAIProvider")
@patch("app.tasks.execute_task.get_sync_db")
def test_resume_skips_completed(mock_get_db, mock_provider_cls, mock_sleep):
    task = _make_task()
    task.started_at = datetime.now(timezone.utc)
    session = _make_session(task, _make_questions(), completed_question_ids=["q-1"])
    mock_get_db.return_value = _wrap_ctx(session)

    provider = MagicMock()
    provider.chat.return_value = LLMResponse(
        content="Answer", model="gpt-4o-mini", usage={}, raw_response={},
    )
    mock_provider_cls.return_value = provider

    from app.tasks.execute_task import run_monitoring_task
    result = run_monitoring_task("task-1")

    assert result["status"] == "completed"
    assert provider.chat.call_count == 1
