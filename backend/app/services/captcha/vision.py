"""
Unified vision API client for CAPTCHA solving.

All solvers share this function — only the prompt differs.
"""
import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def vision_query(screenshot_b64: str, prompt: str, system: str = "") -> dict:
    """Call the vision model with a screenshot and return parsed JSON.

    Args:
        screenshot_b64: Base64-encoded PNG screenshot.
        prompt: User prompt describing what to identify.
        system: Optional system prompt.

    Returns:
        Parsed JSON dict from the model response.

    Raises:
        RuntimeError: If API call fails or response is unparseable.
    """
    if not system:
        system = (
            "You are a CAPTCHA analysis assistant. Analyze the image carefully and "
            "return ONLY a valid JSON object as specified in the user prompt. "
            "No markdown, no explanation — just the JSON."
        )

    user_content = [
        {"type": "text", "text": prompt},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"},
        },
    ]

    payload = {
        "model": settings.CAPTCHA_VISION_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": 500,
        "temperature": 0,
    }

    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    url = f"{settings.LLM_API_BASE_URL}/chat/completions"

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Strip markdown code block if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(content)
        logger.info(f"Vision API response: {content[:200]}")
        return result

    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"Vision API HTTP {e.response.status_code}: {e.response.text[:200]}"
        ) from e
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        raise RuntimeError(f"Failed to parse vision response: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Vision API call failed: {e}") from e
