from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest
from behavior_contracts import (
    EvidenceSummaryAnswerArtifactGuard as RootArtifactGuard,
    EvidenceSummaryAnswerFollowUpSeedGuard as RootFollowUpSeedGuard,
    EvidenceSummaryAnswerGenerationPolicyGuard as RootGenerationPolicyGuard,
    EvidenceSummaryAnswerHeaderGuard as RootEvidenceSummaryAnswerHeaderGuard,
    EvidenceSummaryAnswerResultQualityGuard as RootQualityGuard,
    EvidenceSummaryAnswerTraceGuard as RootTraceGuard,
    validate_evidence_summary_answer_guards as root_validate_guards,
    validate_evidence_summary_answer_generation_policy as root_validate_generation_policy,
)
from behavior_contracts.evidence_summary_answer import (
    EvidenceSummaryAnswerArtifactGuard,
    EvidenceSummaryAnswerContextGuard,
    EvidenceSummaryAnswerDigestGuard,
    EvidenceSummaryAnswerFollowUpSeedGuard,
    EvidenceSummaryAnswerGenerationPolicyGuard,
    EvidenceSummaryAnswerGenerationPreflightGuard,
    EvidenceSummaryAnswerGenerationService,
    EvidenceSummaryAnswerHeaderGuard,
    EvidenceSummaryAnswerLlmRequestBoundaryGuard,
    EvidenceSummaryAnswerNoRawBoundaryGuard,
    EvidenceSummaryAnswerResultCitationGuard,
    EvidenceSummaryAnswerResultMappingGuard,
    EvidenceSummaryAnswerResultQualityGuard,
    EvidenceSummaryAnswerResultRuntimeFlagsGuard,
    EvidenceSummaryAnswerTraceGuard,
    build_evidence_summary_answer_answerability_preflight_facts,
    validate_evidence_summary_answer_answer_quality,
    validate_evidence_summary_answer_generation_policy,
    validate_evidence_summary_answer_generation_preflight,
    validate_evidence_summary_answer_guards,
    validate_evidence_summary_answer_llm_request_boundary,
    validate_evidence_summary_answer_question_answer_quality,
    validate_evidence_summary_answer_result_mapping,
)
from schemas.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX,
    EVIDENCE_SUMMARY_ANSWER_ARTIFACT_VERSION,
    EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION,
    EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SEED_VERSION,
    EVIDENCE_SUMMARY_ANSWER_PRODUCT,
    EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION,
    EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX,
    EVIDENCE_SUMMARY_ANSWER_TRACE_VERSION,
    GOVERNED_EVIDENCE_DIGEST_VERSION,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
BEHAVIOR_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "behavior_contracts" / "src" / "behavior_contracts"
)


def test_evidence_summary_answer_guards_accept_safe_digest() -> None:
    result = validate_evidence_summary_answer_guards(_digest())

    assert result.passed is True
    assert result.violations == ()


def test_evidence_summary_answer_guards_accept_safe_context() -> None:
    result = validate_evidence_summary_answer_guards(_context())

    assert result.passed is True
    assert result.violations == ()


def test_evidence_summary_answer_guards_accept_safe_success_result() -> None:
    result = validate_evidence_summary_answer_guards(_result())

    assert result.passed is True
    assert result.violations == ()


def test_evidence_summary_answer_guards_accept_safe_follow_up_seed() -> None:
    result = validate_evidence_summary_answer_guards(_follow_up_seed())

    assert result.passed is True
    assert result.violations == ()


def test_evidence_summary_answer_guards_accept_safe_trace() -> None:
    result = validate_evidence_summary_answer_guards(_trace())

    assert result.passed is True
    assert result.violations == ()


def test_evidence_summary_answer_guards_accept_safe_artifact() -> None:
    result = validate_evidence_summary_answer_guards(_artifact())

    assert result.passed is True
    assert result.violations == ()


def test_artifact_guard_rejects_runtime_backing_or_missing_answer() -> None:
    artifact = _artifact()
    artifact["backed_by_adk_task_runtime"] = True
    artifact["answer"] = None
    artifact["answer_preview"] = None

    result = EvidenceSummaryAnswerArtifactGuard().validate(artifact)

    assert result.passed is False
    assert any("ADK Task runtime" in item for item in result.violations)
    assert any("answer or answer_preview" in item for item in result.violations)


