"""ADK native FunctionTool service helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from types import SimpleNamespace
from typing import Any, Callable
from uuid import uuid4

from google.adk.tools import FunctionTool
from google.adk.tools.tool_confirmation import ToolConfirmation


@dataclass(frozen=True)
class AdkFunctionToolOptions:
    """Local options for constructing an ADK native FunctionTool."""

    tool_name: str
    tool_kind: str = "function"
    require_confirmation: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        """Return sanitized FunctionTool option metadata."""

        return {
            "options_type": "adk_adapter.tool_service.AdkFunctionToolOptions",
            "tool_name": self.tool_name,
            "tool_kind": self.tool_kind,
            "require_confirmation": self.require_confirmation,
            "metadata_keys": sorted(self.metadata),
        }


@dataclass(frozen=True)
class AdkControlledToolOptions:
    """Controlled execution options for an ADK FunctionTool call."""

    tool_call_allowed: bool = True
    blocked_failure_type: str = "tool_call_not_allowed"
    confirmation_granted: bool | None = None
    tool_approval_ref: str | None = None
    confirmation_decision_source: str | None = None
    session_id: str | None = None
    tool_run_id: str | None = None
    artifact_delta_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        """Return sanitized controlled tool option metadata."""

        return {
            "options_type": "adk_adapter.tool_service.AdkControlledToolOptions",
            "tool_call_allowed": self.tool_call_allowed,
            "blocked_failure_type": self.blocked_failure_type,
            "confirmation_granted": self.confirmation_granted,
            "tool_approval_ref": self.tool_approval_ref,
            "confirmation_decision_source": self.confirmation_decision_source,
            "session_id_present": self.session_id is not None,
            "tool_run_id_present": self.tool_run_id is not None,
            "artifact_delta_ref_count": len(self.artifact_delta_refs),
            "metadata_keys": sorted(self.metadata),
        }


@dataclass(frozen=True)
class AdkToolCallResult:
    """Sanitized result for one ADK FunctionTool call."""

    tool_name: str
    tool_kind: str
    tool_call_allowed: bool
    tool_call_attempted: bool
    tool_runtime_call_performed: bool
    tool_confirmation_required: bool
    tool_confirmation_granted: bool
    adk_tool_confirmation_requested: bool
    tool_approval_ref: str | None
    tool_confirmation_decision_source: str | None
    tool_input_summary: dict[str, Any]
    tool_output_summary: dict[str, Any]
    tool_failure_type: str | None
    tool_run_ref: str
    session_id: str | None = None
    artifact_delta_refs: tuple[str, ...] = ()
    readonly_facts_embedded: bool = False
    does_not_store_raw_tool_input: bool = True
    does_not_store_raw_tool_output: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_observability_input(self) -> dict[str, Any]:
        """Return a sanitized plain shape for observability-hub intake."""

        return {
            "source": "adk_adapter.tool_service",
            "tool_name": self.tool_name,
            "tool_kind": self.tool_kind,
            "tool_call_allowed": self.tool_call_allowed,
            "tool_call_attempted": self.tool_call_attempted,
            "tool_runtime_call_performed": self.tool_runtime_call_performed,
            "tool_confirmation_required": self.tool_confirmation_required,
            "tool_confirmation_granted": self.tool_confirmation_granted,
            "adk_tool_confirmation_requested": (
                self.adk_tool_confirmation_requested
            ),
            "tool_approval_ref": self.tool_approval_ref,
            "tool_confirmation_decision_source": (
                self.tool_confirmation_decision_source
            ),
            "tool_input_summary": dict(self.tool_input_summary),
            "tool_output_summary": dict(self.tool_output_summary),
            "tool_failure_type": self.tool_failure_type,
            "tool_run_ref": self.tool_run_ref,
            "session_id": self.session_id,
            "artifact_delta_refs": list(self.artifact_delta_refs),
            "readonly_facts_embedded": self.readonly_facts_embedded,
            "does_not_store_raw_tool_input": self.does_not_store_raw_tool_input,
            "does_not_store_raw_tool_output": self.does_not_store_raw_tool_output,
            "metadata": dict(self.metadata),
        }


def create_adk_function_tool(
    func: Callable[..., Any],
    *,
    options: AdkFunctionToolOptions | None = None,
) -> FunctionTool:
    """Create an ADK native FunctionTool from a callable."""

    tool = FunctionTool(
        func,
        require_confirmation=options.require_confirmation if options else False,
    )
    if options is not None:
        if tool.name != options.tool_name:
            raise ValueError(
                "FunctionTool name must match AdkFunctionToolOptions.tool_name."
            )
        tool.custom_metadata = options.to_metadata()
    return tool


async def run_adk_function_tool_no_live(
    tool: FunctionTool,
    *,
    args: dict[str, Any],
    tool_options: AdkFunctionToolOptions | None = None,
    controlled_options: AdkControlledToolOptions | None = None,
) -> AdkToolCallResult:
    """Run an ADK FunctionTool through a deterministic no-live boundary."""

    resolved_tool_options = tool_options or _tool_options_from_metadata(tool)
    resolved_controlled_options = controlled_options or AdkControlledToolOptions()
    tool_run_ref = (
        f"adk-function-tool-run://{resolved_controlled_options.tool_run_id}"
        if resolved_controlled_options.tool_run_id
        else f"adk-function-tool-run://{uuid4()}"
    )
    input_summary = _summarize_mapping(args)
    if not resolved_controlled_options.tool_call_allowed:
        return AdkToolCallResult(
            tool_name=tool.name,
            tool_kind=resolved_tool_options.tool_kind,
            tool_call_allowed=False,
            tool_call_attempted=False,
            tool_runtime_call_performed=False,
            tool_confirmation_required=resolved_tool_options.require_confirmation,
            tool_confirmation_granted=False,
            adk_tool_confirmation_requested=False,
            tool_approval_ref=resolved_controlled_options.tool_approval_ref,
            tool_confirmation_decision_source=(
                resolved_controlled_options.confirmation_decision_source
            ),
            tool_input_summary=input_summary,
            tool_output_summary={},
            tool_failure_type=resolved_controlled_options.blocked_failure_type,
            tool_run_ref=tool_run_ref,
            session_id=resolved_controlled_options.session_id,
            artifact_delta_refs=resolved_controlled_options.artifact_delta_refs,
            metadata=_result_metadata(
                resolved_tool_options,
                resolved_controlled_options,
            ),
        )
    if resolved_tool_options.require_confirmation:
        return await _run_adk_function_tool_with_confirmation(
            tool,
            args=args,
            tool_options=resolved_tool_options,
            controlled_options=resolved_controlled_options,
            tool_run_ref=tool_run_ref,
            input_summary=input_summary,
        )
    try:
        result = await tool.run_async(args=args, tool_context=None)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001 - classified as sanitized evidence.
        return AdkToolCallResult(
            tool_name=tool.name,
            tool_kind=resolved_tool_options.tool_kind,
            tool_call_allowed=True,
            tool_call_attempted=True,
            tool_runtime_call_performed=True,
            tool_confirmation_required=resolved_tool_options.require_confirmation,
            tool_confirmation_granted=True,
            adk_tool_confirmation_requested=False,
            tool_approval_ref=resolved_controlled_options.tool_approval_ref,
            tool_confirmation_decision_source=(
                resolved_controlled_options.confirmation_decision_source
            ),
            tool_input_summary=input_summary,
            tool_output_summary={},
            tool_failure_type="tool_runtime_failure",
            tool_run_ref=tool_run_ref,
            session_id=resolved_controlled_options.session_id,
            artifact_delta_refs=resolved_controlled_options.artifact_delta_refs,
            metadata={
                **_result_metadata(
                    resolved_tool_options,
                    resolved_controlled_options,
                ),
                "error_type": type(exc).__name__,
            },
        )
    return AdkToolCallResult(
        tool_name=tool.name,
        tool_kind=resolved_tool_options.tool_kind,
        tool_call_allowed=True,
        tool_call_attempted=True,
        tool_runtime_call_performed=True,
        tool_confirmation_required=resolved_tool_options.require_confirmation,
        tool_confirmation_granted=True,
        adk_tool_confirmation_requested=False,
        tool_approval_ref=resolved_controlled_options.tool_approval_ref,
        tool_confirmation_decision_source=(
            resolved_controlled_options.confirmation_decision_source
        ),
        tool_input_summary=input_summary,
        tool_output_summary=_summarize_output(result),
        tool_failure_type=None,
        tool_run_ref=tool_run_ref,
        session_id=resolved_controlled_options.session_id,
        artifact_delta_refs=resolved_controlled_options.artifact_delta_refs,
        metadata=_result_metadata(
            resolved_tool_options,
            resolved_controlled_options,
        ),
    )


def build_no_live_task_review_function_tool(
    *,
    options: AdkFunctionToolOptions | None = None,
) -> FunctionTool:
    """Build the deterministic no-live task review FunctionTool."""

    resolved_options = options or AdkFunctionToolOptions(
        tool_name="review_task_context",
        tool_kind="deterministic_no_live_task_review",
        require_confirmation=False,
    )
    return create_adk_function_tool(
        review_task_context,
        options=resolved_options,
    )


def build_deterministic_external_echo_function_tool(
    *,
    options: AdkFunctionToolOptions | None = None,
) -> FunctionTool:
    """Build a deterministic low-risk external smoke FunctionTool."""

    resolved_options = options or AdkFunctionToolOptions(
        tool_name="deterministic_external_echo",
        tool_kind="deterministic_low_risk_external_smoke",
        require_confirmation=True,
        metadata={
            "risk_level": "low",
            "external_side_effects": False,
            "smoke_only": True,
        },
    )
    return create_adk_function_tool(
        deterministic_external_echo,
        options=resolved_options,
    )


def review_task_context(
    task_ref: str,
    task_kind: str = "task",
    evidence_ref: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic sanitized review summary for task evidence."""

    return {
        "result_kind": "deterministic_no_live_task_review",
        "task_ref_present": bool(task_ref),
        "task_kind": task_kind,
        "evidence_ref_present": evidence_ref is not None,
        "recommendation": "review_ready",
        "does_not_store_raw_task": True,
    }


