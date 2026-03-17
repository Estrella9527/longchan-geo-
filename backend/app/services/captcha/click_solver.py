"""
Click-target CAPTCHA solver.

Handles CAPTCHAs that require clicking on a specific object/shape,
e.g. "Click on the smallest green cone" or image selection tasks.
"""
import logging

from app.services.captcha.base_solver import BaseCaptchaSolver
from app.services.captcha.vision import vision_query
from app.services.captcha.executor import human_like_click

logger = logging.getLogger(__name__)


class ClickSolver(BaseCaptchaSolver):
    """Solver for click-target CAPTCHAs (3D shapes, image selection, etc.)."""

    async def solve(self, page, captcha_element, context: dict) -> bool:
        instruction = context.get("instruction", "")

        # If no instruction extracted yet, try to find one
        if not instruction:
            instruction = await self._extract_instruction(captcha_element)

        screenshot_b64 = await self._screenshot_element(captcha_element)

        prompt = (
            f"This CAPTCHA shows a challenge. The instruction is: \"{instruction}\"\n\n"
            "Identify the target and return the pixel coordinates of its CENTER "
            "relative to the image top-left corner.\n\n"
            "Return JSON: {\"x\": <int>, \"y\": <int>, \"confidence\": <float 0-1>, "
            "\"reasoning\": \"<brief>\"}"
        )

        try:
            result = vision_query(screenshot_b64, prompt)
        except RuntimeError as e:
            logger.warning(f"ClickSolver vision query failed: {e}")
            return False

        if "x" not in result or "y" not in result:
            logger.warning(f"ClickSolver: missing coordinates in response: {result}")
            return False

        rel_x, rel_y = int(result["x"]), int(result["y"])
        confidence = float(result.get("confidence", 0.5))
        logger.info(
            f"ClickSolver: target at ({rel_x},{rel_y}) "
            f"confidence={confidence:.2f} reason={result.get('reasoning', '')}"
        )

        # Convert to absolute page coordinates
        bbox = await self._get_bbox(captcha_element)
        if not bbox:
            logger.warning("ClickSolver: cannot get bounding box")
            return False

        abs_x = bbox["x"] + rel_x
        abs_y = bbox["y"] + rel_y

        await human_like_click(page, abs_x, abs_y)
        return True  # Caller (solve_with_retry) will verify if CAPTCHA disappeared

    async def _extract_instruction(self, captcha_element) -> str:
        """Try to extract instruction text from the CAPTCHA element."""
        try:
            return await captcha_element.evaluate("""el => {
                const textEls = el.querySelectorAll('span, p, div, label, h3, h4');
                for (const t of textEls) {
                    const text = (t.textContent || '').trim();
                    if (text.length > 5 && text.length < 200) {
                        const lc = text.toLowerCase();
                        if (lc.includes('click') || lc.includes('点击') ||
                            lc.includes('select') || lc.includes('选择') ||
                            lc.includes('tap') || lc.includes('请')) {
                            return text;
                        }
                    }
                }
                return (el.textContent || '').trim().substring(0, 200);
            }""")
        except Exception:
            return "Click on the correct target in this CAPTCHA image."