def test_follow_up_seed_guard_rejects_durable_or_memory_state() -> None:
    seed = _follow_up_seed()
    seed["durable_session"] = True
    seed["memory_enabled"] = True

    result = EvidenceSummaryAnswerFollowUpSeedGuard().validate(seed)

    assert result.passed is False
    assert any("durable session" in item for item in result.violations)
    assert any("Memory runtime" in item for item in result.violations)


def test_header_guard_rejects_invalid_payload_version() -> None:
    digest = _digest()
    digest["payload_version"] = "other"

    result = EvidenceSummaryAnswerHeaderGuard().validate(digest)

    assert result.passed is False
    assert "payload_version" in result.violations[0]


def test_header_guard_rejects_unknown_payload_type() -> None:
    digest = _digest()
    digest["payload_type"] = "other"

    result = EvidenceSummaryAnswerHeaderGuard().validate(digest)

    assert result.passed is False
    assert "payload_type" in result.violations[0]


def test_no_raw_boundary_guard_rejects_raw_provider_response_metadata() -> None:
    digest = _digest()
    digest["metadata"] = {"raw_provider_response": {"content": "raw"}}

    result = EvidenceSummaryAnswerNoRawBoundaryGuard().validate(digest)

    assert result.passed is False
    assert "raw boundary" in result.violations[0]


def test_no_raw_boundary_guard_rejects_sanitized_excerpt_preview() -> None:
    digest = _digest()
    digest["metadata"] = {"sanitized_excerpt_preview": "body text"}

    result = EvidenceSummaryAnswerNoRawBoundaryGuard().validate(digest)

    assert result.passed is False
    assert "sanitized_excerpt_preview" in result.violations[0]


def test_no_raw_boundary_guard_rejects_runtime_object_marker() -> None:
    digest = _digest()
    digest["metadata"] = {"object_module": "runtime_container.registry"}

    result = EvidenceSummaryAnswerNoRawBoundaryGuard().validate(digest)

    assert result.passed is False
    assert "runtime" in result.violations[0] or "raw boundary" in result.violations[0]


def test_digest_guard_rejects_invalid_digest_ref() -> None:
    digest = _digest()
    digest["digest_ref"] = "digest://request-1/digest-1"

    result = EvidenceSummaryAnswerDigestGuard().validate(digest)

    assert result.passed is False
    assert "digest_ref" in result.violations[0]


def test_digest_guard_rejects_invalid_evidence_ref() -> None:
    digest = _digest()
    digest["evidence_ref"] = "evidence://other/request-1/fetch-1"

    result = EvidenceSummaryAnswerDigestGuard().validate(digest)

    assert result.passed is False
    assert "evidence_ref" in result.violations[0]


def test_digest_guard_rejects_answerable_without_model_context_permission() -> None:
    digest = _digest()
    digest["allowed_for_model_context"] = False

    result = EvidenceSummaryAnswerDigestGuard().validate(digest)

    assert result.passed is False
    assert "allowed_for_model_context" in result.violations[0]


def test_digest_guard_rejects_answerable_without_summary_facts() -> None:
    digest = _digest()
    digest["summary_facts"] = []

    result = EvidenceSummaryAnswerDigestGuard().validate(digest)

    assert result.passed is False
    assert "summary_facts" in result.violations[0]


def test_digest_guard_rejects_source_url_host_with_path_or_query() -> None:
    digest = _digest()
    digest["source_url_host"] = "example.com/path?x=1"

    result = EvidenceSummaryAnswerDigestGuard().validate(digest)

    assert result.passed is False
    assert "source_url_host" in result.violations[0]


def test_context_guard_rejects_empty_digests() -> None:
    context = _context()
    context["digests"] = []

    result = EvidenceSummaryAnswerContextGuard().validate(context)

    assert result.passed is False
    assert "digest" in result.violations[0]


