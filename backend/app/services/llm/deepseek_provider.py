"""
DeepSeek browser-based LLM provider.

Platform-specific hooks for chat.deepseek.com Web UI.
Common logic (wait_for_answer, _extract_latest_answer, _crawl_url)
is inherited from BaseBrowserProvider.

DeepSeek login page DOM (verified 2026-03-10):
- URL: https://chat.deepseek.com/sign_in
- Phone: <input type="tel" placeholder="请输入手机号">  (with +86 prefix UI element)
- Code:  <input type="tel" placeholder="请输入验证码">
- Send:  <button class="ds-link-button ds-verify-code-input-countdown">发送验证码</button>
- Login: <button type="submit" class="...ds-basic-button--primary">登录</button>
- No tab switch needed (phone login is the default)
- No checkbox needed (agreement is implicit)
"""
import asyncio
import logging

from app.services.llm.browser_base import BaseBrowserProvider, PlatformSelectors

logger = logging.getLogger(__name__)


class DeepSeekProvider(BaseBrowserProvider):
    """Browser provider for DeepSeek (chat.deepseek.com)."""

    SITE_URL = "https://chat.deepseek.com"

    selectors = PlatformSelectors(
        textarea="textarea",
        answer_selectors=(
            '[class*="message"]',
            '[class*="response"]',
            '[class*="answer"]',
            'div[role="article"]',
        ),
        exclude_domains=("chat.deepseek.com", "localhost"),
    )

    @property
    def provider_name(self) -> str:
        return "deepseek"

    async def check_login_status(self) -> bool:
        """Check login with retry and ERR_ABORTED handling."""
        for attempt in range(2):
            try:
                current_url = self._page.url or ""
                if "deepseek.com" not in current_url:
                    await self._page.goto(self.SITE_URL, wait_until="domcontentloaded", timeout=30000)
                else:
                    try:
                        await self._page.goto(self.SITE_URL, wait_until="domcontentloaded", timeout=30000)
                    except Exception:
                        await asyncio.sleep(3)

                await asyncio.sleep(3)

                # If redirected to login/sign_in page, not logged in
                page_url = self._page.url or ""
                if "/sign_in" in page_url or "/login" in page_url or "/sign-in" in page_url:
                    return False

                # Check for textarea = chat ready = logged in
                textarea = await self._page.query_selector(self.selectors.textarea)
                if textarea:
                    return True

                if attempt == 0:
                    logger.info("DeepSeek: no textarea found, retrying...")
                    await asyncio.sleep(3)
                    continue
                return False
            except Exception as e:
                logger.warning(f"DeepSeek login check attempt {attempt+1} failed: {e}")
                if attempt == 0:
                    await asyncio.sleep(2)
                    continue
                return False
        return False

    async def navigate_to_chat(self):
        if "deepseek.com" not in (self._page.url or ""):
            await self._page.goto(self.SITE_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

    async def navigate_to_new_chat(self):
        """Open a fresh new chat on DeepSeek.

        Tries clicking the "New Chat" button first; falls back to navigating
        to the homepage.
        """
        clicked = await self._page.evaluate("""
            () => {
                const keywords = ['New Chat', '新对话', '新建对话'];
                for (const el of document.querySelectorAll('button, a, div, span')) {
                    const t = (el.textContent || '').trim();
                    for (const kw of keywords) {
                        if (t === kw || t.includes(kw)) {
                            el.click();
                            return true;
                        }
                    }
                }
                return false;
            }
        """)
        if clicked:
            logger.info("DeepSeek: clicked new chat button")
            await asyncio.sleep(2)
            return

        await self._page.goto(self.SITE_URL, wait_until="domcontentloaded", timeout=30000)
        logger.info("DeepSeek: navigated to homepage for new chat")
        await asyncio.sleep(2)

    async def submit_question(self, question: str):
        textarea = await self._page.query_selector(self.selectors.textarea)
        if not textarea:
            raise RuntimeError("DeepSeek: textarea not found, session may be expired")

        # Use keyboard.type for React controlled components
        await textarea.click()
        await textarea.fill("")
        await self._page.keyboard.type(question, delay=20)
        await asyncio.sleep(1)
        await self._find_and_click_send()

    # ─── Login automation ──────────────────────────────────────────

    async def navigate_to_login(self):
        """Navigate to DeepSeek login page.

        DeepSeek auto-redirects to /sign_in when not logged in.
        """
        await self._page.goto(
            f"{self.SITE_URL}/sign_in",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await asyncio.sleep(3)
        logger.info(f"DeepSeek: on login page, url={self._page.url}")

    async def fill_phone_number(self, phone: str):
        """Fill phone number into DeepSeek login form.

        DeepSeek has: <input type="tel" placeholder="请输入手机号">
        The +86 prefix is a separate UI element, only enter digits.
        Uses keyboard.type() to trigger React onChange events.
        """
        # Strip country code if present
        phone_digits = phone.lstrip("+").lstrip("86") if phone.startswith("+86") else phone
        if phone.startswith("1") and len(phone) == 11:
            phone_digits = phone  # Already bare number

        # Find the phone input (first type="tel" input)
        phone_input = await self._page.query_selector('input[type="tel"][placeholder*="手机"]')
        if not phone_input:
            phone_input = await self._page.query_selector('input[type="tel"]')
        if not phone_input:
            raise RuntimeError("DeepSeek: 未找到手机号输入框")

        await phone_input.click()
        await asyncio.sleep(0.3)
        # Clear existing content
        await self._page.keyboard.press("Control+a")
        await self._page.keyboard.press("Backspace")
        # Type with delay to trigger React onChange
        await self._page.keyboard.type(phone_digits, delay=50)
        await asyncio.sleep(0.5)
        logger.info(f"DeepSeek: phone number filled ({phone_digits[:3]}****)")

    async def click_send_code(self):
        """Click the '发送验证码' button.

        Uses Playwright native click for proper React event handling.
        Button selector: class contains 'ds-verify-code' or text '发送验证码'.
        """
        # Try by class (most reliable)
        send_btn = await self._page.query_selector('button.ds-verify-code-input-countdown')
        if not send_btn:
            send_btn = await self._page.query_selector('button.ds-link-button')

        if not send_btn:
            # Fallback: find by text content
            buttons = await self._page.query_selector_all('button')
            for btn in buttons:
                text = await btn.text_content() or ""
                if "验证码" in text and "发送" in text:
                    send_btn = btn
                    break

        if not send_btn:
            raise RuntimeError("DeepSeek: 未找到发送验证码按钮")

        await send_btn.click()
        logger.info("DeepSeek: clicked '发送验证码' button")
        await asyncio.sleep(2)

    # ─── CAPTCHA detection ────────────────────────────────────────

    CAPTCHA_SELECTORS = [
        # Specific captcha services
        'div[class*="captcha"]',
        'div[class*="Captcha"]',
        'div[class*="CAPTCHA"]',
        'div[class*="geetest"]',
        'div[class*="verify"]',
        'iframe[src*="captcha"]',
        # Generic popup/modal/dialog patterns (CAPTCHA often renders as overlay)
        'div[class*="modal"]',
        'div[class*="Modal"]',
        'div[class*="popup"]',
        'div[class*="Popup"]',
        'div[class*="dialog"]',
        'div[role="dialog"]',
        'div[class*="overlay"]',
    ]

    async def find_captcha_element(self):
        """Try to locate the CAPTCHA popup element.

        Checks both specific CAPTCHA selectors and generic modal selectors.
        For generic selectors, validates the element actually contains CAPTCHA
        content (images with instruction text) to avoid false positives.
        """
        # First pass: specific captcha selectors (high confidence)
        specific_selectors = self.CAPTCHA_SELECTORS[:6]
        for selector in specific_selectors:
            el = await self._page.query_selector(selector)
            if el and await el.is_visible():
                logger.info(f"DeepSeek: CAPTCHA found via specific selector: {selector}")
                return el

        # Second pass: generic modal selectors with content validation
        generic_selectors = self.CAPTCHA_SELECTORS[6:]
        for selector in generic_selectors:
            els = await self._page.query_selector_all(selector)
            for el in els:
                if not await el.is_visible():
                    continue
                # Validate: must contain an image and short instruction text
                has_captcha_content = await el.evaluate("""el => {
                    const hasImg = !!el.querySelector('img, canvas');
                    const texts = [];
                    el.querySelectorAll('span, p, div, label').forEach(t => {
                        const s = (t.textContent || '').trim().toLowerCase();
                        if (s.length > 3 && s.length < 200) texts.push(s);
                    });
                    const captchaKeywords = ['click', 'drag', 'slide', 'rotate', 'select',
                        '点击', '拖', '滑', '旋转', '选择', 'pyramid', 'triangle',
                        'smallest', 'largest', 'verify', '验证'];
                    const hasKeyword = texts.some(t =>
                        captchaKeywords.some(kw => t.includes(kw))
                    );
                    return hasImg && hasKeyword;
                }""")
                if has_captcha_content:
                    logger.info(f"DeepSeek: CAPTCHA found via generic selector: {selector}")
                    return el

        return None

    async def wait_for_captcha(self, timeout: float = 8.0, interval: float = 0.5):
        """Wait for CAPTCHA popup to appear, with polling.

        Returns the CAPTCHA element if found within timeout, else None.
        """
        elapsed = 0.0
        while elapsed < timeout:
            el = await self.find_captcha_element()
            if el:
                return el
            await asyncio.sleep(interval)
            elapsed += interval
        return None

    async def is_countdown_active(self) -> bool:
        """Check if the send-code button has turned into a countdown."""
        btn = await self._page.query_selector('button.ds-verify-code-input-countdown')
        if btn:
            text = await btn.text_content() or ""
            if any(c.isdigit() for c in text) and ("s" in text.lower() or "秒" in text):
                return True
        return False

    async def detect_and_solve_captcha(self, session_id: str | None = None) -> bool:
        """Detect and solve CAPTCHA using the unified captcha module.

        Returns True if no CAPTCHA or solved, False if failed.
        """
        from app.services.captcha import solve_captcha
        from app.core.config import settings

        await asyncio.sleep(3)

        if await self.is_countdown_active():
            logger.info("DeepSeek: countdown active, no CAPTCHA needed")
            return True

        captcha_el = await self.find_captcha_element()
        if not captcha_el:
            logger.info("DeepSeek: no CAPTCHA popup detected")
            return True

        logger.info("DeepSeek: CAPTCHA popup detected, delegating to captcha module")
        return await solve_captcha(
            self._page,
            captcha_el,
            session_id=session_id,
            max_retries=settings.CAPTCHA_MAX_AUTO_RETRIES,
        )

    async def fill_verification_code(self, code: str):
        """Fill verification code and submit login.

        DeepSeek has: <input type="tel" placeholder="请输入验证码">
        After filling, click the '登录' submit button.
        """
        # Find code input by placeholder (second tel input, with 验证码)
        code_input = await self._page.query_selector('input[type="tel"][placeholder*="验证码"]')
        if not code_input:
            code_input = await self._page.query_selector('input[placeholder*="验证码"]')
        if not code_input:
            # Fallback: second type="tel" input on the page
            tel_inputs = await self._page.query_selector_all('input[type="tel"]')
            if len(tel_inputs) >= 2:
                code_input = tel_inputs[1]

        if not code_input:
            raise RuntimeError("DeepSeek: 未找到验证码输入框")

        await code_input.click()
        await asyncio.sleep(0.3)
        await self._page.keyboard.press("Control+a")
        await self._page.keyboard.press("Backspace")
        await self._page.keyboard.type(code, delay=50)
        await asyncio.sleep(0.5)
        logger.info("DeepSeek: verification code filled")

        # Click 登录 button (type="submit", primary style)
        login_btn = await self._page.query_selector('button[type="submit"].ds-basic-button--primary')
        if not login_btn:
            login_btn = await self._page.query_selector('button[type="submit"]')
        if not login_btn:
            # Fallback: find by text
            buttons = await self._page.query_selector_all('button')
            for btn in buttons:
                text = (await btn.text_content() or "").strip()
                if text == "登录":
                    login_btn = btn
                    break

        if login_btn:
            await login_btn.click()
            logger.info("DeepSeek: clicked '登录' button")
        else:
            # Last resort: press Enter
            await code_input.press("Enter")
            logger.info("DeepSeek: pressed Enter to submit")

        await asyncio.sleep(3)

    async def verify_login_success(self) -> bool:
        """Wait for redirect after code submission, then verify login."""
        for i in range(15):
            await asyncio.sleep(1)
            url = self._page.url or ""
            # Successfully logged in = no longer on sign_in page
            if "deepseek.com" in url and "/sign_in" not in url and "/login" not in url:
                textarea = await self._page.query_selector(self.selectors.textarea)
                if textarea:
                    logger.info(f"DeepSeek: login verified via textarea (url={url})")
                    return True
                if i < 10:
                    continue

        logger.warning(f"DeepSeek: login verification failed, final url={self._page.url}")
        return False

    # ─── Chat flow methods ─────────────────────────────────────────

    async def _extract_latest_answer(self) -> str:
        """DeepSeek-specific: multi-selector answer extraction."""
        for selector in (
            '[class*="message"]',
            '[class*="response"]',
            '[class*="answer"]',
            'div[role="article"]',
        ):
            try:
                messages = await self._page.query_selector_all(selector)
                if messages:
                    answer = await messages[-1].inner_text()
                    if answer and len(answer) > 10:
                        return answer
            except Exception:
                continue
        return ""

    async def extract_web_sources(self) -> list[dict]:
        """Click 'X个网页' button, scroll right panel, extract all links."""
        try:
            # Step 1: Click the 'X个网页' button
            clicked = await self._page.evaluate("""
                () => {
                    const allElements = document.querySelectorAll('*');
                    for (const el of allElements) {
                        const own = (el.childNodes.length === 1 && el.childNodes[0].nodeType === 3)
                            ? el.textContent.trim()
                            : (el.children.length === 0 ? el.textContent.trim() : '');
                        if (/\\d+\\s*个\\s*网页/.test(own) || /\\d+\\s*web\\s*page/i.test(own)) {
                            el.click();
                            return { clicked: true, text: own };
                        }
                    }
                    // Broader fallback
                    for (const el of allElements) {
                        const text = el.textContent || '';
                        if (text.length < 60 && (text.includes('个网页') || text.includes('已阅读'))) {
                            const tag = el.tagName;
                            if (tag === 'A' || tag === 'BUTTON' || el.getAttribute('role') === 'button'
                                || el.onclick || getComputedStyle(el).cursor === 'pointer') {
                                el.click();
                                return { clicked: true, text: text.trim() };
                            }
                        }
                    }
                    return { clicked: false };
                }
            """)

            if not clicked.get('clicked'):
                logger.debug("DeepSeek: no 'X个网页' button found")
                return []

            logger.info(f"DeepSeek: clicked web sources button: {clicked.get('text', '')}")
            await asyncio.sleep(3)

            # Step 2+3: Scroll panel and collect links (handles virtual lists)
            collected = await self._page.evaluate("""
                async () => {
                    function findScrollContainer() {
                        const allEls = document.querySelectorAll('*');
                        // Strategy 1: find scrollable ancestor of '搜索结果' title
                        for (const el of allEls) {
                            const text = el.textContent ? el.textContent.trim() : '';
                            if ((text === '搜索结果' || text === 'Search Results') && el.children.length === 0) {
                                let parent = el.parentElement;
                                while (parent && parent !== document.body) {
                                    const style = getComputedStyle(parent);
                                    const overflow = style.overflow + style.overflowY;
                                    if ((overflow.includes('scroll') || overflow.includes('auto'))
                                        && parent.scrollHeight > parent.clientHeight) {
                                        return parent;
                                    }
                                    parent = parent.parentElement;
                                }
                            }
                        }
                        // Strategy 2: right-side scrollable container
                        for (const el of allEls) {
                            const rect = el.getBoundingClientRect();
                            if (rect.left > window.innerWidth * 0.5 && rect.height > 200) {
                                const style = getComputedStyle(el);
                                const overflow = style.overflow + style.overflowY;
                                if ((overflow.includes('scroll') || overflow.includes('auto'))
                                    && el.scrollHeight > el.clientHeight) {
                                    return el;
                                }
                            }
                        }
                        return null;
                    }

                    function collectLinks() {
                        const results = [];
                        for (const a of document.querySelectorAll('a[href]')) {
                            const href = a.href;
                            if (!href || !href.startsWith('http')) continue;
                            if (href.includes('chat.deepseek.com')) continue;
                            if (href.includes('javascript:')) continue;
                            const rect = a.getBoundingClientRect();
                            const text = (a.textContent || a.innerText || '').trim();
                            if (rect.left > window.innerWidth * 0.45) {
                                results.push({ url: href, text });
                            }
                        }
                        return results;
                    }

                    const seen = new Set();
                    const allLinks = [];

                    function mergeLinks(links) {
                        for (const l of links) {
                            if (!seen.has(l.url)) {
                                seen.add(l.url);
                                allLinks.push(l);
                            }
                        }
                    }

                    const container = findScrollContainer();

                    if (!container) {
                        mergeLinks(collectLinks());
                        return { found: false, scrolls: 0, links: allLinks };
                    }

                    // Collect top visible links first
                    mergeLinks(collectLinks());

                    // Scroll down step by step
                    let scrollCount = 0;
                    const maxScrolls = 30;
                    while (scrollCount < maxScrolls) {
                        const before = container.scrollTop;
                        container.scrollTop += 200;
                        await new Promise(r => setTimeout(r, 800));
                        mergeLinks(collectLinks());
                        if (container.scrollTop === before) break;
                        scrollCount++;
                    }

                    // Scroll back to top and collect once more
                    container.scrollTop = 0;
                    await new Promise(r => setTimeout(r, 500));
                    mergeLinks(collectLinks());

                    return { found: true, scrolls: scrollCount, links: allLinks };
                }
            """)

            urls = collected.get('links', [])
            scrolls = collected.get('scrolls', 0)
            logger.info(f"DeepSeek: scrolled {scrolls}x, collected {len(urls)} links")

            # Step 4: Close the search panel
            await self._close_search_panel()

            return self._deduplicate_urls(urls)

        except Exception as e:
            logger.warning(f"DeepSeek extract_web_sources failed: {e}")
            return []

    async def _close_search_panel(self):
        """Close the right-side search results panel."""
        closed = await self._page.evaluate("""
            () => {
                // Strategy 1: find close button near '搜索结果' title
                const allEls = document.querySelectorAll('*');
                for (const el of allEls) {
                    const text = el.textContent ? el.textContent.trim() : '';
                    if ((text === '搜索结果' || text === 'Search Results') && el.children.length === 0) {
                        let parent = el.parentElement;
                        for (let i = 0; i < 5; i++) {
                            if (!parent) break;
                            const btns = parent.querySelectorAll('button, [role="button"], [aria-label*="close"], [aria-label*="关闭"]');
                            for (const btn of btns) {
                                const btnText = btn.textContent.trim();
                                if (btnText === '×' || btnText === '✕' || btnText === 'X' || btnText === ''
                                    || btn.getAttribute('aria-label') === 'close'
                                    || btn.getAttribute('aria-label') === '关闭') {
                                    btn.click();
                                    return true;
                                }
                            }
                            parent = parent.parentElement;
                        }
                    }
                }
                // Strategy 2: right-side close/× button
                for (const el of allEls) {
                    const rect = el.getBoundingClientRect();
                    if (rect.left < window.innerWidth * 0.5) continue;
                    const tag = el.tagName;
                    const text = el.textContent.trim();
                    const label = el.getAttribute('aria-label') || '';
                    if ((tag === 'BUTTON' || el.getAttribute('role') === 'button')
                        && (text === '×' || text === '✕' || label.includes('close') || label.includes('关闭'))) {
                        el.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        if closed:
            await asyncio.sleep(1)
            logger.debug("DeepSeek: search panel closed")
