"""Governance candidate behavior guards.

These guards describe safety invariants for governance candidates. They do not
execute release, runtime, policy, or governance actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


FORBIDDEN_RELEASE_ACTIONS = frozenset(
    {
        "release",
        "block",
        "pass",
        "publish",
        "upload",
        "twine_upload",
        "git_tag",
        "git_push",
        "github_release",
        "trusted_publishing",
    }
)

FORBIDDEN_RUNTIME_ACTIONS = frozenset(
    {
        "runtime_fix",
        "run_config_update",
        "service_bundle_update",
        "execute_workflow",
        "call_runtime_container",
        "call_composition",
        "call_adk_adapter",
    }
)

FORBIDDEN_RUNTIME_OBJECT_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "composition",
    "runtime_container",
)

SENSITIVE_OUTPUT_KEYS = frozenset(
    {
        "command_output",
        "command_outputs",
        "credential",
        "credentials",
        "env",
        "raw",
        "raw_output",
        "secret",
        "stderr",
        "stdout",
        "token",
    }
)

SENSITIVE_KEY_EXCEPTIONS = frozenset(
    {
        "raw_output_digest",
        "sensitive_fields_omitted",
        "token_presence_check_mode",
    }
)

PRODUCT_AGENT_OUTPUT_GOVERNANCE_POLICY_DOMAIN = "product_agent_output_governance"
PRODUCT_AGENT_OUTPUT_GOVERNANCE_CASE_TYPE = "product_agent_output_governance_review"
PRODUCT_AGENT_OUTPUT_GOVERNANCE_DECISION_CANDIDATE_SCOPE = (
    "product_agent_output_governance_decision_candidate"
)
PRODUCT_AGENT_OUTPUT_GOVERNANCE_ALLOWED_DOMAIN_METADATA_KEYS = frozenset(
    {
        "product_gateway_request_id",
        "product_gateway_entry_kind",
        "product_gateway_status",
        "product_gateway_exit_code",
        "agent_advice_candidate_id",
        "agent_advice_status",
        "agent_advice_recommendation",
        "ready_for_review",
        "evidence_statuses",
        "missing_evidence",
        "warning_candidates",
        "block_candidates",
        "human_review_reasons",
        "summary_only",
        "refs_only",
        "candidate_only",
    }
)
PRODUCT_AGENT_OUTPUT_GOVERNANCE_BOUNDARY_FLAGS = frozenset(
    {
        "summary_only",
        "refs_only",
        "candidate_only",
    }
)
PRODUCT_AGENT_OUTPUT_GOVERNANCE_FORBIDDEN_KEYS = frozenset(
    {
        "agent_task_advice_consumption_payload",
        "api_key",
        "artifact_content",
        "completion",
        "credential",
        "credentials",
        "full_response",
        "message",
        "messages",
        "payload",
        "product_gateway_request",
        "product_gateway_response",
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
        "system_prompt",
        "text",
        "token",
        "tool_context",
        "tool_input",
        "tool_output",
        "user_message",
    }
)
PRODUCT_AGENT_OUTPUT_GOVERNANCE_FORBIDDEN_ACTION_FIELDS = frozenset(
    {
        "action_kind",
        "can_publish",
        "can_release",
        "execution_result",
        "release_action_kind",
        "release_action_result",
        "runtime_action_kind",
        "tag_release_and_publish",
    }
)
PRODUCT_AGENT_OUTPUT_GOVERNANCE_FALSE_INVARIANT_FIELDS = (
    "execution_enabled",
    "formal_decision_enabled",
    "formal_outcome_enabled",
    "governance_outcome_enabled",
    "policy_execution_enabled",
    "release_action_enabled",
    "runtime_execution_enabled",
)
PRODUCT_AGENT_OUTPUT_GOVERNANCE_FORBIDDEN_RELEASE_REASON = (
    "Release action boundary review is pending."
)


@dataclass(frozen=True)
class CandidateGuardResult:
    """Result returned by a governance candidate guard."""

    passed: bool
    violations: tuple[str, ...] = field(default_factory=tuple)


class CandidateGuard:
    """Base class for non-executing governance candidate guards."""

    guard_name = "candidate_guard"

    def validate(self, candidate: Mapping[str, Any]) -> CandidateGuardResult:
        """Validate a candidate mapping without executing any action."""

        raise NotImplementedError

    def _result(self, violations: list[str]) -> CandidateGuardResult:
        return CandidateGuardResult(
            passed=not violations,
            violations=tuple(violations),
        )


class CandidateOnlyGuard(CandidateGuard):
    """Require explicit candidate-only semantics."""

    guard_name = "candidate_only_guard"

    _semantic_fields = (
        "action_semantics",
        "decision_semantics",
        "outcome_semantics",
        "review_semantics",
        "policy_status",
    )

    def validate(self, candidate: Mapping[str, Any]) -> CandidateGuardResult:
        values = [candidate.get(field_name) for field_name in self._semantic_fields]
        has_candidate_scope = bool(candidate.get("candidate_scope"))
        is_explicit_candidate = candidate.get("candidate_only") is True
        if "candidate_only" in values or has_candidate_scope or is_explicit_candidate:
            return self._result([])
        return self._result(["Candidate must declare candidate_only semantics."])


class NoExecutionGuard(CandidateGuard):
    """Ensure candidate objects cannot enable execution."""

    guard_name = "no_execution_guard"

    _false_invariant_fields = (
        "execution_enabled",
        "formal_decision_enabled",
        "formal_outcome_enabled",
        "governance_outcome_enabled",
        "policy_execution_enabled",
        "release_action_enabled",
        "runtime_execution_enabled",
    )

    def validate(self, candidate: Mapping[str, Any]) -> CandidateGuardResult:
        violations = [
            f"{field_name} must not be true."
            for field_name in self._false_invariant_fields
            if candidate.get(field_name) is True
        ]
        return self._result(violations)


class OperatorConfirmationRequiredGuard(CandidateGuard):
    """Require operator confirmation before any external action boundary."""

    guard_name = "operator_confirmation_required_guard"

    def validate(self, candidate: Mapping[str, Any]) -> CandidateGuardResult:
        if candidate.get("requires_operator_confirmation") is True:
            return self._result([])
        return self._result(["requires_operator_confirmation must be true."])


class ReviewerExecutorSeparationGuard(CandidateGuard):
    """Require reviewer and executor identities to remain separate."""

    guard_name = "reviewer_executor_separation_guard"

    def validate(self, candidate: Mapping[str, Any]) -> CandidateGuardResult:
        reviewer = candidate.get("reviewer")
        executor = candidate.get("executor")
        if reviewer and executor and reviewer == executor:
            return self._result(["reviewer and executor must be separate."])
        return self._result([])


class NoReleaseActionGuard(CandidateGuard):
    """Reject formal release, block, pass, and publishing action names."""

    guard_name = "no_release_action_guard"

    def validate(self, candidate: Mapping[str, Any]) -> CandidateGuardResult:
        values = _candidate_action_values(candidate)
        forbidden = sorted(value for value in values if value in FORBIDDEN_RELEASE_ACTIONS)
        return self._result(
            [f"Release action is forbidden: {value}." for value in forbidden]
        )


class NoRuntimeActionGuard(CandidateGuard):
    """Reject formal runtime fix and runtime update action names."""

    guard_name = "no_runtime_action_guard"

    def validate(self, candidate: Mapping[str, Any]) -> CandidateGuardResult:
        values = _candidate_action_values(candidate)
        forbidden = sorted(value for value in values if value in FORBIDDEN_RUNTIME_ACTIONS)
        return self._result(
            [f"Runtime action is forbidden: {value}." for value in forbidden]
        )


class NoAdkNativeObjectLeakageGuard(CandidateGuard):
    """Reject ADK and execution-layer object leakage."""

    guard_name = "no_adk_native_object_leakage_guard"

    def validate(self, candidate: Mapping[str, Any]) -> CandidateGuardResult:
        violations = [
            f"Runtime object leakage is forbidden at {path}."
            for path, value in _walk(candidate)
            if _is_runtime_object(value)
        ]
        return self._result(violations)


class SensitiveOutputRedactionGuard(CandidateGuard):
    """Reject raw or sensitive output fields in public candidate boundaries."""

    guard_name = "sensitive_output_redaction_guard"

    def validate(self, candidate: Mapping[str, Any]) -> CandidateGuardResult:
        violations = [
            f"Sensitive output key is forbidden at {path}."
            for path, _value in _walk(candidate)
            if _is_sensitive_path(path)
        ]
        return self._result(violations)


class ProductAgentOutputGovernanceDomainGuard(CandidateGuard):
    """Enforce product-agent output governance candidate boundaries."""

    guard_name = "product_agent_output_governance_domain_guard"

    def validate(self, candidate: Mapping[str, Any]) -> CandidateGuardResult:
        if not _is_product_agent_output_governance_candidate(candidate):
            return self._result([])

        violations: list[str] = []
        domain_metadata = candidate.get("domain_metadata", {})
        if "domain_metadata" in candidate and not isinstance(domain_metadata, Mapping):
            violations.append("domain_metadata must be a mapping.")
        elif isinstance(domain_metadata, Mapping):
            unexpected_keys = sorted(
                str(key)
                for key in domain_metadata
                if str(key)
                not in PRODUCT_AGENT_OUTPUT_GOVERNANCE_ALLOWED_DOMAIN_METADATA_KEYS
            )
            violations.extend(
                f"Product-agent domain_metadata key is not allowed: {key}."
                for key in unexpected_keys
            )
            for flag in PRODUCT_AGENT_OUTPUT_GOVERNANCE_BOUNDARY_FLAGS:
                if flag in domain_metadata and domain_metadata.get(flag) is not True:
                    violations.append(f"{flag} must be true for product-agent candidates.")

        violations.extend(
            f"{field_name} must not be true for product-agent candidates."
            for field_name in PRODUCT_AGENT_OUTPUT_GOVERNANCE_FALSE_INVARIANT_FIELDS
            if candidate.get(field_name) is True
        )

        for path, value in _walk(candidate):
            key = _path_key(path)
            if key in PRODUCT_AGENT_OUTPUT_GOVERNANCE_FORBIDDEN_KEYS:
                violations.append(
                    f"Product-agent raw or sensitive key is forbidden at {path}."
                )
            if key in PRODUCT_AGENT_OUTPUT_GOVERNANCE_FORBIDDEN_ACTION_FIELDS:
                violations.append(
                    f"Product-agent action field is forbidden at {path}."
                )
            if (
                isinstance(value, str)
                and PRODUCT_AGENT_OUTPUT_GOVERNANCE_FORBIDDEN_RELEASE_REASON in value
            ):
                violations.append(
                    "Product-agent candidate must not use release action boundary "
                    f"reason at {path}."
                )

        return self._result(violations)


DEFAULT_GOVERNANCE_CANDIDATE_GUARDS = (
    CandidateOnlyGuard(),
    NoExecutionGuard(),
    OperatorConfirmationRequiredGuard(),
    ReviewerExecutorSeparationGuard(),
    NoReleaseActionGuard(),
    NoRuntimeActionGuard(),
    ProductAgentOutputGovernanceDomainGuard(),
    NoAdkNativeObjectLeakageGuard(),
    SensitiveOutputRedactionGuard(),
)


def validate_governance_candidate_guards(
    candidate: Mapping[str, Any],
    guards: tuple[CandidateGuard, ...] = DEFAULT_GOVERNANCE_CANDIDATE_GUARDS,
) -> CandidateGuardResult:
    """Run candidate guards and return a combined non-executing result."""

    violations: list[str] = []
    for guard in guards:
        result = guard.validate(candidate)
        violations.extend(f"{guard.guard_name}: {item}" for item in result.violations)
    return CandidateGuardResult(
        passed=not violations,
        violations=tuple(violations),
    )


def _candidate_action_values(candidate: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("action_kind", "decision", "runtime_action_kind", "release_action_kind"):
        value = candidate.get(key)
        if isinstance(value, str):
            values.add(value.lower())
    for key in ("allowed_action_kinds", "forbidden_action_kinds"):
        value = candidate.get(key)
        if isinstance(value, (list, tuple, set)):
            values.update(item.lower() for item in value if isinstance(item, str))
    return values


def _walk(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, Mapping):
        for key, item in value.items():
            items.extend(_walk(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            items.extend(_walk(item, f"{path}[{index}]"))
    return items


def _is_runtime_object(value: Any) -> bool:
    if isinstance(value, Mapping):
        module_name = value.get("object_module")
        return isinstance(module_name, str) and module_name.startswith(
            FORBIDDEN_RUNTIME_OBJECT_MODULE_PREFIXES
        )
    if value is None or isinstance(value, (str, int, float, bool, list, tuple, dict)):
        return False
    return type(value).__module__.startswith(FORBIDDEN_RUNTIME_OBJECT_MODULE_PREFIXES)


def _is_sensitive_path(path: str) -> bool:
    key = path.rsplit(".", maxsplit=1)[-1].lower()
    if key in SENSITIVE_KEY_EXCEPTIONS:
        return False
    return (
        key in SENSITIVE_OUTPUT_KEYS
        or key.endswith("_token")
        or key.endswith("_credential")
        or key.endswith("_secret")
    )


def _is_product_agent_output_governance_candidate(
    candidate: Mapping[str, Any],
) -> bool:
    return (
        candidate.get("policy_domain") == PRODUCT_AGENT_OUTPUT_GOVERNANCE_POLICY_DOMAIN
        or candidate.get("case_type") == PRODUCT_AGENT_OUTPUT_GOVERNANCE_CASE_TYPE
        or candidate.get("candidate_scope")
        == PRODUCT_AGENT_OUTPUT_GOVERNANCE_DECISION_CANDIDATE_SCOPE
    )


def _path_key(path: str) -> str:
    key = path.rsplit(".", maxsplit=1)[-1]
    if "[" in key:
        key = key.split("[", maxsplit=1)[0]
    return key.lower()