def test_context_guard_rejects_uncovered_digest_evidence_ref() -> None:
    context = _context()
    context["evidence_refs"] = [
        {"ref": "evidence://external-readonly/other", "kind": "evidence"}
    ]

    result = EvidenceSummaryAnswerContextGuard().validate(context)

    assert result.passed is False
    assert "evidence_refs" in result.violations[0]


def test_context_guard_rejects_prompt_messages_or_system_prompt_fields() -> None:
    context = _context()
    context["prompt"] = "forbidden"

    result = EvidenceSummaryAnswerContextGuard().validate(context)

    assert result.passed is False
    assert "prompt" in result.violations[0]


def test_result_citation_guard_rejects_success_without_evidence_refs_used() -> None:
    result_payload = _result()
    result_payload["evidence_refs_used"] = []

    result = EvidenceSummaryAnswerResultCitationGuard().validate(result_payload)

    assert result.passed is False
    assert "evidence_refs_used" in result.violations[0]


def test_result_citation_guard_rejects_insufficient_evidence_without_reason() -> None:
    result_payload = _result(status="insufficient_evidence")
    result_payload["answer"] = None
    result_payload["answer_preview"] = None
    result_payload["evidence_refs_used"] = []
    result_payload["digest_refs_used"] = []
    result_payload["insufficient_evidence_reason"] = None
    result_payload["llm_runtime_call_performed"] = False

    result = EvidenceSummaryAnswerResultCitationGuard().validate(result_payload)

    assert result.passed is False
    assert "insufficient_evidence_reason" in result.violations[0]


def test_result_citation_guard_rejects_blocked_without_reasons() -> None:
    result_payload = _result(status="blocked")
    result_payload["answer"] = None
    result_payload["answer_preview"] = None
    result_payload["evidence_refs_used"] = []
    result_payload["digest_refs_used"] = []
    result_payload["blocking_reasons"] = []
    result_payload["llm_runtime_call_performed"] = False

    result = EvidenceSummaryAnswerResultCitationGuard().validate(result_payload)

    assert result.passed is False
    assert "blocking_reasons" in result.violations[0]


def test_result_runtime_flags_guard_rejects_inconsistent_flags() -> None:
    result_payload = _result()
    result_payload["llm_call_allowed"] = False
    result_payload["llm_call_attempted"] = True
    result_payload["llm_runtime_call_performed"] = True

    result = EvidenceSummaryAnswerResultRuntimeFlagsGuard().validate(result_payload)

    assert result.passed is False
    assert "llm_runtime_call_performed" in result.violations[0]


def test_trace_guard_rejects_runtime_backing() -> None:
    trace = _trace()
    trace["backed_by_adk_task_runtime"] = True

    result = EvidenceSummaryAnswerTraceGuard().validate(trace)

    assert result.passed is False
    assert "ADK Task runtime" in " ".join(result.violations)


def test_result_quality_guard_rejects_visible_reasoning_json_wrapper() -> None:
    result_payload = _result()
    result_payload["answer"] = '{"thought": "I should summarize the evidence."}'
    result_payload["answer_preview"] = '{"thought": "I should summarize'

    result = EvidenceSummaryAnswerResultQualityGuard().validate(result_payload)
    all_guards = validate_evidence_summary_answer_guards(result_payload)

    assert result.passed is False
    assert "visible reasoning" in " ".join(result.violations)
    assert all_guards.passed is False
    assert "quality" in " ".join(all_guards.violations)


def test_result_quality_guard_rejects_incomplete_jsonish_answer() -> None:
    result = validate_evidence_summary_answer_answer_quality(
        '{ "thought": "The user wants a concise answer."'
    )

    assert result.passed is False
    assert "incomplete JSON-ish" in " ".join(result.violations)


def test_result_quality_guard_rejects_visible_reasoning_label() -> None:
    result = validate_evidence_summary_answer_answer_quality(
        "reasoning: I should answer only from governed facts."
    )

    assert result.passed is False
    assert "visible reasoning label" in " ".join(result.violations)


