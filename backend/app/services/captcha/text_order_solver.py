"""
Text/character order CAPTCHA solver.

Handles CAPTCHAs that require clicking characters in a specific order,
e.g. "按顺序点击: 天 地 人" or "Click in order: A B C".
"""
import logging

from app.services.captcha.base_solver import BaseCaptchaSolver
from app.services.captcha.vision import vision_query
from app.services.captcha.executor import click_sequence

logger = logging.getLogger(__name__)


class TextOrderSolver(BaseCaptchaSolver):
    """Solver for sequential text/character click CAPTCHAs."""

    async def solve(self, page, captcha_element, context: dict) -> bool:
        instruction = context.get("instruction", "")
        screenshot_b64 = await self._screenshot_element(captcha_element)

        prompt = (
            "This CAPTCHA requires clicking characters/words in a specific order.\n"
        )
        if instruction:
            prompt += f"Instruction: \"{instruction}\"\n"
        prompt += (
            "\nIdentify each target character/word in the image and return their "
            "center coordinates IN THE REQUIRED ORDER.\n\n"
            "Return JSON: {\n"
            '  "targets": [\n'
            '    {"char": "<character>", "x": <int>, "y": <int>},\n'
            '    {"char": "<character>", "x": <int>, "y": <int>},\n'
            "    ...\n"
            "  ],\n"
            '  "confidence": <float 0-1>,\n'
            '  "reasoning": "<brief>"\n'
            "}\n"
            "Coordinates relative to image top-left. Order must match the instruction."
        )

        try:
            result = vision_query(screenshot_b64, prompt)
        except RuntimeError as e:
            logger.warning(f"TextOrderSolver vision query failed: {e}")
            return False

        targets = result.get("targets", [])
        if not targets:
            logger.warning(f"TextOrderSolver: no targets found: {result}")
            return False

        logger.info(
            f"TextOrderSolver: {len(targets)} targets found: "
            + ", ".join(f"{t.get('char', '?')}@({t['x']},{t['y']})" for t in targets)
        )

        # Convert to absolute page coordinates
        bbox = await self._get_bbox(captcha_element)
        if not bbox:
            return False

        abs_points = [
            (bbox["x"] + int(t["x"]), bbox["y"] + int(t["y"]))
            for t in targets
        ]

        await click_sequence(page, abs_points, delay_between=0.4)
        return True
