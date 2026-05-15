"""Publishable no-live verification entry for the runtime-container facade."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from typing import Any

from contract_core.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from contract_core.model_routing import ModelRouteFacts
from runtime_container.llm_invocation_facade import (
    RuntimeContainerLlmInvocationFacade,
    build_runtime_container_llm_invocation_request,
)


DEFAULT_REQUEST_ID = "runtime-container-no-live-dev-entry-request"
DEFAULT_MODEL_NAME = "ollama/gemma4-pro:latest"
ENTRY_KIND = "runtime_container_dev_entry_no_live_verification"


class _NoLiveFixtureService:
    """Entry-local fixture service; never performs a model call."""

    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        """Return a fixed no-live result through the facade boundary."""

        return LlmInvocationResult(
            request_id=request.request_id,
            route_facts=request.route_facts,
            governance_precondition=request.governance_precondition,
            call_attempted=False,
            call_allowed=request.governance_precondition.allowed,
            runtime_call_performed=False,
            success=False,
            response_non_empty=False,
            failure_type=LlmInvocationFailureType.LIVE_DISABLED,
            error_message_sanitized="no-live verification entry does not call models",
            metadata={
                "entry_kind": ENTRY_KIND,
                "fixture_service": "_NoLiveFixtureService",
                "facade_only": True,
                "dev_only": True,
            },
        )


def build_no_live_verification_payload(
    *,
    request_id: str = DEFAULT_REQUEST_ID,
    model_name: str = DEFAULT_MODEL_NAME,
) -> dict[str, Any]:
    """Run the no-live facade verification and return sanitized JSON data."""

    request = build_runtime_container_llm_invocation_request(
        request_id=request_id,
        route_facts=_route_facts(model_name),
        governance_precondition=_governance_precondition(),
        prompt_ref="dev-entry-placeholder",
        prompt_preview_sanitized="no-live placeholder",
        metadata={
            "entry_kind": ENTRY_KIND,
            "facade_only": True,
            "dev_only": True,
        },
    )
    facade = RuntimeContainerLlmInvocationFacade(
        service=_NoLiveFixtureService(),
        metadata={
            "entry_kind": ENTRY_KIND,
            "facade_only": True,
            "dev_only": True,
        },
    )
    result = facade.run(request)
    return _result_payload(result)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the no-live verification entry and print sanitized JSON."""

    parser = argparse.ArgumentParser(
        description="Run runtime_container no-live facade verification.",
    )
    parser.add_argument("--request-id", default=DEFAULT_REQUEST_ID)
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    payload = build_no_live_verification_payload(
        request_id=args.request_id,
        model_name=args.model_name,
    )
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
    )
    return 0


def _route_facts(model_name: str) -> ModelRouteFacts:
    return ModelRouteFacts(
        model_name=model_name,
        provider="litellm",
        source="runtime_container.dev_entry.no_live_llm_invocation",
        metadata={
            "backend_provider": "ollama",
            "route_target": model_name,
            "route_kind": "adk_litellm",
            "entry_kind": ENTRY_KIND,
            "facade_only": True,
            "dev_only": True,
        },
    )


def _governance_precondition() -> LlmGovernancePrecondition:
    return LlmGovernancePrecondition(
        allowed=True,
        reason="no_live_verification_entry_allowed",
        decision="continue",
        governance_decision_ref="dev-entry-governance-fixture",
        metadata={
            "entry_kind": ENTRY_KIND,
            "facade_only": True,
            "dev_only": True,
        },
    )


def _result_payload(result: LlmInvocationResult) -> dict[str, Any]:
    route_metadata = result.route_facts.metadata
    failure_type = result.failure_type.value if result.failure_type else None
    return {
        "entry": {
            "kind": ENTRY_KIND,
            "facade_only": True,
            "dev_only": True,
            "product_cli": False,
        },
        "request_id": result.request_id,
        "success": result.success,
        "call_attempted": result.call_attempted,
        "call_allowed": result.call_allowed,
        "runtime_call_performed": result.runtime_call_performed,
        "failure_type": failure_type,
        "error_message_sanitized": result.error_message_sanitized,
        "sanitized_response_preview": result.sanitized_response_preview,
        "sanitized_response_length": result.sanitized_response_length,
        "route": {
            "model_name": result.route_facts.model_name,
            "provider": result.route_facts.provider,
            "backend_provider": route_metadata.get("backend_provider"),
            "route_kind": route_metadata.get("route_kind"),
            "route_target": route_metadata.get("route_target"),
        },
        "governance": {
            "allowed": result.governance_precondition.allowed,
            "decision": result.governance_precondition.decision,
            "reason": result.governance_precondition.reason,
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