def deterministic_external_echo(
    message_ref: str,
    message_kind: str = "smoke",
    echo_label: str | None = None,
) -> dict[str, Any]:
    """Return deterministic low-risk external smoke facts without raw input."""

    return {
        "result_kind": "deterministic_external_echo",
        "message_ref_present": bool(message_ref),
        "message_kind": message_kind,
        "echo_label_present": echo_label is not None,
        "recommendation": "external_tool_smoke_ready",
        "external_side_effects": False,
        "does_not_store_raw_input": True,
    }


def _result_metadata(
    tool_options: AdkFunctionToolOptions,
    controlled_options: AdkControlledToolOptions,
) -> dict[str, Any]:
    return {
        "tool_options": tool_options.to_metadata(),
        "controlled_options": controlled_options.to_metadata(),
        "adk_native_tool": "google.adk.tools.FunctionTool",
        "adk_native_tool_context": "google.adk.tools.ToolContext",
        "adk_tool_confirmation": "google.adk.tools.tool_confirmation.ToolConfirmation",
        "adk_tool_confirmation_experimental": True,
        "confirmation_mapping": (
            "operator_approval_ref_to_adk_tool_confirmation"
        ),
        "no_live_tool": True,
    }


async def _run_adk_function_tool_with_confirmation(
    tool: FunctionTool,
    *,
    args: dict[str, Any],
    tool_options: AdkFunctionToolOptions,
    controlled_options: AdkControlledToolOptions,
    tool_run_ref: str,
    input_summary: dict[str, Any],
) -> AdkToolCallResult:
    confirmation_granted = controlled_options.confirmation_granted is True
    context = _ControlledAdkToolContext(
        confirmation=_tool_confirmation(controlled_options),
        function_call_id=tool_run_ref,
    )
    try:
        result = await tool.run_async(args=args, tool_context=context)
    except Exception as exc:  # noqa: BLE001 - classified as sanitized evidence.
        return AdkToolCallResult(
            tool_name=tool.name,
            tool_kind=tool_options.tool_kind,
            tool_call_allowed=True,
            tool_call_attempted=True,
            tool_runtime_call_performed=confirmation_granted,
            tool_confirmation_required=True,
            tool_confirmation_granted=confirmation_granted,
            adk_tool_confirmation_requested=(
                context.adk_tool_confirmation_requested
            ),
            tool_approval_ref=controlled_options.tool_approval_ref,
            tool_confirmation_decision_source=(
                controlled_options.confirmation_decision_source
            ),
            tool_input_summary=input_summary,
            tool_output_summary={},
            tool_failure_type="tool_runtime_failure",
            tool_run_ref=tool_run_ref,
            session_id=controlled_options.session_id,
            artifact_delta_refs=controlled_options.artifact_delta_refs,
            metadata={
                **_result_metadata(tool_options, controlled_options),
                "error_type": type(exc).__name__,
            },
        )
    failure_type = _confirmation_failure_type(
        result=result,
        controlled_options=controlled_options,
        context=context,
    )
    if failure_type is not None:
        return AdkToolCallResult(
            tool_name=tool.name,
            tool_kind=tool_options.tool_kind,
            tool_call_allowed=True,
            tool_call_attempted=True,
            tool_runtime_call_performed=False,
            tool_confirmation_required=True,
            tool_confirmation_granted=False,
            adk_tool_confirmation_requested=(
                context.adk_tool_confirmation_requested
            ),
            tool_approval_ref=controlled_options.tool_approval_ref,
            tool_confirmation_decision_source=(
                controlled_options.confirmation_decision_source
            ),
            tool_input_summary=input_summary,
            tool_output_summary=_summarize_output(result),
            tool_failure_type=failure_type,
            tool_run_ref=tool_run_ref,
            session_id=controlled_options.session_id,
            artifact_delta_refs=controlled_options.artifact_delta_refs,
            metadata=_result_metadata(tool_options, controlled_options),
        )
    return AdkToolCallResult(
        tool_name=tool.name,
        tool_kind=tool_options.tool_kind,
        tool_call_allowed=True,
        tool_call_attempted=True,
        tool_runtime_call_performed=True,
        tool_confirmation_required=True,
        tool_confirmation_granted=True,
        adk_tool_confirmation_requested=context.adk_tool_confirmation_requested,
        tool_approval_ref=controlled_options.tool_approval_ref,
        tool_confirmation_decision_source=(
            controlled_options.confirmation_decision_source
        ),
        tool_input_summary=input_summary,
        tool_output_summary=_summarize_output(result),
        tool_failure_type=None,
        tool_run_ref=tool_run_ref,
        session_id=controlled_options.session_id,
        artifact_delta_refs=controlled_options.artifact_delta_refs,
        metadata=_result_metadata(tool_options, controlled_options),
    )


