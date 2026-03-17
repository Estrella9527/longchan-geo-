"""
Rotation CAPTCHA solver.

Handles CAPTCHAs that require dragging a slider to rotate an image
to the correct orientation (e.g. Baidu rotation CAPTCHA).

Approach:
1. Screenshot → vision model estimates rotation angle needed
2. Map angle → slider drag distance (linear proportion of slider track width)
3. Execute human-like drag
"""
import logging

from app.services.captcha.base_solver import BaseCaptchaSolver
from app.services.captcha.vision import vision_query
from app.services.captcha.executor import human_like_drag

logger = logging.getLogger(__name__)


class RotateSolver(BaseCaptchaSolver):
    """Solver for rotation/alignment CAPTCHAs."""

    async def solve(self, page, captcha_element, context: dict) -> bool:
        screenshot_b64 = await self._screenshot_element(captcha_element)

        prompt = (
            "This image shows a rotation CAPTCHA. There is an image that needs to "
            "be rotated to the correct upright orientation, controlled by a slider.\n\n"
            "Estimate:\n"
            "1. How many degrees clockwise the image needs to be rotated to be upright\n"
            "2. The slider handle current position (center X, Y)\n"
            "3. The total width of the slider track\n\n"
            "Return JSON: {\n"
            '  "angle_degrees": <float, clockwise degrees needed>,\n'
            '  "slider_x": <int, slider handle center X>,\n'
            '  "slider_y": <int, slider handle center Y>,\n'
            '  "track_width": <int, total slider track width in pixels>,\n'
            '  "confidence": <float 0-1>,\n'
            '  "reasoning": "<brief>"\n'
            "}\n"
            "All coordinates relative to image top-left."
        )

        try:
            result = vision_query(screenshot_b64, prompt)
        except RuntimeError as e:
            logger.warning(f"RotateSolver vision query failed: {e}")
            return False

        angle = result.get("angle_degrees")
        slider_x = result.get("slider_x")
        slider_y = result.get("slider_y")
        track_width = result.get("track_width")

        if angle is None or slider_x is None or track_width is None:
            logger.warning(f"RotateSolver: missing required fields: {result}")
            return False

        angle = float(angle)
        slider_x = int(slider_x)
        slider_y = int(slider_y) if slider_y else await self._find_slider_y(captcha_element)
        track_width = int(track_width)

        if slider_y is None:
            return False

        # Map angle to horizontal pixel distance
        # Full track width = 360 degrees of rotation
        drag_distance = int((angle / 360.0) * track_width)

        logger.info(
            f"RotateSolver: angle={angle:.1f}°, drag={drag_distance}px, "
            f"track_width={track_width}px"
        )

        bbox = await self._get_bbox(captcha_element)
        if not bbox:
            return False

        abs_start_x = bbox["x"] + slider_x
        abs_start_y = bbox["y"] + slider_y
        abs_end_x = abs_start_x + drag_distance
        abs_end_y = abs_start_y

        await human_like_drag(page, abs_start_x, abs_start_y, abs_end_x, abs_end_y)
        return True

    async def _find_slider_y(self, captcha_element) -> int | None:
        """Locate slider handle Y position via DOM."""
        try:
            handle = await captcha_element.query_selector(
                '[class*="slider"], [class*="handle"], [class*="drag"], [class*="btn"]'
            )
            if handle:
                handle_bbox = await handle.bounding_box()
                captcha_bbox = await captcha_element.bounding_box()
                if handle_bbox and captcha_bbox:
                    return int(
                        handle_bbox["y"] + handle_bbox["height"] / 2 - captcha_bbox["y"]
                    )
        except Exception:
            pass
        return None
