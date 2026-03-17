"""
Slider/puzzle CAPTCHA solver.

Handles CAPTCHAs that require dragging a slider to fill a gap,
e.g. GeeTest slider, Alibaba Cloud Shield (阿里云盾).

Approach:
1. Screenshot the puzzle area
2. Vision model identifies the gap X position
3. Calculate drag distance from slider start to gap
4. Execute human-like drag with easing and wobble
"""
import logging

from app.services.captcha.base_solver import BaseCaptchaSolver
from app.services.captcha.vision import vision_query
from app.services.captcha.executor import human_like_drag

logger = logging.getLogger(__name__)


class SliderSolver(BaseCaptchaSolver):
    """Solver for slider/puzzle drag CAPTCHAs."""

    async def solve(self, page, captcha_element, context: dict) -> bool:
        screenshot_b64 = await self._screenshot_element(captcha_element)

        prompt = (
            "This image shows a slider CAPTCHA puzzle. There is a puzzle piece "
            "that needs to be dragged into a gap/hole in the background image.\n\n"
            "Identify:\n"
            "1. The current position (left edge) of the slider handle/button at the bottom\n"
            "2. The X position of the gap/hole where the puzzle piece should fit\n"
            "3. The Y position of the slider handle center\n\n"
            "Return JSON: {\n"
            '  "slider_x": <int, current slider handle center X>,\n'
            '  "slider_y": <int, slider handle center Y>,\n'
            '  "gap_x": <int, gap center X position>,\n'
            '  "confidence": <float 0-1>,\n'
            '  "reasoning": "<brief>"\n'
            "}\n"
            "All coordinates relative to image top-left."
        )

        try:
            result = vision_query(screenshot_b64, prompt)
        except RuntimeError as e:
            logger.warning(f"SliderSolver vision query failed: {e}")
            return False

        slider_x = result.get("slider_x")
        slider_y = result.get("slider_y")
        gap_x = result.get("gap_x")

        if slider_x is None or gap_x is None:
            logger.warning(f"SliderSolver: missing coordinates: {result}")
            return False

        slider_x = int(slider_x)
        gap_x = int(gap_x)

        # If slider_y not provided, try to find the slider handle
        if slider_y is None:
            slider_y = await self._find_slider_y(captcha_element)
            if slider_y is None:
                logger.warning("SliderSolver: cannot determine slider Y position")
                return False
        else:
            slider_y = int(slider_y)

        logger.info(
            f"SliderSolver: slider at x={slider_x}, gap at x={gap_x}, "
            f"drag distance={gap_x - slider_x}px"
        )

        # Convert to absolute page coordinates
        bbox = await self._get_bbox(captcha_element)
        if not bbox:
            return False

        abs_start_x = bbox["x"] + slider_x
        abs_start_y = bbox["y"] + slider_y
        abs_end_x = bbox["x"] + gap_x
        abs_end_y = abs_start_y  # Horizontal drag only

        await human_like_drag(page, abs_start_x, abs_start_y, abs_end_x, abs_end_y)
        return True

    async def _find_slider_y(self, captcha_element) -> int | None:
        """Try to locate the slider handle via DOM and get its Y center."""
        try:
            handle = await captcha_element.query_selector(
                '[class*="slider"], [class*="slide-btn"], [class*="handler"], '
                '[class*="drag"], [class*="geetest_btn"], [class*="btn"]'
            )
            if handle:
                handle_bbox = await handle.bounding_box()
                captcha_bbox = await captcha_element.bounding_box()
                if handle_bbox and captcha_bbox:
                    # Return Y relative to captcha element
                    return int(
                        handle_bbox["y"] + handle_bbox["height"] / 2 - captcha_bbox["y"]
                    )
        except Exception as e:
            logger.warning(f"SliderSolver: failed to find slider handle: {e}")
        return None
