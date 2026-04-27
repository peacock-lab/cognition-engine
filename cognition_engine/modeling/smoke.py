from __future__ import annotations

import json
import os

from .contracts import (
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_PROVIDER,
    PROVIDER_ADK_LITELLM_OLLAMA,
    ModelRequest,
)
from .runtime import ModelRuntime


def build_smoke_request() -> ModelRequest:
    provider = os.environ.get("CE_MODEL_PROVIDER", DEFAULT_PROVIDER)
    default_model = DEFAULT_OLLAMA_MODEL if provider == PROVIDER_ADK_LITELLM_OLLAMA else "mock"
    return ModelRequest(
        purpose="modeling-smoke",
        input_text=os.environ.get("CE_MODEL_INPUT", "Return OK."),
        instruction=os.environ.get(
            "CE_MODEL_INSTRUCTION",
            "Return a short plain text answer.",
        ),
        model=os.environ.get("CE_MODEL_NAME", default_model),
        provider=provider,
        temperature=float(os.environ.get("CE_MODEL_TEMPERATURE", "0")),
        timeout_seconds=float(os.environ.get("CE_MODEL_TIMEOUT_SECONDS", "30")),
        metadata={"entry": "python -m cognition_engine.modeling.smoke"},
    )


def main() -> int:
    runtime = ModelRuntime()
    response = runtime.run(build_smoke_request())
    print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
