"""
Browser-based LLM Provider base classes.

Extends BaseLLMProvider for Playwright-based browser automation
that captures AI responses + real "read web pages" sources.

Architecture:
    BaseLLMProvider (ABC)
      ├── OpenAIProvider          — sync httpx → OpenAI API
      └── BaseBrowserProvider     — Playwright 浏览器自动化基类
            ├── DoubaoProvider    — 封装 doubao.com
            └── DeepSeekProvider  — 封装 chat.deepseek.com

Key design decisions:
    - chat() is sync (Celery requirement). Browser providers bridge via _run_async().
    - Browser lifecycle (start/close) is managed inside chat(), not by caller.
    - Subclasses only implement platform-specific hooks; common waiting/extraction
      logic lives in the base class.
    - Selectors are configurable class-level dicts, overridable per platform.
"""
import asyncio
import json
import logging
import re
import time
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone

from app.services.llm.base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CrawledSource:
    """A web page crawled via the browser."""
    url: str
    title: str = ""
    text_content: str = ""
    html_content: str = ""
    success: bool = True
    error: str = ""
    crawled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class BrowserLLMResponse(LLMResponse):
    """Extended response from browser-based providers.

    Adds fields that only browser crawling can produce:
    - ai_read_sources: URLs the AI actually "read" (from UI element)
    - crawled_sources: full page content for each crawled URL
    - response_time_ms: end-to-end time including browser interaction
    """
    crawled_sources: list[CrawledSource] = field(default_factory=list)
    ai_read_sources: list[str] = field(default_factory=list)
    response_time_ms: int = 0


# ---------------------------------------------------------------------------
# Selector configuration — override in subclasses for platform-specific DOM
# ---------------------------------------------------------------------------

