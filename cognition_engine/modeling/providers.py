from __future__ import annotations

import asyncio
import os
import time
from typing import Protocol

from .contracts import (
    DEFAULT_OLLAMA_MODEL,
    PROVIDER_ADK_LITELLM_OLLAMA,
    PROVIDER_MOCK,
    STATUS_ERROR,
    STATUS_SUCCESS,
    ModelRequest,
    ModelResponse,
)


class ModelProvider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse:
        ...


class MockModelProvider:
    async def generate(self, request: ModelRequest) -> ModelResponse:
        started_at = time.perf_counter()
        instruction = request.instruction.strip() or "No instruction supplied."
        input_text = request.input_text.strip() or "No input supplied."
        output_text = (
            f"[mock:{request.purpose}] instruction={instruction} | input={input_text}"
        )

        return ModelResponse(
            status=STATUS_SUCCESS,
            output_text=output_text,
            model=request.model or "mock",
            provider=PROVIDER_MOCK,
            latency_ms=_elapsed_ms(started_at),
            raw_summary={
                "provider": PROVIDER_MOCK,
                "purpose": request.purpose,
                "input_length": len(request.input_text),
                "instruction_length": len(request.instruction),
            },
        )


class AdkLiteLlmOllamaProvider:
    async def generate(self, request: ModelRequest) -> ModelResponse:
        started_at = time.perf_counter()
        model_name = (
            request.model
            if request.model and request.model != "mock"
            else DEFAULT_OLLAMA_MODEL
        )
        litellm_model = _as_ollama_chat_model(model_name)
        ollama_api_base = os.environ.setdefault(
            "OLLAMA_API_BASE",
            "http://127.0.0.1:11434",
        )

        try:
            output_text, raw_summary = await asyncio.wait_for(
                self._run_adk_chain(request, litellm_model, ollama_api_base),
                timeout=request.timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            return ModelResponse(
                status=STATUS_ERROR,
                output_text="",
                model=litellm_model,
                provider=PROVIDER_ADK_LITELLM_OLLAMA,
                latency_ms=_elapsed_ms(started_at),
                raw_summary={
                    "provider": PROVIDER_ADK_LITELLM_OLLAMA,
                    "model": litellm_model,
                    "ollama_api_base": ollama_api_base,
                },
                error_code=type(exc).__name__,
                error_message=str(exc),
            )

        return ModelResponse(
            status=STATUS_SUCCESS,
            output_text=output_text,
            model=litellm_model,
            provider=PROVIDER_ADK_LITELLM_OLLAMA,
            latency_ms=_elapsed_ms(started_at),
            raw_summary=raw_summary,
        )

    async def _run_adk_chain(
        self,
        request: ModelRequest,
        litellm_model: str,
        ollama_api_base: str,
    ) -> tuple[str, dict[str, object]]:
        from google.adk.agents import LlmAgent
        from google.adk.models.lite_llm import LiteLlm
        from google.adk.runners import Runner
        from google.adk.sessions.in_memory_session_service import (
            InMemorySessionService,
        )
        from google.genai import types

        model = LiteLlm(model=litellm_model)
        agent = LlmAgent(
            name="ce_modeling_ollama_agent",
            model=model,
            instruction=request.instruction,
            mode="chat",
        )
        session_service = InMemorySessionService()
        runner = Runner(
            app_name="cognition_engine_modeling",
            agent=agent,
            session_service=session_service,
        )
        session = await session_service.create_session(
            app_name="cognition_engine_modeling",
            user_id="cognition-engine-modeling-user",
        )
        message = types.Content(
            role="user",
            parts=[types.Part(text=request.input_text)],
        )

        events = []
        texts: list[str] = []
        async for event in runner.run_async(
            user_id="cognition-engine-modeling-user",
            session_id=session.id,
            new_message=message,
        ):
            events.append(event)
            texts.extend(_extract_text_parts(event))

        output_text = "\n".join(text for text in texts if text).strip()
        if not output_text:
            raise RuntimeError("ADK LiteLlm Ollama provider returned no text.")

        return output_text, {
            "provider": PROVIDER_ADK_LITELLM_OLLAMA,
            "model": litellm_model,
            "ollama_api_base": ollama_api_base,
            "selected_runtime_path": (
                "LiteLlm -> LlmAgent -> Runner -> InMemorySessionService"
            ),
            "event_count": len(events),
            "text_count": len(texts),
        }


def build_default_providers() -> dict[str, ModelProvider]:
    return {
        PROVIDER_MOCK: MockModelProvider(),
        PROVIDER_ADK_LITELLM_OLLAMA: AdkLiteLlmOllamaProvider(),
    }


def _as_ollama_chat_model(model_name: str) -> str:
    if model_name.startswith("ollama_chat/"):
        return model_name
    return f"ollama_chat/{model_name}"


def _elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 3)


def _extract_text_parts(event: object) -> list[str]:
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) or []
    texts: list[str] = []
    for part in parts:
        text = getattr(part, "text", None)
        if text:
            texts.append(text)
    return texts