@pytest.mark.parametrize(
    "answer",
    (
        "我们被要求只返回最终的用户自然语言，不输出JSON等。这个网页主要说明 Example Domain 的用途。",
        "我们被要求用中文回答这个网页主要说明了什么，并且只基于给定的摘要事实。",
        "我们被问到：这个网页主要说明了什么？证据摘要指出 Example Domain 可用于文档示例。",
        "I was instructed to return only the final answer. The page explains Example Domain.",
        "We are asked what the page mainly explains. It explains Example Domain.",
        "We are given summary facts and evidence refs. The question is about Example Domain.",
        "The question is: 这个网页主要说明了什么？ Example Domain is for documentation examples.",
        "The prompt requires that I do not output JSON. The page explains Example Domain.",
    ),
)
def test_result_quality_guard_rejects_prompt_instruction_leakage(answer: str) -> None:
    result = validate_evidence_summary_answer_answer_quality(answer)

    assert result.passed is False
    assert "instruction leakage" in " ".join(result.violations)


@pytest.mark.parametrize(
    "answer",
    (
        "我是一个 AI 解决方案架构师，运行在本地 MacBook M5 环境下，原生支持 MCP 协议。",
        "我是一个专业的智能代理，负责 AI 治理逻辑、安全审计和本地推理。",
        "I am an AI solution architect running in a local MacBook environment with MCP support.",
    ),
)
def test_result_quality_guard_rejects_identity_runtime_leakage(answer: str) -> None:
    result = validate_evidence_summary_answer_answer_quality(answer)

    assert result.passed is False
    assert "identity or runtime" in " ".join(result.violations)


def test_question_answer_quality_rejects_chinese_question_with_english_answer() -> None:
    result = validate_evidence_summary_answer_question_answer_quality(
        "The provided material is a domain example used for documentation purposes.",
        user_question="帮我将该份资料整理出1500字的内容摘要",
    )

    assert result.passed is False
    assert "use Chinese" in " ".join(result.violations)


def test_question_answer_quality_rejects_request_for_more_source_context() -> None:
    result = validate_evidence_summary_answer_question_answer_quality(
        "请提供您希望我详细展开的首页摘要的具体内容或主题。",
        user_question="首页内容可做成更详细的摘要吗？",
    )

    assert result.passed is False
    assert "already in the governed context" in " ".join(result.violations)


def test_question_answer_quality_rejects_request_for_longer_source_content() -> None:
    result = validate_evidence_summary_answer_question_answer_quality(
        "该内容本身非常简短，无法生成1200字的摘要。"
        "请提供更长的源内容以获得所需的详细摘要。",
        user_question="将其首页内容生成1200字的摘要",
    )

    assert result.passed is False
    assert "already in the governed context" in " ".join(result.violations)


def test_question_answer_quality_rejects_request_for_complete_homepage_content() -> None:
    result = validate_evidence_summary_answer_question_answer_quality(
        "摘要事实内容过于简短，不包含可以扩展到1200字的详细首页内容。"
        "请提供完整的、需要我进行摘要的首页内容。",
        user_question="请将首页内容改写成1200字的中文摘要",
    )

    assert result.passed is False
    assert "already in the governed context" in " ".join(result.violations)


def test_question_answer_quality_rejects_short_long_summary_without_limit_note() -> None:
    result = validate_evidence_summary_answer_question_answer_quality(
        "这是一个示例域名，用于文档示例，无需许可，不应实际使用。 (字数：约50字)",
        user_question="将首页内容做成500字的中文摘要",
    )

    assert result.passed is False
    assert "evidence limits" in " ".join(result.violations)


def test_question_answer_quality_rejects_short_inferred_long_summary_request() -> None:
    result = validate_evidence_summary_answer_question_answer_quality(
        "这个网页主要说明 Example Domain 是一个用于文档示例的域名。",
        user_question="帮我将其首页内容改写成1200 d的内容",
    )

    assert result.passed is False
    assert "evidence limits" in " ".join(result.violations)


def test_answerability_preflight_facts_detect_short_evidence_long_summary() -> None:
    facts = build_evidence_summary_answer_answerability_preflight_facts(
        user_question="请将首页内容改写成1200字的中文摘要",
        evidence_total_chars=96,
        summary_fact_chars=88,
        summary_fact_count=1,
    )

    assert facts["preflight_required"] is True
    assert facts["long_summary_requested"] is True
    assert facts["requested_chars"] == 1200
    assert facts["preflight_reason"] == "long_summary_request_evidence_too_brief"
    assert facts["does_not_call_model"] is True


