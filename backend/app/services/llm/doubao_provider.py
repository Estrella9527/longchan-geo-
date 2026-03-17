"""
Doubao (豆包) browser-based LLM provider.

Platform-specific hooks for doubao.com Web UI.
Common logic (wait_for_answer, _extract_latest_answer, _crawl_url)
is inherited from BaseBrowserProvider.
"""
import asyncio
import logging

from app.services.llm.browser_base import BaseBrowserProvider, PlatformSelectors

logger = logging.getLogger(__name__)


class DoubaoProvider(BaseBrowserProvider):
    """Browser provider for 豆包 (doubao.com)."""

    SITE_URL = "https://www.doubao.com/"

    selectors = PlatformSelectors(
        textarea="textarea",
        answer_selectors=(
            '[class*="message"]',
            '[class*="response"]',
            '[class*="answer"]',
            '[class*="chat"]',
            'div[role="article"]',
        ),
        exclude_domains=("doubao.com", "localhost"),
    )

    @property
    def provider_name(self) -> str:
        return "doubao"

    async def check_login_status(self) -> bool:
        """Check login status — doubao shows a '登录' button when not logged in.

        IMPORTANT: doubao.com shows a textarea even when NOT logged in (for trial),
        so we MUST check for the absence of the login button, not just textarea presence.
        """
        for attempt in range(2):
            try:
                try:
                    await self._page.goto(self.SITE_URL, wait_until="domcontentloaded", timeout=30000)
                except Exception:
                    await asyncio.sleep(3)

                await asyncio.sleep(3)

                # Check 1: URL-based detection
                page_url = self._page.url or ""
                if "login" in page_url or "passport" in page_url:
                    logger.info(f"Doubao: login page detected (url={page_url})")
                    return False

                # Check 2: login button presence — this is the PRIMARY check
                has_login_btn = await self._page.evaluate("""
                    () => {
                        for (const el of document.querySelectorAll('button, a')) {
                            const t = (el.textContent || '').trim();
                            if (t === '登录' || t === '登录/注册') return true;
                        }
                        return false;
                    }
                """)

                if has_login_btn:
                    if attempt == 0:
                        logger.info("Doubao: login button found, retrying after wait...")
                        await asyncio.sleep(3)
                        continue
                    logger.info("Doubao: NOT logged in (login button present)")
                    return False

                # No login button = logged in
                logger.info(f"Doubao: logged in (no login button, url={page_url})")
                return True

            except Exception as e:
                logger.warning(f"Doubao login check attempt {attempt+1} failed: {e}")
                if attempt == 0:
                    await asyncio.sleep(2)
                    continue
                return False
        return False

    async def navigate_to_chat(self):
        """Navigate to doubao home (which is the chat page)."""
        if "doubao.com" not in (self._page.url or ""):
            await self._page.goto(self.SITE_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

    async def navigate_to_new_chat(self):
        """Open a fresh new chat on doubao.com.

        Tries clicking the "新对话" button first; falls back to navigating
        to the homepage (which is always a new chat on doubao).
        """
        # Strategy 1: click "新对话" / "新建对话" button if available
        clicked = await self._page.evaluate("""
            () => {
                const keywords = ['新对话', '新建对话', '新建', 'New Chat'];
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
            logger.info("Doubao: clicked new chat button")
            await asyncio.sleep(2)
            return

        # Strategy 2: navigate to homepage (doubao homepage = new chat)
        await self._page.goto(self.SITE_URL, wait_until="domcontentloaded", timeout=30000)
        logger.info("Doubao: navigated to homepage for new chat")
        await asyncio.sleep(2)

    async def submit_question(self, question: str):
        """Type question into textarea and send via click+fill + send button."""
        # Close any lingering reference panel first
        await self._close_reference_panel()

        textarea = await self._page.query_selector(self.selectors.textarea)
        if not textarea:
            raise RuntimeError("Doubao: textarea not found, session may be expired")

        await textarea.click()
        await asyncio.sleep(0.5)
        await textarea.fill(question)
        await asyncio.sleep(1)

        # Try to find and click a send button first; fall back to Enter
        send_clicked = False
        for btn in await self._page.query_selector_all("button"):
            try:
                text = await btn.inner_text()
                label = await btn.get_attribute("aria-label") or ""
                if "发送" in text or "Send" in text or "发送" in label:
                    await btn.click()
                    send_clicked = True
                    break
            except Exception:
                continue

        if not send_clicked:
            await self._page.keyboard.press("Enter")

        logger.info(f"Doubao: submitted question ({len(question)} chars, btn={send_clicked})")
        await asyncio.sleep(2)

    # ─── Login automation (for in-system auth flow) ──────────────────

    async def navigate_to_login(self):
        """Navigate to doubao.com and click the login button."""
        await self._page.goto(self.SITE_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        clicked = await self._page.evaluate("""
            () => {
                for (const el of document.querySelectorAll('button, a, div, span')) {
                    const t = (el.textContent || '').trim();
                    if (t === '登录' || t === '登錄' || t === 'Login' || t === '登录/注册') {
                        el.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        if not clicked:
            raise RuntimeError("Doubao: 未找到登录按钮")
        await asyncio.sleep(2)

    async def fill_phone_number(self, phone: str):
        """Fill phone number into the login dialog."""
        phone_input = await self._page.query_selector('input[placeholder*="手机"]')
        if not phone_input:
            phone_input = await self._page.query_selector('input[type="tel"]')
        if not phone_input:
            inputs = await self._page.query_selector_all('input')
            for inp in inputs:
                visible = await inp.is_visible()
                inp_type = await inp.get_attribute("type") or ""
                if visible and inp_type in ("text", "tel", ""):
                    phone_input = inp
                    break
        if not phone_input:
            raise RuntimeError("Doubao: 未找到手机号输入框")

        await phone_input.click()
        await phone_input.fill(phone)
        await asyncio.sleep(0.5)

    async def click_send_code(self):
        """Check the agreement checkbox and click '下一步' to send SMS code."""
        # Step 1: Check the agreement checkbox
        await self._page.evaluate("""
            () => {
                for (const el of document.querySelectorAll('.semi-checkbox, label, span')) {
                    const t = el.textContent || '';
                    if (t.includes('已阅读') || t.includes('同意')) {
                        el.click();
                        return 'clicked_wrapper';
                    }
                }
                const inner = document.querySelector('.semi-checkbox-inner-display');
                if (inner) { inner.click(); return 'clicked_inner'; }
                const cb = document.querySelector('input[type="checkbox"]');
                if (cb) {
                    cb.checked = true;
                    cb.dispatchEvent(new Event('change', {bubbles: true}));
                    return 'forced_check';
                }
                return 'not_found';
            }
        """)
        logger.info("Doubao: toggled agreement checkbox")
        await asyncio.sleep(0.5)

        # Step 2: Click "下一步" button
        clicked = await self._page.evaluate("""
            () => {
                const keywords = ['下一步', '获取验证码', '发送验证码', '发送'];
                for (const el of document.querySelectorAll('button')) {
                    const t = (el.textContent || '').trim();
                    for (const kw of keywords) {
                        if (t.includes(kw)) {
                            el.click();
                            return t;
                        }
                    }
                }
                return null;
            }
        """)
        if not clicked:
            raise RuntimeError("Doubao: 未找到「下一步」按钮")
        logger.info(f"Doubao: clicked '{clicked}'")
        await asyncio.sleep(2)

        # Handle agreement popup
        popup_handled = await self._page.evaluate("""
            () => {
                for (const btn of document.querySelectorAll('button')) {
                    const t = (btn.textContent || '').trim();
                    if (t === '去' || t === '同意' || t === '确认') {
                        btn.click();
                        return 'clicked_agree';
                    }
                }
                return 'no_popup';
            }
        """)
        if popup_handled != 'no_popup':
            logger.info(f"Doubao: handled agreement popup: {popup_handled}")
            await asyncio.sleep(1)
            await self._page.evaluate("""
                () => {
                    for (const el of document.querySelectorAll('.semi-checkbox, label, span')) {
                        const t = el.textContent || '';
                        if (t.includes('已阅读') || t.includes('同意')) {
                            el.click();
                            return;
                        }
                    }
                }
            """)
            await asyncio.sleep(0.5)
            await self._page.evaluate("""
                () => {
                    for (const btn of document.querySelectorAll('button')) {
                        const t = (btn.textContent || '').trim();
                        if (t.includes('下一步')) { btn.click(); return; }
                    }
                }
            """)
            await asyncio.sleep(3)
        else:
            await asyncio.sleep(1)

    async def fill_verification_code(self, code: str):
        """Fill the 6-digit OTP verification code on the second screen."""
        first_input = await self._page.evaluate("""
            () => {
                const inputs = document.querySelectorAll('input');
                for (const inp of inputs) {
                    if (inp.offsetParent !== null && inp.type !== 'checkbox' && inp.type !== 'file') {
                        inp.focus();
                        inp.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        if not first_input:
            raise RuntimeError("Doubao: 未找到验证码输入框")

        await asyncio.sleep(0.3)

        for digit in code:
            await self._page.keyboard.type(digit, delay=100)
            await asyncio.sleep(0.2)

        logger.info(f"Doubao: typed {len(code)} digits")
        await asyncio.sleep(5)

    async def verify_login_success(self) -> bool:
        """Check if login was successful after submitting code.

        Wait for page to redirect, then verify login button is gone.
        """
        for i in range(15):
            await asyncio.sleep(1)
            url = self._page.url or ""

            # Check if login button has disappeared
            has_login_btn = await self._page.evaluate("""
                () => {
                    for (const el of document.querySelectorAll('button, a')) {
                        const t = (el.textContent || '').trim();
                        if (t === '登录' || t === '登录/注册') return true;
                    }
                    return false;
                }
            """)

            if not has_login_btn and "doubao.com" in url:
                logger.info(f"Doubao: login verified (no login button, url={url})")
                return True

        logger.warning(f"Doubao: login verification failed, final url={self._page.url}")
        return False

    # ─── Chat flow methods ─────────────────────────────────────────

    async def wait_for_answer_v2(self, pre_text: str, timeout: int = 90) -> str:
        """Doubao-specific: detect completion via new '参考X篇资料' button appearing.

        Falls back to stop-button + text-stability from the base class.
        """
        await asyncio.sleep(3)

        # Count existing ref buttons before answer starts
        ref_count_before = await self._page.evaluate("""
            () => {
                const pattern = /参考\\s*\\d+\\s*篇资料/;
                let count = 0;
                for (const el of document.querySelectorAll('*')) {
                    const own = el.children.length === 0
                        ? (el.textContent || '').trim() : '';
                    if (own.length < 20 && pattern.test(own)) count++;
                }
                return count;
            }
        """)
        logger.debug(f"Doubao: {ref_count_before} ref buttons before answer")

        elapsed = 0
        check_interval = 2
        last_text = ""
        stable_count = 0
        stop_was_present = False

        while elapsed < timeout:
            status = await self._page.evaluate("""
                (refBefore) => {
                    // Check stop button
                    for (const el of document.querySelectorAll('button,svg,[class*="loading"],[class*="spin"]')) {
                        const t = (el.textContent || '').trim();
                        const l = el.getAttribute('aria-label') || '';
                        if (t.includes('停止') || t.includes('Stop') || t.includes('暂停')
                            || l.includes('停止') || l.includes('Stop')) {
                            return 'generating';
                        }
                    }
                    // Check new ref button
                    const pattern = /参考\\s*\\d+\\s*篇资料/;
                    let count = 0;
                    for (const el of document.querySelectorAll('*')) {
                        const own = el.children.length === 0
                            ? (el.textContent || '').trim() : '';
                        if (own.length < 20 && pattern.test(own)) count++;
                    }
                    if (count > refBefore) return 'done';
                    return 'waiting';
                }
            """, ref_count_before)

            if status == 'done':
                logger.info("Doubao: new ref button detected, answer complete")
                break
            if status == 'generating':
                stop_was_present = True

            # Fallback: text stability
            current_text = await self._get_page_text()
            diff = self._extract_diff(pre_text, current_text)

            if stop_was_present and status != 'generating' and len(diff) > 10:
                logger.info("Doubao: stop button gone, answer ready")
                break

            if current_text == last_text and len(diff) > 10:
                stable_count += 1
                if stable_count >= 3:
                    logger.info("Doubao: text stable, answer ready")
                    break
            else:
                stable_count = 0

            last_text = current_text
            await asyncio.sleep(check_interval)
            elapsed += check_interval

        if elapsed >= timeout:
            logger.warning(f"Doubao: wait_for_answer_v2 timeout ({timeout}s)")

        await asyncio.sleep(2)
        final_text = await self._get_page_text()
        return self._extract_diff(pre_text, final_text)

    async def _extract_latest_answer(self) -> str:
        """Doubao-specific 3-strategy answer extraction."""
        # Strategy 1: main content area by class name
        answer = await self._page.evaluate("""
            () => {
                function getMainContainer() {
                    const candidates = [
                        'main',
                        '[class*="main-content"]',
                        '[class*="chat-container"]',
                        '[class*="conversation"]',
                        '[class*="content-area"]',
                    ];
                    for (const sel of candidates) {
                        const el = document.querySelector(sel);
                        if (el) return el;
                    }
                    let best = null, bestArea = 0;
                    for (const el of document.querySelectorAll('div, section, article')) {
                        const r = el.getBoundingClientRect();
                        if (r.left < window.innerWidth * 0.25) continue;
                        const area = r.width * r.height;
                        if (area > bestArea) { bestArea = area; best = el; }
                    }
                    return best || document.body;
                }

                const main = getMainContainer();
                const selectors = [
                    '[class*="bot-reply"]',
                    '[class*="assistant"]',
                    '[class*="model-reply"]',
                    '[class*="receive"]',
                    '[class*="message-content"]',
                    '[class*="chat-message"]',
                    '[class*="message"]',
                ];
                let best = '';
                for (const sel of selectors) {
                    const els = main.querySelectorAll(sel);
                    if (!els.length) continue;
                    const text = (els[els.length - 1].innerText || '').trim();
                    if (text.length > best.length) best = text;
                }
                return best;
            }
        """)
        if answer and len(answer) > 10:
            return answer

        # Strategy 2: traverse up from last '参考X篇资料' button
        answer = await self._page.evaluate("""
            () => {
                const refPattern = /参考\\s*\\d+\\s*篇资料/;
                const matches = [];
                for (const el of document.querySelectorAll('*')) {
                    const own = el.children.length === 0
                        ? (el.textContent || '').trim() : '';
                    if (own.length < 20 && refPattern.test(own)) matches.push(el);
                }
                if (matches.length > 0) {
                    let node = matches[matches.length - 1].parentElement;
                    let best = '';
                    for (let i = 0; i < 10; i++) {
                        if (!node || node === document.body) break;
                        const t = (node.innerText || '').trim();
                        if (t.length > best.length) best = t;
                        node = node.parentElement;
                    }
                    if (best.length > 10) return best;
                }
                return '';
            }
        """)
        if answer and len(answer) > 10:
            return answer

        # Strategy 3: fallback — longest text block in right half of page
        answer = await self._page.evaluate("""
            () => {
                let best = '';
                for (const el of document.querySelectorAll('div, article, section, p')) {
                    const r = el.getBoundingClientRect();
                    if (r.left < window.innerWidth * 0.25) continue;
                    const text = (el.innerText || '').trim();
                    if (text.length > best.length && text.length > 50
                        && !el.closest('nav, aside, header, footer, textarea')) {
                        best = text;
                    }
                }
                return best;
            }
        """)
        return answer if answer and len(answer) > 10 else ""

    async def extract_web_sources(self) -> list[dict]:
        """Click '参考 X 篇资料' button, scroll panel, extract links."""
        try:
            # Step 1: Click the last '参考X篇资料' button
            clicked = await self._page.evaluate("""
                () => {
                    const pattern = /参考\\s*\\d+\\s*篇资料/;
                    const matches = [];
                    for (const el of document.querySelectorAll('*')) {
                        const own = el.children.length === 0
                            ? (el.textContent || '').trim()
                            : (el.childNodes.length === 1 && el.childNodes[0].nodeType === 3
                                ? el.textContent.trim() : '');
                        if (own.length < 20 && pattern.test(own)) {
                            matches.push({ el, text: own });
                        }
                    }
                    if (matches.length > 0) {
                        const last = matches[matches.length - 1];
                        last.el.click();
                        return { ok: true, text: last.text };
                    }
                    // Fallback: clickable elements containing '参考' + digit
                    const fallbacks = [];
                    for (const el of document.querySelectorAll('button,[role="button"],a,span,div')) {
                        const t = (el.textContent || '').trim();
                        if (t.length < 30 && t.includes('参考') && /\\d/.test(t)) {
                            fallbacks.push({ el, text: t });
                        }
                    }
                    if (fallbacks.length > 0) {
                        const last = fallbacks[fallbacks.length - 1];
                        last.el.click();
                        return { ok: true, text: last.text };
                    }
                    return { ok: false };
                }
            """)

            if not clicked.get('ok'):
                logger.debug("Doubao: no reference button found")
                return []

            logger.info(f"Doubao: clicked ref button: {clicked.get('text', '')}")
            await asyncio.sleep(2)

            # Step 2: Scroll the reference panel to load all links
            await self._page.evaluate("""
                async () => {
                    function findPanel() {
                        for (const el of document.querySelectorAll('*')) {
                            if (el.children.length === 0
                                && (el.textContent || '').trim() === '参考资料') {
                                let p = el.parentElement;
                                for (let i = 0; i < 8; i++) {
                                    if (!p) break;
                                    const s = getComputedStyle(p);
                                    if ((s.overflow + s.overflowY).match(/scroll|auto/)
                                        && p.scrollHeight > p.clientHeight) return p;
                                    p = p.parentElement;
                                }
                            }
                        }
                        for (const el of document.querySelectorAll('*')) {
                            const r = el.getBoundingClientRect();
                            if (r.left > window.innerWidth * 0.45 && r.height > 200) {
                                const s = getComputedStyle(el);
                                if ((s.overflow + s.overflowY).match(/scroll|auto/)
                                    && el.scrollHeight > el.clientHeight) return el;
                            }
                        }
                        return null;
                    }
                    const panel = findPanel();
                    if (!panel) return;
                    let count = 0;
                    while (count < 15) {
                        const before = panel.scrollTop;
                        panel.scrollTop += 200;
                        await new Promise(r => setTimeout(r, 600));
                        if (panel.scrollTop === before) break;
                        count++;
                    }
                }
            """)
            await asyncio.sleep(1)

            # Step 3: Collect links from the right-side panel
            exclude = list(self.selectors.exclude_domains)
            urls = await self._page.evaluate(f"""
                () => {{
                    const exclude = {exclude};
                    const seen = new Set();
                    const results = [];
                    for (const a of document.querySelectorAll('a[href]')) {{
                        const href = a.href;
                        if (!href.startsWith('http')) continue;
                        if (exclude.some(d => href.includes(d))) continue;
                        if (href.includes('volces.com')) continue;
                        if (seen.has(href)) continue;
                        const r = a.getBoundingClientRect();
                        if (r.left < window.innerWidth * 0.4) continue;
                        seen.add(href);
                        results.push({{ url: href, text: (a.textContent || '').trim() }});
                    }}
                    return results;
                }}
            """)

            logger.info(f"Doubao: extracted {len(urls)} reference links")

            # Step 4: Close the panel
            await self._close_reference_panel()

            return self._deduplicate_urls(urls)

        except Exception as e:
            logger.warning(f"Doubao extract_web_sources failed: {e}")
            return []

    async def _close_reference_panel(self):
        """Close the right-side reference panel if open."""
        closed = await self._page.evaluate("""
            () => {
                // Find close button near '参考资料' title
                for (const el of document.querySelectorAll('*')) {
                    if (el.children.length === 0
                        && (el.textContent || '').trim() === '参考资料') {
                        let p = el.parentElement;
                        for (let i = 0; i < 5; i++) {
                            if (!p) break;
                            for (const btn of p.querySelectorAll('button,[role="button"]')) {
                                const t = btn.textContent.trim();
                                const l = btn.getAttribute('aria-label') || '';
                                if (['×','✕','X',''].includes(t) || l.match(/close|关闭/i)) {
                                    btn.click(); return true;
                                }
                            }
                            p = p.parentElement;
                        }
                    }
                }
                // Fallback: right-side close button
                for (const btn of document.querySelectorAll('button,[role="button"]')) {
                    const r = btn.getBoundingClientRect();
                    if (r.left < window.innerWidth * 0.45) continue;
                    const t = btn.textContent.trim();
                    const l = btn.getAttribute('aria-label') || '';
                    if (['×','✕'].includes(t) || l.match(/close|关闭/i)) {
                        btn.click(); return true;
                    }
                }
                return false;
            }
        """)
        if closed:
            await asyncio.sleep(1)
            logger.debug("Doubao: reference panel closed")
