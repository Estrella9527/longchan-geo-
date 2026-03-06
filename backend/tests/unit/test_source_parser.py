"""Unit tests for source_parser.parse_sources()."""
import pytest
from app.services.llm.source_parser import parse_sources


def test_empty_text():
    assert parse_sources("") == []
    assert parse_sources(None) == []


def test_bare_url():
    text = "参考 https://example.com/page 获取更多信息"
    result = parse_sources(text)
    assert len(result) == 1
    assert result[0]["url"] == "https://example.com/page"


def test_multiple_bare_urls():
    text = "来源: https://a.com 和 https://b.com"
    result = parse_sources(text)
    assert len(result) == 2
    urls = {s["url"] for s in result}
    assert urls == {"https://a.com", "https://b.com"}


def test_markdown_link():
    text = "请参阅 [官方文档](https://docs.example.com/guide)"
    result = parse_sources(text)
    assert len(result) == 1
    assert result[0]["url"] == "https://docs.example.com/guide"
    assert result[0]["title"] == "官方文档"


def test_numbered_reference():
    text = "[1] 百度百科 - https://baike.baidu.com/item/test"
    result = parse_sources(text)
    assert len(result) == 1
    assert result[0]["url"] == "https://baike.baidu.com/item/test"
    assert result[0]["title"] == "百度百科"


def test_dedup():
    text = "来源 https://a.com ，另见 https://a.com"
    result = parse_sources(text)
    assert len(result) == 1


def test_trailing_punctuation_stripped():
    text = "来源: https://example.com/page。更多信息请见 https://other.com/path，以及其他。"
    result = parse_sources(text)
    urls = {s["url"] for s in result}
    assert "https://example.com/page" in urls
    assert "https://other.com/path" in urls


def test_trailing_chinese_punctuation():
    text = "参考https://a.com/test。"
    result = parse_sources(text)
    assert result[0]["url"] == "https://a.com/test"


def test_mixed_patterns():
    text = """
    根据 [官方报告](https://report.com/2024) 和以下来源:
    [1] 新浪财经 - https://finance.sina.com.cn/article
    更多参考: https://other.com/ref
    """
    result = parse_sources(text)
    assert len(result) == 3
    urls = {s["url"] for s in result}
    assert "https://report.com/2024" in urls
    assert "https://finance.sina.com.cn/article" in urls
    assert "https://other.com/ref" in urls


def test_url_with_query_params():
    text = "来源: https://example.com/search?q=brand&page=1"
    result = parse_sources(text)
    assert result[0]["url"] == "https://example.com/search?q=brand&page=1"


def test_http_url():
    text = "来源: http://old-site.com/page"
    result = parse_sources(text)
    assert len(result) == 1
    assert result[0]["url"] == "http://old-site.com/page"


def test_no_urls():
    text = "这个品牌非常好，推荐购买。没有引用任何来源。"
    assert parse_sources(text) == []


def test_bare_url_title_defaults_to_url():
    text = "来源 https://example.com"
    result = parse_sources(text)
    assert result[0]["title"] == "https://example.com"
