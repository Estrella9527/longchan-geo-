"""
CAPTCHA type detection.

Two-phase approach:
1. DOM structure analysis (free, fast)
2. Vision model fallback (accurate, costs API call)
"""
import base64
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class CaptchaType(Enum):
    CLICK_TARGET = "click_target"
    SLIDER_PUZZLE = "slider_puzzle"
    TEXT_ORDER = "text_order"
    ROTATE = "rotate"
    TEXT_OCR = "text_ocr"
    UNKNOWN = "unknown"


# DOM class/attribute patterns → CAPTCHA type
_DOM_PATTERNS = {
    CaptchaType.SLIDER_PUZZLE: [
        "slider", "slide", "drag", "puzzle",
        "geetest_slider", "nc_wrapper", "captcha-slider",
    ],
    CaptchaType.ROTATE: [
        "rotate", "rotation", "spin",
    ],
    CaptchaType.TEXT_ORDER: [
        "order", "sequence", "word-click", "char-click",
    ],
    CaptchaType.TEXT_OCR: [
        "text-captcha", "img-captcha", "code-input",
    ],
}


async def detect_captcha_type(page, captcha_element) -> tuple[CaptchaType, dict]:
    """Detect the type of CAPTCHA and extract context.

    Returns:
        (CaptchaType, context_dict) where context may contain instruction text,
        element references, etc.
    """
    context = {}

    # Phase 1: DOM analysis
    dom_type = await _detect_from_dom(captcha_element, context)
    if dom_type != CaptchaType.UNKNOWN:
        logger.info(f"CAPTCHA type detected via DOM: {dom_type.value}")
        return dom_type, context

    # Phase 2: Vision model classification
    try:
        vision_type = await _detect_from_vision(captcha_element, context)
        logger.info(f"CAPTCHA type detected via vision: {vision_type.value}")
        return vision_type, context
    except Exception as e:
        logger.warning(f"Vision detection failed: {e}")

    # Default to click target (most common)
    return CaptchaType.CLICK_TARGET, context


async def _detect_from_dom(captcha_element, context: dict) -> CaptchaType:
    """Analyze DOM structure to determine CAPTCHA type."""
    try:
        dom_info = await captcha_element.evaluate("""el => {
            const classes = el.className || '';
            const html = el.innerHTML || '';
            const allClasses = [];
            el.querySelectorAll('*').forEach(n => {
                if (n.className && typeof n.className === 'string')
                    allClasses.push(n.className.toLowerCase());
            });

            // Check for slider handle element
            const hasSlider = !!el.querySelector(
                '[class*="slider"], [class*="slide-btn"], [class*="drag"], ' +
                '[class*="handler"], [class*="geetest_btn"]'
            );

            // Check for rotation UI
            const hasRotate = !!el.querySelector(
                '[class*="rotate"], [class*="rotation"]'
            );

            // Check for text input inside CAPTCHA
            const hasInput = !!el.querySelector('input[type="text"], input:not([type])');

            // Extract instruction text
            let instruction = '';
            const textEls = el.querySelectorAll('span, p, div, label, h3, h4');
            for (const t of textEls) {
                const text = (t.textContent || '').trim();
                if (text.length > 3 && text.length < 200) {
                    const lc = text.toLowerCase();
                    if (lc.includes('click') || lc.includes('点击') ||
                        lc.includes('drag') || lc.includes('拖') ||
                        lc.includes('slide') || lc.includes('滑') ||
                        lc.includes('rotate') || lc.includes('旋转') ||
                        lc.includes('order') || lc.includes('顺序') ||
                        lc.includes('输入') || lc.includes('type') ||
                        lc.includes('select') || lc.includes('请')) {
                        instruction = text;
                        break;
                    }
                }
            }

            return {
                classes: classes.toLowerCase(),
                allClasses: allClasses.join(' '),
                hasSlider, hasRotate, hasInput,
                instruction,
            };
        }""")

        context["instruction"] = dom_info.get("instruction", "")
        all_classes = dom_info["classes"] + " " + dom_info["allClasses"]

        # Instruction text is the most reliable signal — check FIRST
        # (DOM element checks can false-positive on generic modal containers)
        instruction = context.get("instruction", "").lower()
        if instruction:
            if any(kw in instruction for kw in ["click", "点击", "select", "选择", "find", "找"]):
                return CaptchaType.CLICK_TARGET
            if any(kw in instruction for kw in ["拖", "drag", "slide", "滑"]):
                return CaptchaType.SLIDER_PUZZLE
            if any(kw in instruction for kw in ["旋转", "rotate"]):
                return CaptchaType.ROTATE
            if any(kw in instruction for kw in ["顺序", "order", "按顺序"]):
                return CaptchaType.TEXT_ORDER

        # Check explicit element types
        if dom_info["hasSlider"]:
            return CaptchaType.SLIDER_PUZZLE
        if dom_info["hasRotate"]:
            return CaptchaType.ROTATE
        if dom_info["hasInput"]:
            return CaptchaType.TEXT_OCR

        # Check class name patterns
        for captcha_type, patterns in _DOM_PATTERNS.items():
            for pattern in patterns:
                if pattern in all_classes:
                    return captcha_type

    except Exception as e:
        logger.warning(f"DOM analysis failed: {e}")

    return CaptchaType.UNKNOWN


async def _detect_from_vision(captcha_element, context: dict) -> CaptchaType:
    """Use vision model to classify the CAPTCHA type."""
    from app.services.captcha.vision import vision_query

    screenshot_bytes = await captcha_element.screenshot(type="png")
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

    prompt = (
        "This image shows a CAPTCHA challenge. Classify it into one of these types:\n"
        '- "click_target": Click on a specific object/shape (e.g. "click the green cone")\n'
        '- "slider_puzzle": Drag a slider to fill a puzzle gap\n'
        '- "text_order": Click characters/words in a specific order\n'
        '- "rotate": Rotate an image to align it correctly\n'
        '- "text_ocr": Type the text/numbers shown in the image\n\n'
        "Also extract the instruction text if visible.\n\n"
        'Return JSON: {"type": "<type>", "instruction": "<instruction text>"}'
    )

    result = vision_query(screenshot_b64, prompt)
    captcha_type_str = result.get("type", "click_target")

    if result.get("instruction"):
        context["instruction"] = result["instruction"]

    try:
        return CaptchaType(captcha_type_str)
    except ValueError:
        return CaptchaType.CLICK_TARGET
