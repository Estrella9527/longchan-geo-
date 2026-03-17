"""
Unified CAPTCHA detection and solving system.

Supports multiple CAPTCHA types:
- Click target (3D geometric, image selection)
- Slider puzzle (drag to fill gap)
- Text order (click characters in sequence)
- Rotate (drag to align image rotation)
- Text OCR (type distorted text)
- Manual fallback (push to user when AI fails)

Usage:
    from app.services.captcha import solve_captcha

    solved = await solve_captcha(page, captcha_element, session_id="xxx")
"""
from app.services.captcha.detector import CaptchaType, detect_captcha_type
from app.services.captcha.click_solver import ClickSolver
from app.services.captcha.slider_solver import SliderSolver
from app.services.captcha.text_order_solver import TextOrderSolver
from app.services.captcha.rotate_solver import RotateSolver
from app.services.captcha.fallback_solver import FallbackSolver
import logging

logger = logging.getLogger(__name__)

_SOLVER_MAP = {
    CaptchaType.CLICK_TARGET: ClickSolver,
    CaptchaType.SLIDER_PUZZLE: SliderSolver,
    CaptchaType.TEXT_ORDER: TextOrderSolver,
    CaptchaType.ROTATE: RotateSolver,
    CaptchaType.TEXT_OCR: ClickSolver,  # OCR uses same vision approach
}


async def solve_captcha(
    page,
    captcha_element,
    session_id: str | None = None,
    max_retries: int = 3,
) -> bool:
    """Detect CAPTCHA type and solve it. Falls back to manual if AI fails.

    Args:
        page: Playwright page object.
        captcha_element: The CAPTCHA container element.
        session_id: Auth session ID (enables manual fallback + status updates).
        max_retries: Max auto-solve attempts per solver.

    Returns:
        True if solved, False if all attempts (including manual) failed.
    """
    from app.core.config import settings

    captcha_type, context = await detect_captcha_type(page, captcha_element)
    context["session_id"] = session_id
    context["captcha_type"] = captcha_type.value
    logger.info(f"CAPTCHA detected: type={captcha_type.value}")

    # Try the appropriate AI solver
    solver_cls = _SOLVER_MAP.get(captcha_type)
    if solver_cls:
        solver = solver_cls()
        success = await solver.solve_with_retry(
            page, captcha_element, context, max_retries=max_retries
        )
        if success:
            return True
        logger.warning(f"AI solver ({captcha_type.value}) failed after {max_retries} attempts")

    # Fall back to manual if enabled and session_id available
    if session_id and settings.CAPTCHA_FALLBACK_TO_MANUAL:
        logger.info("Falling back to manual CAPTCHA solving")
        fallback = FallbackSolver()
        return await fallback.solve(page, captcha_element, context)

    return False
