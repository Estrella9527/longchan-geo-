"""
Browser authentication flow coordinator.

Uses Redis as a message channel between the API layer (receives user input)
and the Celery browser worker (drives the actual browser).

State machine:
  starting → navigating → sending_code → [solving_captcha → manual_captcha] →
  waiting_for_code → submitting_code → verifying → success/failed

Redis keys (TTL 5 min):
  auth:{session_id}:state       — current state string
  auth:{session_id}:message     — human-readable status message
  auth:{session_id}:code        — verification code submitted by user
  auth:{session_id}:error       — error message if failed
  auth:{session_id}:screenshot  — base64 screenshot for debug (optional)
  auth:{session_id}:captcha_screenshot — CAPTCHA area screenshot for manual solving
  auth:{session_id}:captcha_instruction — CAPTCHA instruction text
  auth:{session_id}:captcha_type — CAPTCHA type (click_target, slider_puzzle, etc.)
  auth:{session_id}:captcha_action — user's manual CAPTCHA action (JSON)
"""
import redis
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

AUTH_TTL = 300  # 5 minutes

_redis_client = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        broker_url = settings.CELERY_BROKER_URL  # redis://redis:6379/1
        base = broker_url.rsplit("/", 1)[0]
        _redis_client = redis.from_url(f"{base}/3", decode_responses=True)
    return _redis_client


def _key(session_id: str, field: str) -> str:
    return f"auth:{session_id}:{field}"


# ─── Write operations (called from Celery worker) ────────────────

def set_auth_state(session_id: str, state: str, message: str = ""):
    r = _get_redis()
    r.setex(_key(session_id, "state"), AUTH_TTL, state)
    if message:
        r.setex(_key(session_id, "message"), AUTH_TTL, message)
    logger.info(f"[Auth {session_id[:8]}] state={state} msg={message}")


def set_auth_error(session_id: str, error: str):
    r = _get_redis()
    r.setex(_key(session_id, "state"), AUTH_TTL, "failed")
    r.setex(_key(session_id, "error"), AUTH_TTL, error)
    r.setex(_key(session_id, "message"), AUTH_TTL, error)


def set_auth_screenshot(session_id: str, screenshot_b64: str):
    r = _get_redis()
    r.setex(_key(session_id, "screenshot"), AUTH_TTL, screenshot_b64)


# ─── Read operations (called from API layer) ─────────────────────

def get_auth_status(session_id: str) -> dict:
    r = _get_redis()
    state = r.get(_key(session_id, "state"))
    if not state:
        return {"state": "idle", "message": ""}
    result = {
        "state": state,
        "message": r.get(_key(session_id, "message")) or "",
        "error": r.get(_key(session_id, "error")) or "",
    }
    if state == "manual_captcha":
        result["captcha_type"] = r.get(_key(session_id, "captcha_type")) or ""
        result["captcha_instruction"] = r.get(_key(session_id, "captcha_instruction")) or ""
    return result


def get_auth_screenshot(session_id: str) -> str:
    r = _get_redis()
    return r.get(_key(session_id, "screenshot")) or ""


def is_auth_in_progress(session_id: str) -> bool:
    status = get_auth_status(session_id)
    return status["state"] not in ("idle", "success", "failed")


# ─── Code exchange (API writes, worker reads) ────────────────────

def submit_verification_code(session_id: str, code: str):
    r = _get_redis()
    r.setex(_key(session_id, "code"), AUTH_TTL, code)


def poll_verification_code(session_id: str, timeout: int = 180, interval: float = 1.0) -> str:
    import time
    r = _get_redis()
    key = _key(session_id, "code")
    elapsed = 0
    while elapsed < timeout:
        code = r.get(key)
        if code:
            r.delete(key)
            return code
        time.sleep(interval)
        elapsed += interval
    return ""


def cleanup_auth(session_id: str):
    r = _get_redis()
    for field in (
        "state", "message", "code", "error", "screenshot",
        "captcha_screenshot", "captcha_instruction", "captcha_type", "captcha_action",
    ):
        r.delete(_key(session_id, field))


# ─── CAPTCHA data exchange (manual fallback) ─────────────────────

def set_captcha_data(session_id: str, screenshot_b64: str, instruction: str, captcha_type: str):
    """Worker pushes CAPTCHA data for frontend manual solving."""
    r = _get_redis()
    r.setex(_key(session_id, "captcha_screenshot"), AUTH_TTL, screenshot_b64)
    r.setex(_key(session_id, "captcha_instruction"), AUTH_TTL, instruction)
    r.setex(_key(session_id, "captcha_type"), AUTH_TTL, captcha_type)
    # Clear any previous action
    r.delete(_key(session_id, "captcha_action"))


def get_captcha_data(session_id: str) -> dict:
    """API reads CAPTCHA data for frontend display."""
    r = _get_redis()
    return {
        "screenshot": r.get(_key(session_id, "captcha_screenshot")) or "",
        "instruction": r.get(_key(session_id, "captcha_instruction")) or "",
        "captcha_type": r.get(_key(session_id, "captcha_type")) or "",
    }


def submit_captcha_action(session_id: str, action_json: str):
    """Frontend submits user's manual CAPTCHA action (click coords, drag, etc.)."""
    r = _get_redis()
    r.setex(_key(session_id, "captcha_action"), AUTH_TTL, action_json)


def poll_captcha_action(session_id: str, timeout: int = 60, interval: float = 1.0) -> dict | None:
    """Worker polls for user's manual CAPTCHA action."""
    import time
    import json
    r = _get_redis()
    key = _key(session_id, "captcha_action")
    elapsed = 0
    while elapsed < timeout:
        data = r.get(key)
        if data:
            r.delete(key)
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return None
        time.sleep(interval)
        elapsed += interval
    return None
