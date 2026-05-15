"""Composition entries for ADK native FunctionTool service chains."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from adk_adapter import (
    AdkAgentShellOptions,
    AdkControlledToolOptions,
    AdkFunctionToolOptions,
    AdkNoLiveLlm,
    AdkToolCallResult,
    build_deterministic_external_echo_function_tool,
    build_no_live_task_review_function_tool,
    run_adk_function_tool_no_live,
)
from adk_adapter.async_utils import run_sync
from observability_hub import AdkToolCallEvidence, build_adk_tool_call_evidence

from composition.adk_agent_shell_assembly import AdkAgentShellAssemblyOptions
from composition.runtime import RuntimeCompositionOptions, build_runtime_config_context


DETERMINISTIC_EXTERNAL_ECHO_TOOL_ID = "deterministic_external_echo"


@dataclass(frozen=True)
class AdkFunctionToolAssemblyOptions:
    """Local composition options for a controlled ADK FunctionTool."""

    app_name: str = "cognition_engine_adk_function_tool"
    user_id: str = "cognition-engine-adk-tool-user"
    agent_name: str = "cognition_agent_tool_shell"
    model: str = "adk-no-live/cognition-agent-tool-shell"
    instruction: str = (
        "Review governed task evidence through an ADK native FunctionTool. "
        "Return only sanitized product observations."
    )
    description: str = "Cognition Engine ADK native FunctionTool shell"
    mode: str | None = "chat"
    tool_options: AdkFunctionToolOptions = field(
        default_factory=lambda: AdkFunctionToolOptions(
            tool_name="review_task_context",
            tool_kind="deterministic_no_live_task_review",
            require_confirmation=False,
        )
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_agent_shell_options(self) -> AdkAgentShellOptions:
        """Return adapter-local options for constructing the ADK Agent."""

        return AdkAgentShellOptions(
            name=self.agent_name,
            model=self.model,
            instruction=self.instruction,
            description=self.description,
            mode=self.mode,
            metadata=dict(self.metadata),
        )

    def to_metadata(self) -> dict[str, Any]:
        """Return safe option metadata without exposing full instructions."""

        return {
            "options_type": "composition.adk_tool_assembly."
            "AdkFunctionToolAssemblyOptions",
            "app_name": self.app_name,
            "user_id": self.user_id,
            "agent_name": self.agent_name,
            "model": self.model,
            "description": self.description,
            "mode": self.mode,
            "instruction_length": len(self.instruction),
            "tool_options": self.tool_options.to_metadata(),
            "metadata_keys": sorted(self.metadata),
        }


@dataclass(frozen=True)
class AdkFunctionToolAssembly:
    """Assemble an ADK native FunctionTool and injectable Agent shell."""

    assembly_options: AdkFunctionToolAssemblyOptions = field(
        default_factory=AdkFunctionToolAssemblyOptions
    )
    tool: Any | None = None
    agent: Any | None = None

    def build_tool(self) -> Any:
        """Return the provided or default ADK native FunctionTool."""

        if self.tool is not None:
            return self.tool
        if (
            self.assembly_options.tool_options.tool_name
            == DETERMINISTIC_EXTERNAL_ECHO_TOOL_ID
        ):
            return build_deterministic_external_echo_function_tool(
                options=self.assembly_options.tool_options
            )
        return build_no_live_task_review_function_tool(
            options=self.assembly_options.tool_options
        )

    def build_agent(self) -> Any:
        """Build an ADK Agent with the controlled FunctionTool injected."""

        if self.agent is not None:
            return self.agent
        from google.adk.agents import Agent

        options = self.assembly_options.to_agent_shell_options()
        return Agent(
            name=options.name,
            model=AdkNoLiveLlm(
                model=options.model,
                response_text="No-live ADK FunctionTool shell response.",
            ),
            instruction=options.instruction,
            description=options.description,
            mode=options.mode,
            tools=[self.build_tool()],
        )

    def metadata(self) -> dict[str, Any]:
        """Return assembly metadata for later observability intake."""

        agent = self.build_agent()
        tool = self.build_tool()
        return {
            "assembly": "composition.adk_tool_assembly",
            "agent_type": type(agent).__name__,
            "agent_name": getattr(agent, "name", self.assembly_options.agent_name),
            "app_name": self.assembly_options.app_name,
            "user_id": self.assembly_options.user_id,
            "tool_type": type(tool).__name__,
            "tool_name": getattr(tool, "name", self.assembly_options.tool_options.tool_name),
            "tool_kind": self.assembly_options.tool_options.tool_kind,
            "tool_count": len(getattr(agent, "tools", []) or []),
            "assembly_options": self.assembly_options.to_metadata(),
            "metadata": dict(self.assembly_options.metadata),
            "observability_candidate": "observability_hub.adk_tool_evidence",
        }


@dataclass(frozen=True)
class AdkFunctionToolRunEvidenceAssembly:
    """Observability evidence assembly for one ADK FunctionTool call."""

    tool_call_evidence: AdkToolCallEvidence
    assembly_metadata: dict[str, Any]
    source: str = (
        "composition.adk_tool_assembly.AdkFunctionToolRunEvidenceAssembly"
    )


@dataclass(frozen=True)
class AdkFunctionToolProductRunAssembly:
    """Product-entry assembly result for one no-live ADK FunctionTool call."""

    tool_call_result: AdkToolCallResult
    run_evidence_assembly: AdkFunctionToolRunEvidenceAssembly
    source: str = "composition.adk_tool_assembly.product_run"

    @property
    def tool_call_evidence(self) -> AdkToolCallEvidence:
        """Return the sanitized Tool call evidence candidate."""

        return self.run_evidence_assembly.tool_call_evidence

    def to_governance_audit(self) -> dict[str, Any]:
        """Return compact governance audit facts for product summary payloads."""

        evidence = self.tool_call_evidence
        return {
            "tool_evidence_ref": evidence.tool_evidence_ref,
            "tool_run_ref": evidence.tool_run_ref,
            "tool_name": evidence.tool_name,
            "tool_kind": evidence.tool_kind,
            "status": evidence.status,
            "session_id": evidence.session_id,
            "artifact_delta_refs": list(evidence.artifact_delta_refs),
            "tool_call_allowed": evidence.tool_call_allowed,
            "tool_call_attempted": evidence.tool_call_attempted,
            "tool_runtime_call_performed": evidence.tool_runtime_call_performed,
            "tool_confirmation_required": evidence.tool_confirmation_required,
            "tool_confirmation_granted": evidence.tool_confirmation_granted,
            "adk_tool_confirmation_requested": (
                evidence.adk_tool_confirmation_requested
            ),
            "tool_approval_ref": evidence.tool_approval_ref,
            "tool_confirmation_decision_source": (
                evidence.tool_confirmation_decision_source
            ),
            "tool_input_summary": dict(evidence.tool_input_summary),
            "tool_output_summary": dict(evidence.tool_output_summary),
            "tool_failure_type": evidence.tool_failure_type,
            "readonly_facts_embedded": evidence.readonly_facts_embedded,
            "does_not_store_raw_tool_input": (
                evidence.does_not_store_raw_tool_input
            ),
            "does_not_store_raw_tool_output": (
                evidence.does_not_store_raw_tool_output
            ),
            "raw_adk_object_included": evidence.raw_adk_object_included,
        }


def build_adk_function_tool_run_evidence(
    *,
    tool_call_result: AdkToolCallResult,
    tool_assembly: AdkFunctionToolAssembly,
) -> AdkFunctionToolRunEvidenceAssembly:
    """Build observability evidence from an ADK FunctionTool call."""

    assembly_metadata = tool_assembly.metadata()
    evidence = build_adk_tool_call_evidence(
        tool_call_result.to_observability_input(),
        assembly_metadata=assembly_metadata,
    )
    return AdkFunctionToolRunEvidenceAssembly(
        tool_call_evidence=evidence,
        assembly_metadata=assembly_metadata,
    )


def run_no_live_adk_function_tool_product_entry(
    *,
    options: RuntimeCompositionOptions,
    task_ref: str,
    invocation_id: str,
    runtime_id: str,
    task_kind: str = "task",
    evidence_ref: str | None = None,
    assembly_options: AdkFunctionToolAssemblyOptions | None = None,
    require_confirmation: bool | None = None,
    tool_confirmation_granted: bool | None = True,
    tool_approval_ref: str | None = None,
    tool_confirmation_decision_source: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AdkFunctionToolProductRunAssembly:
    """Run a deterministic ADK FunctionTool through a no-live product path."""

    config_context = build_runtime_config_context(options)
    tool_confirmation = config_context.tool_confirmation
    resolved_require_confirmation = (
        require_confirmation
        if require_confirmation is not None
        else tool_confirmation.default_require_confirmation
    )
    confirmation_config_source = (
        "runtime_override"
        if require_confirmation is not None
        else "config_contexts.ToolConfirmationConfigView"
    )
    resolved_options = assembly_options or AdkFunctionToolAssemblyOptions(
        app_name="cognition_agent_tool_product_entry",
        user_id="cognition-agent-tool-product-user",
        agent_name="cognition_agent_tool_shell",
        model="adk-no-live/cognition-agent-tool-shell",
        metadata={
            "source": "composition.adk_tool_assembly",
            "product_entry": "cognition_run",
            "runtime_id": runtime_id,
            "config_runtime_name": config_context.runtime.runtime_name,
            "tool_confirmation_config_source": confirmation_config_source,
            "tool_confirmation_default_mode": tool_confirmation.default_mode,
            "tool_confirmation_auto_allowed": (
                tool_confirmation.auto_confirmation_allowed
            ),
            **dict(metadata or {}),
        },
    )
    if (
        resolved_options.tool_options.require_confirmation
        != resolved_require_confirmation
    ):
        resolved_options = replace(
            resolved_options,
            tool_options=replace(
                resolved_options.tool_options,
                require_confirmation=resolved_require_confirmation,
            ),
        )
    assembly = AdkFunctionToolAssembly(assembly_options=resolved_options)
    tool_call_result = run_sync(
        run_adk_function_tool_no_live(
            assembly.build_tool(),
            args={
                "task_ref": task_ref,
                "task_kind": task_kind,
                "evidence_ref": evidence_ref,
            },
            tool_options=resolved_options.tool_options,
            controlled_options=AdkControlledToolOptions(
                tool_call_allowed=True,
                confirmation_granted=tool_confirmation_granted,
                tool_approval_ref=tool_approval_ref,
                confirmation_decision_source=tool_confirmation_decision_source,
                session_id=f"session://{runtime_id}",
                tool_run_id=invocation_id,
                metadata={
                    "runtime_id": runtime_id,
                    "config_runtime_name": config_context.runtime.runtime_name,
                    "tool_confirmation_config_source": confirmation_config_source,
                    "tool_confirmation_default_mode": tool_confirmation.default_mode,
                    "tool_confirmation_low_risk_tool_allowlist": (
                        list(tool_confirmation.low_risk_tool_allowlist)
                    ),
                },
            ),
        )
    )
    return AdkFunctionToolProductRunAssembly(
        tool_call_result=tool_call_result,
        run_evidence_assembly=build_adk_function_tool_run_evidence(
            tool_call_result=tool_call_result,
            tool_assembly=assembly,
        ),
    )


def run_controlled_live_low_risk_external_tool_smoke(
    *,
    options: RuntimeCompositionOptions,
    message_ref: str,
    invocation_id: str,
    runtime_id: str,
    message_kind: str = "smoke",
    echo_label: str | None = None,
    tool_id: str = DETERMINISTIC_EXTERNAL_ECHO_TOOL_ID,
    controlled_live_external_tool_smoke_enabled: bool | None = None,
    smoke_override_source: str | None = None,
    require_confirmation: bool | None = None,
    tool_confirmation_granted: bool | None = None,
    tool_approval_ref: str | None = None,
    tool_confirmation_decision_source: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AdkFunctionToolProductRunAssembly:
    """Run a config-gated low-risk external ADK FunctionTool smoke."""

    config_context = build_runtime_config_context(options)
    tool_confirmation = config_context.tool_confirmation
    allowlist = tuple(tool_confirmation.low_risk_tool_allowlist)
    resolved_require_confirmation = (
        require_confirmation
        if require_confirmation is not None
        else tool_confirmation.default_require_confirmation
    )
    resolved_smoke_enabled = (
        controlled_live_external_tool_smoke_enabled
        if controlled_live_external_tool_smoke_enabled is not None
        else tool_confirmation.controlled_live_external_tool_smoke_enabled
    )
    smoke_source = (
        smoke_override_source
        if controlled_live_external_tool_smoke_enabled is not None
        else "config_contexts.ToolConfirmationConfigView"
    )
    blocked_failure_type: str | None = None
    if (
        controlled_live_external_tool_smoke_enabled is not None
        and smoke_override_source is None
    ):
        blocked_failure_type = "tool_smoke_override_source_missing"
    elif not resolved_smoke_enabled:
        blocked_failure_type = "tool_smoke_disabled"
    elif tool_id not in allowlist:
        blocked_failure_type = "tool_not_in_low_risk_allowlist"

    tool_options = AdkFunctionToolOptions(
        tool_name=tool_id,
        tool_kind="deterministic_low_risk_external_smoke",
        require_confirmation=resolved_require_confirmation,
        metadata={
            "risk_level": "low",
            "external_side_effects": False,
            "smoke_only": True,
        },
    )
    assembly_options = AdkFunctionToolAssemblyOptions(
        app_name="cognition_agent_low_risk_external_tool_smoke",
        user_id="cognition-agent-tool-smoke-user",
        agent_name="cognition_agent_low_risk_tool_shell",
        model="adk-no-live/cognition-agent-low-risk-tool-shell",
        instruction=(
            "Run a gated deterministic ADK native FunctionTool smoke. "
            "Return only sanitized product observations."
        ),
        description=(
            "Cognition Engine ADK native low-risk external FunctionTool smoke"
        ),
        tool_options=tool_options,
        metadata={
            "source": "composition.adk_tool_assembly",
            "product_entry": "cognition_run",
            "runtime_id": runtime_id,
            "config_runtime_name": config_context.runtime.runtime_name,
            "tool_confirmation_config_source": (
                "runtime_override"
                if require_confirmation is not None
                else "config_contexts.ToolConfirmationConfigView"
            ),
            "tool_confirmation_default_mode": tool_confirmation.default_mode,
            "tool_confirmation_auto_allowed": (
                tool_confirmation.auto_confirmation_allowed
            ),
            "controlled_live_external_tool_smoke_enabled": (
                resolved_smoke_enabled
            ),
            "controlled_live_external_tool_smoke_source": smoke_source,
            "low_risk_tool_allowlist_count": len(allowlist),
            **dict(metadata or {}),
        },
    )
    assembly = AdkFunctionToolAssembly(assembly_options=assembly_options)
    tool_call_result = run_sync(
        run_adk_function_tool_no_live(
            assembly.build_tool(),
            args={
                "message_ref": message_ref,
                "message_kind": message_kind,
                "echo_label": echo_label,
            },
            tool_options=tool_options,
            controlled_options=AdkControlledToolOptions(
                tool_call_allowed=blocked_failure_type is None,
                blocked_failure_type=(
                    blocked_failure_type or "tool_call_not_allowed"
                ),
                confirmation_granted=tool_confirmation_granted,
                tool_approval_ref=tool_approval_ref,
                confirmation_decision_source=tool_confirmation_decision_source,
                session_id=f"session://{runtime_id}",
                tool_run_id=invocation_id,
                metadata={
                    "runtime_id": runtime_id,
                    "config_runtime_name": config_context.runtime.runtime_name,
                    "controlled_live_external_tool_smoke_enabled": (
                        resolved_smoke_enabled
                    ),
                    "controlled_live_external_tool_smoke_source": smoke_source,
                    "low_risk_tool_allowlist": list(allowlist),
                },
            ),
        )
    )
    return AdkFunctionToolProductRunAssembly(
        tool_call_result=tool_call_result,
        run_evidence_assembly=build_adk_function_tool_run_evidence(
            tool_call_result=tool_call_result,
            tool_assembly=assembly,
        ),
    )


def runtime_composition_options_from_tool_metadata(
    metadata: dict[str, Any],
) -> RuntimeCompositionOptions:
    """Build runtime composition options from product runtime input metadata."""

    config_root = metadata.get("config_root") or "config"
    environment = metadata.get("environment") or "local"
    return RuntimeCompositionOptions(
        config_root=Path(str(config_root)),
        environment=str(environment),
    )
