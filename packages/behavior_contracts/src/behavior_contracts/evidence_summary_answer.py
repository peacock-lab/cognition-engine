"""Behavior guards for evidence summary answer contracts."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import TYPE_CHECKING, Any, Protocol

from behavior_contracts.governance_candidate import CandidateGuardResult
from schemas.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_CONTEXT_PAYLOAD_TYPE,
    EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION,
    EVIDENCE_SUMMARY_ANSWER_PRODUCT,
    EVIDENCE_SUMMARY_ANSWER_RESULT_PAYLOAD_TYPE,
    EVIDENCE_SUMMARY_ANSWER_RESULT_STATUSES,
    EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION,
    EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
    FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_KEYS,
    FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_OBJECT_MODULE_PREFIXES,
    GOVERNED_EVIDENCE_ANSWERABILITY_VALUES,
    GOVERNED_EVIDENCE_DIGEST_PAYLOAD_TYPE,
    GOVERNED_EVIDENCE_DIGEST_REF_PREFIX,
    GOVERNED_EVIDENCE_DIGEST_STATUSES,
    GOVERNED_EVIDENCE_DIGEST_VERSION,
)


if TYPE_CHECKING:
    from behavior_contracts.llm_invocation import GovernedLlmInvocationService
    from schemas.evidence_summary_answer import (
        EvidenceSummaryAnswerContextSchema,
        EvidenceSummaryAnswerResultSchema,
    )
    from schemas.llm_invocation import LlmGovernancePrecondition
    from schemas.model_routing import ModelRouteFacts


EVIDENCE_SUMMARY_ANSWER_PAYLOAD_VERSIONS = {
    GOVERNED_EVIDENCE_DIGEST_PAYLOAD_TYPE: GOVERNED_EVIDENCE_DIGEST_VERSION,
    EVIDENCE_SUMMARY_ANSWER_CONTEXT_PAYLOAD_TYPE: (
        EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION
    ),
    EVIDENCE_SUMMARY_ANSWER_RESULT_PAYLOAD_TYPE: (
        EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION
    ),
}

EVIDENCE_SUMMARY_ANSWER_PAYLOAD_TYPES = frozenset(
    EVIDENCE_SUMMARY_ANSWER_PAYLOAD_VERSIONS
)

EVIDENCE_SUMMARY_ANSWER_FORBIDDEN_CONTEXT_FIELDS = frozenset(
    {
        "additional_refs_used",
        "answer",
        "answer_preview",
        "citation_failures",
        "digest_refs_used",
        "evidence_refs_used",
        "insufficient_evidence_reason",
        "llm_call_allowed",
        "llm_call_attempted",
        "llm_runtime_call_performed",
        "messages",
        "prompt",
        "system_prompt",
    }
)

STRING_MARKER_EXEMPT_PATHS = frozenset(
    {
        "$.answer",
        "$.answer_preview",
        "$.insufficient_evidence_reason",
        "$.user_question",
    }
)

EVIDENCE_SUMMARY_ANSWER_GENERATION_PROFILES = frozenset(
    {"smoke_only", "controlled_live_answer_generation"}
)

EVIDENCE_SUMMARY_ANSWER_QUALITY_BLOCKING_REASON = (
    "llm_answer_quality_contract_violation"
)

EVIDENCE_SUMMARY_ANSWER_VISIBLE_REASONING_KEYS = frozenset(
    {
        "analysis",
        "chain_of_thought",
        "internal_reasoning",
        "internal_thought",
        "reasoning",
        "scratchpad",
        "thought",
    }
)

EVIDENCE_SUMMARY_ANSWER_VISIBLE_REASONING_LABEL_RE = re.compile(
    r"^\s*(?:analysis|chain[-_ ]?of[-_ ]?thought|internal[-_ ]?reasoning|"
    r"internal[-_ ]?thought|reasoning|scratchpad|thought)\s*[:：]",
    re.IGNORECASE,
)

EVIDENCE_SUMMARY_ANSWER_VISIBLE_REASONING_KEY_RE = re.compile(
    r"(?:^|[{,\s])[\"']?(?:analysis|chain[-_ ]?of[-_ ]?thought|"
    r"internal[-_ ]?reasoning|internal[-_ ]?thought|reasoning|scratchpad|"
    r"thought)[\"']?\s*[:：]",
    re.IGNORECASE,
)

EVIDENCE_SUMMARY_ANSWER_PROMPT_INSTRUCTION_LEAKAGE_RE = re.compile(
    r"(?:"
    r"^\s*(?:我|我们)\s*(?:被问到|被问及|需要回答|要回答|来回答)"
    r"|^\s*(?:我|我们)\s*(?:被)?要求"
    r"|^\s*(?:I|we)\s+(?:am|are|was|were)\s+asked"
    r"|^\s*(?:I|we)\s+(?:am|are|was|were)\s+given\s+"
    r"(?:summary\s+facts|evidence|the\s+summary)"
    r"|^\s*the\s+question\s+is\s*[:：]"
    r"|"
    r"(?:我|我们|模型|系统|助手|AI)\s*(?:被)?要求.*?"
    r"(?:只返回|不输出|不要输出|最终的用户|用户自然语言|JSON|YAML|代码块|分析|推理|思考)"
    r"|(?:I|we|the\s+model|the\s+assistant)\s+"
    r"(?:am|are|was|were)\s+(?:asked|required|instructed)\s+to"
    r"|(?:the\s+prompt|the\s+instruction)\s+(?:asks|requires|instructs)"
    r")",
    re.IGNORECASE,
)

EVIDENCE_SUMMARY_ANSWER_LLM_REQUEST_METADATA_KEYS = frozenset(
    {
        "answerable_digest_count",
        "context_payload_type",
        "context_payload_version",
        "digest_count",
        "evidence_summary_answer_context",
        "generation_profile",
        "interaction_mode",
        "no_fetch_search",
        "policy_ref",
        "refs_source",
        "service_ref",
        "smoke_only",
        "source",
    }
)

EVIDENCE_SUMMARY_ANSWER_GENERATION_RESULT_METADATA_KEYS = frozenset(
    {
        "answerable_digest_count",
        "context_payload_type",
        "context_payload_version",
        "digest_count",
        "generation_profile",
        "llm_failure_type",
        "llm_request_id",
        "llm_route_model",
        "llm_route_provider",
        "no_fetch_search",
        "policy_ref",
        "refs_source",
        "service_ref",
        "smoke_only",
        "source",
    }
)

EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_PAYLOAD_TYPE = (
    "evidence_summary_answer_outcome_observation_readonly_public_refs"
)
EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_VERSION = (
    "evidence_summary_answer_outcome_observation_readonly_public_refs_v1"
)
EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_STATUSES = (
    frozenset({"success", "insufficient_evidence", "blocked", "failed", "mixed", "empty"})
)
EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_REF_PREFIX = (
    "evidence-summary-answer-outcome-observation://"
)
EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_FACTS_KEY = (
    "evidence_summary_answer_outcome_observation_readonly_facts"
)
EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_PUBLIC_FORBIDDEN_METADATA_KEYS = (
    "answer",
    "answer_preview",
    "authorization",
    "body",
    "candidate_body",
    "config_context",
    "config_context_value",
    "cookie",
    "credential",
    "full_product_gateway_response",
    "header",
    "html",
    "message",
    "observability_candidate_body",
    "password",
    "payload",
    "productgatewayresponse",
    "prompt",
    "provider",
    "raw",
    "response",
    "sanitized_excerpt_preview",
    "secret",
    "summary_facts",
    "system_prompt",
    "token",
    "user_question",
)
EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_PUBLIC_FORBIDDEN_METADATA_VALUES = (
    "authorization",
    "composition",
    "cookie",
    "google.adk",
    "litellm",
    "message",
    "observability_candidate_body",
    "observability_hub",
    "password",
    "product_gateway",
    "productgatewayresponse",
    "prompt",
    "provider_payload",
    "provider_response",
    "raw payload",
    "raw provider response",
    "raw_html",
    "raw_payload",
    "raw_provider_response",
    "raw_response",
    "response_headers",
    "response_text",
    "runtime_container",
    "sanitized_excerpt_preview",
    "secret",
    "token",
)
EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_PUBLIC_FORBIDDEN_PAYLOAD_KEYS = (
    frozenset(
        {
            "answer",
            "answer_preview",
            "complete_context",
            "complete_digest",
            "complete_result",
            "config_context",
            "config_context_value",
            "full_product_gateway_response",
            "full_response",
            "messages",
            "observability_candidate_body",
            "productgatewayresponse",
            "prompt",
            "provider_payload",
            "provider_response",
            "raw_payload",
            "raw_provider_response",
            "raw_response",
            "sanitized_excerpt_preview",
            "summary_facts",
            "system_prompt",
            "user_question",
        }
    )
)


@dataclass(frozen=True)
class EvidenceSummaryAnswerOutcomeObservationReadonlyFacts:
    """Readonly public facts for evidence-summary-answer outcome observations."""

    observation_candidate_ids: tuple[str, ...]
    request_ids: tuple[str, ...]
    result_statuses: tuple[str, ...]
    status: str
    external_readonly_evidence_refs: tuple[str, ...]
    governed_evidence_digest_refs: tuple[str, ...]
    candidate_count: int
    request_count: int
    evidence_ref_count: int
    digest_ref_count: int
    summary_fact_count: int
    schema_validation_passed: bool
    schema_validation_error_count: int
    guard_validation_passed: bool | None
    guard_violation_count: int
    guard_names: tuple[str, ...] = ()
    answer_present: bool = False
    answer_preview_present: bool = False
    raw_boundary_violation_count: int = 0
    blocking_reasons: tuple[str, ...] = ()
    citation_failures: tuple[str, ...] = ()
    policy_profile: str | None = None
    policy_ref: str | None = None
    config_source_ref: str | None = None
    readonly: bool = True
    candidate_only: bool = True
    does_not_store_answer: bool = True
    does_not_store_user_question: bool = True
    does_not_store_summary_facts: bool = True
    does_not_store_raw_payload: bool = True
    does_not_store_provider_raw_response: bool = True
    does_not_store_sanitized_excerpt_preview: bool = True
    does_not_store_config_context_value: bool = True
    does_not_call_model: bool = True
    does_not_fetch_or_search: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceSummaryAnswerOutcomeObservationReadonlyPublicRefs:
    """Stable public refs/facts contract for answer outcome observations."""

    payload_type: str
    payload_version: str
    evidence_summary_answer_outcome_observation_refs: tuple[str, ...]
    external_readonly_evidence_refs: tuple[str, ...]
    governed_evidence_digest_refs: tuple[str, ...]
    facts: EvidenceSummaryAnswerOutcomeObservationReadonlyFacts
    readonly: bool = True
    refs_only: bool = True
    candidate_only: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class EvidenceSummaryAnswerGenerationService(Protocol):
    """Protocol for evidence-summary-answer generation orchestration."""

    def generate(
        self,
        context: "EvidenceSummaryAnswerContextSchema | Mapping[str, Any]",
        *,
        llm_invocation_service: "GovernedLlmInvocationService | None" = None,
        generation_policy: Mapping[str, Any] | None = None,
        route_facts: "ModelRouteFacts | None" = None,
        governance_precondition: "LlmGovernancePrecondition | None" = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "EvidenceSummaryAnswerResultSchema":
        """Return an evidence-summary-answer result from governed public inputs."""
        ...


class EvidenceSummaryAnswerHeaderGuard:
    """Validate frozen evidence summary answer payload headers."""

    guard_name = "evidence_summary_answer_header_guard"

    def validate(self, payload: Mapping[str, Any]) -> CandidateGuardResult:
        violations: list[str] = []
        if payload.get("product") != EVIDENCE_SUMMARY_ANSWER_PRODUCT:
            violations.append(
                f"product must be {EVIDENCE_SUMMARY_ANSWER_PRODUCT}."
            )

        payload_type = payload.get("payload_type")
        if payload_type not in EVIDENCE_SUMMARY_ANSWER_PAYLOAD_TYPES:
            violations.append(
                f"unsupported evidence-summary-answer payload_type: {payload_type}."
            )
            return _result(violations)

        expected_version = EVIDENCE_SUMMARY_ANSWER_PAYLOAD_VERSIONS[payload_type]
        if payload.get("payload_version") != expected_version:
            violations.append(f"payload_version must be {expected_version}.")

        if payload_type == GOVERNED_EVIDENCE_DIGEST_PAYLOAD_TYPE:
            _require_string_fields(
                payload,
                ("digest_id", "digest_ref", "evidence_ref", "status", "answerability"),
                violations,
            )
            status = payload.get("status")
            if (
                isinstance(status, str)
                and status not in GOVERNED_EVIDENCE_DIGEST_STATUSES
            ):
                violations.append(f"unsupported digest status: {status}.")
            answerability = payload.get("answerability")
            if isinstance(answerability, str) and (
                answerability not in GOVERNED_EVIDENCE_ANSWERABILITY_VALUES
            ):
                violations.append(f"unsupported digest answerability: {answerability}.")
        elif payload_type == EVIDENCE_SUMMARY_ANSWER_CONTEXT_PAYLOAD_TYPE:
            _require_string_fields(payload, ("request_id", "user_question"), violations)
        elif payload_type == EVIDENCE_SUMMARY_ANSWER_RESULT_PAYLOAD_TYPE:
            _require_string_fields(payload, ("request_id", "status"), violations)
            status = payload.get("status")
            if (
                isinstance(status, str)
                and status not in EVIDENCE_SUMMARY_ANSWER_RESULT_STATUSES
            ):
                violations.append(f"unsupported answer result status: {status}.")
        return _result(violations)


class EvidenceSummaryAnswerNoRawBoundaryGuard:
    """Reject raw, provider, config, prompt, and runtime boundary leakage."""

    guard_name = "evidence_summary_answer_no_raw_boundary_guard"

    def validate(self, payload: Mapping[str, Any]) -> CandidateGuardResult:
        violations: list[str] = []
        for path, value in _walk(payload):
            if _is_runtime_boundary(path, value):
                violations.append(f"runtime object leakage is forbidden at {path}.")
            elif _is_raw_boundary(path, value):
                violations.append(f"raw boundary field is forbidden at {path}.")
        for path, value in _walk(payload):
            if _key_at_path(path) == "raw_boundary_flags" and isinstance(
                value, Mapping
            ):
                violations.extend(_raw_boundary_flag_violations(path, value))
        return _result(violations)


class EvidenceSummaryAnswerDigestGuard:
    """Validate behavior constraints for governed evidence digests."""

    guard_name = "evidence_summary_answer_digest_guard"

    def validate(self, payload: Mapping[str, Any]) -> CandidateGuardResult:
        if payload.get("payload_type") != GOVERNED_EVIDENCE_DIGEST_PAYLOAD_TYPE:
            return _result([])

        violations: list[str] = []
        digest_ref = payload.get("digest_ref")
        if not isinstance(digest_ref, str) or not digest_ref.startswith(
            GOVERNED_EVIDENCE_DIGEST_REF_PREFIX
        ):
            violations.append(
                "digest_ref must start with "
                f"{GOVERNED_EVIDENCE_DIGEST_REF_PREFIX}."
            )
        evidence_ref = payload.get("evidence_ref")
        if not isinstance(evidence_ref, str) or not evidence_ref.startswith(
            EXTERNAL_READONLY_EVIDENCE_REF_PREFIX
        ):
            violations.append(
                "evidence_ref must start with "
                f"{EXTERNAL_READONLY_EVIDENCE_REF_PREFIX}."
            )
        if payload.get("status") == "blocked" and not _has_nonempty_string_item(
            payload.get("blocking_reasons")
        ):
            violations.append("blocked digests require blocking_reasons.")

        if payload.get("answerability") == "answerable":
            if payload.get("allowed_for_model_context") is not True:
                violations.append(
                    "answerable digests require allowed_for_model_context=true."
                )
            if not _has_nonempty_string_item(payload.get("summary_facts")):
                violations.append("answerable digests require summary_facts.")
            if _raw_boundary_flags_any_true(payload.get("raw_boundary_flags")):
                violations.append(
                    "answerable digests cannot include raw boundary flags."
                )

        source_url_host = payload.get("source_url_host")
        if isinstance(source_url_host, str) and _host_has_path_or_query(
            source_url_host
        ):
            violations.append(
                "source_url_host must be a host without scheme, path, or query."
            )

        summary_facts = payload.get("summary_facts")
        if isinstance(summary_facts, (list, tuple)):
            for index, fact in enumerate(summary_facts):
                if isinstance(fact, str) and _looks_like_forbidden_marker(fact):
                    violations.append(
                        f"summary_facts[{index}] contains forbidden boundary marker."
                    )
        return _result(violations)


class EvidenceSummaryAnswerContextGuard:
    """Validate behavior constraints for answer contexts."""

    guard_name = "evidence_summary_answer_context_guard"

    def validate(self, payload: Mapping[str, Any]) -> CandidateGuardResult:
        if payload.get("payload_type") != EVIDENCE_SUMMARY_ANSWER_CONTEXT_PAYLOAD_TYPE:
            return _result([])

        violations: list[str] = []
        _require_string_fields(payload, ("request_id", "user_question"), violations)

        for key in sorted(EVIDENCE_SUMMARY_ANSWER_FORBIDDEN_CONTEXT_FIELDS):
            if key in payload:
                violations.append(f"{key} is forbidden in answer context.")

        digests = payload.get("digests")
        if not isinstance(digests, (list, tuple)) or not digests:
            violations.append("answer contexts require at least one digest.")
            digests = ()

        evidence_refs = payload.get("evidence_refs")
        if not isinstance(evidence_refs, (list, tuple)):
            violations.append("evidence_refs must be a list.")
            evidence_refs = ()

        digest_evidence_refs = {
            digest.get("evidence_ref")
            for digest in digests
            if isinstance(digest, Mapping)
            and isinstance(digest.get("evidence_ref"), str)
        }
        provided_refs = {
            ref.get("ref")
            for ref in evidence_refs
            if isinstance(ref, Mapping) and isinstance(ref.get("ref"), str)
        }
        missing = sorted(digest_evidence_refs - provided_refs)
        if missing:
            violations.append(
                "evidence_refs must cover digest evidence_ref values: "
                + ", ".join(missing)
            )
        return _result(violations)


class EvidenceSummaryAnswerGenerationPolicyGuard:
    """Validate policy facts before real answer generation can be attempted."""

    guard_name = "evidence_summary_answer_generation_policy_guard"

    def validate(self, policy: Mapping[str, Any]) -> CandidateGuardResult:
        violations: list[str] = []
        if not isinstance(policy, Mapping):
            return _result(["generation policy must be a mapping."])

        violations.extend(_raw_or_runtime_boundary_violations(policy))

        profile = policy.get("profile", "smoke_only")
        if not isinstance(profile, str) or (
            profile not in EVIDENCE_SUMMARY_ANSWER_GENERATION_PROFILES
        ):
            violations.append(f"unsupported generation profile: {profile}.")

        allow_success = policy.get("allow_answer_generation_success", False)
        if not isinstance(allow_success, bool):
            violations.append("allow_answer_generation_success must be a boolean.")
            allow_success = False

        if policy.get("enabled_by_default") is True:
            violations.append("answer generation must not be enabled by default.")
        _require_policy_value(policy, "allow_governed_summary_facts", True, violations)
        _reject_policy_value(policy, "allow_raw_boundary", True, violations)
        _reject_policy_value(
            policy,
            "allow_sanitized_excerpt_preview",
            True,
            violations,
        )
        _reject_policy_value(
            policy,
            "allow_observability_candidate_body",
            True,
            violations,
        )
        _reject_policy_value(policy, "allow_citation_exception", True, violations)
        _require_policy_value(policy, "citation_required", True, violations)
        _require_policy_value(policy, "insufficient_evidence_required", True, violations)
        _require_policy_value(policy, "requires_live_llm_gate", True, violations)

        if profile == "smoke_only" and allow_success:
            violations.append("smoke_only profile cannot allow generation success.")

        if allow_success:
            if profile != "controlled_live_answer_generation":
                violations.append(
                    "allow_answer_generation_success requires "
                    "controlled_live_answer_generation profile."
                )
            _require_string_fields(
                policy,
                (
                    "answer_generation_service_ref",
                    "llm_provider_factory_ref",
                    "answer_policy_ref",
                    "citation_policy_ref",
                ),
                violations,
            )
        return _result(violations)


class EvidenceSummaryAnswerGenerationPreflightGuard:
    """Validate context and policy facts before generation enters an LLM boundary."""

    guard_name = "evidence_summary_answer_generation_preflight_guard"

    def validate(
        self,
        context: Mapping[str, Any],
        *,
        generation_policy: Mapping[str, Any] | None = None,
    ) -> CandidateGuardResult:
        violations: list[str] = []
        if not isinstance(context, Mapping):
            return _result(["generation context must be a mapping."])

        context_result = EvidenceSummaryAnswerContextGuard().validate(context)
        violations.extend(context_result.violations)
        violations.extend(_raw_or_runtime_boundary_violations(context))

        if not _has_answerable_generation_digest(context.get("digests")):
            violations.append(
                "answer generation requires an answerable governed evidence "
                "digest with allowed_for_model_context=true."
            )

        if generation_policy is not None:
            policy_result = EvidenceSummaryAnswerGenerationPolicyGuard().validate(
                generation_policy
            )
            violations.extend(policy_result.violations)
            if generation_policy.get("allow_answer_generation_success") is not True:
                violations.append(
                    "generation policy must explicitly allow answer generation "
                    "success."
                )

        return _result(violations)


class EvidenceSummaryAnswerLlmRequestBoundaryGuard:
    """Validate governed LLM request facts for evidence-summary-answer generation."""

    guard_name = "evidence_summary_answer_llm_request_boundary_guard"

    def validate(self, request: Mapping[str, Any]) -> CandidateGuardResult:
        violations: list[str] = []
        if not isinstance(request, Mapping):
            return _result(["LLM invocation request facts must be a mapping."])

        _require_string_fields(request, ("request_id",), violations)
        if not isinstance(request.get("route_facts"), Mapping):
            violations.append("route_facts must be a mapping.")
        if not isinstance(request.get("governance_precondition"), Mapping):
            violations.append("governance_precondition must be a mapping.")

        prompt_ref = request.get("prompt_ref")
        if prompt_ref is not None and not (
            isinstance(prompt_ref, str)
            and prompt_ref.startswith("prompt://evidence-summary-answer/")
        ):
            violations.append(
                "prompt_ref must be an opaque evidence-summary-answer prompt ref."
            )

        prompt_preview = request.get("prompt_preview_sanitized")
        if prompt_preview is not None and not isinstance(prompt_preview, str):
            violations.append("prompt_preview_sanitized must be a string.")
        if isinstance(prompt_preview, str) and len(prompt_preview) > 80:
            violations.append("prompt_preview_sanitized must not exceed 80 chars.")

        metadata = request.get("metadata", {})
        if not isinstance(metadata, Mapping):
            violations.append("metadata must be a mapping.")
        else:
            violations.extend(
                _metadata_key_allowlist_violations(
                    metadata,
                    EVIDENCE_SUMMARY_ANSWER_LLM_REQUEST_METADATA_KEYS,
                    path="$.metadata",
                )
            )
            if "external_readonly_answer_context" in metadata:
                violations.append(
                    "external_readonly_answer_context is a CLI smoke field and "
                    "is forbidden in generation request metadata."
                )
            if "product_response_summary" in metadata:
                violations.append(
                    "product_response_summary is forbidden in generation request "
                    "metadata."
                )

        violations.extend(_raw_or_runtime_boundary_violations(request))
        return _result(violations)


class EvidenceSummaryAnswerResultCitationGuard:
    """Validate citation and terminal-state constraints for answer results."""

    guard_name = "evidence_summary_answer_result_citation_guard"

    def validate(self, payload: Mapping[str, Any]) -> CandidateGuardResult:
        if payload.get("payload_type") != EVIDENCE_SUMMARY_ANSWER_RESULT_PAYLOAD_TYPE:
            return _result([])

        violations: list[str] = []
        status = payload.get("status")
        if status == "success":
            if not _is_nonempty_string(payload.get("answer")):
                violations.append("successful answer results require answer.")
            if not _has_mapping_item(payload.get("evidence_refs_used")):
                violations.append(
                    "successful answer results require evidence_refs_used."
                )
        elif status == "insufficient_evidence":
            if not _is_nonempty_string(payload.get("insufficient_evidence_reason")):
                violations.append(
                    "insufficient_evidence results require "
                    "insufficient_evidence_reason."
                )
            if _is_nonempty_string(payload.get("answer")):
                violations.append(
                    "insufficient_evidence results must not carry success-style answer."
                )
        elif status == "blocked":
            if not _has_nonempty_string_item(payload.get("blocking_reasons")):
                violations.append("blocked answer results require blocking_reasons.")
            if _is_nonempty_string(payload.get("answer")):
                violations.append("blocked answer results must not carry answer.")
        elif status == "failed":
            if not (
                _has_nonempty_string_item(payload.get("blocking_reasons"))
                or _has_nonempty_string_item(payload.get("citation_failures"))
            ):
                violations.append(
                    "failed answer results require blocking_reasons or "
                    "citation_failures."
                )
        return _result(violations)


class EvidenceSummaryAnswerResultRuntimeFlagsGuard:
    """Validate answer result runtime flag consistency."""

    guard_name = "evidence_summary_answer_result_runtime_flags_guard"

    def validate(self, payload: Mapping[str, Any]) -> CandidateGuardResult:
        if payload.get("payload_type") != EVIDENCE_SUMMARY_ANSWER_RESULT_PAYLOAD_TYPE:
            return _result([])

        violations: list[str] = []
        llm_call_allowed = payload.get("llm_call_allowed")
        llm_call_attempted = payload.get("llm_call_attempted")
        llm_runtime_call_performed = payload.get("llm_runtime_call_performed")
        if llm_runtime_call_performed is True and not (
            llm_call_allowed is True and llm_call_attempted is True
        ):
            violations.append(
                "llm_runtime_call_performed requires llm_call_allowed and "
                "llm_call_attempted."
            )
        if llm_call_attempted is True and llm_call_allowed is not True:
            violations.append("llm_call_attempted requires llm_call_allowed.")
        if payload.get("status") in {"blocked", "insufficient_evidence"} and (
            llm_runtime_call_performed is True
        ):
            violations.append(
                "blocked or insufficient_evidence results must not report "
                "llm_runtime_call_performed."
            )
        return _result(violations)


class EvidenceSummaryAnswerResultQualityGuard:
    """Validate user-facing answer text quality for successful results."""

    guard_name = "evidence_summary_answer_result_quality_guard"

    def validate(self, payload: Mapping[str, Any]) -> CandidateGuardResult:
        if payload.get("payload_type") != EVIDENCE_SUMMARY_ANSWER_RESULT_PAYLOAD_TYPE:
            return _result([])
        if payload.get("status") != "success":
            return _result([])
        return validate_evidence_summary_answer_answer_quality(payload.get("answer"))


class EvidenceSummaryAnswerResultMappingGuard:
    """Validate generation-specific answer result mapping constraints."""

    guard_name = "evidence_summary_answer_result_mapping_guard"

    def validate(self, payload: Mapping[str, Any]) -> CandidateGuardResult:
        if payload.get("payload_type") != EVIDENCE_SUMMARY_ANSWER_RESULT_PAYLOAD_TYPE:
            return _result([])

        violations: list[str] = []
        if payload.get("status") == "success":
            if not _has_nonempty_string_item(payload.get("digest_refs_used")):
                violations.append(
                    "successful generated answer results require digest_refs_used."
                )
            if payload.get("llm_call_allowed") is not True:
                violations.append(
                    "successful generated answer results require "
                    "llm_call_allowed=true."
                )
            if payload.get("llm_call_attempted") is not True:
                violations.append(
                    "successful generated answer results require "
                    "llm_call_attempted=true."
                )
            if payload.get("llm_runtime_call_performed") is not True:
                violations.append(
                    "successful generated answer results require "
                    "llm_runtime_call_performed=true."
                )
            if _has_nonempty_string_item(payload.get("citation_failures")):
                violations.append(
                    "successful generated answer results must not carry "
                    "citation_failures."
                )

            metadata = payload.get("metadata", {})
            if not isinstance(metadata, Mapping):
                violations.append("metadata must be a mapping.")
            else:
                violations.extend(
                    _metadata_key_allowlist_violations(
                        metadata,
                        EVIDENCE_SUMMARY_ANSWER_GENERATION_RESULT_METADATA_KEYS,
                        path="$.metadata",
                    )
                )
        return _result(violations)


DEFAULT_EVIDENCE_SUMMARY_ANSWER_GUARDS = (
    EvidenceSummaryAnswerHeaderGuard(),
    EvidenceSummaryAnswerNoRawBoundaryGuard(),
    EvidenceSummaryAnswerDigestGuard(),
    EvidenceSummaryAnswerContextGuard(),
    EvidenceSummaryAnswerResultCitationGuard(),
    EvidenceSummaryAnswerResultRuntimeFlagsGuard(),
    EvidenceSummaryAnswerResultQualityGuard(),
)


def validate_evidence_summary_answer_guards(
    payload: Mapping[str, Any],
    guards: tuple[
        EvidenceSummaryAnswerHeaderGuard
        | EvidenceSummaryAnswerNoRawBoundaryGuard
        | EvidenceSummaryAnswerDigestGuard
        | EvidenceSummaryAnswerContextGuard
        | EvidenceSummaryAnswerResultCitationGuard
        | EvidenceSummaryAnswerResultRuntimeFlagsGuard
        | EvidenceSummaryAnswerResultQualityGuard,
        ...,
    ] = DEFAULT_EVIDENCE_SUMMARY_ANSWER_GUARDS,
) -> CandidateGuardResult:
    """Run evidence summary answer guards without executing anything."""

    violations: list[str] = []
    for guard in guards:
        result = guard.validate(payload)
        violations.extend(f"{guard.guard_name}: {item}" for item in result.violations)
    return _result(violations)


def validate_evidence_summary_answer_generation_policy(
    policy: Mapping[str, Any],
) -> CandidateGuardResult:
    """Validate evidence-summary-answer generation policy facts."""

    return EvidenceSummaryAnswerGenerationPolicyGuard().validate(policy)


def validate_evidence_summary_answer_generation_preflight(
    context: Mapping[str, Any],
    *,
    generation_policy: Mapping[str, Any] | None = None,
) -> CandidateGuardResult:
    """Validate context and policy before generation enters an LLM boundary."""

    return EvidenceSummaryAnswerGenerationPreflightGuard().validate(
        context,
        generation_policy=generation_policy,
    )


def validate_evidence_summary_answer_llm_request_boundary(
    request: Mapping[str, Any],
) -> CandidateGuardResult:
    """Validate governed LLM request facts for evidence-summary-answer."""

    return EvidenceSummaryAnswerLlmRequestBoundaryGuard().validate(request)


def validate_evidence_summary_answer_result_mapping(
    result: Mapping[str, Any],
) -> CandidateGuardResult:
    """Validate generated answer result mapping constraints."""

    return EvidenceSummaryAnswerResultMappingGuard().validate(result)


def validate_evidence_summary_answer_answer_quality(
    answer: Any,
) -> CandidateGuardResult:
    """Validate answer text before it becomes a successful product answer."""

    return _result(_answer_quality_violations(answer))


def build_evidence_summary_answer_outcome_observation_readonly_facts(
    *,
    observation_candidate_ids: Sequence[Any] = (),
    request_ids: Sequence[Any] = (),
    result_statuses: Sequence[Any] = (),
    status: str | None = None,
    external_readonly_evidence_refs: Sequence[Any] = (),
    governed_evidence_digest_refs: Sequence[Any] = (),
    candidate_count: Any | None = None,
    request_count: Any | None = None,
    evidence_ref_count: Any | None = None,
    digest_ref_count: Any | None = None,
    summary_fact_count: Any = 0,
    schema_validation_passed: Any = True,
    schema_validation_error_count: Any = 0,
    guard_validation_passed: Any | None = None,
    guard_violation_count: Any = 0,
    guard_names: Sequence[Any] = (),
    answer_present: Any = False,
    answer_preview_present: Any = False,
    raw_boundary_violation_count: Any = 0,
    blocking_reasons: Sequence[Any] = (),
    citation_failures: Sequence[Any] = (),
    policy_profile: str | None = None,
    policy_ref: str | None = None,
    config_source_ref: str | None = None,
    readonly: Any = True,
    candidate_only: Any = True,
    does_not_store_answer: Any = True,
    does_not_store_user_question: Any = True,
    does_not_store_summary_facts: Any = True,
    does_not_store_raw_payload: Any = True,
    does_not_store_provider_raw_response: Any = True,
    does_not_store_sanitized_excerpt_preview: Any = True,
    does_not_store_config_context_value: Any = True,
    does_not_call_model: Any = True,
    does_not_fetch_or_search: Any = True,
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceSummaryAnswerOutcomeObservationReadonlyFacts:
    """Build compact readonly facts without carrying answer or raw values."""

    candidate_ids = tuple(_ordered_unique_texts(observation_candidate_ids))
    request_id_values = tuple(_ordered_unique_texts(request_ids))
    result_status_values = tuple(_ordered_unique_result_statuses(result_statuses))
    evidence_refs = tuple(_ordered_unique_texts(external_readonly_evidence_refs))
    digest_refs = tuple(_ordered_unique_texts(governed_evidence_digest_refs))
    facts = EvidenceSummaryAnswerOutcomeObservationReadonlyFacts(
        observation_candidate_ids=candidate_ids,
        request_ids=request_id_values,
        result_statuses=result_status_values,
        status=_outcome_observation_status(status, result_status_values),
        external_readonly_evidence_refs=evidence_refs,
        governed_evidence_digest_refs=digest_refs,
        candidate_count=_count_or_expected(
            candidate_count,
            len(candidate_ids),
            "candidate_count",
        ),
        request_count=_count_or_expected(
            request_count,
            len(request_id_values),
            "request_count",
        ),
        evidence_ref_count=_count_or_expected(
            evidence_ref_count,
            len(evidence_refs),
            "evidence_ref_count",
        ),
        digest_ref_count=_count_or_expected(
            digest_ref_count,
            len(digest_refs),
            "digest_ref_count",
        ),
        summary_fact_count=_non_negative_int(
            summary_fact_count,
            "summary_fact_count",
        ),
        schema_validation_passed=_strict_bool(
            schema_validation_passed,
            "schema_validation_passed",
        ),
        schema_validation_error_count=_non_negative_int(
            schema_validation_error_count,
            "schema_validation_error_count",
        ),
        guard_validation_passed=_optional_bool(
            guard_validation_passed,
            "guard_validation_passed",
        ),
        guard_violation_count=_non_negative_int(
            guard_violation_count,
            "guard_violation_count",
        ),
        guard_names=tuple(_ordered_unique_texts(guard_names)),
        answer_present=_strict_bool(answer_present, "answer_present"),
        answer_preview_present=_strict_bool(
            answer_preview_present,
            "answer_preview_present",
        ),
        raw_boundary_violation_count=_non_negative_int(
            raw_boundary_violation_count,
            "raw_boundary_violation_count",
        ),
        blocking_reasons=tuple(_ordered_unique_texts(blocking_reasons)),
        citation_failures=tuple(_ordered_unique_texts(citation_failures)),
        policy_profile=_compact_optional_public_text(policy_profile),
        policy_ref=_compact_optional_public_text(policy_ref),
        config_source_ref=_compact_optional_public_text(config_source_ref),
        readonly=_strict_bool(readonly, "readonly"),
        candidate_only=_strict_bool(candidate_only, "candidate_only"),
        does_not_store_answer=_strict_bool(
            does_not_store_answer,
            "does_not_store_answer",
        ),
        does_not_store_user_question=_strict_bool(
            does_not_store_user_question,
            "does_not_store_user_question",
        ),
        does_not_store_summary_facts=_strict_bool(
            does_not_store_summary_facts,
            "does_not_store_summary_facts",
        ),
        does_not_store_raw_payload=_strict_bool(
            does_not_store_raw_payload,
            "does_not_store_raw_payload",
        ),
        does_not_store_provider_raw_response=_strict_bool(
            does_not_store_provider_raw_response,
            "does_not_store_provider_raw_response",
        ),
        does_not_store_sanitized_excerpt_preview=_strict_bool(
            does_not_store_sanitized_excerpt_preview,
            "does_not_store_sanitized_excerpt_preview",
        ),
        does_not_store_config_context_value=_strict_bool(
            does_not_store_config_context_value,
            "does_not_store_config_context_value",
        ),
        does_not_call_model=_strict_bool(
            does_not_call_model,
            "does_not_call_model",
        ),
        does_not_fetch_or_search=_strict_bool(
            does_not_fetch_or_search,
            "does_not_fetch_or_search",
        ),
        metadata=_compact_outcome_observation_public_metadata(metadata or {}),
    )
    _validate_evidence_summary_answer_outcome_observation_readonly_facts(facts)
    return facts


def build_evidence_summary_answer_outcome_observation_readonly_facts_from_candidates(
    candidates: Sequence[Any],
) -> EvidenceSummaryAnswerOutcomeObservationReadonlyFacts:
    """Project readonly facts from compact candidate-like mappings."""

    candidate_data = tuple(
        data for data in (_contract_mapping(candidate) for candidate in candidates) if data
    )
    schema_error_count = sum(
        _non_negative_int(
            data.get("schema_validation_error_count", 0),
            "schema_validation_error_count",
        )
        for data in candidate_data
    )
    guard_violation_count = sum(
        _non_negative_int(
            data.get("guard_violation_count", 0),
            "guard_violation_count",
        )
        for data in candidate_data
    )
    guard_passed_values = tuple(
        value
        for value in (
            _optional_bool(data.get("guard_validation_passed"), "guard_validation_passed")
            for data in candidate_data
        )
        if value is not None
    )
    return build_evidence_summary_answer_outcome_observation_readonly_facts(
        observation_candidate_ids=tuple(
            _first_present_text(data, "observation_id", "candidate_id")
            for data in candidate_data
        ),
        request_ids=tuple(
            _first_present_text(data, "request_id")
            for data in candidate_data
        ),
        result_statuses=tuple(
            _first_present_text(data, "status") for data in candidate_data
        ),
        external_readonly_evidence_refs=_flatten_sequence_texts(
            data.get("evidence_refs") for data in candidate_data
        ),
        governed_evidence_digest_refs=_flatten_sequence_texts(
            data.get("digest_refs") for data in candidate_data
        ),
        summary_fact_count=sum(
            _non_negative_int(data.get("summary_fact_count", 0), "summary_fact_count")
            for data in candidate_data
        ),
        schema_validation_passed=(
            all(data.get("schema_validation_passed") is True for data in candidate_data)
            if candidate_data
            else True
        ),
        schema_validation_error_count=schema_error_count,
        guard_validation_passed=(
            all(guard_passed_values) and guard_violation_count == 0
            if guard_passed_values
            else None
        ),
        guard_violation_count=guard_violation_count,
        guard_names=_flatten_sequence_texts(
            data.get("guard_names") for data in candidate_data
        ),
        answer_present=any(data.get("answer_present") is True for data in candidate_data),
        answer_preview_present=any(
            data.get("answer_preview_present") is True for data in candidate_data
        ),
        raw_boundary_violation_count=sum(
            _non_negative_int(
                data.get("raw_boundary_violation_count", 0),
                "raw_boundary_violation_count",
            )
            for data in candidate_data
        ),
        blocking_reasons=_flatten_sequence_texts(
            data.get("blocking_reasons") for data in candidate_data
        ),
        citation_failures=_flatten_sequence_texts(
            data.get("citation_failures") for data in candidate_data
        ),
        policy_profile=_first_present_text(*candidate_data, key="policy_profile"),
        policy_ref=_first_present_text(*candidate_data, key="policy_ref"),
        config_source_ref=_first_present_text(*candidate_data, key="config_source_ref"),
    )


def build_evidence_summary_answer_outcome_observation_readonly_public_refs(
    *,
    evidence_summary_answer_outcome_observation_refs: Sequence[Any] = (),
    external_readonly_evidence_refs: Sequence[Any] = (),
    governed_evidence_digest_refs: Sequence[Any] = (),
    facts: EvidenceSummaryAnswerOutcomeObservationReadonlyFacts | Mapping[str, Any],
    payload_type: str = (
        EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_PAYLOAD_TYPE
    ),
    payload_version: str = (
        EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_VERSION
    ),
    readonly: Any = True,
    refs_only: Any = True,
    candidate_only: Any = True,
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceSummaryAnswerOutcomeObservationReadonlyPublicRefs:
    """Build the stable readonly refs/facts contract for outcome observations."""

    contract = EvidenceSummaryAnswerOutcomeObservationReadonlyPublicRefs(
        payload_type=_required_exact_text(
            payload_type,
            EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_PAYLOAD_TYPE,
            "payload_type",
        ),
        payload_version=_required_exact_text(
            payload_version,
            EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_VERSION,
            "payload_version",
        ),
        evidence_summary_answer_outcome_observation_refs=tuple(
            _ordered_unique_texts(evidence_summary_answer_outcome_observation_refs)
        ),
        external_readonly_evidence_refs=tuple(
            _ordered_unique_texts(external_readonly_evidence_refs)
        ),
        governed_evidence_digest_refs=tuple(
            _ordered_unique_texts(governed_evidence_digest_refs)
        ),
        facts=_outcome_observation_readonly_facts_from_value(facts),
        readonly=_strict_bool(readonly, "readonly"),
        refs_only=_strict_bool(refs_only, "refs_only"),
        candidate_only=_strict_bool(candidate_only, "candidate_only"),
        metadata=_compact_outcome_observation_public_metadata(metadata or {}),
    )
    validate_evidence_summary_answer_outcome_observation_readonly_public_refs(
        contract
    )
    return contract


def evidence_summary_answer_outcome_observation_readonly_public_refs_status_dict(
    public_refs: (
        EvidenceSummaryAnswerOutcomeObservationReadonlyPublicRefs | Mapping[str, Any]
    ),
) -> dict[str, Any]:
    """Return a JSON-ready readonly outcome observation refs/facts payload."""

    contract = _outcome_observation_public_refs_from_value(public_refs)
    validate_evidence_summary_answer_outcome_observation_readonly_public_refs(
        contract
    )
    facts = contract.facts
    return {
        "payload_type": contract.payload_type,
        "payload_version": contract.payload_version,
        "evidence_summary_answer_outcome_observation_refs": list(
            contract.evidence_summary_answer_outcome_observation_refs
        ),
        "external_readonly_evidence_refs": list(
            contract.external_readonly_evidence_refs
        ),
        "governed_evidence_digest_refs": list(
            contract.governed_evidence_digest_refs
        ),
        EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_FACTS_KEY: {
            "observation_candidate_ids": list(facts.observation_candidate_ids),
            "request_ids": list(facts.request_ids),
            "result_statuses": list(facts.result_statuses),
            "status": facts.status,
            "external_readonly_evidence_refs": list(
                facts.external_readonly_evidence_refs
            ),
            "governed_evidence_digest_refs": list(
                facts.governed_evidence_digest_refs
            ),
            "candidate_count": facts.candidate_count,
            "request_count": facts.request_count,
            "evidence_ref_count": facts.evidence_ref_count,
            "digest_ref_count": facts.digest_ref_count,
            "summary_fact_count": facts.summary_fact_count,
            "schema_validation_passed": facts.schema_validation_passed,
            "schema_validation_error_count": facts.schema_validation_error_count,
            "guard_validation_passed": facts.guard_validation_passed,
            "guard_violation_count": facts.guard_violation_count,
            "guard_names": list(facts.guard_names),
            "answer_present": facts.answer_present,
            "answer_preview_present": facts.answer_preview_present,
            "raw_boundary_violation_count": facts.raw_boundary_violation_count,
            "blocking_reasons": list(facts.blocking_reasons),
            "citation_failures": list(facts.citation_failures),
            "policy_profile": facts.policy_profile,
            "policy_ref": facts.policy_ref,
            "config_source_ref": facts.config_source_ref,
            "readonly": facts.readonly,
            "candidate_only": facts.candidate_only,
            "does_not_store_answer": facts.does_not_store_answer,
            "does_not_store_user_question": facts.does_not_store_user_question,
            "does_not_store_summary_facts": facts.does_not_store_summary_facts,
            "does_not_store_raw_payload": facts.does_not_store_raw_payload,
            "does_not_store_provider_raw_response": (
                facts.does_not_store_provider_raw_response
            ),
            "does_not_store_sanitized_excerpt_preview": (
                facts.does_not_store_sanitized_excerpt_preview
            ),
            "does_not_store_config_context_value": (
                facts.does_not_store_config_context_value
            ),
            "does_not_call_model": facts.does_not_call_model,
            "does_not_fetch_or_search": facts.does_not_fetch_or_search,
            "metadata": dict(facts.metadata),
        },
        "readonly": contract.readonly,
        "refs_only": contract.refs_only,
        "candidate_only": contract.candidate_only,
        "metadata": dict(contract.metadata),
    }


def validate_evidence_summary_answer_outcome_observation_readonly_public_refs(
    public_refs: (
        EvidenceSummaryAnswerOutcomeObservationReadonlyPublicRefs | Mapping[str, Any]
    ),
) -> None:
    """Validate readonly outcome observation refs/facts."""

    if isinstance(public_refs, Mapping):
        _validate_no_forbidden_outcome_observation_public_payload(public_refs)
    contract = _outcome_observation_public_refs_from_value(public_refs)
    if (
        contract.payload_type
        != EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_PAYLOAD_TYPE
    ):
        raise ValueError("payload_type must be evidence-summary-answer refs.")
    if (
        contract.payload_version
        != EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_VERSION
    ):
        raise ValueError("payload_version must be outcome observation refs v1.")
    if not contract.readonly:
        raise ValueError("readonly must be true.")
    if not contract.refs_only:
        raise ValueError("refs_only must be true.")
    if not contract.candidate_only:
        raise ValueError("candidate_only must be true.")
    _validate_refs_with_prefix(
        contract.evidence_summary_answer_outcome_observation_refs,
        EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_REF_PREFIX,
        "evidence_summary_answer_outcome_observation_refs",
    )
    _validate_refs_with_prefix(
        contract.external_readonly_evidence_refs,
        EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
        "external_readonly_evidence_refs",
    )
    _validate_refs_with_prefix(
        contract.governed_evidence_digest_refs,
        GOVERNED_EVIDENCE_DIGEST_REF_PREFIX,
        "governed_evidence_digest_refs",
    )
    _validate_evidence_summary_answer_outcome_observation_readonly_facts(
        contract.facts
    )
    if (
        contract.external_readonly_evidence_refs
        != contract.facts.external_readonly_evidence_refs
    ):
        raise ValueError("external_readonly_evidence_refs must match facts.")
    if (
        contract.governed_evidence_digest_refs
        != contract.facts.governed_evidence_digest_refs
    ):
        raise ValueError("governed_evidence_digest_refs must match facts.")
    if (
        contract.facts.status == "empty"
        and contract.evidence_summary_answer_outcome_observation_refs
    ):
        raise ValueError("empty refs must not include observation refs.")
    _validate_outcome_observation_public_metadata(contract.metadata, "metadata")


def _validate_evidence_summary_answer_outcome_observation_readonly_facts(
    facts: EvidenceSummaryAnswerOutcomeObservationReadonlyFacts,
) -> None:
    if (
        facts.status
        not in EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_STATUSES
    ):
        raise ValueError("status is invalid.")
    expected_status = _aggregate_outcome_observation_status(facts.result_statuses)
    if facts.status != expected_status:
        raise ValueError("status must match result_statuses.")
    _validate_refs_with_prefix(
        facts.external_readonly_evidence_refs,
        EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
        "facts.external_readonly_evidence_refs",
    )
    _validate_refs_with_prefix(
        facts.governed_evidence_digest_refs,
        GOVERNED_EVIDENCE_DIGEST_REF_PREFIX,
        "facts.governed_evidence_digest_refs",
    )
    if facts.candidate_count != len(facts.observation_candidate_ids):
        raise ValueError("candidate_count must match observation_candidate_ids.")
    if facts.request_count != len(facts.request_ids):
        raise ValueError("request_count must match request_ids.")
    if facts.evidence_ref_count != len(facts.external_readonly_evidence_refs):
        raise ValueError("evidence_ref_count must match external evidence refs.")
    if facts.digest_ref_count != len(facts.governed_evidence_digest_refs):
        raise ValueError("digest_ref_count must match digest refs.")
    for field_name in (
        "candidate_count",
        "request_count",
        "evidence_ref_count",
        "digest_ref_count",
        "summary_fact_count",
        "schema_validation_error_count",
        "guard_violation_count",
        "raw_boundary_violation_count",
    ):
        _non_negative_int(getattr(facts, field_name), field_name)
    if facts.schema_validation_passed and facts.schema_validation_error_count:
        raise ValueError("schema_validation_passed cannot hide schema errors.")
    if facts.guard_validation_passed is True and facts.guard_violation_count:
        raise ValueError("guard_validation_passed cannot hide guard violations.")
    for field_name in (
        "readonly",
        "candidate_only",
        "does_not_store_answer",
        "does_not_store_user_question",
        "does_not_store_summary_facts",
        "does_not_store_raw_payload",
        "does_not_store_provider_raw_response",
        "does_not_store_sanitized_excerpt_preview",
        "does_not_store_config_context_value",
        "does_not_call_model",
        "does_not_fetch_or_search",
    ):
        if getattr(facts, field_name) is not True:
            raise ValueError(f"{field_name} must be true.")
    for field_name in ("answer_present", "answer_preview_present"):
        if not isinstance(getattr(facts, field_name), bool):
            raise ValueError(f"{field_name} must be bool.")
    if facts.guard_validation_passed is not None and not isinstance(
        facts.guard_validation_passed,
        bool,
    ):
        raise ValueError("guard_validation_passed must be bool or None.")
    if facts.status == "empty":
        if facts.result_statuses:
            raise ValueError("empty facts must not include result statuses.")
        if facts.observation_candidate_ids:
            raise ValueError("empty facts must not include candidate ids.")
        if facts.request_ids:
            raise ValueError("empty facts must not include request ids.")
        if facts.external_readonly_evidence_refs:
            raise ValueError("empty facts must not include evidence refs.")
        if facts.governed_evidence_digest_refs:
            raise ValueError("empty facts must not include digest refs.")
    _validate_safe_public_texts(facts.guard_names, "guard_names")
    _validate_safe_public_texts(facts.blocking_reasons, "blocking_reasons")
    _validate_safe_public_texts(facts.citation_failures, "citation_failures")
    for field_name in ("policy_profile", "policy_ref", "config_source_ref"):
        value = getattr(facts, field_name)
        if value is not None and _outcome_observation_public_value_blocked(value):
            raise ValueError(f"{field_name} contains forbidden marker.")
    _validate_outcome_observation_public_metadata(
        facts.metadata,
        "facts.metadata",
    )


def _outcome_observation_public_refs_from_value(
    value: EvidenceSummaryAnswerOutcomeObservationReadonlyPublicRefs | Mapping[str, Any],
) -> EvidenceSummaryAnswerOutcomeObservationReadonlyPublicRefs:
    if isinstance(value, EvidenceSummaryAnswerOutcomeObservationReadonlyPublicRefs):
        return value
    _validate_no_forbidden_outcome_observation_public_payload(value)
    data = _contract_mapping(value)
    facts_value = data.get("facts")
    if facts_value is None:
        facts_value = data.get(
            EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_FACTS_KEY
        )
    if facts_value is None:
        raise ValueError("facts is required.")
    return build_evidence_summary_answer_outcome_observation_readonly_public_refs(
        evidence_summary_answer_outcome_observation_refs=_sequence_texts(
            data.get("evidence_summary_answer_outcome_observation_refs")
        ),
        external_readonly_evidence_refs=_sequence_texts(
            data.get("external_readonly_evidence_refs")
        ),
        governed_evidence_digest_refs=_sequence_texts(
            data.get("governed_evidence_digest_refs")
        ),
        facts=_outcome_observation_readonly_facts_from_value(facts_value),
        payload_type=_plain_text(
            data.get("payload_type")
            or EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_PAYLOAD_TYPE
        ),
        payload_version=_plain_text(
            data.get("payload_version")
            or EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_VERSION
        ),
        readonly=data.get("readonly", True),
        refs_only=data.get("refs_only", True),
        candidate_only=data.get("candidate_only", True),
        metadata=_contract_mapping(data.get("metadata")),
    )


def _outcome_observation_readonly_facts_from_value(
    value: EvidenceSummaryAnswerOutcomeObservationReadonlyFacts | Mapping[str, Any],
) -> EvidenceSummaryAnswerOutcomeObservationReadonlyFacts:
    if isinstance(value, EvidenceSummaryAnswerOutcomeObservationReadonlyFacts):
        return value
    data = _contract_mapping(value)
    return build_evidence_summary_answer_outcome_observation_readonly_facts(
        observation_candidate_ids=_sequence_texts(
            data.get("observation_candidate_ids")
        ),
        request_ids=_sequence_texts(data.get("request_ids")),
        result_statuses=_sequence_texts(data.get("result_statuses")),
        status=_plain_optional_text(data.get("status")),
        external_readonly_evidence_refs=_sequence_texts(
            data.get("external_readonly_evidence_refs")
        ),
        governed_evidence_digest_refs=_sequence_texts(
            data.get("governed_evidence_digest_refs")
        ),
        candidate_count=data.get("candidate_count"),
        request_count=data.get("request_count"),
        evidence_ref_count=data.get("evidence_ref_count"),
        digest_ref_count=data.get("digest_ref_count"),
        summary_fact_count=data.get("summary_fact_count", 0),
        schema_validation_passed=data.get("schema_validation_passed", True),
        schema_validation_error_count=data.get("schema_validation_error_count", 0),
        guard_validation_passed=data.get("guard_validation_passed"),
        guard_violation_count=data.get("guard_violation_count", 0),
        guard_names=_sequence_texts(data.get("guard_names")),
        answer_present=data.get("answer_present", False),
        answer_preview_present=data.get("answer_preview_present", False),
        raw_boundary_violation_count=data.get("raw_boundary_violation_count", 0),
        blocking_reasons=_sequence_texts(data.get("blocking_reasons")),
        citation_failures=_sequence_texts(data.get("citation_failures")),
        policy_profile=_plain_optional_text(data.get("policy_profile")),
        policy_ref=_plain_optional_text(data.get("policy_ref")),
        config_source_ref=_plain_optional_text(data.get("config_source_ref")),
        readonly=data.get("readonly", True),
        candidate_only=data.get("candidate_only", True),
        does_not_store_answer=data.get("does_not_store_answer", True),
        does_not_store_user_question=data.get("does_not_store_user_question", True),
        does_not_store_summary_facts=data.get("does_not_store_summary_facts", True),
        does_not_store_raw_payload=data.get("does_not_store_raw_payload", True),
        does_not_store_provider_raw_response=data.get(
            "does_not_store_provider_raw_response",
            True,
        ),
        does_not_store_sanitized_excerpt_preview=data.get(
            "does_not_store_sanitized_excerpt_preview",
            True,
        ),
        does_not_store_config_context_value=data.get(
            "does_not_store_config_context_value",
            True,
        ),
        does_not_call_model=data.get("does_not_call_model", True),
        does_not_fetch_or_search=data.get("does_not_fetch_or_search", True),
        metadata=_contract_mapping(data.get("metadata")),
    )


def _outcome_observation_status(
    status: str | None,
    result_statuses: Sequence[str],
) -> str:
    if status is None or not status.strip():
        return _aggregate_outcome_observation_status(result_statuses)
    if (
        status
        not in EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_STATUSES
    ):
        raise ValueError("status is invalid.")
    return status


def _aggregate_outcome_observation_status(result_statuses: Sequence[str]) -> str:
    if not result_statuses:
        return "empty"
    if len(result_statuses) == 1:
        return result_statuses[0]
    return "mixed"


def _ordered_unique_result_statuses(values: Sequence[Any]) -> list[str]:
    statuses = _ordered_unique_texts(values)
    for status in statuses:
        if status not in EVIDENCE_SUMMARY_ANSWER_RESULT_STATUSES:
            raise ValueError("result_statuses contains invalid status.")
    return statuses


def _contract_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return {
            str(key): item
            for key, item in value.items()
            if isinstance(key, str)
        }
    if is_dataclass(value) and not isinstance(value, type):
        return _contract_mapping(asdict(value))
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")
        if isinstance(dumped, Mapping):
            return _contract_mapping(dumped)
    return {}


def _sequence_texts(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        text = value.strip()
        return (text,) if text else ()
    if isinstance(value, Mapping):
        if "ref" in value:
            return _sequence_texts(value.get("ref"))
        return ()
    if isinstance(value, Sequence) and not isinstance(value, bytes):
        texts: list[str] = []
        for item in value:
            texts.extend(_sequence_texts(item))
        return tuple(texts)
    text = str(value).strip()
    return (text,) if text else ()


def _ordered_unique_texts(values: Any) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in _sequence_texts(values):
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _flatten_sequence_texts(values: Sequence[Any]) -> tuple[str, ...]:
    texts: list[str] = []
    for value in values:
        texts.extend(_sequence_texts(value))
    return tuple(texts)


def _plain_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _plain_optional_text(value: Any) -> str | None:
    text = _plain_text(value)
    return text or None


def _compact_optional_public_text(value: Any) -> str | None:
    text = _plain_optional_text(value)
    if text is None or _outcome_observation_public_value_blocked(text):
        return None
    return text


def _first_present_text(*values: Any, key: str | None = None) -> str | None:
    if key is not None:
        for value in values:
            text = _compact_optional_public_text(_contract_mapping(value).get(key))
            if text is not None:
                return text
        return None
    if values and isinstance(values[0], Mapping):
        data = _contract_mapping(values[0])
        for field_name in values[1:]:
            if isinstance(field_name, str):
                text = _compact_optional_public_text(data.get(field_name))
                if text is not None:
                    return text
        return None
    for value in values:
        text = _compact_optional_public_text(value)
        if text is not None:
            return text
    return None


def _strict_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be bool.")
    return value


def _optional_bool(value: Any, field_name: str) -> bool | None:
    if value is None:
        return None
    return _strict_bool(value, field_name)


def _non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be non-negative int.")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be non-negative int.") from exc
    if number < 0:
        raise ValueError(f"{field_name} must be non-negative int.")
    return number


def _count_or_expected(value: Any | None, expected: int, field_name: str) -> int:
    if value is None:
        return expected
    count = _non_negative_int(value, field_name)
    if count != expected:
        raise ValueError(f"{field_name} must match the compact refs.")
    return count


def _required_exact_text(value: Any, expected: str, field_name: str) -> str:
    text = _plain_text(value)
    if text != expected:
        raise ValueError(f"{field_name} must be {expected}.")
    return text


def _compact_outcome_observation_public_metadata(
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in metadata.items():
        if not isinstance(key, str):
            continue
        if _outcome_observation_public_metadata_key_blocked(key):
            continue
        if not isinstance(value, bool | int | float | str):
            continue
        if isinstance(value, str) and _outcome_observation_public_value_blocked(value):
            continue
        compact[key] = value
    return compact


def _validate_outcome_observation_public_metadata(
    metadata: Mapping[str, Any],
    field_name: str,
) -> None:
    for key, value in metadata.items():
        if not isinstance(key, str):
            raise ValueError(f"{field_name} keys must be strings.")
        if _outcome_observation_public_metadata_key_blocked(key):
            raise ValueError(f"{field_name}.{key} is forbidden.")
        if not isinstance(value, bool | int | float | str):
            raise ValueError(f"{field_name}.{key} must be compact scalar.")
        if isinstance(value, str) and _outcome_observation_public_value_blocked(value):
            raise ValueError(f"{field_name}.{key} contains forbidden marker.")


def _outcome_observation_public_metadata_key_blocked(key: str) -> bool:
    normalized = key.lower()
    return any(
        marker in normalized
        for marker in (
            EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_PUBLIC_FORBIDDEN_METADATA_KEYS
        )
    )


def _outcome_observation_public_value_blocked(value: str) -> bool:
    normalized = value.lower()
    return _looks_like_forbidden_marker(value) or any(
        marker in normalized
        for marker in (
            EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_PUBLIC_FORBIDDEN_METADATA_VALUES
        )
    )


def _validate_safe_public_texts(values: Sequence[str], field_name: str) -> None:
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must contain strings.")
        if len(value) > 160 or "\n" in value or "\r" in value:
            raise ValueError(f"{field_name} values must be short tokens.")
        if _outcome_observation_public_value_blocked(value):
            raise ValueError(f"{field_name} contains forbidden marker.")


def _validate_refs_with_prefix(
    values: Sequence[str],
    prefix: str,
    field_name: str,
) -> None:
    for value in values:
        if not value.startswith(prefix) or len(value) <= len(prefix):
            raise ValueError(f"{field_name} must use {prefix} refs.")


def _validate_no_forbidden_outcome_observation_public_payload(
    value: Any,
    path: str = "$",
) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in (
                EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_PUBLIC_FORBIDDEN_PAYLOAD_KEYS
            ):
                raise ValueError(f"{path}.{key_text} is forbidden.")
            _validate_no_forbidden_outcome_observation_public_payload(
                item,
                f"{path}.{key_text}",
            )
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for index, item in enumerate(value):
            _validate_no_forbidden_outcome_observation_public_payload(
                item,
                f"{path}[{index}]",
            )
    elif isinstance(value, str) and _outcome_observation_public_value_blocked(value):
        raise ValueError(f"{path} contains forbidden marker.")


def _raw_or_runtime_boundary_violations(payload: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    for path, value in _walk(payload):
        if _is_runtime_boundary(path, value):
            violations.append(f"runtime object leakage is forbidden at {path}.")
        elif _is_raw_boundary(path, value):
            violations.append(f"raw boundary field is forbidden at {path}.")
    for path, value in _walk(payload):
        if _key_at_path(path) == "raw_boundary_flags" and isinstance(value, Mapping):
            violations.extend(_raw_boundary_flag_violations(path, value))
    return violations


def _require_policy_value(
    policy: Mapping[str, Any],
    key: str,
    expected: Any,
    violations: list[str],
) -> None:
    if key in policy and policy.get(key) is not expected:
        violations.append(f"{key} must be {expected}.")


def _reject_policy_value(
    policy: Mapping[str, Any],
    key: str,
    forbidden: Any,
    violations: list[str],
) -> None:
    if key in policy and policy.get(key) is forbidden:
        violations.append(f"{key} must not be {forbidden}.")


def _has_answerable_generation_digest(value: Any) -> bool:
    if not isinstance(value, (list, tuple)):
        return False
    for digest in value:
        if not isinstance(digest, Mapping):
            continue
        if (
            digest.get("status") == "ready"
            and digest.get("answerability") == "answerable"
            and digest.get("allowed_for_model_context") is True
            and _has_nonempty_string_item(digest.get("summary_facts"))
            and not _raw_boundary_flags_any_true(digest.get("raw_boundary_flags"))
        ):
            return True
    return False


def _metadata_key_allowlist_violations(
    metadata: Mapping[str, Any],
    allowed_keys: frozenset[str],
    *,
    path: str,
) -> list[str]:
    violations: list[str] = []
    for key in metadata:
        if not isinstance(key, str) or key not in allowed_keys:
            violations.append(f"{path}.{key} is not allowed generation metadata.")
    return violations


def _result(violations: list[str]) -> CandidateGuardResult:
    return CandidateGuardResult(
        passed=not violations,
        violations=tuple(violations),
    )


def _walk(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, Mapping):
        for key, item in value.items():
            items.extend(_walk(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            items.extend(_walk(item, f"{path}[{index}]"))
    return items


def _key_at_path(path: str) -> str:
    return path.rsplit(".", maxsplit=1)[-1].split("[", maxsplit=1)[0].lower()


def _is_raw_boundary(path: str, value: Any) -> bool:
    key = _key_at_path(path)
    if (
        key in FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_KEYS
        or key.endswith("_token")
        or key.endswith("_secret")
        or key.endswith("_credential")
    ):
        return True
    return (
        isinstance(value, str)
        and path not in STRING_MARKER_EXEMPT_PATHS
        and _looks_like_forbidden_marker(value)
    )


def _is_runtime_boundary(path: str, value: Any) -> bool:
    key = _key_at_path(path)
    if key == "object_module" and isinstance(value, str) and _is_runtime_module(value):
        return True
    return _is_runtime_object(value)


def _raw_boundary_flag_violations(
    path: str,
    raw_boundary_flags: Mapping[str, Any],
) -> list[str]:
    return [
        f"{path}.{key} must not be true."
        for key, value in raw_boundary_flags.items()
        if value is True
    ]


def _raw_boundary_flags_any_true(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    return any(item is True for item in value.values())


def _host_has_path_or_query(value: str) -> bool:
    return any(marker in value for marker in ("://", "/", "?", "#", "@", ":"))


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_nonempty_string_item(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and any(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def _has_mapping_item(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and any(
        isinstance(item, Mapping) for item in value
    )


def _require_string_fields(
    payload: Mapping[str, Any],
    fields: tuple[str, ...],
    violations: list[str],
) -> None:
    for field in fields:
        if not _is_nonempty_string(payload.get(field)):
            violations.append(f"{field} is required.")


def _is_runtime_object(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool, list, tuple, dict)):
        return False
    return _is_runtime_module(type(value).__module__)


def _is_runtime_module(module_name: str) -> bool:
    return module_name.startswith(
        FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_OBJECT_MODULE_PREFIXES
    )


def _answer_quality_violations(answer: Any) -> list[str]:
    if not isinstance(answer, str) or not answer.strip():
        return ["successful answer results require user-facing answer text."]

    text = answer.strip()
    violations: list[str] = []
    if EVIDENCE_SUMMARY_ANSWER_VISIBLE_REASONING_LABEL_RE.search(text):
        violations.append(
            "successful answer must not start with a visible reasoning label."
        )
    if EVIDENCE_SUMMARY_ANSWER_PROMPT_INSTRUCTION_LEAKAGE_RE.search(text):
        violations.append(
            "successful answer must not expose prompt or instruction leakage."
        )

    if _looks_like_jsonish_wrapper(text):
        if _contains_visible_reasoning_key(text):
            violations.append(
                "successful answer must not expose visible reasoning fields."
            )
        if _looks_like_incomplete_jsonish_wrapper(text):
            violations.append(
                "successful answer must not be an incomplete JSON-ish wrapper."
            )
        elif _looks_like_complete_jsonish_wrapper(text):
            violations.append(
                "successful answer must be user-facing natural language, "
                "not a JSON wrapper."
            )

    return violations


def _looks_like_jsonish_wrapper(value: str) -> bool:
    return value.startswith(("{", "["))


def _looks_like_incomplete_jsonish_wrapper(value: str) -> bool:
    if value.startswith("{") and not value.endswith("}"):
        return True
    if value.startswith("[") and not value.endswith("]"):
        return True
    return False


def _looks_like_complete_jsonish_wrapper(value: str) -> bool:
    if not (
        (value.startswith("{") and value.endswith("}"))
        or (value.startswith("[") and value.endswith("]"))
    ):
        return False
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return True
    return isinstance(parsed, (dict, list))


def _contains_visible_reasoning_key(value: str) -> bool:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return EVIDENCE_SUMMARY_ANSWER_VISIBLE_REASONING_KEY_RE.search(value) is not None
    return _object_contains_visible_reasoning_key(parsed)


def _object_contains_visible_reasoning_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _is_visible_reasoning_key(key)
            or _object_contains_visible_reasoning_key(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_object_contains_visible_reasoning_key(item) for item in value)
    return False


def _is_visible_reasoning_key(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = (
        value.strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )
    return normalized in EVIDENCE_SUMMARY_ANSWER_VISIBLE_REASONING_KEYS


def _looks_like_forbidden_marker(value: str) -> bool:
    lowered = value.lower()
    return any(
        marker in lowered
        for marker in (
            "api_key",
            "config_context",
            "config context value",
            "full productgatewayresponse",
            "full_product_gateway_response",
            "observability_candidate_body",
            "prompt_or_messages",
            "raw html",
            "raw payload",
            "raw provider response",
            "raw_payload",
            "raw_provider_response",
            "response_headers",
            "response_text",
            "sanitized_excerpt_preview",
            "system_prompt",
        )
    )


__all__ = [
    "DEFAULT_EVIDENCE_SUMMARY_ANSWER_GUARDS",
    "EVIDENCE_SUMMARY_ANSWER_FORBIDDEN_CONTEXT_FIELDS",
    "EVIDENCE_SUMMARY_ANSWER_GENERATION_PROFILES",
    "EVIDENCE_SUMMARY_ANSWER_GENERATION_RESULT_METADATA_KEYS",
    "EVIDENCE_SUMMARY_ANSWER_LLM_REQUEST_METADATA_KEYS",
    "EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_PAYLOAD_TYPE",
    "EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_STATUSES",
    "EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_VERSION",
    "EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_REF_PREFIX",
    "EVIDENCE_SUMMARY_ANSWER_PAYLOAD_TYPES",
    "EVIDENCE_SUMMARY_ANSWER_PAYLOAD_VERSIONS",
    "EVIDENCE_SUMMARY_ANSWER_QUALITY_BLOCKING_REASON",
    "EvidenceSummaryAnswerContextGuard",
    "EvidenceSummaryAnswerDigestGuard",
    "EvidenceSummaryAnswerGenerationPolicyGuard",
    "EvidenceSummaryAnswerGenerationPreflightGuard",
    "EvidenceSummaryAnswerGenerationService",
    "EvidenceSummaryAnswerHeaderGuard",
    "EvidenceSummaryAnswerLlmRequestBoundaryGuard",
    "EvidenceSummaryAnswerNoRawBoundaryGuard",
    "EvidenceSummaryAnswerOutcomeObservationReadonlyFacts",
    "EvidenceSummaryAnswerOutcomeObservationReadonlyPublicRefs",
    "EvidenceSummaryAnswerResultCitationGuard",
    "EvidenceSummaryAnswerResultMappingGuard",
    "EvidenceSummaryAnswerResultQualityGuard",
    "EvidenceSummaryAnswerResultRuntimeFlagsGuard",
    "build_evidence_summary_answer_outcome_observation_readonly_facts",
    "build_evidence_summary_answer_outcome_observation_readonly_facts_from_candidates",
    "build_evidence_summary_answer_outcome_observation_readonly_public_refs",
    "evidence_summary_answer_outcome_observation_readonly_public_refs_status_dict",
    "validate_evidence_summary_answer_answer_quality",
    "validate_evidence_summary_answer_generation_policy",
    "validate_evidence_summary_answer_generation_preflight",
    "validate_evidence_summary_answer_guards",
    "validate_evidence_summary_answer_llm_request_boundary",
    "validate_evidence_summary_answer_outcome_observation_readonly_public_refs",
    "validate_evidence_summary_answer_result_mapping",
]
