"""
Parse information sources (URLs, references) from LLM response text.
"""
import re


def parse_sources(text: str) -> list[dict]:
    """Extract source URLs and references from LLM response text.

    Handles:
    - Bare URLs: https://example.com
    - Markdown links: [title](url)
    - Numbered references: [1] title - url

    Returns:
        List of dicts with 'url' and optional 'title'.
    """
    if not text:
        return []

    seen_urls: set[str] = set()
    sources: list[dict] = []

    def _add(url: str, title: str = ""):
        url = url.strip().rstrip(".,;:!?)>」】。，；：！？）")
        if url and url not in seen_urls:
            seen_urls.add(url)
            sources.append({"url": url, "title": title.strip() or url})

    # Pattern 1: Markdown links [title](url)
    for m in re.finditer(r'\[([^\]]+)\]\((https?://[^\s\)]+)\)', text):
        _add(m.group(2), m.group(1))

    # Pattern 2: Numbered references like [1] Title - https://...
    for m in re.finditer(r'\[\d+\]\s*([^:\n]*?)\s*[-—:]\s*(https?://\S+)', text):
        _add(m.group(2), m.group(1))

    # Pattern 3: Bare URLs (not already captured)
    # Exclude CJK characters and common CJK punctuation from URL matching
    for m in re.finditer(r'(?<!\()(https?://[^\s\)\]>"」】\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+)', text):
        _add(m.group(1))

    return sources