def test_answerability_preflight_facts_allows_long_evidence_long_summary() -> None:
    facts = build_evidence_summary_answer_answerability_preflight_facts(
        user_question="请将首页内容改写成1200字的中文摘要",
        evidence_total_chars=1200,
        summary_fact_chars=500,
        summary_fact_count=4,
    )

    assert facts["preflight_required"] is False
    assert facts["long_summary_requested"] is True
    assert facts["does_not_call_model"] is False


def test_answerability_preflight_facts_detect_short_evidence_100_char_summary() -> None:
    facts = build_evidence_summary_answer_answerability_preflight_facts(
        user_question="帮我生成100字内容摘要",
        evidence_total_chars=96,
        summary_fact_chars=88,
        summary_fact_count=1,
    )

    assert facts["preflight_required"] is True
    assert facts["long_summary_requested"] is True
    assert facts["requested_chars"] == 100
    assert facts["preflight_reason"] == "long_summary_request_evidence_too_brief"


def test_question_answer_quality_allows_short_long_summary_with_limit_note() -> None:
    result = validate_evidence_summary_answer_question_answer_quality(
        "资料内容很短，无法在不添加未证实信息的情况下整理成500字。"
        "基于现有证据，它说明 Example Domain 仅用于文档示例，无需许可，"
        "且不应在实际操作中使用。",
        user_question="将首页内容做成500字的中文摘要",
    )

    assert result.passed is True
    assert result.violations == ()


def test_result_quality_guard_accepts_natural_language_with_analysis_word() -> None:
    result = validate_evidence_summary_answer_answer_quality(
        "This analysis says the governed evidence supports using a schema first."
    )

    assert result.passed is True
    assert result.violations == ()


def test_generation_service_protocol_is_structural() -> None:
    class FakeGenerationService:
        def generate(self, context, **kwargs):  # noqa: ANN001, ANN003, ANN201
            return context

    service: EvidenceSummaryAnswerGenerationService = FakeGenerationService()

    assert service.generate({"request_id": "request-1"}) == {"request_id": "request-1"}


def test_generation_policy_guard_accepts_controlled_live_generation_policy() -> None:
    result = validate_evidence_summary_answer_generation_policy(_generation_policy())

    assert result.passed is True
    assert result.violations == ()


def test_generation_policy_guard_rejects_smoke_only_success() -> None:
    policy = _generation_policy()
    policy["profile"] = "smoke_only"

    result = EvidenceSummaryAnswerGenerationPolicyGuard().validate(policy)

    assert result.passed is False
    assert "smoke_only" in result.violations[0]


def test_generation_policy_guard_rejects_missing_provider_factory_ref() -> None:
    policy = _generation_policy()
    policy["llm_provider_factory_ref"] = None

    result = validate_evidence_summary_answer_generation_policy(policy)

    assert result.passed is False
    assert "llm_provider_factory_ref" in " ".join(result.violations)


def test_generation_preflight_guard_accepts_answerable_context_and_policy() -> None:
    result = validate_evidence_summary_answer_generation_preflight(
        _context(),
        generation_policy=_generation_policy(),
    )

    assert result.passed is True
    assert result.violations == ()


def test_generation_preflight_guard_rejects_no_answerable_digest() -> None:
    context = _context()
    digest = context["digests"][0]
    assert isinstance(digest, dict)
    digest["answerability"] = "insufficient_evidence"

    result = EvidenceSummaryAnswerGenerationPreflightGuard().validate(
        context,
        generation_policy=_generation_policy(),
    )

    assert result.passed is False
    assert "answerable" in " ".join(result.violations)


def test_llm_request_boundary_guard_accepts_generation_request_facts() -> None:
    result = validate_evidence_summary_answer_llm_request_boundary(_llm_request())

    assert result.passed is True
    assert result.violations == ()


