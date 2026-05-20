"""Internal controlled run facade for runtime-container service execution."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from contract_core.llm_invocation import GovernedLlmInvocationService

from runtime_container.controlled_adk_run_entry import (
    ControlledAdkRunRequest,
    run_productized_controlled_adk_run,
)
from runtime_container.controlled_adk_run_request_builder import (
    ControlledAdkRunRequestBuildInput,
    build_controlled_adk_run_request_from_registry,
)
from runtime_container.workflow_registry import (
    WorkflowRegistry,
    build_default_workflow_registry,
)

DEFAULT_CONTROLLED_RUN_WORKFLOW_ID = "workflow-controlled-adk-run"
DEFAULT_CONTROLLED_RUN_WORKFLOW_NAME = "controlled-adk-run"

ControlledRunEntryRunner = Callable[[ControlledAdkRunRequest], Mapping[str, Any]]

_FORBIDDEN_RAW_KEYS = frozenset(
    {
        "adk_object",
        "artifact_content",
        "credential",
        "function_tool",
        "live_model_payload",
        "message",
        "messages",
        "payload",
        "prompt",
        "provider_payload",
        "provider_response",
        "raw",
        "raw_adk_object",
        "raw_api_payload",
        "raw_input",
        "raw_output",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_provider_response",
        "raw_response",
        "raw_tool_input",
        "raw_tool_output",
        "raw_user_message",
        "response",
        "response_text",
        "secret",
        "token",
        "tool_context",
        "tool_input",
        "tool_output",
        "user_message",
    }
)
_FORBIDDEN_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "litellm",
)


@dataclass(frozen=True)
class ControlledRunFacadeInput:
    """Runtime-container owned input for the controlled run facade."""

    runtime_id: str
    config_root: Path = Path("config")
    environment: str = "local"
    profile: str | None = None
    invocation_id: str | None = None
    workflow_id: str = DEFAULT_CONTROLLED_RUN_WORKFLOW_ID
    workflow_name: str = DEFAULT_CONTROLLED_RUN_WORKFLOW_NAME
    input_payload: Mapping[str, Any] | None = None
    operator_approved: bool = False
    approval_ref: str | None = None
    audit_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    governance_summary_output_ref: str | None = None
    request_live_llm: bool = False
    request_ollama: bool = False
    allow_live_llm: bool = False
    allow_ollama: bool = False
    live_llm_approval_ref: str | None = None
    allow_tool_confirmation: bool | None = None
    tool_confirmation_approval_ref: str | None = None
    tool_confirmation_decision_source: str | None = None
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ControlledRunFacadeResult:
    """Runtime-container owned narrow output for the controlled run facade."""

    runtime_id: str | None = None
    invocation_id: str | None = None
    workflow_id: str | None = None
    execution_mode: str | None = None
    status: str = "failed"
    controlled_run: bool = False
    productized_controlled_run: bool = False
    sanitized: bool = True
    adk_run_allowed: bool = False
    adk_run_performed: bool = False
    execution_performed: bool = False
    live_llm_allowed: bool = False
    live_llm_call_performed: bool = False
    ollama_allowed: bool = False
    ollama_call_performed: bool = False
    llm_invocation_call_allowed: bool | None = None
    llm_invocation_call_attempted: bool | None = None
    llm_invocation_runtime_call_performed: bool | None = None
    llm_invocation_failure_type: str | None = None
    tool_runtime_call_performed: bool | None = None
    tool_status: str | None = None
    tool_failure_type: str | None = None
    observability_source: str | None = None
    sanitized_evidence_ref: str | None = None
    audit_ref: str | None = None
    governance_summary_payload_ref: str | None = None
    governance_summary_output_ref: str | None = None
    tool_evidence_ref: str | None = None
    tool_run_ref: str | None = None
    llm_invocation_result_ref: str | None = None
    llm_invocation_observation_ref: str | None = None
    llm_invocation_summary_ref: str | None = None
    sanitized_response_display: str | None = None
    sanitized_response_preview: str | None = None
    final_preflight: Mapping[str, Any] | None = None
    controlled_live_llm_preflight: Mapping[str, Any] | None = None
    lifecycle_facts: Mapping[str, Any] | None = None
    run_config_service_bundle_facts: Mapping[str, Any] | None = None
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @classmethod
    def from_entry_result(
        cls,
        entry_result: Mapping[str, Any],
    ) -> "ControlledRunFacadeResult":
        """Build the narrow facade result from the sanitized entry result."""

        blocking_reasons = tuple(_string_items(entry_result.get("blocking_reasons")))
        execution_performed = bool(entry_result.get("execution_performed", False))
        adk_run_performed = bool(entry_result.get("adk_run_performed", False))
        status = _facade_status(
            blocking_reasons=blocking_reasons,
            execution_performed=execution_performed,
            adk_run_performed=adk_run_performed,
        )

        return cls(
            runtime_id=_optional_text(entry_result.get("runtime_id")),
            invocation_id=_optional_text(entry_result.get("invocation_id")),
            workflow_id=_optional_text(entry_result.get("workflow_id")),
            execution_mode=_optional_text(entry_result.get("execution_mode")),
            status=status,
            controlled_run=bool(entry_result.get("controlled_run", False)),
            productized_controlled_run=bool(
                entry_result.get("productized_controlled_run", False)
            ),
            sanitized=bool(entry_result.get("sanitized", True)),
            adk_run_allowed=bool(entry_result.get("adk_run_allowed", False)),
            adk_run_performed=adk_run_performed,
            execution_performed=execution_performed,
            live_llm_allowed=bool(entry_result.get("live_llm_allowed", False)),
            live_llm_call_performed=bool(
                entry_result.get("live_llm_call_performed", False)
            ),
            ollama_allowed=bool(entry_result.get("ollama_allowed", False)),
            ollama_call_performed=bool(
                entry_result.get("ollama_call_performed", False)
            ),
            llm_invocation_call_allowed=_optional_bool(
                entry_result.get("llm_invocation_call_allowed")
            ),
            llm_invocation_call_attempted=_optional_bool(
                entry_result.get("llm_invocation_call_attempted")
            ),
            llm_invocation_runtime_call_performed=_optional_bool(
                entry_result.get("llm_invocation_runtime_call_performed")
            ),
            llm_invocation_failure_type=_optional_text(
                entry_result.get("llm_invocation_failure_type")
            ),
            tool_runtime_call_performed=_optional_bool(
                entry_result.get("tool_runtime_call_performed")
            ),
            tool_status=_optional_text(entry_result.get("tool_status")),
            tool_failure_type=_optional_text(entry_result.get("tool_failure_type")),
            observability_source=_optional_text(
                entry_result.get("observability_source")
            ),
            sanitized_evidence_ref=_optional_text(
                entry_result.get("sanitized_evidence_ref")
            ),
            audit_ref=_optional_text(entry_result.get("audit_ref")),
            governance_summary_payload_ref=_optional_text(
                entry_result.get("governance_summary_payload_ref")
            ),
            governance_summary_output_ref=_optional_text(
                entry_result.get("governance_summary_output_ref")
            ),
            tool_evidence_ref=_optional_text(entry_result.get("tool_evidence_ref")),
            tool_run_ref=_optional_text(entry_result.get("tool_run_ref")),
            llm_invocation_result_ref=_optional_text(
                entry_result.get("llm_invocation_result_ref")
            ),
            llm_invocation_observation_ref=_optional_text(
                entry_result.get("llm_invocation_observation_ref")
            ),
            llm_invocation_summary_ref=_optional_text(
                entry_result.get("llm_invocation_summary_ref")
            ),
            sanitized_response_display=_sanitized_response_display(entry_result),
            sanitized_response_preview=_sanitized_response_preview(entry_result),
            final_preflight=_optional_mapping(entry_result.get("final_preflight")),
            controlled_live_llm_preflight=_optional_mapping(
                entry_result.get("controlled_live_llm_preflight")
            ),
            lifecycle_facts=_optional_mapping(entry_result.get("lifecycle_facts")),
            run_config_service_bundle_facts=_optional_mapping(
                entry_result.get("run_config_service_bundle_facts")
            ),
            blocking_reasons=blocking_reasons,
            warnings=tuple(_string_items(entry_result.get("warnings"))),
        )

    def to_mapping(self) -> dict[str, Any]:
        """Return a sanitized, narrow mapping for diagnostics."""

        result: dict[str, Any] = {
            "runtime_id": self.runtime_id,
            "invocation_id": self.invocation_id,
            "workflow_id": self.workflow_id,
            "execution_mode": self.execution_mode,
            "status": self.status,
            "controlled_run": self.controlled_run,
            "productized_controlled_run": self.productized_controlled_run,
            "sanitized": self.sanitized,
            "adk_run_allowed": self.adk_run_allowed,
            "adk_run_performed": self.adk_run_performed,
            "execution_performed": self.execution_performed,
            "live_llm_allowed": self.live_llm_allowed,
            "live_llm_call_performed": self.live_llm_call_performed,
            "ollama_allowed": self.ollama_allowed,
            "ollama_call_performed": self.ollama_call_performed,
            "tool_status": self.tool_status,
            "tool_failure_type": self.tool_failure_type,
            "tool_runtime_call_performed": self.tool_runtime_call_performed,
            "observability_source": self.observability_source,
            "sanitized_evidence_ref": self.sanitized_evidence_ref,
            "audit_ref": self.audit_ref,
            "governance_summary_payload_ref": self.governance_summary_payload_ref,
            "governance_summary_output_ref": self.governance_summary_output_ref,
            "tool_evidence_ref": self.tool_evidence_ref,
            "tool_run_ref": self.tool_run_ref,
            "llm_invocation_result_ref": self.llm_invocation_result_ref,
            "llm_invocation_observation_ref": self.llm_invocation_observation_ref,
            "llm_invocation_summary_ref": self.llm_invocation_summary_ref,
            "sanitized_response_display": self.sanitized_response_display,
            "sanitized_response_preview": self.sanitized_response_preview,
            "final_preflight": self.final_preflight,
            "controlled_live_llm_preflight": self.controlled_live_llm_preflight,
            "lifecycle_facts": self.lifecycle_facts,
            "run_config_service_bundle_facts": self.run_config_service_bundle_facts,
            "blocking_reasons": list(self.blocking_reasons),
            "warnings": list(self.warnings),
        }
        optional_fields = {
            "llm_invocation_call_allowed": self.llm_invocation_call_allowed,
            "llm_invocation_call_attempted": self.llm_invocation_call_attempted,
            "llm_invocation_runtime_call_performed": (
                self.llm_invocation_runtime_call_performed
            ),
            "llm_invocation_failure_type": self.llm_invocation_failure_type,
        }
        result.update(
            {key: value for key, value in optional_fields.items() if value is not None}
        )
        return {key: value for key, value in result.items() if value is not None}


def coerce_controlled_run_facade_input(
    value: ControlledRunFacadeInput | Mapping[str, Any],
) -> ControlledRunFacadeInput:
    """Coerce a product-level mapping into a sanitized facade input."""

    if isinstance(value, ControlledRunFacadeInput):
        raw_value: Mapping[str, Any] = {
            "runtime_id": value.runtime_id,
            "config_root": value.config_root,
            "environment": value.environment,
            "profile": value.profile,
            "invocation_id": value.invocation_id,
            "workflow_id": value.workflow_id,
            "workflow_name": value.workflow_name,
            "input_payload": value.input_payload,
            "operator_approved": value.operator_approved,
            "approval_ref": value.approval_ref,
            "audit_ref": value.audit_ref,
            "sanitized_evidence_ref": value.sanitized_evidence_ref,
            "governance_summary_output_ref": value.governance_summary_output_ref,
            "request_live_llm": value.request_live_llm,
            "request_ollama": value.request_ollama,
            "allow_live_llm": value.allow_live_llm,
            "allow_ollama": value.allow_ollama,
            "live_llm_approval_ref": value.live_llm_approval_ref,
            "allow_tool_confirmation": value.allow_tool_confirmation,
            "tool_confirmation_approval_ref": (
                value.tool_confirmation_approval_ref
            ),
            "tool_confirmation_decision_source": (
                value.tool_confirmation_decision_source
            ),
            "metadata": value.metadata,
        }
    else:
        raw_value = value

    runtime_id = _required_text(raw_value, "runtime_id")
    invocation_id = _optional_text(raw_value.get("invocation_id")) or f"inv-{runtime_id}"
    input_payload = _sanitized_mapping(
        raw_value.get("input_payload"),
        field_name="input_payload",
    )
    metadata = _sanitized_mapping(
        raw_value.get("metadata"),
        field_name="metadata",
    )

    return ControlledRunFacadeInput(
        runtime_id=runtime_id,
        config_root=Path(raw_value.get("config_root") or "config"),
        environment=str(raw_value.get("environment") or "local"),
        profile=_optional_text(raw_value.get("profile")),
        invocation_id=invocation_id,
        workflow_id=str(
            raw_value.get("workflow_id") or DEFAULT_CONTROLLED_RUN_WORKFLOW_ID
        ),
        workflow_name=str(
            raw_value.get("workflow_name") or DEFAULT_CONTROLLED_RUN_WORKFLOW_NAME
        ),
        input_payload=input_payload,
        operator_approved=bool(raw_value.get("operator_approved", False)),
        approval_ref=_optional_text(raw_value.get("approval_ref")),
        audit_ref=_optional_text(raw_value.get("audit_ref")),
        sanitized_evidence_ref=_optional_text(
            raw_value.get("sanitized_evidence_ref")
        ),
        governance_summary_output_ref=_optional_text(
            raw_value.get("governance_summary_output_ref")
        ),
        request_live_llm=bool(raw_value.get("request_live_llm", False)),
        request_ollama=bool(raw_value.get("request_ollama", False)),
        allow_live_llm=bool(raw_value.get("allow_live_llm", False)),
        allow_ollama=bool(raw_value.get("allow_ollama", False)),
        live_llm_approval_ref=_optional_text(raw_value.get("live_llm_approval_ref")),
        allow_tool_confirmation=_optional_bool(
            raw_value.get("allow_tool_confirmation")
        ),
        tool_confirmation_approval_ref=_optional_text(
            raw_value.get("tool_confirmation_approval_ref")
        ),
        tool_confirmation_decision_source=_optional_text(
            raw_value.get("tool_confirmation_decision_source")
        ),
        metadata=metadata,
    )


def build_controlled_run_request_from_facade_input(
    facade_input: ControlledRunFacadeInput | Mapping[str, Any],
    *,
    workflow_registry: WorkflowRegistry | None = None,
    llm_invocation_service: GovernedLlmInvocationService | None = None,
    agent_shell_live_client: Any | None = None,
) -> ControlledAdkRunRequest:
    """Build a controlled ADK run request from the facade input."""

    normalized_input = coerce_controlled_run_facade_input(facade_input)
    build_input = ControlledAdkRunRequestBuildInput(
        config_root=normalized_input.config_root,
        environment=normalized_input.environment,
        profile=normalized_input.profile,
        runtime_id=normalized_input.runtime_id,
        invocation_id=normalized_input.invocation_id or f"inv-{normalized_input.runtime_id}",
        workflow_id=normalized_input.workflow_id,
        workflow_name=normalized_input.workflow_name,
        input_payload=dict(normalized_input.input_payload or {}),
        operator_approved=normalized_input.operator_approved,
        approval_ref=normalized_input.approval_ref,
        audit_ref=normalized_input.audit_ref,
        sanitized_evidence_ref=normalized_input.sanitized_evidence_ref,
        governance_summary_output_ref=normalized_input.governance_summary_output_ref,
        request_live_llm=normalized_input.request_live_llm,
        request_ollama=normalized_input.request_ollama,
        allow_live_llm=normalized_input.allow_live_llm,
        allow_ollama=normalized_input.allow_ollama,
        live_llm_approval_ref=normalized_input.live_llm_approval_ref,
        allow_tool_confirmation=normalized_input.allow_tool_confirmation,
        tool_confirmation_approval_ref=(
            normalized_input.tool_confirmation_approval_ref
        ),
        tool_confirmation_decision_source=(
            normalized_input.tool_confirmation_decision_source
        ),
        evidence_id=f"controlled-run-facade-{normalized_input.runtime_id}",
        llm_invocation_service=(
            llm_invocation_service or _default_llm_invocation_service()
        ),
        agent_shell_live_client=agent_shell_live_client,
    )
    return build_controlled_adk_run_request_from_registry(
        build_input=build_input,
        workflow_registry=workflow_registry or _default_workflow_registry(),
    )


def run_controlled_run_facade(
    facade_input: ControlledRunFacadeInput | Mapping[str, Any],
    *,
    workflow_registry: WorkflowRegistry | None = None,
    llm_invocation_service: GovernedLlmInvocationService | None = None,
    agent_shell_live_client: Any | None = None,
    entry_runner: ControlledRunEntryRunner = run_productized_controlled_adk_run,
) -> ControlledRunFacadeResult:
    """Run a controlled request through the runtime-container public facade."""

    request = build_controlled_run_request_from_facade_input(
        facade_input,
        workflow_registry=workflow_registry,
        llm_invocation_service=llm_invocation_service,
        agent_shell_live_client=agent_shell_live_client,
    )
    return ControlledRunFacadeResult.from_entry_result(dict(entry_runner(request)))


def _default_workflow_registry() -> WorkflowRegistry:
    from composition.controlled_adk_run_provider import (
        build_controlled_adk_run_runtime_assembly_provider,
    )

    return build_default_workflow_registry(
        runtime_assembly_provider=(
            build_controlled_adk_run_runtime_assembly_provider()
        )
    )


def _default_llm_invocation_service() -> GovernedLlmInvocationService:
    from composition.llm_invocation_assembly import (
        build_adk_governed_llm_invocation_service,
    )

    return build_adk_governed_llm_invocation_service()


def _required_text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if item is None:
        raise ValueError(f"{key} is required.")
    text = str(item)
    if not text:
        raise ValueError(f"{key} is required.")
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _optional_mapping(value: Any) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        return None
    return dict(value)


def _sanitized_response_display(entry_result: Mapping[str, Any]) -> str | None:
    value = _find_nested_text(entry_result, "sanitized_response_display")
    return _optional_text(value)


def _sanitized_response_preview(entry_result: Mapping[str, Any]) -> str | None:
    value = _find_nested_text(entry_result, "sanitized_response_preview")
    return _optional_text(value)


def _find_nested_text(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        item = value.get(key)
        if isinstance(item, str) and item.strip():
            return item
        for nested in value.values():
            found = _find_nested_text(nested, key)
            if found is not None:
                return found
    elif isinstance(value, (list, tuple)):
        for nested in value:
            found = _find_nested_text(nested, key)
            if found is not None:
                return found
    return None


def _string_items(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [str(value)]


def _facade_status(
    *,
    blocking_reasons: tuple[str, ...],
    execution_performed: bool,
    adk_run_performed: bool,
) -> str:
    if blocking_reasons:
        return "blocked"
    if execution_performed or adk_run_performed:
        return "success"
    return "failed"


def _sanitized_mapping(value: Any, *, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping.")
    result = dict(value)
    _raise_if_raw_payload_found(result, field_name=field_name)
    return result


def _raise_if_raw_payload_found(value: Any, *, field_name: str) -> None:
    violations = [
        f"{field_name} contains forbidden raw payload at {path}."
        for path, item in _walk(value)
        if _is_raw_payload(path, item)
    ]
    if violations:
        raise ValueError("; ".join(violations))


def _walk(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, dict):
        for key, item in value.items():
            items.extend(_walk(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            items.extend(_walk(item, f"{path}[{index}]"))
    return items


def _is_raw_payload(path: str, value: Any) -> bool:
    key = path.rsplit(".", maxsplit=1)[-1].lower()
    if key in _FORBIDDEN_RAW_KEYS:
        return True
    if isinstance(value, dict):
        module_name = value.get("object_module")
        return isinstance(module_name, str) and module_name.startswith(
            _FORBIDDEN_MODULE_PREFIXES
        )
    if value is None or isinstance(value, (str, int, float, bool, list, tuple, dict)):
        return False
    return type(value).__module__.startswith(_FORBIDDEN_MODULE_PREFIXES)


__all__ = [
    "ControlledRunEntryRunner",
    "ControlledRunFacadeInput",
    "ControlledRunFacadeResult",
    "DEFAULT_CONTROLLED_RUN_WORKFLOW_ID",
    "DEFAULT_CONTROLLED_RUN_WORKFLOW_NAME",
    "build_controlled_run_request_from_facade_input",
    "coerce_controlled_run_facade_input",
    "run_controlled_run_facade",
]
