"""Composition entries for ADK native Agent shell service chains."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from adk_adapter import (
    AdkAgentControlledLiveOptions,
    AdkAgentRunResult,
    AdkAgentServiceAdapter,
    AdkAgentShellOptions,
    AdkRunConfigOptions,
    AdkRunnerServiceBundle,
    AdkRunnerServiceBundleOptions,
    create_adk_llm_agent,
    create_controlled_live_adk_llm_agent,
    create_no_live_adk_llm_agent,
)
from adk_adapter.async_utils import run_sync
from observability_hub import AdkAgentShellEvidence, build_adk_agent_shell_evidence

from composition.adk_workflow_runner_assembly import (
    build_adk_run_config_options_from_runtime_config,
)
from composition.runtime import RuntimeCompositionOptions, build_runtime_config_context


@dataclass(frozen=True)
class AdkAgentShellAssemblyOptions:
    """Local composition options for ADK native Agent shell assembly."""

    app_name: str = "cognition_engine_adk_agent_shell"
    user_id: str = "cognition-engine-adk-user"
    agent_name: str = "cognition_agent_shell"
    model: str = "gemini-2.0-flash"
    instruction: str = "Review the supplied task context through governed evidence."
    description: str = "Cognition Engine ADK native agent shell"
    mode: str | None = "chat"
    service_bundle_options: AdkRunnerServiceBundleOptions = field(
        default_factory=AdkRunnerServiceBundleOptions
    )
    run_config_options: AdkRunConfigOptions | None = None
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
            "options_type": "composition.adk_agent_shell_assembly."
            "AdkAgentShellAssemblyOptions",
            "app_name": self.app_name,
            "user_id": self.user_id,
            "agent_name": self.agent_name,
            "model": self.model,
            "description": self.description,
            "mode": self.mode,
            "instruction_length": len(self.instruction),
            "service_bundle_options": self.service_bundle_options.metadata(),
            "run_config_options": (
                self.run_config_options.to_metadata()
                if self.run_config_options is not None
                else None
            ),
            "metadata_keys": sorted(self.metadata),
        }


@dataclass(frozen=True)
class AdkAgentShellAssembly:
    """Assemble an ADK native Agent shell with injectable ADK services."""

    agent: Any | None = None
    service_bundle: AdkRunnerServiceBundle | None = None
    assembly_options: AdkAgentShellAssemblyOptions = field(
        default_factory=AdkAgentShellAssemblyOptions
    )

    def build_service_bundle(self) -> AdkRunnerServiceBundle:
        """Return the provided or default in-memory ADK service bundle."""

        return self.service_bundle or (
            self.assembly_options.service_bundle_options.build_service_bundle(
                app_name=self.assembly_options.app_name,
                user_id=self.assembly_options.user_id,
            )
        )

    def build_agent(self) -> Any:
        """Return the provided or locally constructed ADK native Agent."""

        return self.agent or create_adk_llm_agent(
            self.assembly_options.to_agent_shell_options()
        )

    def build_agent_service(self) -> AdkAgentServiceAdapter:
        """Build the Agent service adapter over the ADK native Agent."""

        return AdkAgentServiceAdapter(
            agent=self.build_agent(),
            app_name=self.assembly_options.app_name,
            user_id=self.assembly_options.user_id,
            service_bundle=self.build_service_bundle(),
            run_config_options=self.assembly_options.run_config_options,
        )

    def metadata(self) -> dict[str, Any]:
        """Return assembly metadata for later observability intake."""

        agent = self.build_agent()
        service_bundle = self.build_service_bundle()
        return {
            "assembly": "composition.adk_agent_shell_assembly",
            "agent_type": type(agent).__name__,
            "agent_name": getattr(agent, "name", self.assembly_options.agent_name),
            "app_name": self.assembly_options.app_name,
            "user_id": self.assembly_options.user_id,
            "service_bundle": service_bundle.metadata(),
            "assembly_options": self.assembly_options.to_metadata(),
            "metadata": dict(self.assembly_options.metadata),
            "observability_candidate": "observability_hub.adk_agent_shell_intake",
        }


def build_adk_agent_shell_assembly_from_runtime_config(
    *,
    options: RuntimeCompositionOptions,
    assembly_options: AdkAgentShellAssemblyOptions | None = None,
    agent: Any | None = None,
    service_bundle: AdkRunnerServiceBundle | None = None,
) -> AdkAgentShellAssembly:
    """Build an ADK Agent shell assembly using runtime config RunConfig mapping."""

    config_context = build_runtime_config_context(options)
    config_run_config_options = build_adk_run_config_options_from_runtime_config(
        config_context
    )
    resolved_options = assembly_options or AdkAgentShellAssemblyOptions()
    if resolved_options.run_config_options is None:
        resolved_options = replace(
            resolved_options,
            run_config_options=config_run_config_options,
        )
    return AdkAgentShellAssembly(
        agent=agent,
        service_bundle=service_bundle,
        assembly_options=resolved_options,
    )


@dataclass(frozen=True)
class AdkAgentShellRunEvidenceAssembly:
    """Observability evidence assembly for one ADK Agent shell run."""

    agent_shell_evidence: AdkAgentShellEvidence
    assembly_metadata: dict[str, Any]
    source: str = (
        "composition.adk_agent_shell_assembly.AdkAgentShellRunEvidenceAssembly"
    )


@dataclass(frozen=True)
class AdkAgentShellProductRunAssembly:
    """Product-entry assembly result for one no-live ADK Agent shell run."""

    agent_run_result: AdkAgentRunResult
    run_evidence_assembly: AdkAgentShellRunEvidenceAssembly
    source: str = "composition.adk_agent_shell_assembly.product_run"

    @property
    def agent_shell_evidence(self) -> AdkAgentShellEvidence:
        """Return the sanitized Agent shell evidence candidate."""

        return self.run_evidence_assembly.agent_shell_evidence

    def to_governance_audit(self) -> dict[str, Any]:
        """Return compact governance audit facts for product summary payloads."""

        evidence = self.agent_shell_evidence
        return {
            "agent_shell_evidence_ref": (
                f"adk-agent-shell-evidence://{evidence.evidence_id}"
            ),
            "agent_shell_run_ref": (
                f"adk-agent-shell-run://"
                f"{self.agent_run_result.requested_invocation_id}"
            ),
            "agent_name": evidence.agent_name,
            "agent_type": evidence.agent_type,
            "app_name": evidence.app_name,
            "session_id": evidence.session_id,
            "requested_invocation_id": evidence.requested_invocation_id,
            "adk_invocation_id": evidence.adk_invocation_id,
            "status": evidence.status,
            "event_count": evidence.event_summary.get("event_count", 0),
            "event_authors": list(evidence.event_summary.get("event_authors") or []),
            "no_live_execution_observed": evidence.no_live_execution_observed,
            "runtime_call_performed": True,
            "failure_type": (
                None if evidence.status == "success" else "agent_shell_run_failed"
            ),
            "readonly_facts_embedded": False,
            "does_not_store_prompt": True,
            "does_not_store_raw_response": True,
            "raw_adk_object_included": False,
            "raw_adk_event_included": False,
            "raw_adk_session_included": False,
        }


@dataclass(frozen=True)
class AdkAgentShellControlledLiveProfile:
    """Config-derived controlled-live profile for an ADK Agent shell smoke."""

    assembly_options: AdkAgentShellAssemblyOptions
    live_options: AdkAgentControlledLiveOptions
    enabled_by_default: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        """Return sanitized controlled-live profile metadata."""

        return {
            "profile": "adk_agent_shell_controlled_live",
            "agent_name": self.assembly_options.agent_name,
            "app_name": self.assembly_options.app_name,
            "user_id": self.assembly_options.user_id,
            "enabled_by_default": self.enabled_by_default,
            "live_options": self.live_options.to_metadata(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class AdkAgentShellControlledLiveSmokeResult:
    """Compact controlled-live Agent shell smoke result."""

    profile: AdkAgentShellControlledLiveProfile
    success: bool
    status: str
    failure_type: str | None
    runtime_call_performed: bool
    call_attempted: bool
    error_message_sanitized: str | None = None
    product_run: AdkAgentShellProductRunAssembly | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_governance_audit(self) -> dict[str, Any]:
        """Return compact governance audit facts for controlled-live smoke."""

        profile_metadata = self.profile.to_metadata()
        if self.product_run is not None:
            audit = self.product_run.to_governance_audit()
            audit.update(
                {
                    "controlled_live": True,
                    "controlled_live_smoke": True,
                    "controlled_live_smoke_enabled": True,
                    "failure_type": self.failure_type,
                    "runtime_call_performed": self.runtime_call_performed,
                    "call_attempted": self.call_attempted,
                    "live_profile": _compact_agent_shell_live_profile(
                        profile_metadata
                    ),
                    "metadata": dict(self.metadata),
                }
            )
            return audit

        return {
            "agent_shell_evidence_ref": None,
            "agent_shell_run_ref": None,
            "agent_name": profile_metadata["agent_name"],
            "agent_type": "LlmAgent",
            "app_name": profile_metadata["app_name"],
            "session_id": None,
            "requested_invocation_id": None,
            "adk_invocation_id": None,
            "status": self.status,
            "event_count": 0,
            "event_authors": [],
            "controlled_live": True,
            "controlled_live_smoke": True,
            "controlled_live_smoke_enabled": bool(
                self.metadata.get("live_enabled", False)
            ),
            "no_live_execution_observed": False,
            "runtime_call_performed": self.runtime_call_performed,
            "call_attempted": self.call_attempted,
            "failure_type": self.failure_type,
            "error_message_sanitized": self.error_message_sanitized,
            "live_profile": _compact_agent_shell_live_profile(profile_metadata),
            "readonly_facts_embedded": False,
            "does_not_store_prompt": True,
            "does_not_store_raw_response": True,
            "raw_adk_object_included": False,
            "raw_adk_event_included": False,
            "raw_adk_session_included": False,
            "metadata": dict(self.metadata),
        }


def build_adk_agent_shell_run_evidence(
    *,
    agent_run_result: AdkAgentRunResult,
    agent_shell_assembly: AdkAgentShellAssembly,
) -> AdkAgentShellRunEvidenceAssembly:
    """Build observability evidence from an ADK Agent shell run."""

    assembly_metadata = agent_shell_assembly.metadata()
    evidence = build_adk_agent_shell_evidence(
        agent_run_result.to_observability_input(),
        assembly_metadata=assembly_metadata,
    )
    return AdkAgentShellRunEvidenceAssembly(
        agent_shell_evidence=evidence,
        assembly_metadata=assembly_metadata,
    )


def run_no_live_adk_agent_shell_product_entry(
    *,
    options: RuntimeCompositionOptions,
    input_text: str,
    invocation_id: str,
    runtime_id: str,
    assembly_options: AdkAgentShellAssemblyOptions | None = None,
    response_text: str = "No-live cognition Agent shell product review completed.",
    metadata: dict[str, Any] | None = None,
) -> AdkAgentShellProductRunAssembly:
    """Run the ADK native Agent shell through a no-live product-entry path."""

    resolved_options = assembly_options or AdkAgentShellAssemblyOptions(
        app_name="cognition_agent_shell_product_entry",
        user_id="cognition-agent-product-user",
        agent_name="cognition_agent_shell",
        model="adk-no-live/cognition-agent-shell",
        instruction=(
            "Review governed cognition-run task evidence through the ADK native "
            "Agent shell. Return only sanitized product review observations."
        ),
        mode="chat",
        metadata={
            "source": "composition.adk_agent_shell_assembly",
            "product_entry": "cognition_run",
            "runtime_id": runtime_id,
            **dict(metadata or {}),
        },
    )
    agent = create_no_live_adk_llm_agent(
        resolved_options.to_agent_shell_options(),
        response_text=response_text,
    )
    assembly = build_adk_agent_shell_assembly_from_runtime_config(
        options=options,
        assembly_options=resolved_options,
        agent=agent,
    )
    run_result = run_sync(
        assembly.build_agent_service().run_text_async(
            text=input_text,
            invocation_id=invocation_id,
            state={
                "runtime_id": runtime_id,
                "product_entry": "cognition_run",
                "no_live_agent_shell": True,
            },
        )
    )
    run_evidence_assembly = build_adk_agent_shell_run_evidence(
        agent_run_result=run_result,
        agent_shell_assembly=assembly,
    )
    return AdkAgentShellProductRunAssembly(
        agent_run_result=run_result,
        run_evidence_assembly=run_evidence_assembly,
    )


def build_controlled_live_adk_agent_shell_profile_from_runtime_config(
    *,
    options: RuntimeCompositionOptions,
    assembly_options: AdkAgentShellAssemblyOptions | None = None,
    live_client: Any | None = None,
    model_name: str | None = None,
    ollama_api_base: str | None = None,
    timeout_seconds: int | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AdkAgentShellControlledLiveProfile:
    """Build controlled-live ADK Agent shell profile from runtime config."""

    config_context = build_runtime_config_context(options)
    live_llm = config_context.live_llm
    run_config_options = build_adk_run_config_options_from_runtime_config(
        config_context
    )
    resolved_model_name = model_name or live_llm.model_name
    resolved_ollama_api_base = ollama_api_base or live_llm.ollama_api_base
    resolved_timeout_seconds = (
        timeout_seconds
        if timeout_seconds is not None
        else live_llm.timeout_seconds
    )
    resolved_temperature = (
        temperature if temperature is not None else live_llm.temperature
    )
    resolved_max_tokens = max_tokens if max_tokens is not None else live_llm.max_tokens
    profile_metadata = {
        "live_options_source": "config_contexts.runtime.RuntimeLiveLlmConfigView",
        "live_service_profile": live_llm.profile,
        "configured_model_name": resolved_model_name,
        "config_model_name": live_llm.model_name,
        "live_options_override_applied": any(
            value is not None
            for value in (
                model_name,
                ollama_api_base,
                timeout_seconds,
                temperature,
                max_tokens,
            )
        ),
        "enabled_by_default": live_llm.enabled_by_default,
        "config_metadata_keys": sorted(live_llm.metadata),
        "config_metadata": dict(live_llm.metadata),
        **dict(metadata or {}),
    }
    resolved_assembly_options = assembly_options or AdkAgentShellAssemblyOptions(
        app_name="cognition_agent_shell_controlled_live_smoke",
        user_id="cognition-agent-controlled-live-user",
        agent_name="cognition_agent_shell",
        model=resolved_model_name,
        instruction=(
            "Review governed cognition-run task evidence through the ADK native "
            "Agent shell. Return only sanitized product review observations."
        ),
        mode="chat",
        metadata={
            "source": "composition.adk_agent_shell_assembly",
            "controlled_live_agent_shell": True,
            **profile_metadata,
        },
    )
    if resolved_assembly_options.run_config_options is None:
        resolved_assembly_options = replace(
            resolved_assembly_options,
            run_config_options=run_config_options,
        )
    return AdkAgentShellControlledLiveProfile(
        assembly_options=resolved_assembly_options,
        live_options=AdkAgentControlledLiveOptions(
            model=resolved_model_name,
            ollama_api_base=resolved_ollama_api_base,
            timeout_seconds=resolved_timeout_seconds,
            temperature=resolved_temperature,
            max_tokens=resolved_max_tokens,
            llm_client=live_client,
            metadata=profile_metadata,
        ),
        enabled_by_default=live_llm.enabled_by_default,
        metadata=profile_metadata,
    )


def run_controlled_live_adk_agent_shell_smoke(
    *,
    options: RuntimeCompositionOptions,
    input_text: str,
    invocation_id: str,
    runtime_id: str,
    live_enabled: bool = False,
    assembly_options: AdkAgentShellAssemblyOptions | None = None,
    live_client: Any | None = None,
    model_name: str | None = None,
    ollama_api_base: str | None = None,
    timeout_seconds: int | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AdkAgentShellControlledLiveSmokeResult:
    """Run a gated controlled-live ADK Agent shell smoke."""

    profile = build_controlled_live_adk_agent_shell_profile_from_runtime_config(
        options=options,
        assembly_options=assembly_options,
        live_client=live_client,
        model_name=model_name,
        ollama_api_base=ollama_api_base,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        max_tokens=max_tokens,
        metadata={
            "source": "composition.adk_agent_shell_assembly",
            "runtime_id": runtime_id,
            **dict(metadata or {}),
        },
    )
    if not live_enabled:
        return AdkAgentShellControlledLiveSmokeResult(
            profile=profile,
            success=False,
            status="skipped",
            failure_type="live_disabled",
            runtime_call_performed=False,
            call_attempted=False,
            error_message_sanitized=(
                "controlled-live Agent shell smoke is disabled by default"
            ),
            metadata={"live_enabled": False},
        )

    agent = create_controlled_live_adk_llm_agent(
        profile.assembly_options.to_agent_shell_options(),
        live_options=profile.live_options,
    )
    assembly = build_adk_agent_shell_assembly_from_runtime_config(
        options=options,
        assembly_options=profile.assembly_options,
        agent=agent,
    )
    try:
        run_result = run_sync(
            assembly.build_agent_service().run_text_async(
                text=input_text,
                invocation_id=invocation_id,
                state={
                    "runtime_id": runtime_id,
                    "product_entry": "controlled_live_agent_shell_smoke",
                    "controlled_live_agent_shell": True,
                },
            )
        )
    except Exception as exc:  # noqa: BLE001 - provider failures must be classified.
        return AdkAgentShellControlledLiveSmokeResult(
            profile=profile,
            success=False,
            status="failure",
            failure_type=_classify_agent_shell_live_failure(exc),
            runtime_call_performed=True,
            call_attempted=True,
            error_message_sanitized=_sanitize_agent_shell_live_error(str(exc)),
            metadata={"live_enabled": True},
        )

    product_run = AdkAgentShellProductRunAssembly(
        agent_run_result=run_result,
        run_evidence_assembly=build_adk_agent_shell_run_evidence(
            agent_run_result=run_result,
            agent_shell_assembly=assembly,
        ),
        source="composition.adk_agent_shell_assembly.controlled_live_smoke",
    )
    return AdkAgentShellControlledLiveSmokeResult(
        profile=profile,
        success=True,
        status=product_run.agent_shell_evidence.status,
        failure_type=(
            None
            if product_run.agent_shell_evidence.status == "success"
            else "agent_shell_run_failed"
        ),
        runtime_call_performed=True,
        call_attempted=True,
        product_run=product_run,
        metadata={"live_enabled": True},
    )


def runtime_composition_options_from_metadata(
    metadata: dict[str, Any],
) -> RuntimeCompositionOptions:
    """Build runtime composition options from product runtime input metadata."""

    config_root = metadata.get("config_root") or "config"
    environment = metadata.get("environment") or "local"
    return RuntimeCompositionOptions(
        config_root=Path(str(config_root)),
        environment=str(environment),
    )


def _compact_agent_shell_live_profile(
    profile_metadata: dict[str, Any],
) -> dict[str, Any]:
    live_options = profile_metadata.get("live_options") or {}
    return {
        "live_options_source": live_options.get("live_options_source"),
        "live_service_profile": live_options.get("live_service_profile"),
        "configured_model_name": live_options.get("model"),
        "ollama_api_base": live_options.get("ollama_api_base"),
        "timeout_seconds": live_options.get("timeout_seconds"),
        "temperature": live_options.get("temperature"),
        "max_tokens": live_options.get("max_tokens"),
        "enabled_by_default": profile_metadata.get("enabled_by_default"),
    }


def _classify_agent_shell_live_failure(exc: Exception) -> str:
    message = str(exc).lower()
    if isinstance(exc, ModuleNotFoundError):
        return "dependency_failure"
    if isinstance(exc, TimeoutError) or "timeout" in message:
        return "timeout_failure"
    if any(
        marker in message
        for marker in (
            "connection refused",
            "connecterror",
            "connection error",
            "provider unavailable",
            "ollama",
            "api_base",
        )
    ):
        return "provider_unavailable"
    return "live_call_failure"


def _sanitize_agent_shell_live_error(value: str, limit: int = 240) -> str:
    sanitized = " ".join(str(value).split())
    for marker in (
        "api_key",
        "completion",
        "message",
        "messages",
        "prompt",
        "raw_provider_response",
        "raw_response",
        "response_text",
        "system_prompt",
        "token",
        "secret",
    ):
        sanitized = sanitized.replace(marker, "[redacted]")
    if len(sanitized) <= limit:
        return sanitized
    return sanitized[:limit]