def _tool_confirmation(
    controlled_options: AdkControlledToolOptions,
) -> ToolConfirmation | None:
    if controlled_options.confirmation_granted is None:
        return None
    return ToolConfirmation(
        confirmed=controlled_options.confirmation_granted is True,
        payload={
            "tool_approval_ref": controlled_options.tool_approval_ref,
            "confirmation_decision_source": (
                controlled_options.confirmation_decision_source
            ),
        },
    )


def _confirmation_failure_type(
    *,
    result: Any,
    controlled_options: AdkControlledToolOptions,
    context: "_ControlledAdkToolContext",
) -> str | None:
    if context.adk_tool_confirmation_requested:
        return "tool_confirmation_required"
    if controlled_options.confirmation_granted is False:
        return "tool_confirmation_rejected"
    if (
        isinstance(result, dict)
        and isinstance(result.get("error"), str)
        and "confirmation" in result["error"].lower()
    ):
        return "tool_confirmation_required"
    return None


class _ControlledAdkToolContext:
    """Minimal ToolContext-compatible object for FunctionTool confirmation."""

    def __init__(
        self,
        *,
        confirmation: ToolConfirmation | None,
        function_call_id: str,
    ) -> None:
        self.tool_confirmation = confirmation
        self.function_call_id = function_call_id
        self.actions = SimpleNamespace(skip_summarization=False)
        self.adk_tool_confirmation_requested = False
        self.requested_tool_confirmation: dict[str, Any] = {}

    def request_confirmation(
        self,
        *,
        hint: str | None = None,
        payload: Any | None = None,
    ) -> None:
        self.adk_tool_confirmation_requested = True
        self.requested_tool_confirmation = {
            "hint_present": hint is not None,
            "payload_present": payload is not None,
        }


