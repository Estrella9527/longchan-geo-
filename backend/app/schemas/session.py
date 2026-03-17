"""
Pydantic schemas for browser session management.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SessionCreate(BaseModel):
    provider_name: str = Field(..., pattern="^(doubao|deepseek)$")
    display_name: Optional[str] = None
    phone_number: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    provider_name: str
    display_name: Optional[str] = None
    status: str
    phone_number: Optional[str] = None
    last_used_at: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    health_check_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SessionHealthCheck(BaseModel):
    session_id: str
    is_healthy: bool
    message: str = ""


class AuthStartRequest(BaseModel):
    phone_number: str = Field(..., min_length=5, max_length=20)


class AuthStatusResponse(BaseModel):
    state: str
    message: str = ""
    error: str = ""
    screenshot: Optional[str] = None
    captcha_type: Optional[str] = None
    captcha_instruction: Optional[str] = None


class AuthCodeRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=10)


class CaptchaDataResponse(BaseModel):
    screenshot: str = ""
    instruction: str = ""
    captcha_type: str = ""


class CaptchaActionRequest(BaseModel):
    """User's manual CAPTCHA action.

    For click: {"type": "click", "x": 120, "y": 85}
    For drag:  {"type": "drag", "start_x": 10, "start_y": 100, "end_x": 200, "end_y": 100}
    For sequence: {"type": "click_sequence", "points": [{"x": 1, "y": 2}, ...]}
    """
    type: str = Field(..., pattern="^(click|drag|click_sequence|refresh)$")
    x: Optional[int] = None
    y: Optional[int] = None
    start_x: Optional[int] = None
    start_y: Optional[int] = None
    end_x: Optional[int] = None
    end_y: Optional[int] = None
    points: Optional[list[dict]] = None
