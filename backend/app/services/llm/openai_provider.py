"""
OpenAI-compatible LLM provider (synchronous, for Celery worker).
"""
import time
import httpx
from typing import Optional
from app.core.config import settings
from app.services.llm.base import BaseLLMProvider, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """Sync OpenAI-compatible provider using httpx."""

    def __init__(
        self,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        self.api_base = (api_base or settings.LLM_API_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.LLM_API_KEY
        self.default_model = default_model or settings.LLM_DEFAULT_MODEL
        self.timeout = timeout or settings.LLM_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.LLM_MAX_RETRIES

    def chat(self, messages: list[dict], model: Optional[str] = None) -> LLMResponse:
        """Send a synchronous chat completion request with retry."""
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2048,
        }

        last_error = None
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()

                choice = data["choices"][0]
                usage = data.get("usage", {})
                return LLMResponse(
                    content=choice["message"]["content"] or "",
                    model=data.get("model", payload["model"]),
                    usage={
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    },
                    raw_response=data,
                )
            except (httpx.HTTPStatusError, httpx.RequestError, KeyError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

        raise RuntimeError(
            f"LLM request failed after {self.max_retries} retries: {last_error}"
        )
