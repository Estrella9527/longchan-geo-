"""
Browser Session Management API.

POST   /sessions              — Create a new browser session
GET    /sessions              — List all sessions
GET    /sessions/{id}         — Get session detail
POST   /sessions/{id}/activate — Mark session as active
POST   /sessions/{id}/health-check — Trigger health check
DELETE /sessions/{id}         — Delete session
POST   /sessions/{id}/auth/start  — Start auth flow
GET    /sessions/{id}/auth/status — Poll auth status
POST   /sessions/{id}/auth/code   — Submit verification code
GET    /sessions/{id}/auth/captcha — Get CAPTCHA data for manual solving
POST   /sessions/{id}/auth/captcha — Submit manual CAPTCHA action
GET    /sessions/server-info  — Get server connection info
"""
import os
import socket
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional

from app.middleware.auth import get_current_user, require_role
from app.models.user import User
from app.services.session_manager import get_session_manager
from app.schemas.session import (
    SessionCreate, SessionResponse,
    AuthStartRequest, AuthStatusResponse, AuthCodeRequest,
    CaptchaDataResponse, CaptchaActionRequest,
)

router = APIRouter()

admin_only = require_role("admin")


def _serialize(session: dict) -> dict:
    """Serialize datetime/UUID fields for JSON."""
    out = dict(session)
    for key in ("created_at", "updated_at", "last_used_at", "last_health_check"):
        if key in out and out[key] is not None:
            out[key] = out[key].isoformat() if hasattr(out[key], "isoformat") else str(out[key])
    for key in ("id",):
        if key in out and out[key] is not None:
            out[key] = str(out[key])
    out.pop("user_data_dir", None)
    return out


@router.get("/server-info")
async def get_server_info(user: User = Depends(admin_only)):
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "unknown"

    server_addr = os.environ.get("SERVER_ADDRESS", "")
    return {
        "hostname": hostname,
        "ip": ip if ip != "127.0.0.1" else server_addr or "请在 .env 中配置 SERVER_ADDRESS",
        "server_address": server_addr,
        "vnc_port": os.environ.get("VNC_PORT", "5900"),
        "rdp_port": os.environ.get("RDP_PORT", "3389"),
    }


@router.post("", response_model=SessionResponse)
async def create_session(body: SessionCreate, user: User = Depends(admin_only)):
    mgr = get_session_manager()
    session = mgr.create_session(
        provider_name=body.provider_name,
        display_name=body.display_name or "",
        phone_number=body.phone_number or "",
    )
    return _serialize(session)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    provider_name: Optional[str] = Query(None),
    user: User = Depends(admin_only),
):
    mgr = get_session_manager()
    sessions = mgr.list_sessions(provider_name=provider_name)
    return [_serialize(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, user: User = Depends(admin_only)):
    mgr = get_session_manager()
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _serialize(session)


@router.post("/{session_id}/activate")
async def activate_session(session_id: str, user: User = Depends(admin_only)):
    mgr = get_session_manager()
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    mgr.update_status(session_id, "active")

    health_check_queued = False
    try:
        from app.tasks.browser_tasks import check_session_health
        if check_session_health:
            check_session_health.apply_async(args=[session_id], queue="browser")
            health_check_queued = True
    except Exception:
        pass

    session = mgr.get_session(session_id)
    return {
        "session": _serialize(session),
        "activated": True,
        "health_check_queued": health_check_queued,
        "message": "会话已激活" + ("，健康检查已排队验证" if health_check_queued else ""),
    }


@router.post("/{session_id}/health-check")
async def health_check_session(session_id: str, user: User = Depends(admin_only)):
    mgr = get_session_manager()
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        from app.tasks.browser_tasks import check_session_health
        check_session_health.apply_async(args=[session_id], queue="browser")
        return {"status": "queued", "message": "健康检查已提交，等待浏览器 Worker 执行"}
    except Exception as e:
        return {"status": "error", "message": f"提交失败: {str(e)}"}


@router.post("/{session_id}/auth/start")
async def start_auth(
    session_id: str,
    body: AuthStartRequest,
    user: User = Depends(admin_only),
):
    mgr = get_session_manager()
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from app.services.auth_flow import is_auth_in_progress
    if is_auth_in_progress(session_id):
        raise HTTPException(
            status_code=409,
            detail="认证流程进行中，请等待完成或超时后重试",
        )

    if body.phone_number:
        mgr.update_phone(session_id, body.phone_number)

    try:
        from app.tasks.browser_tasks import start_browser_auth
        if start_browser_auth:
            start_browser_auth.apply_async(
                args=[session_id, body.phone_number],
                queue="browser",
            )
            return {"status": "started", "message": "认证流程已启动，请等待短信验证码"}
        else:
            raise HTTPException(status_code=503, detail="Browser worker 不可用")
    except ImportError:
        raise HTTPException(status_code=503, detail="Browser worker 未配置")


@router.get("/{session_id}/auth/status", response_model=AuthStatusResponse)
async def get_auth_status(session_id: str, user: User = Depends(admin_only)):
    from app.services.auth_flow import get_auth_status as _get_status, get_auth_screenshot
    status = _get_status(session_id)

    result = {
        "state": status["state"],
        "message": status["message"],
        "error": status.get("error", ""),
        "screenshot": get_auth_screenshot(session_id),
    }
    if status.get("captcha_type"):
        result["captcha_type"] = status["captcha_type"]
    if status.get("captcha_instruction"):
        result["captcha_instruction"] = status["captcha_instruction"]
    return result


@router.post("/{session_id}/auth/code")
async def submit_auth_code(
    session_id: str,
    body: AuthCodeRequest,
    user: User = Depends(admin_only),
):
    from app.services.auth_flow import get_auth_status as _get_status, submit_verification_code
    status = _get_status(session_id)

    if status["state"] != "waiting_for_code":
        raise HTTPException(
            status_code=400,
            detail=f"当前状态为 {status['state']}，无法提交验证码（需要 waiting_for_code 状态）",
        )

    submit_verification_code(session_id, body.code)
    return {"status": "submitted", "message": "验证码已提交，正在验证..."}


@router.get("/{session_id}/auth/captcha", response_model=CaptchaDataResponse)
async def get_captcha_data(session_id: str, user: User = Depends(admin_only)):
    """Get CAPTCHA screenshot and instruction for manual solving."""
    from app.services.auth_flow import get_captcha_data as _get_captcha
    return _get_captcha(session_id)


@router.post("/{session_id}/auth/captcha")
async def submit_captcha_action(
    session_id: str,
    body: CaptchaActionRequest,
    user: User = Depends(admin_only),
):
    """Submit user's manual CAPTCHA action (click coords, drag, etc.)."""
    from app.services.auth_flow import (
        get_auth_status as _get_status,
        submit_captcha_action as _submit_action,
    )
    import json

    status = _get_status(session_id)
    if status["state"] != "manual_captcha":
        raise HTTPException(
            status_code=400,
            detail=f"当前状态为 {status['state']}，无法提交验证码操作（需要 manual_captcha 状态）",
        )

    _submit_action(session_id, json.dumps(body.model_dump(exclude_none=True)))
    return {"status": "submitted", "message": "验证码操作已提交"}


@router.delete("/{session_id}")
async def delete_session(session_id: str, user: User = Depends(admin_only)):
    mgr = get_session_manager()
    ok = mgr.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted"}