@dataclass
class PlatformSelectors:
    """CSS selectors / JS snippets configurable per platform."""
    # Chat input
    textarea: str = "textarea"

    # Answer containers (tried in order, first non-empty wins)
    answer_selectors: tuple[str, ...] = (
        '[class*="message"]',
        '[class*="response"]',
        '[class*="answer"]',
        '[class*="chat"]',
        'div[role="article"]',
    )

    # Domains to exclude when collecting external source links
    exclude_domains: tuple[str, ...] = ()

    # JS to detect "stop generating" button
    stop_button_js: str = """
        () => {
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {
                const text = btn.textContent || btn.innerText || '';
                const ariaLabel = btn.getAttribute('aria-label') || '';
                if (text.includes('停止') || text.includes('Stop') ||
                    ariaLabel.includes('停止') || ariaLabel.includes('Stop')) {
                    return true;
                }
            }
            return false;
        }
    """


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseBrowserProvider(BaseLLMProvider):
    """Abstract base for Playwright browser-based LLM providers.

    Subclasses MUST implement:
        provider_name, SITE_URL, selectors,
        check_login_status(), navigate_to_chat(),
        submit_question(question), extract_web_sources()
    """

    SITE_URL: str = ""
    selectors: PlatformSelectors = PlatformSelectors()

    def __init__(self, user_data_dir: str, headless: bool = True, max_crawl_urls: int = 10):
        self.user_data_dir = user_data_dir
        self.headless = headless
        self.max_crawl_urls = max_crawl_urls
        self._playwright = None
        self._context = None
        self._page = None

    @property
    def page(self):
        return self._page

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    # -- browser lifecycle ---------------------------------------------------

    async def _close(self):
        if self._context:
            try:
                # Manually export cookies before closing — persistent context
                # doesn't reliably write cookies to SQLite in headless mode
                import os, json
                cookies = await self._context.cookies()
                if cookies:
                    state_path = os.path.join(self.user_data_dir, "cookies.json")
                    with open(state_path, "w") as f:
                        json.dump(cookies, f)
                    logger.info(f"[{self.provider_name}] Saved {len(cookies)} cookies to cookies.json")
            except Exception as e:
                logger.debug(f"[{self.provider_name}] Cookie save failed: {e}")
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        self._page = None
        logger.info(f"[{self.provider_name}] Browser closed")

    async def _start(self):
        if self._page is not None:
            return
        from playwright.async_api import async_playwright
        import os
        self._playwright = await async_playwright().start()

        self._context = await self._playwright.chromium.launch_persistent_context(
            self.user_data_dir,
            headless=self.headless,
            viewport={"width": 1280, "height": 800},
        )

        # Restore saved cookies — persistent context doesn't reliably persist
        # cookies in headless mode, so we manually save/restore them
        cookies_path = os.path.join(self.user_data_dir, "cookies.json")
        if os.path.exists(cookies_path):
            try:
                import json
                with open(cookies_path, "r") as f:
                    cookies = json.load(f)
                if cookies:
                    await self._context.add_cookies(cookies)
                    logger.info(f"[{self.provider_name}] Restored {len(cookies)} cookies from cookies.json")
            except Exception as e:
                logger.debug(f"[{self.provider_name}] Failed to restore cookies: {e}")

        self._page = await self._context.new_page()
        logger.info(f"[{self.provider_name}] Browser started (headless={self.headless})")

    # -- async/sync bridge ---------------------------------------------------

    @staticmethod
    def _run_async(coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    # -- BaseLLMProvider interface (sync) ------------------------------------

    def chat(self, messages: list[dict], model: Optional[str] = None) -> BrowserLLMResponse:
        return self._run_async(self._async_chat(messages, model))

    # -- core async flow -----------------------------------------------------

    async def _async_chat(self, messages: list[dict], model: Optional[str] = None) -> BrowserLLMResponse:
        question = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                question = msg["content"]
                break
        if not question:
            return BrowserLLMResponse(
                content="[ERROR] No user question found in messages",
                model=self.provider_name,
            )

        start_time = time.time()
        try:
            await self._start()

            logged_in = await self.check_login_status()
            if not logged_in:
                return BrowserLLMResponse(
                    content=f"[ERROR] {self.provider_name} session expired, please re-authenticate",
                    model=self.provider_name,
                    response_time_ms=int((time.time() - start_time) * 1000),
                )

            await self.navigate_to_new_chat()
            await asyncio.sleep(1)

            pre_text = await self._get_page_text()
            await self.submit_question(question)

            answer_text = await self.wait_for_answer_v2(pre_text, timeout=90)

            # Collect URLs from both UI element and answer text
            web_sources = await self.extract_web_sources()
            ai_read_urls = [s["url"] for s in web_sources if s.get("url")]
            text_urls = self._extract_urls_from_text(answer_text)
            all_urls = self._merge_urls(ai_read_urls, text_urls)

            crawled_sources = []
            for url in all_urls[:self.max_crawl_urls]:
                source = await self._crawl_url(url)
                crawled_sources.append(source)
                await asyncio.sleep(1)

            response_time_ms = int((time.time() - start_time) * 1000)
            return BrowserLLMResponse(
                content=answer_text or "[ERROR] Failed to extract answer",
                model=self.provider_name,
                crawled_sources=crawled_sources,
                ai_read_sources=ai_read_urls,
                response_time_ms=response_time_ms,
            )

        except Exception as e:
            logger.exception(f"[{self.provider_name}] chat failed: {e}")
            return BrowserLLMResponse(
                content=f"[ERROR] Browser provider failed: {e}",
                model=self.provider_name,
                response_time_ms=int((time.time() - start_time) * 1000),
            )
        finally:
            await self._close()

    # -- subclass hooks (abstract) -------------------------------------------

    @abstractmethod
    async def check_login_status(self) -> bool:
        ...

    @abstractmethod
    async def navigate_to_chat(self):
        ...

    @abstractmethod
    async def navigate_to_new_chat(self):
        """Navigate to a fresh/new chat session (no prior conversation context)."""
        ...

    @abstractmethod
    async def submit_question(self, question: str):
        ...

    @abstractmethod
    async def extract_web_sources(self) -> list[dict]:
        ...

    # -- common implementations (overridable) --------------------------------

    async def wait_for_answer(self, timeout: int = 60, check_interval: int = 2) -> str:
        await asyncio.sleep(3)

        elapsed = 0
        last_length = 0
        stable_count = 0
        stop_was_present = False

        while elapsed < timeout:
            stop_exists = await self._page.evaluate(self.selectors.stop_button_js)

            if stop_exists:
                stop_was_present = True

            current_length = await self._measure_answer_length()

            if stop_was_present and not stop_exists and current_length > 0:
                break

            if current_length == last_length and current_length > 0:
                stable_count += 1
                if stable_count >= 3:
                    break
            else:
                stable_count = 0
                last_length = current_length

            await asyncio.sleep(check_interval)
            elapsed += check_interval

        if elapsed >= timeout:
            logger.warning(f"[{self.provider_name}] Wait timeout ({timeout}s), extracting anyway")

        await asyncio.sleep(2)
        return await self._extract_latest_answer()

    async def _measure_answer_length(self) -> int:
        selectors_js = json.dumps(list(self.selectors.answer_selectors))
        return await self._page.evaluate(f"""
            () => {{
                const selectors = {selectors_js};
                for (const selector of selectors) {{
                    const msgs = document.querySelectorAll(selector);
                    if (msgs.length > 0) {{
                        return (msgs[msgs.length - 1].innerText || '').length;
                    }}
                }}
                return 0;
            }}
        """)

    async def _extract_latest_answer(self) -> str:
        for selector in self.selectors.answer_selectors:
            try:
                messages = await self._page.query_selector_all(selector)
                if messages:
                    answer = await messages[-1].inner_text()
                    if answer and len(answer) > 10:
                        return answer
            except Exception:
                continue
        return ""

    async def _crawl_url(self, url: str, timeout: int = 30) -> CrawledSource:
        new_page = None
        try:
            new_page = await self._context.new_page()
            await new_page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            await asyncio.sleep(2)

            title = await new_page.title()
            html_content = await new_page.content()
            text_content = await new_page.evaluate("""
                () => {
                    document.querySelectorAll('script, style').forEach(s => s.remove());
                    return document.body.innerText || document.body.textContent || '';
                }
            """)
            return CrawledSource(
                url=url, title=title,
                text_content=text_content, html_content=html_content,
                success=True,
            )
        except Exception as e:
            return CrawledSource(url=url, success=False, error=str(e))
        finally:
            if new_page:
                try:
                    await new_page.close()
                except Exception:
                    pass

    # -- text-diff answer extraction (v2 — platform-agnostic) -----------------

    async def _get_page_text(self) -> str:
        """Snapshot the full visible text of the page."""
        return await self._page.evaluate("() => document.body.innerText || ''")

    def _extract_diff(self, before: str, after: str) -> str:
        """Extract new lines in `after` that were not in `before`."""
        before_lines = set(before.splitlines())
        new_lines = [l for l in after.splitlines() if l.strip() and l not in before_lines]
        return "\n".join(new_lines).strip()

    _URL_PATTERN = re.compile(
        r'https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}'
        r'\b[-a-zA-Z0-9()@:%_+.~#?&/=]*'
    )

    def _extract_urls_from_text(self, text: str) -> list[str]:
        """Extract HTTP(S) URLs from answer text via regex."""
        if not text:
            return []
        urls = self._URL_PATTERN.findall(text)
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique.append(url)
        return unique

    def _merge_urls(self, primary: list[str], secondary: list[str]) -> list[str]:
        """Merge two URL lists, deduplicating, primary first."""
        seen = set()
        merged = []
        for url in primary + secondary:
            if url not in seen:
                seen.add(url)
                merged.append(url)
        return merged

    async def wait_for_answer_v2(self, pre_text: str, timeout: int = 90) -> str:
        """Wait for answer using text-diff (no CSS selectors needed).

        Strategy: compare page text before and after question submission.
        Waits for stop button to disappear OR text to stabilize.
        """
        await asyncio.sleep(5)  # initial generation delay

        elapsed = 0
        check_interval = 2
        last_text = ""
        stable_count = 0
        stop_was_present = False

        while elapsed < timeout:
            stop_exists = await self._page.evaluate(self.selectors.stop_button_js)
            if stop_exists:
                stop_was_present = True

            current_text = await self._get_page_text()
            diff = self._extract_diff(pre_text, current_text)

            # Signal 1: stop button appeared then disappeared, and we have content
            if stop_was_present and not stop_exists and len(diff) > 10:
                logger.debug(f"[{self.provider_name}] Stop button gone, answer ready ({len(diff)} chars)")
                break

            # Signal 2: text stabilized for 3 consecutive checks
            if current_text == last_text and len(diff) > 10:
                stable_count += 1
                if stable_count >= 3:
                    logger.debug(f"[{self.provider_name}] Text stable, answer ready ({len(diff)} chars)")
                    break
            else:
                stable_count = 0

            last_text = current_text
            await asyncio.sleep(check_interval)
            elapsed += check_interval

        if elapsed >= timeout:
            logger.warning(f"[{self.provider_name}] wait_for_answer_v2 timeout ({timeout}s)")

        await asyncio.sleep(2)  # final render buffer
        final_text = await self._get_page_text()
        return self._extract_diff(pre_text, final_text)

    # -- batch execution (browser stays open across questions) ----------------

    def chat_batch(self, questions: list[dict], model: str | None = None) -> list[BrowserLLMResponse]:
        """Synchronous batch entry — runs all questions with a single browser session."""
        return self._run_async(self._async_chat_batch(questions, model))

    async def _async_chat_batch(self, questions: list[dict], model: str | None = None) -> list[BrowserLLMResponse]:
        """Batch flow: start browser once → iterate questions → close once."""
        results: list[BrowserLLMResponse] = []
        try:
            await self._start()

            logged_in = await self.check_login_status()
            if not logged_in:
                error_resp = BrowserLLMResponse(
                    content=f"[ERROR] {self.provider_name} session expired, please re-authenticate",
                    model=self.provider_name,
                )
                return [error_resp] * len(questions)

            for i, q_data in enumerate(questions):
                question = q_data.get("question", "")
                start_time = time.time()
                try:
                    await self.navigate_to_new_chat()
                    await asyncio.sleep(1)

                    pre_text = await self._get_page_text()
                    await self.submit_question(question)
                    answer_text = await self.wait_for_answer_v2(pre_text, timeout=90)

                    web_sources = await self.extract_web_sources()
                    ai_read_urls = [s["url"] for s in web_sources if s.get("url")]
                    text_urls = self._extract_urls_from_text(answer_text)
                    all_urls = self._merge_urls(ai_read_urls, text_urls)

                    crawled_sources = []
                    for url in all_urls[:self.max_crawl_urls]:
                        source = await self._crawl_url(url)
                        crawled_sources.append(source)
                        await asyncio.sleep(1)

                    response_time_ms = int((time.time() - start_time) * 1000)
                    results.append(BrowserLLMResponse(
                        content=answer_text or "[ERROR] Failed to extract answer",
                        model=self.provider_name,
                        crawled_sources=crawled_sources,
                        ai_read_sources=ai_read_urls,
                        response_time_ms=response_time_ms,
                    ))
                    logger.info(
                        f"[{self.provider_name}] Batch {i+1}/{len(questions)} done "
                        f"({len(answer_text)} chars, {int((time.time()-start_time)*1000)}ms)"
                    )
                except Exception as e:
                    logger.warning(f"[{self.provider_name}] Batch question {i+1} failed: {e}")
                    results.append(BrowserLLMResponse(
                        content=f"[ERROR] Browser provider failed: {e}",
                        model=self.provider_name,
                        response_time_ms=int((time.time() - start_time) * 1000),
                    ))

                # Anti-bot delay between questions
                if i < len(questions) - 1:
                    await asyncio.sleep(3)

        except Exception as e:
            logger.exception(f"[{self.provider_name}] Batch execution failed: {e}")
            # Fill remaining with errors
            while len(results) < len(questions):
                results.append(BrowserLLMResponse(
                    content=f"[ERROR] Batch execution failed: {e}",
                    model=self.provider_name,
                ))
        finally:
            await self._close()

        return results

    # -- helpers for subclasses ----------------------------------------------

    async def _find_and_click_send(self):
        page = self._page

        for label in ("发送", "Send"):
            btn = await page.query_selector(f'button[aria-label*="{label}"]')
            if btn:
                await btn.click()
                return

        for button in await page.query_selector_all("button"):
            try:
                text = await button.inner_text()
                if text and ("发送" in text or "Send" in text):
                    await button.click()
                    return
            except Exception:
                continue

        clicked = await page.evaluate("""
            () => {
                const ta = document.querySelector('textarea');
                if (!ta) return false;
                const parent = ta.closest('div');
                if (!parent) return false;
                const btns = parent.querySelectorAll('button');
                if (btns.length > 0) { btns[btns.length - 1].click(); return true; }
                return false;
            }
        """)
        if clicked:
            return

        textarea = await page.query_selector(self.selectors.textarea)
        if textarea:
            await textarea.press("Enter")

    def _deduplicate_urls(self, items: list[dict]) -> list[dict]:
        seen = set()
        unique = []
        for item in items:
            url = item.get("url", "")
            if url and url not in seen:
                seen.add(url)
                unique.append(item)
        return unique
