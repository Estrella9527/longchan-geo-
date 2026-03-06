"""Unit tests for analysis_service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.services.analysis.analysis_service import (
    get_brand_analysis,
    get_competitor_analysis,
    export_task_results_csv,
)


def _make_result(answer_text, sources=None, created_at=None):
    """Helper to create mock TaskResult."""
    r = MagicMock()
    r.answer_text = answer_text
    r.question_text = "测试问题"
    r.model_name = "gpt-4o-mini"
    r.sources = sources or []
    r.created_at = created_at or datetime(2024, 1, 15, tzinfo=timezone.utc)
    r.task_id = "task-1"
    return r


def _make_brand(name="测试品牌"):
    b = MagicMock()
    b.id = "brand-1"
    b.name = name
    return b


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_brand_not_found(mock_db):
    result_obj = MagicMock()
    result_obj.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = result_obj

    result = await get_brand_analysis(mock_db, "nonexistent")
    assert "error" in result


@pytest.mark.asyncio
async def test_brand_no_results(mock_db):
    brand = _make_brand()

    call_count = [0]

    async def mock_execute(stmt):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.scalar_one_or_none.return_value = brand
        else:
            result.scalars.return_value.all.return_value = []
        return result

    mock_db.execute = mock_execute

    result = await get_brand_analysis(mock_db, "brand-1")
    assert result["total_results"] == 0
    assert result["visibility"]["score"] == 0


@pytest.mark.asyncio
async def test_visibility_calculation(mock_db):
    brand = _make_brand("TestBrand")
    results = [
        _make_result("TestBrand is great for GEO optimization"),
        _make_result("This product has no mention of the brand"),
        _make_result("testbrand offers good features"),  # case-insensitive
        _make_result("Nothing relevant here"),
    ]

    call_count = [0]

    async def mock_execute(stmt):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.scalar_one_or_none.return_value = brand
        else:
            result.scalars.return_value.all.return_value = results
        return result

    mock_db.execute = mock_execute

    analysis = await get_brand_analysis(mock_db, "brand-1")
    assert analysis["total_results"] == 4
    assert analysis["visibility"]["mentioned_count"] == 2
    assert analysis["visibility"]["score"] == 50.0


@pytest.mark.asyncio
async def test_sentiment_classification(mock_db):
    brand = _make_brand("品牌A")
    results = [
        _make_result("品牌A非常优秀，推荐购买"),  # positive
        _make_result("品牌A有很多问题，差评"),  # negative
        _make_result("品牌A是一个品牌"),  # neutral
    ]

    call_count = [0]

    async def mock_execute(stmt):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.scalar_one_or_none.return_value = brand
        else:
            result.scalars.return_value.all.return_value = results
        return result

    mock_db.execute = mock_execute

    analysis = await get_brand_analysis(mock_db, "brand-1")
    assert analysis["sentiment"]["positive"] == 1
    assert analysis["sentiment"]["negative"] == 1
    assert analysis["sentiment"]["neutral"] == 1


@pytest.mark.asyncio
async def test_source_domain_analysis(mock_db):
    brand = _make_brand("品牌B")
    results = [
        _make_result("品牌B info", sources=[
            {"url": "https://example.com/page1", "title": "Ex1"},
            {"url": "https://example.com/page2", "title": "Ex2"},
            {"url": "https://other.com/page", "title": "Other"},
        ]),
    ]

    call_count = [0]

    async def mock_execute(stmt):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.scalar_one_or_none.return_value = brand
        else:
            result.scalars.return_value.all.return_value = results
        return result

    mock_db.execute = mock_execute

    analysis = await get_brand_analysis(mock_db, "brand-1")
    domains = {d["domain"]: d["count"] for d in analysis["sources"]["domains"]}
    assert domains["example.com"] == 2
    assert domains["other.com"] == 1
    assert analysis["sources"]["total_sources"] == 3


@pytest.mark.asyncio
async def test_trend_grouped_by_date(mock_db):
    brand = _make_brand("品牌C")
    results = [
        _make_result("品牌C mentioned", created_at=datetime(2024, 1, 15, tzinfo=timezone.utc)),
        _make_result("品牌C again", created_at=datetime(2024, 1, 15, tzinfo=timezone.utc)),
        _make_result("no mention", created_at=datetime(2024, 1, 16, tzinfo=timezone.utc)),
    ]

    call_count = [0]

    async def mock_execute(stmt):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.scalar_one_or_none.return_value = brand
        else:
            result.scalars.return_value.all.return_value = results
        return result

    mock_db.execute = mock_execute

    analysis = await get_brand_analysis(mock_db, "brand-1")
    assert len(analysis["trend"]) == 2
    # Jan 15: 2/2 mentioned = 100%
    day1 = next(t for t in analysis["trend"] if t["date"] == "2024-01-15")
    assert day1["visibility"] == 100.0
    assert day1["mentioned"] == 2
    # Jan 16: 0/1 mentioned = 0%
    day2 = next(t for t in analysis["trend"] if t["date"] == "2024-01-16")
    assert day2["visibility"] == 0.0


@pytest.mark.asyncio
async def test_export_csv(mock_db):
    results = [
        _make_result("Answer text", sources=[{"url": "https://a.com", "title": "A"}]),
    ]

    result_obj = MagicMock()
    result_obj.scalars.return_value.all.return_value = results
    mock_db.execute.return_value = result_obj

    rows = await export_task_results_csv(mock_db, "task-1")
    assert len(rows) == 1
    assert rows[0]["question"] == "测试问题"
    assert rows[0]["answer"] == "Answer text"
    assert "https://a.com" in rows[0]["sources"]
    assert rows[0]["source_count"] == 1


@pytest.mark.asyncio
async def test_export_csv_empty(mock_db):
    result_obj = MagicMock()
    result_obj.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = result_obj

    rows = await export_task_results_csv(mock_db, "task-1")
    assert rows == []
