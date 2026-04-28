from __future__ import annotations

import subprocess
import sys

from cognition_engine.modeling.contracts import (
    STATUS_ERROR,
    STATUS_FALLBACK,
    STATUS_SUCCESS,
    ModelRequest,
)
from cognition_engine.modeling.runtime import ModelRuntime


def test_mock_provider_returns_success() -> None:
    runtime = ModelRuntime()
    response = runtime.run(
        ModelRequest(
            purpose="unit",
            input_text="input text",
            instruction="stable instruction",
        )
    )

    assert response.status == STATUS_SUCCESS
    assert response.provider == "mock"
    assert "[mock:unit]" in response.output_text
    assert "input text" in response.output_text
    assert response.error_code is None


def test_unsupported_provider_returns_structured_error() -> None:
    runtime = ModelRuntime()
    response = runtime.run(
        ModelRequest(
            purpose="unit",
            input_text="hello",
            instruction="test",
            provider="not_supported",
        )
    )

    assert response.status == STATUS_ERROR
    assert response.provider == "not_supported"
    assert response.error_code == "unsupported_provider"
    assert "Unsupported model provider" in response.error_message


def test_runtime_exception_returns_structured_error() -> None:
    class BrokenProvider:
        async def generate(self, request: ModelRequest):  # noqa: ANN202
            del request
            raise RuntimeError("provider exploded")

    runtime = ModelRuntime(providers={"broken": BrokenProvider()})
    response = runtime.run(
        ModelRequest(
            purpose="unit",
            input_text="hello",
            instruction="test",
            provider="broken",
        )
    )

    assert response.status == STATUS_ERROR
    assert response.error_code == "RuntimeError"
    assert response.error_message == "provider exploded"


def test_runtime_can_fallback_to_mock() -> None:
    runtime = ModelRuntime(fallback_to_mock=True)
    response = runtime.run(
        ModelRequest(
            purpose="unit",
            input_text="hello",
            instruction="test",
            provider="not_supported",
        )
    )

    assert response.status == STATUS_FALLBACK
    assert response.provider == "mock"
    assert response.fallback_used is True
    assert response.error_code == "unsupported_provider"
    assert response.raw_summary["fallback_from_provider"] == "not_supported"


def test_smoke_mock_path_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "cognition_engine.modeling.smoke"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert '"status": "success"' in result.stdout
    assert '"provider": "mock"' in result.stdout
