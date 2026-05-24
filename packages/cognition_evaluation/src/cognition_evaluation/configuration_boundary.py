"""Configuration boundary evaluation helpers."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from cognition_evaluation.models import (
    EvaluationBaseModel,
    EvaluationFinding,
    EvaluationProfileRef,
    EvaluationResult,
)


CONFIGURATION_BOUNDARY_EVALUATION_PROFILE = EvaluationProfileRef(
    ref="evaluation-profile://configuration-boundary/v1",
    name="configuration_boundary_evaluation",
    version="v1",
)

EXPECTED_INSTALL_DEFAULT_CONFIG_OWNER = "config_assembly/default_config"


class ConfigurationBoundarySnapshot(EvaluationBaseModel):
    """Safe configuration snapshot for single-source boundary evaluation."""

    config_ref: str = Field(..., min_length=1)
    root_config_published_as_package: bool = False
    root_config_synced_to_public_repo: bool = False
    release_distribution_includes_root_config: bool = False
    install_default_config_owner: str | None = None
    config_contexts_contains_default_resources: list[str] = Field(default_factory=list)
    config_contexts_used_as_fact_source: list[str] = Field(default_factory=list)
    direct_root_config_consumers: list[str] = Field(default_factory=list)
    provider_profiles_without_config_contexts: list[str] = Field(default_factory=list)
    provider_profiles_without_config_assembly_defaults: list[str] = Field(
        default_factory=list
    )
    public_repo_forbidden_config_paths: list[str] = Field(default_factory=list)
    secret_or_local_only_config_paths: list[str] = Field(default_factory=list)
    stable_config_consumption_without_contexts: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_safe_snapshot(self) -> "ConfigurationBoundarySnapshot":
        _reject_forbidden_values(self.model_dump())
        return self


def evaluate_configuration_boundary(
    snapshot: ConfigurationBoundarySnapshot,
    *,
    evaluation_id: str = "evaluation://configuration-boundary",
) -> EvaluationResult:
    """Evaluate configuration single-source boundaries."""

    findings: list[EvaluationFinding] = []
    if snapshot.root_config_published_as_package:
        findings.append(
            _finding(
                "root_config_private_source_boundary",
                "failed",
                "blocking",
                "Private root config is treated as an independent publishable package.",
            )
        )
    if snapshot.root_config_synced_to_public_repo:
        findings.append(
            _finding(
                "public_repository_config_boundary",
                "failed",
                "blocking",
                "Private root config is synced into the public repository surface.",
            )
        )
    if snapshot.release_distribution_includes_root_config:
        findings.append(
            _finding(
                "config_release_boundary",
                "failed",
                "blocking",
                "Release distribution includes private root config directly.",
            )
        )
    if (
        snapshot.install_default_config_owner
        and snapshot.install_default_config_owner != EXPECTED_INSTALL_DEFAULT_CONFIG_OWNER
    ):
        findings.append(
            _finding(
                "install_state_default_config_boundary",
                "failed",
                "error",
                "Install-state default config resources are not owned by config_assembly/default_config.",
                {"owner": snapshot.install_default_config_owner},
            )
        )
    if snapshot.config_contexts_contains_default_resources:
        findings.append(
            _finding(
                "config_contexts_contract_view_boundary",
                "failed",
                "error",
                "config_contexts contains default config resources instead of contract views.",
                {"resources": snapshot.config_contexts_contains_default_resources},
            )
        )
    if snapshot.config_contexts_used_as_fact_source:
        findings.append(
            _finding(
                "config_contexts_contract_view_boundary",
                "failed",
                "error",
                "config_contexts is used as a configuration fact source.",
                {"usages": snapshot.config_contexts_used_as_fact_source},
            )
        )
    if snapshot.direct_root_config_consumers:
        findings.append(
            _finding(
                "config_single_source_of_truth",
                "failed",
                "error",
                "Packages consume private root config directly as stable configuration facts.",
                {"consumers": snapshot.direct_root_config_consumers},
            )
        )
    if snapshot.provider_profiles_without_config_contexts:
        findings.append(
            _finding(
                "provider_profile_config_boundary",
                "warning",
                "warning",
                "Provider or model profiles lack config_contexts contract view coverage.",
                {"profiles": snapshot.provider_profiles_without_config_contexts},
            )
        )
    if snapshot.provider_profiles_without_config_assembly_defaults:
        findings.append(
            _finding(
                "config_assembly_default_resource_boundary",
                "warning",
                "warning",
                "Provider or model profiles lack config_assembly default resource coverage.",
                {"profiles": snapshot.provider_profiles_without_config_assembly_defaults},
            )
        )
    if snapshot.public_repo_forbidden_config_paths:
        findings.append(
            _finding(
                "public_repository_config_boundary",
                "failed",
                "blocking",
                "Forbidden configuration paths appear in the public repository surface.",
                {"paths": snapshot.public_repo_forbidden_config_paths},
            )
        )
    if snapshot.secret_or_local_only_config_paths:
        findings.append(
            _finding(
                "public_repository_config_boundary",
                "failed",
                "blocking",
                "Secret or local-only configuration paths appear in publishable surfaces.",
                {"paths": snapshot.secret_or_local_only_config_paths},
            )
        )
    if snapshot.stable_config_consumption_without_contexts:
        findings.append(
            _finding(
                "config_fact_stable_consumption",
                "failed",
                "error",
                "Stable configuration consumption bypasses config_contexts review.",
                {"facts": snapshot.stable_config_consumption_without_contexts},
            )
        )

    status = _result_status(findings)
    return EvaluationResult(
        evaluation_id=evaluation_id,
        status=status,
        findings=findings,
        profile_ref=CONFIGURATION_BOUNDARY_EVALUATION_PROFILE,
        summary=(
            "Configuration boundary evaluation passed."
            if status == "passed"
            else "Configuration boundary evaluation produced findings."
        ),
        metadata={
            "config_ref": snapshot.config_ref,
            "evaluation_scope": "configuration_boundary",
            "governance_decision": False,
        },
    )


def _finding(
    criterion: str,
    status: str,
    severity: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> EvaluationFinding:
    return EvaluationFinding(
        criterion=criterion,
        status=status,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        message=message,
        metadata=metadata or {},
    )


def _result_status(findings: list[EvaluationFinding]) -> str:
    if not findings:
        return "passed"
    if any(finding.status == "failed" for finding in findings):
        return "failed"
    return "warning"


def _reject_forbidden_values(value: Any) -> None:
    if isinstance(value, str):
        lowered = value.lower()
        forbidden_markers = (
            " access_token",
            "api_key",
            "api_token",
            "auth_token",
            "credential",
            "private_key",
            "provider_token",
            "raw_provider_response",
            "refresh_token",
            "secret",
            "system_prompt",
            "_token.",
            "_token/",
            "_token=",
            "_token:",
            "_token.yaml",
            "/token",
            "token=",
            "token:",
            "traceback",
        )
        if any(marker in lowered for marker in forbidden_markers):
            raise ValueError("configuration boundary snapshot contains forbidden marker.")
    elif isinstance(value, dict):
        for item in value.values():
            _reject_forbidden_values(item)
    elif isinstance(value, list | tuple | set):
        for item in value:
            _reject_forbidden_values(item)