def test_llm_request_boundary_guard_rejects_cli_smoke_metadata() -> None:
    request = _llm_request()
    metadata = request["metadata"]
    assert isinstance(metadata, dict)
    metadata["external_readonly_answer_context"] = {"user_question": "legacy"}

    result = EvidenceSummaryAnswerLlmRequestBoundaryGuard().validate(request)

    assert result.passed is False
    assert "external_readonly_answer_context" in " ".join(result.violations)


def test_llm_request_boundary_guard_rejects_prompt_messages_or_raw_metadata() -> None:
    request = _llm_request()
    metadata = request["metadata"]
    assert isinstance(metadata, dict)
    metadata["prompt"] = "raw prompt"

    result = validate_evidence_summary_answer_llm_request_boundary(request)

    assert result.passed is False
    assert "prompt" in " ".join(result.violations)


def test_result_mapping_guard_accepts_successful_generation_result() -> None:
    result = validate_evidence_summary_answer_result_mapping(_result())

    assert result.passed is True
    assert result.violations == ()


def test_result_mapping_guard_rejects_success_without_digest_refs() -> None:
    result_payload = _result()
    result_payload["digest_refs_used"] = []

    result = EvidenceSummaryAnswerResultMappingGuard().validate(result_payload)

    assert result.passed is False
    assert "digest_refs_used" in result.violations[0]


def test_evidence_summary_answer_guards_have_no_execution_layer_imports() -> None:
    source = (BEHAVIOR_SOURCE_ROOT / "evidence_summary_answer.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|cognition_cli|config_contexts|runtime_container|"
        r"composition|product_runtime_assembly|observability_hub|adk_adapter|"
        r"google\.adk|litellm)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None


def test_behavior_contracts_root_exports_evidence_summary_answer_guards() -> None:
    assert RootEvidenceSummaryAnswerHeaderGuard is EvidenceSummaryAnswerHeaderGuard
    assert RootFollowUpSeedGuard is EvidenceSummaryAnswerFollowUpSeedGuard
    assert RootQualityGuard is EvidenceSummaryAnswerResultQualityGuard
    assert RootTraceGuard is EvidenceSummaryAnswerTraceGuard
    assert RootArtifactGuard is EvidenceSummaryAnswerArtifactGuard
    assert root_validate_guards(_digest()).passed is True
    assert RootGenerationPolicyGuard is EvidenceSummaryAnswerGenerationPolicyGuard
    assert root_validate_generation_policy(_generation_policy()).passed is True


def _generation_policy() -> dict[str, object]:
    return {
        "enabled_by_default": False,
        "profile": "controlled_live_answer_generation",
        "exposure_enabled": True,
        "allow_model_context": True,
        "allow_governed_summary_facts": True,
        "allow_answer_generation_success": True,
        "requires_live_llm_gate": True,
        "answer_generation_service_ref": (
            "behavior-contract://evidence-summary-answer/generation-service-v1"
        ),
        "llm_provider_factory_ref": (
            "provider-factory://evidence-summary-answer/controlled-live/default-v1"
        ),
        "answer_policy_ref": "policy://evidence-summary-answer/answer-generation-v1",
        "citation_policy_ref": "policy://evidence-summary-answer/citation-v1",
        "allow_raw_boundary": False,
        "allow_sanitized_excerpt_preview": False,
        "allow_observability_candidate_body": False,
        "citation_required": True,
        "allow_citation_exception": False,
        "insufficient_evidence_required": True,
        "metadata": {"source": "behavior_contracts.test"},
    }


def _llm_request() -> dict[str, object]:
    return {
        "request_id": "request-1/llm",
        "route_facts": {
            "model_name": "ollama/gemma4-pro:latest",
            "provider": "litellm",
            "source": "behavior_contracts.test",
            "runtime_call_performed": False,
            "direct_litellm_completion": False,
            "governance_direct_model_call": False,
            "metadata": {
                "route_kind": "adk_litellm",
                "route_target": "ollama/gemma4-pro:latest",
            },
        },
        "governance_precondition": {
            "allowed": True,
            "reason": "evidence_summary_answer_generation_policy_allowed",
            "decision": "allow",
            "governance_decision_ref": "approval://test/evidence-summary-answer",
            "metadata": {"source": "behavior_contracts.test"},
        },
        "prompt_ref": "prompt://evidence-summary-answer/request-1",
        "prompt_preview_sanitized": "What does the governed evidence say?",
        "metadata": {
            "source": "behavior_contracts.test",
            "interaction_mode": "evidence_summary_answer_generation",
            "generation_profile": "controlled_live_answer_generation",
            "context_payload_type": "evidence_summary_answer_context",
            "context_payload_version": EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION,
            "digest_count": 1,
            "answerable_digest_count": 1,
            "no_fetch_search": True,
            "refs_source": "context",
            "evidence_summary_answer_context": {
                "request_id": "request-1",
                "user_question": "What does the governed evidence say?",
                "summary_facts": [
                    "The source describes a governed answer context."
                ],
                "evidence_refs": [
                    {
                        "ref": "evidence://external-readonly/request-1/fetch-1",
                        "kind": "external_readonly_evidence",
                        "purpose": "answer_context",
                    }
                ],
                "digest_refs": [
                    "governed-evidence-digest://request-1/digest-1"
                ],
                "additional_refs": [],
                "answer_policy_ref": (
                    "policy://evidence-summary-answer/answer-generation-v1"
                ),
                "citation_policy_ref": (
                    "policy://evidence-summary-answer/citation-v1"
                ),
                "answer_constraints": [
                    "Only answer from governed summary facts and refs."
                ],
            },
        },
    }


def _follow_up_seed() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_follow_up_seed",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SEED_VERSION,
        "seed_id": "seed-1",
        "seed_ref": "evidence-summary-answer-follow-up://seed-1",
        "source_request_id": "request-1",
        "source_result_status": "success",
        "digest_refs": ["governed-evidence-digest://request-1/digest-1"],
        "evidence_refs": [
            {
                "ref": "evidence://external-readonly/request-1/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "answer_context",
            }
        ],
        "additional_refs": [
            {
                "ref": "governed-evidence-digest://request-1/digest-1",
                "kind": "governed_evidence_digest",
                "purpose": "digest_context",
            }
        ],
        "follow_up_allowed": True,
        "temporary_only": True,
        "durable_session": False,
        "memory_enabled": False,
        "blocking_reasons": [],
        "warnings": [],
        "metadata": {"source": "behavior_contracts.test"},
    }


