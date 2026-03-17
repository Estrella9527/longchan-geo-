"""Unit tests for the CAPTCHA vision module and detector."""
import json
from unittest.mock import patch, MagicMock

import pytest

from app.services.captcha.vision import vision_query
from app.services.captcha.detector import CaptchaType


FAKE_SCREENSHOT_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"


def _mock_response(content: str | dict):
    """Build a mock httpx response."""
    if isinstance(content, dict):
        content = json.dumps(content)
    body = {"choices": [{"message": {"content": content}}]}
    resp = MagicMock()
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    return resp


def _patch_httpx(return_content):
    """Create a mock httpx.Client context manager."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = _mock_response(return_content)
    return mock_client


class TestVisionQuery:
    """Tests for vision_query()."""

    @patch("app.services.captcha.vision.httpx.Client")
    def test_basic_json_parsing(self, mock_cls):
        mock_cls.return_value = _patch_httpx({"x": 120, "y": 85, "confidence": 0.95})

        result = vision_query(FAKE_SCREENSHOT_B64, "Find the target")

        assert result["x"] == 120
        assert result["y"] == 85
        assert result["confidence"] == 0.95

    @patch("app.services.captcha.vision.httpx.Client")
    def test_markdown_wrapped_json(self, mock_cls):
        raw = '```json\n{"x": 50, "y": 60}\n```'
        mock_cls.return_value = _patch_httpx(raw)

        result = vision_query(FAKE_SCREENSHOT_B64, "Find target")

        assert result["x"] == 50
        assert result["y"] == 60

    @patch("app.services.captcha.vision.httpx.Client")
    def test_invalid_json_raises(self, mock_cls):
        mock_cls.return_value = _patch_httpx("not json at all")

        with pytest.raises(RuntimeError, match="Failed to parse"):
            vision_query(FAKE_SCREENSHOT_B64, "Find target")

    @patch("app.services.captcha.vision.httpx.Client")
    def test_http_error_raises(self, mock_cls):
        import httpx

        resp = MagicMock()
        resp.status_code = 500
        resp.text = "Internal Server Error"
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=resp
        )

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = resp
        mock_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="Vision API HTTP"):
            vision_query(FAKE_SCREENSHOT_B64, "Find target")

    @patch("app.services.captcha.vision.httpx.Client")
    def test_captcha_type_detection_response(self, mock_cls):
        mock_cls.return_value = _patch_httpx({
            "type": "slider_puzzle",
            "instruction": "Drag slider to fill the gap",
        })

        result = vision_query(FAKE_SCREENSHOT_B64, "Classify this CAPTCHA")

        assert result["type"] == "slider_puzzle"
        assert "slider" in result["instruction"].lower()

    @patch("app.services.captcha.vision.httpx.Client")
    def test_click_solver_response_with_coords(self, mock_cls):
        mock_cls.return_value = _patch_httpx({
            "x": 200, "y": 150, "confidence": 0.9, "reasoning": "green cone"
        })

        result = vision_query(FAKE_SCREENSHOT_B64, "Click on the smallest green cone")

        assert result["x"] == 200
        assert result["y"] == 150

    @patch("app.services.captcha.vision.httpx.Client")
    def test_slider_solver_response(self, mock_cls):
        mock_cls.return_value = _patch_httpx({
            "slider_x": 30, "slider_y": 180, "gap_x": 250,
            "confidence": 0.85, "reasoning": "gap visible"
        })

        result = vision_query(FAKE_SCREENSHOT_B64, "Find the gap position")

        assert result["gap_x"] == 250
        assert result["slider_x"] == 30

    @patch("app.services.captcha.vision.httpx.Client")
    def test_text_order_response(self, mock_cls):
        mock_cls.return_value = _patch_httpx({
            "targets": [
                {"char": "天", "x": 50, "y": 80},
                {"char": "地", "x": 150, "y": 120},
                {"char": "人", "x": 100, "y": 60},
            ],
            "confidence": 0.88,
        })

        result = vision_query(FAKE_SCREENSHOT_B64, "Click in order: 天地人")

        assert len(result["targets"]) == 3
        assert result["targets"][0]["char"] == "天"


class TestCaptchaType:
    """Tests for CaptchaType enum."""

    def test_all_types_have_values(self):
        assert CaptchaType.CLICK_TARGET.value == "click_target"
        assert CaptchaType.SLIDER_PUZZLE.value == "slider_puzzle"
        assert CaptchaType.TEXT_ORDER.value == "text_order"
        assert CaptchaType.ROTATE.value == "rotate"
        assert CaptchaType.TEXT_OCR.value == "text_ocr"
        assert CaptchaType.UNKNOWN.value == "unknown"

    def test_from_value(self):
        assert CaptchaType("slider_puzzle") == CaptchaType.SLIDER_PUZZLE

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            CaptchaType("nonexistent_type")
