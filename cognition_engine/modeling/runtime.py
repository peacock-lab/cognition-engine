from __future__ import annotations

import asyncio
import time

from .contracts import (
    PROVIDER_MOCK,
    STATUS_ERROR,
    STATUS_FALLBACK,
    ModelRequest,
    ModelResponse,
)
from .providers import ModelProvider, build_default_providers


class ModelRuntime:
    def __init__(
        self,
        providers: dict[str, ModelProvider] | None = None,
        *,
        fallback_to_mock: bool = False,
    ) -> None:
        self.providers = providers if providers is not None else build_default_providers()
        self.fallback_to_mock = fallback_to_mock

    def run(self, request: ModelRequest) -> ModelResponse:
        return asyncio.run(self.run_async(request))

    async def run_async(self, request: ModelRequest) -> ModelResponse:
        started_at = time.perf_counter()
        provider = self.providers.get(request.provider)
        if provider is None:
            return await self._error_or_fallback(
                request,
                started_at,
                "unsupported_provider",
                f"Unsupported model provider: {request.provider}",
            )

        try:
            response = await provider.generate(request)
        except Exception as exc:  # noqa: BLE001
            return await self._error_or_fallback(
                request,
                started_at,
                type(exc).__name__,
                str(exc),
            )

        if response.status == STATUS_ERROR and self.fallback_to_mock:
            return await self._fallback_to_mock(request, response)
        return response

    async def _error_or_fallback(
        self,
        request: ModelRequest,
        started_at: float,
        error_code: str,
        error_message: str,
    ) -> ModelResponse:
        error_response = ModelResponse(
            status=STATUS_ERROR,
            output_text="",
            model=request.model,
            provider=request.provider,
            latency_ms=_elapsed_ms(started_at),
            raw_summary={
                "provider": request.provider,
                "purpose": request.purpose,
            },
            error_code=error_code,
            error_message=error_message,
        )
        if self.fallback_to_mock:
            return await self._fallback_to_mock(request, error_response)
        return error_response

    async def _fallback_to_mock(
        self,
        request: ModelRequest,
        original_response: ModelResponse,
    ) -> ModelResponse:
        mock_provider = self.providers.get(PROVIDER_MOCK)
        if mock_provider is None:
            return original_response

        fallback_request = ModelRequest(
            purpose=request.purpose,
            input_text=request.input_text,
            instruction=request.instruction,
            model=request.model,
            provider=PROVIDER_MOCK,
            temperature=request.temperature,
            timeout_seconds=request.timeout_seconds,
            metadata={
                **request.metadata,
                "fallback_from_provider": request.provider,
                "fallback_error_code": original_response.error_code,
            },
        )
        fallback_response = await mock_provider.generate(fallback_request)
        fallback_response.status = STATUS_FALLBACK
        fallback_response.fallback_used = True
        fallback_response.error_code = original_response.error_code
        fallback_response.error_message = original_response.error_message
        fallback_response.raw_summary = {
            **fallback_response.raw_summary,
            "fallback_from_provider": request.provider,
            "fallback_reason": original_response.error_code,
        }
        return fallback_response


def _elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 3)