def _tool_options_from_metadata(tool: FunctionTool) -> AdkFunctionToolOptions:
    metadata = tool.custom_metadata if isinstance(tool.custom_metadata, dict) else {}
    return AdkFunctionToolOptions(
        tool_name=str(metadata.get("tool_name") or tool.name),
        tool_kind=str(metadata.get("tool_kind") or "function"),
        require_confirmation=bool(metadata.get("require_confirmation", False)),
    )


def _summarize_mapping(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "argument_keys": sorted(str(key) for key in value),
        "argument_count": len(value),
        "value_types": {
            str(key): type(item).__name__ for key, item in value.items()
        },
        "string_lengths": {
            str(key): len(item)
            for key, item in value.items()
            if isinstance(item, str)
        },
        "input_digest": _digest(value),
    }


def _summarize_output(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "output_kind": "mapping",
            "output_keys": sorted(str(key) for key in value),
            "value_types": {
                str(key): type(item).__name__ for key, item in value.items()
            },
            "result_kind": (
                value.get("result_kind")
                if isinstance(value.get("result_kind"), str)
                else None
            ),
            "recommendation": (
                value.get("recommendation")
                if isinstance(value.get("recommendation"), str)
                else None
            ),
            "output_digest": _digest(value),
        }
    return {
        "output_kind": type(value).__name__,
        "output_digest": _digest(value),
    }


def _digest(value: Any) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()
