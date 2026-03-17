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


def _make_task(provider_type="api"):
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
    task.provider_type = provider_type
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


# ─── Browser batch + crawled pages tests ─────────────────────────────

from app.services.llm.browser_base import BaseBrowserProvider, BrowserLLMResponse, CrawledSource


class FakeBrowserProvider(BaseBrowserProvider):
    """Minimal concrete subclass for testing isinstance checks."""

    SITE_URL = "https://example.com"

    @property
    def provider_name(self):
        return "fake_browser"

    async def check_login_status(self):
        return True

    async def navigate_to_chat(self):
        pass

    async def navigate_to_new_chat(self):
        pass

    async def submit_question(self, question):
        pass

    async def extract_web_sources(self):
        return []


def _make_browser_task():
    return _make_task(provider_type="browser_doubao")


def _make_crawled_source(url="https://example.com/page1", title="Example Page",
                         text_content="This is crawled text content for testing.",
                         success=True):
    return CrawledSource(
        url=url,
        title=title,
        text_content=text_content,
        html_content=f"<html><body>{text_content}</body></html>",
        success=success,
    )


def _make_browser_response(answer="AI回答内容", crawled_sources=None, ai_read_sources=None):
    return BrowserLLMResponse(
        content=answer,
        model="doubao",
        crawled_sources=crawled_sources or [],
        ai_read_sources=ai_read_sources or [],
        response_time_ms=5000,
    )


@patch("app.tasks.execute_task.get_provider")
@patch("app.tasks.execute_task.get_sync_db")
def test_browser_batch_saves_crawled_pages(mock_get_db, mock_get_provider):
    """Browser batch path should call chat_batch and save CrawledPage records."""
    task = _make_browser_task()
    questions = _make_questions()
    session = _make_session(task, questions)
    mock_get_db.return_value = _wrap_ctx(session)

    # Create a real FakeBrowserProvider instance
    provider = FakeBrowserProvider(user_data_dir="/tmp/fake", headless=True)

    # Mock chat_batch to return responses with crawled sources
    src1 = _make_crawled_source("https://example.com/1", "Page 1", "Content of page 1")
    src2 = _make_crawled_source("https://example.com/2", "Page 2", "Content of page 2")
    resp1 = _make_browser_response("回答1", [src1], ["https://example.com/1"])
    resp2 = _make_browser_response("回答2", [src2], ["https://example.com/2"])
    provider.chat_batch = MagicMock(return_value=[resp1, resp2])

    mock_get_provider.return_value = provider

    from app.tasks.execute_task import run_monitoring_task
    result = run_monitoring_task("task-1")

    assert result["status"] == "completed"
    assert result["completed"] == 2

    # Verify chat_batch was called (not chat)
    provider.chat_batch.assert_called_once()
    batch_args = provider.chat_batch.call_args[0][0]
    assert len(batch_args) == 2
    assert batch_args[0]["question"] == "什么是GEO?"
    assert batch_args[1]["question"] == "品牌推荐?"

    # Verify db.add was called for both TaskResult AND CrawledPage objects
    add_calls = session.add.call_args_list
    # Should have: 2 TaskResults + 2 CrawledPages = 4 adds minimum
    assert len(add_calls) >= 4


@patch("app.tasks.execute_task.get_provider")
@patch("app.tasks.execute_task.get_sync_db")
def test_browser_batch_saves_sources_with_text_snippet(mock_get_db, mock_get_provider):
    """sources JSON should include text_snippet field from crawled content."""
    task = _make_browser_task()
    questions = [MagicMock(id="q-1", content="测试问题", sort_order=1)]
    session = _make_session(task, questions)
    mock_get_db.return_value = _wrap_ctx(session)

    provider = FakeBrowserProvider(user_data_dir="/tmp/fake", headless=True)

    long_text = "这是一段很长的爬取内容。" * 100  # ~1200 chars
    src = _make_crawled_source("https://ex.com", "Title", long_text)
    resp = _make_browser_response("AI回答", [src], ["https://ex.com"])
    provider.chat_batch = MagicMock(return_value=[resp])
    mock_get_provider.return_value = provider

    from app.tasks.execute_task import run_monitoring_task
    result = run_monitoring_task("task-1")

    assert result["status"] == "completed"

    # Find the TaskResult add call and check sources
    from app.models.task import TaskResult as TR
    task_result_adds = [
        call for call in session.add.call_args_list
        if isinstance(call[0][0], TR)
    ]
    assert len(task_result_adds) == 1
    tr = task_result_adds[0][0][0]
    assert len(tr.sources) == 1
    assert "text_snippet" in tr.sources[0]
    assert len(tr.sources[0]["text_snippet"]) <= 500  # truncated


