"""
Base class for all CAPTCHA solvers.
"""
import asyncio
import base64
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseCaptchaSolver(ABC):
    """Abstract base for CAPTCHA solvers."""

    @abstractmethod
    async def solve(self, page, captcha_element, context: dict) -> bool:
        """Attempt to solve the CAPTCHA once.

        Args:
            page: Playwright page.
            captcha_element: The CAPTCHA container element.
            context: Dict with instruction, session_id, etc.

        Returns:
            True if solved, False if failed.
        """

    async def solve_with_retry(
        self,
        page,
        captcha_element,
        context: dict,
        max_retries: int = 3,
    ) -> bool:
        """Solve with retries and optional refresh between attempts."""
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"CAPTCHA solve attempt {attempt}/{max_retries}")
                success = await self.solve(page, captcha_element, context)

                if success:
                    # Verify CAPTCHA actually disappeared
                    await asyncio.sleep(2)
                    still_visible = await self._is_still_visible(captcha_element)
                    if not still_visible:
                        logger.info(f"CAPTCHA solved on attempt {attempt}")
                        return True
                    logger.info("CAPTCHA still visible after solve, retrying")

            except Exception as e:
                logger.warning(f"CAPTCHA solve attempt {attempt} error: {e}")

            # Try to refresh the CAPTCHA before next attempt
            if attempt < max_retries:
                await self._try_refresh(captcha_element)
                await asyncio.sleep(1)

        return False

    async def _is_still_visible(self, captcha_element) -> bool:
        """Check if the CAPTCHA element is still visible."""
        try:
            return await captcha_element.is_visible()
        except Exception:
            return False  # Element gone = solved

    async def _try_refresh(self, captcha_element):
        """Try to click a refresh button within the CAPTCHA."""
        try:
            refresh_btn = await captcha_element.query_selector(
                'button[class*="refresh"], button[class*="reload"], '
                'a[class*="refresh"], span[class*="refresh"], '
                '[class*="icon-refresh"], [class*="retry"]'
            )
            if refresh_btn and await refresh_btn.is_visible():
                await refresh_btn.click()
                logger.info("Clicked CAPTCHA refresh button")
                await asyncio.sleep(2)
        except Exception:
            pass

    @staticmethod
    async def _screenshot_element(element) -> str:
        """Take a PNG screenshot of an element, return base64."""
        screenshot_bytes = await element.screenshot(type="png")
        return base64.b64encode(screenshot_bytes).decode()

    @staticmethod
    async def _get_bbox(element) -> dict | None:
        """Get bounding box of element."""
        try:
            return await element.bounding_box()
        except Exception:
            return None
