from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from schemas.model_routing import ModelRouteFacts


REPO_ROOT = Path(__file__).resolve().parents[3]
LLM_INVOCATION_ROOT = (
    REPO_ROOT / "packages" / "schemas" / "src" / "schemas" / "llm_invocation"
)


def test_llm_invocation_request_requires_route_facts_and_governance() -> None:
    request = LlmInvocationRequest(
        request_id="llm-request-1",
        route_facts=_route_facts(),
        governance_precondition=_governance_precondition(allowed=True),
        prompt_ref="prompt-ref-1",
        prompt_preview_sanitized="sanitized short prompt summary",
        metadata={"purpose": "contract_test"},
    )

    assert request.route_facts.provider == "litellm"
    assert request.route_facts.runtime_call_performed is False
    assert request.governance_precondition.allowed is True
    assert "prompt" not in request.metadata


def test_llm_invocation_result_can_represent_governance_block_without_call() -> None:
    result = LlmInvocationResult(
        request_id="llm-request-1",
        route_facts=_route_facts(),
        governance_precondition=_governance_precondition(allowed=False),
        call_attempted=False,
        call_allowed=False,
        runtime_call_performed=False,
        success=False,
        failure_type=LlmInvocationFailureType.GOVERNANCE_BLOCKED,
        error_message_sanitized="blocked before model call",
    )

    assert result.failure_type == LlmInvocationFailureType.GOVERNANCE_BLOCKED
    assert result.runtime_call_performed is False


def test_llm_invocation_result_can_represent_sanitized_success() -> None:
    result = LlmInvocationResult(
        request_id="llm-request-1",
        route_facts=_route_facts(),
        governance_precondition=_governance_precondition(allowed=True),
        call_attempted=True,
        call_allowed=True,
        runtime_call_performed=True,
        success=True,
        response_non_empty=True,
        sanitized_response_length=2,
        sanitized_response_preview="你好",
        latency_ms=42,
    )

    assert result.success is True
    assert result.failure_type is None
    assert result.sanitized_response_preview == "你好"


@pytest.mark.parametrize(
    "metadata",
    [
        {"prompt": "raw prompt"},
        {"messages": [{"role": "user", "content": "raw"}]},
        {"raw_provider_response": {"choices": []}},
        {"nested": {"object_module": "litellm.main"}},
    ],
)
def test_llm_invocation_contracts_reject_raw_payload_metadata(
    metadata: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        LlmInvocationRequest(
            request_id="llm-request-1",
            route_facts=_route_facts(),
            governance_precondition=_governance_precondition(allowed=True),
            metadata=metadata,
        )


def test_llm_invocation_result_rejects_success_without_runtime_call() -> None:
    with pytest.raises(ValidationError):
        LlmInvocationResult(
            request_id="llm-request-1",
            route_facts=_route_facts(),
            governance_precondition=_governance_precondition(allowed=True),
            call_attempted=True,
            call_allowed=True,
            runtime_call_performed=False,
            success=True,
        )


def test_llm_invocation_schemas_do_not_import_adapter_or_model_libraries() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+(?:adk_adapter|google\.adk|litellm)\b",
        re.MULTILINE,
    )

    for source_path in LLM_INVOCATION_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path


def _route_facts() -> ModelRouteFacts:
    return ModelRouteFacts(
        model_name="ollama/gemma4-pro:latest",
        provider="litellm",
        source="adk_adapter.models",
        metadata={
            "backend_provider": "ollama",
            "route_target": "ollama/gemma4-pro:latest",
            "route_kind": "adk_litellm",
        },
    )


def _governance_precondition(*, allowed: bool) -> LlmGovernancePrecondition:
    return LlmGovernancePrecondition(
        allowed=allowed,
        reason="governance_allowed" if allowed else "governance_blocked",
        decision="continue" if allowed else "block",
        governance_decision_ref="governance-decision-1",
        metadata={"policy_refs": ["policy.llm.precondition"]},
    )
