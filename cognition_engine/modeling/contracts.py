from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


DEFAULT_PROVIDER = "mock"
DEFAULT_MODEL = "mock"
DEFAULT_OLLAMA_MODEL = "gemma4-pro:latest"

PROVIDER_MOCK = "mock"
PROVIDER_ADK_LITELLM_OLLAMA = "adk_litellm_ollama"
SUPPORTED_PROVIDERS = (PROVIDER_MOCK, PROVIDER_ADK_LITELLM_OLLAMA)

STATUS_SUCCESS = "success"
STATUS_ERROR = "error"
STATUS_FALLBACK = "fallback"


@dataclass(slots=True)
class ModelRequest:
    purpose: str
    input_text: str
    instruction: str = ""
    model: str = DEFAULT_MODEL
    provider: str = DEFAULT_PROVIDER
    temperature: float = 0.0
    timeout_seconds: float = 30.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, dict):
            self.metadata = dict(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ModelResponse:
    status: str
    output_text: str
    model: str
    provider: str
    latency_ms: float
    raw_summary: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    fallback_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