def _digest() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "governed_evidence_digest",
        "payload_version": GOVERNED_EVIDENCE_DIGEST_VERSION,
        "digest_id": "digest-1",
        "digest_ref": "governed-evidence-digest://request-1/digest-1",
        "evidence_ref": "evidence://external-readonly/request-1/fetch-1",
        "evidence_output_ref": "external-readonly-output://request-1/fetch-1",
        "source_url_host": "example.com",
        "source_url_scheme": "https",
        "runtime_status": "success",
        "status": "ready",
        "reference_review_ready": True,
        "allowed_for_model_context": True,
        "evidence_written": True,
        "content_hash": "sha256:abc123",
        "total_excerpt_chars": 128,
        "raw_boundary_flags": {},
        "blocking_reasons": [],
        "warnings": [],
        "summary_facts": ["The source describes a governed answer context."],
        "topic_labels": ["contracts"],
        "risk_labels": [],
        "answerability": "answerable",
        "digest_generation_policy_ref": (
            "policy://evidence-summary-answer/digest-generation-v1"
        ),
        "digest_budget": 4000,
        "metadata": {"source": "behavior_contracts.test"},
    }


def _context() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_context",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION,
        "request_id": "request-1",
        "user_question": "What does the governed evidence say?",
        "digests": [copy.deepcopy(_digest())],
        "evidence_refs": [
            {
                "ref": "evidence://external-readonly/request-1/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "answer_context",
            }
        ],
        "additional_refs": [
            {
                "ref": "governed-evidence-digest://request-1/digest-1",
                "kind": "governed_evidence_digest",
                "purpose": "digest_context",
            }
        ],
        "answer_policy_ref": "policy://evidence-summary-answer/answer-v1",
        "citation_policy_ref": "policy://evidence-summary-answer/citation-v1",
        "model_context_budget": 4000,
        "metadata": {"source": "behavior_contracts.test"},
    }