@patch("app.tasks.execute_task.get_provider")
@patch("app.tasks.execute_task.get_sync_db")
def test_browser_batch_handles_failed_crawl(mock_get_db, mock_get_provider):
    """Failed crawls should still be saved in crawled_pages with error."""
    task = _make_browser_task()
    questions = [MagicMock(id="q-1", content="测试", sort_order=1)]
    session = _make_session(task, questions)
    mock_get_db.return_value = _wrap_ctx(session)

    provider = FakeBrowserProvider(user_data_dir="/tmp/fake", headless=True)

    failed_src = CrawledSource(url="https://fail.com", success=False, error="Timeout")
    ok_src = _make_crawled_source("https://ok.com", "OK", "Content")
    resp = _make_browser_response("回答", [failed_src, ok_src], ["https://fail.com", "https://ok.com"])
    provider.chat_batch = MagicMock(return_value=[resp])
    mock_get_provider.return_value = provider

    from app.tasks.execute_task import run_monitoring_task
    result = run_monitoring_task("task-1")

    assert result["status"] == "completed"

    # Both crawled pages should be saved (success + failure)
    from app.models.task import CrawledPage as CP
    cp_adds = [
        call for call in session.add.call_args_list
        if isinstance(call[0][0], CP)
    ]
    assert len(cp_adds) == 2

    # Only the successful one should be in sources (filtered by success)
    from app.models.task import TaskResult as TR
    tr_adds = [
        call for call in session.add.call_args_list
        if isinstance(call[0][0], TR)
    ]
    assert len(tr_adds) == 1
    tr = tr_adds[0][0][0]
    assert len(tr.sources) == 1  # only ok_src


@patch("app.tasks.execute_task.time.sleep")
@patch("app.tasks.execute_task.OpenAIProvider")
@patch("app.tasks.execute_task.get_sync_db")
def test_api_provider_unchanged(mock_get_db, mock_provider_cls, mock_sleep):
    """API provider path should still work (no browser batch), no crawled pages."""
    task = _make_task(provider_type="api")
    session = _make_session(task, _make_questions())
    mock_get_db.return_value = _wrap_ctx(session)

    provider = MagicMock()
    provider.chat.return_value = LLMResponse(
        content="普通API回答。来源: https://example.com",
        model="gpt-4o-mini", usage={}, raw_response={},
    )
    mock_provider_cls.return_value = provider

    from app.tasks.execute_task import run_monitoring_task
    result = run_monitoring_task("task-1")

    assert result["status"] == "completed"
    assert provider.chat.call_count == 2

    # No CrawledPage should be saved
    from app.models.task import CrawledPage as CP
    cp_adds = [
        call for call in session.add.call_args_list
        if isinstance(call[0][0], CP)
    ]
    assert len(cp_adds) == 0


# ─── URL extraction from text tests ──────────────────────────────

def test_extract_urls_from_text():
    """_extract_urls_from_text should find HTTP URLs in answer text."""
    from app.services.llm.browser_base import BaseBrowserProvider

    provider = FakeBrowserProvider(user_data_dir="/tmp/fake", headless=True)

    text = "参考 https://example.com/page1 和 http://test.org/path?q=1 了解更多。"
    urls = provider._extract_urls_from_text(text)
    assert len(urls) == 2
    assert "https://example.com/page1" in urls
    assert "http://test.org/path?q=1" in urls


def test_extract_urls_deduplicates():
    """Duplicate URLs in text should be deduplicated."""
    from app.services.llm.browser_base import BaseBrowserProvider

    provider = FakeBrowserProvider(user_data_dir="/tmp/fake", headless=True)

    text = "见 https://a.com 和 https://a.com 两处引用"
    urls = provider._extract_urls_from_text(text)
    assert len(urls) == 1


def test_merge_urls():
    """_merge_urls should merge primary + secondary, dedup, primary first."""
    from app.services.llm.browser_base import BaseBrowserProvider

    provider = FakeBrowserProvider(user_data_dir="/tmp/fake", headless=True)

    primary = ["https://a.com", "https://b.com"]
    secondary = ["https://b.com", "https://c.com"]
    merged = provider._merge_urls(primary, secondary)
    assert merged == ["https://a.com", "https://b.com", "https://c.com"]


def test_extract_urls_empty_text():
    """Empty or None text should return empty list."""
    from app.services.llm.browser_base import BaseBrowserProvider

    provider = FakeBrowserProvider(user_data_dir="/tmp/fake", headless=True)

    assert provider._extract_urls_from_text("") == []
    assert provider._extract_urls_from_text("没有链接的文本") == []
