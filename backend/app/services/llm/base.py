"""
LLM Provider base classes for synchronous task execution.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    usage: dict = field(default_factory=dict)
    raw_response: Optional[dict] = None


class BaseLLMProvider(ABC):
    """Abstract base class for synchronous LLM providers."""

    @abstractmethod
    def chat(self, messages: list[dict], model: Optional[str] = None) -> LLMResponse:
        """Send a chat request synchronously."""
        ...