def _result(*, status: str = "success") -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_result",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION,
        "request_id": "request-1",
        "status": status,
        "answer": "The governed evidence supports using a schema first.",
        "answer_preview": "The governed evidence supports using a schema first.",
        "evidence_refs_used": [
            {
                "ref": "evidence://external-readonly/request-1/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "citation",
            }
        ],
        "digest_refs_used": ["governed-evidence-digest://request-1/digest-1"],
        "additional_refs_used": [],
        "insufficient_evidence_reason": None,
        "citation_failures": [],
        "blocking_reasons": [],
        "warnings": [],
        "llm_call_allowed": True,
        "llm_call_attempted": True,
        "llm_runtime_call_performed": True,
        "raw_boundary_flags": {},
        "metadata": {"source": "behavior_contracts.test"},
    }


def _trace() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_trace",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_TRACE_VERSION,
        "trace_id": "trace-1",
        "trace_ref": f"{EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX}trace-1",
        "request_id": "request-1",
        "answer_status": "success",
        "readonly_refs_status": "ready",
        "evidence_ref_count": 1,
        "additional_ref_count": 1,
        "digest_ref_count": 1,
        "evidence_refs": [
            {
                "ref": "evidence://external-readonly/request-1/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "answer_context",
            }
        ],
        "additional_refs": [
            {
                "ref": "governed-evidence-digest://request-1/digest-1",
                "kind": "governed_evidence_digest",
                "purpose": "digest_context",
            }
        ],
        "digest_refs": ["governed-evidence-digest://request-1/digest-1"],
        "blocking_reasons": [],
        "warnings": [],
        "insufficient_evidence_reason": None,
        "citation_failures": [],
        "llm_call_allowed": True,
        "llm_call_attempted": True,
        "llm_runtime_call_performed": True,
        "answerability_preflight_applied": False,
        "answer_ref": f"{EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX}trace-1/answer",
        "answer_preview": "The governed evidence supports using a schema first.",
        "follow_up": False,
        "temporary_follow_up": True,
        "durable_session": False,
        "memory_enabled": False,
        "task_compatible": True,
        "workflow_compatible": True,
        "backed_by_adk_task_runtime": False,
        "backed_by_adk_workflow_runtime": False,
        "raw_boundary_flags": {},
        "metadata": {"source": "behavior_contracts.test"},
    }


def _artifact() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_artifact",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_ARTIFACT_VERSION,
        "artifact_id": "artifact-1",
        "artifact_ref": f"{EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX}artifact-1",
        "request_id": "request-1",
        "answer_status": "success",
        "artifact_status": "success",
        "trace_ref": f"{EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX}trace-1",
        "artifact_policy_ref": (
            "policy://product-application-assembly/evidence-summary-answer/"
            "artifact-v1"
        ),
        "evidence_ref_count": 1,
        "additional_ref_count": 1,
        "digest_ref_count": 1,
        "evidence_refs": [
            {
                "ref": "evidence://external-readonly/request-1/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "answer_context",
            }
        ],
        "additional_refs": [
            {
                "ref": "governed-evidence-digest://request-1/digest-1",
                "kind": "governed_evidence_digest",
                "purpose": "digest_context",
            }
        ],
        "digest_refs": ["governed-evidence-digest://request-1/digest-1"],
        "blocking_reasons": [],
        "warnings": [],
        "insufficient_evidence_reason": None,
        "citation_failures": [],
        "llm_call_allowed": True,
        "llm_call_attempted": True,
        "llm_runtime_call_performed": True,
        "answerability_preflight_applied": False,
        "answer_ref": f"{EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX}trace-1/answer",
        "answer": "The governed evidence supports using a schema first.",
        "answer_preview": "The governed evidence supports using a schema first.",
        "export_allowed": False,
        "delete_supported": True,
        "retention_policy_ref": None,
        "durable_session": False,
        "memory_enabled": False,
        "task_compatible": True,
        "workflow_compatible": True,
        "backed_by_adk_task_runtime": False,
        "backed_by_adk_workflow_runtime": False,
        "raw_boundary_flags": {},
        "metadata": {"source": "behavior_contracts.test"},
    }
