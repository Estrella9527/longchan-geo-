"""
Manual fallback CAPTCHA solver.

When AI solvers fail, this pushes the CAPTCHA screenshot to the frontend
via Redis and waits for the user to manually interact (click coordinates,
drag distance, etc.).

Communication flow:
  Worker → Redis (captcha screenshot + instruction)
  Frontend polls → displays interactive CAPTCHA UI
  User clicks/drags → Frontend → API → Redis (action data)
  Worker polls Redis → executes the action via Playwright

Retry loop (up to 3 attempts):
  1. Screenshot → push to Redis
  2. Poll for user action (60s timeout)
  3. "refresh" action → click refresh button, re-loop
  4. Execute click/drag/click_sequence
  5. Wait 2s → check if CAPTCHA disappeared
  6. Still visible → re-loop with fresh screenshot
"""
import asyncio
import logging

from app.services.captcha.base_solver import BaseCaptchaSolver
from app.services.captcha.executor import human_like_click, human_like_drag

logger = logging.getLogger(__name__)

MAX_MANUAL_ATTEMPTS = 3


class FallbackSolver(BaseCaptchaSolver):
    """Manual fallback: push CAPTCHA to user, wait for their action."""

    async def solve(self, page, captcha_element, context: dict) -> bool:
        from app.services.auth_flow import (
            set_auth_state,
            set_captcha_data,
            poll_captcha_action,
        )

        session_id = context.get("session_id")
        if not session_id:
            logger.warning("FallbackSolver: no session_id, cannot use manual fallback")
            return False

        instruction = context.get("instruction", "请在验证码图片上点击正确的目标")
        captcha_type = context.get("captcha_type", "click_target")

        bbox = await self._get_bbox(captcha_element)
        if not bbox:
            return False

        for attempt in range(1, MAX_MANUAL_ATTEMPTS + 1):
            logger.info(f"FallbackSolver: attempt {attempt}/{MAX_MANUAL_ATTEMPTS}")

            # 1. Take fresh screenshot and push to Redis
            screenshot_b64 = await self._screenshot_element(captcha_element)
            set_auth_state(session_id, "manual_captcha", "需要人工处理验证码，请在截图上操作")
            set_captcha_data(session_id, screenshot_b64, instruction, captcha_type)

            # 2. Poll for user action (60s timeout)
            logger.info("FallbackSolver: waiting for user manual action...")
            action = poll_captcha_action(session_id, timeout=60)

            if not action:
                logger.warning("FallbackSolver: user action timeout")
                return False

            action_type = action.get("type", "click")

            # 3. Handle refresh — re-take screenshot and loop
            if action_type == "refresh":
                logger.info("FallbackSolver: user requested refresh")
                await self._try_refresh(captcha_element)
                # Re-read bbox in case element moved
                bbox = await self._get_bbox(captcha_element) or bbox
                continue

            # 4. Execute the user's action
            if action_type == "click":
                rel_x = int(action.get("x", 0))
                rel_y = int(action.get("y", 0))
                abs_x = bbox["x"] + rel_x
                abs_y = bbox["y"] + rel_y
                logger.info(f"FallbackSolver: user clicked ({rel_x},{rel_y}) → page ({abs_x:.0f},{abs_y:.0f})")
                await human_like_click(page, abs_x, abs_y)

            elif action_type == "drag":
                start_x = int(action.get("start_x", 0))
                start_y = int(action.get("start_y", 0))
                end_x = int(action.get("end_x", 0))
                end_y = int(action.get("end_y", 0))
                abs_sx = bbox["x"] + start_x
                abs_sy = bbox["y"] + start_y
                abs_ex = bbox["x"] + end_x
                abs_ey = bbox["y"] + end_y
                logger.info(f"FallbackSolver: user drag ({start_x},{start_y})→({end_x},{end_y})")
                await human_like_drag(page, abs_sx, abs_sy, abs_ex, abs_ey)

            elif action_type == "click_sequence":
                points = action.get("points", [])
                for i, pt in enumerate(points):
                    abs_x = bbox["x"] + int(pt["x"])
                    abs_y = bbox["y"] + int(pt["y"])
                    await human_like_click(page, abs_x, abs_y)
                    if i < len(points) - 1:
                        await asyncio.sleep(0.3)

            else:
                logger.warning(f"FallbackSolver: unknown action type: {action_type}")
                return False

            # 5. Wait and verify CAPTCHA disappeared
            await asyncio.sleep(2)
            still_visible = await self._is_still_visible(captcha_element)
            if not still_visible:
                logger.info(f"FallbackSolver: CAPTCHA solved on attempt {attempt}")
                return True

            logger.info(f"FallbackSolver: CAPTCHA still visible after attempt {attempt}, retrying")
            # Re-read bbox for next iteration
            bbox = await self._get_bbox(captcha_element) or bbox

        logger.warning(f"FallbackSolver: failed after {MAX_MANUAL_ATTEMPTS} manual attempts")
        return False

    async def solve_with_retry(self, page, captcha_element, context, max_retries=1):
        """Manual fallback has its own retry loop inside solve()."""
        return await self.solve(page, captcha_element, context)
