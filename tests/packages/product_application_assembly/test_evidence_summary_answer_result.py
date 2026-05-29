from __future__ import annotations

from pathlib import Path

from behavior_contracts.evidence_summary_answer import (
    validate_evidence_summary_answer_guards,
)
from product_application_assembly import (
    EvidenceSummaryAnswerProductOutputAssemblyResult,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ARTIFACT_POLICY_REF,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_POLICY_REF,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_PRODUCT_OUTPUT_SOURCE,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_POLICY_REF,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_SOURCE,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RUN_POLICY_REF,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_POLICY_REF,
    build_evidence_summary_answer_run,
    build_evidence_summary_answer_artifact,
    build_evidence_summary_answer_context,
    build_evidence_summary_answer_observability_summary,
    assemble_evidence_summary_answer_product_output,
    build_evidence_summary_answer_trace,
    build_evidence_summary_answer_trace_inspect,
    build_evidence_summary_answer_answerability_preflight_result,
    build_no_model_evidence_summary_answer_result,
    evidence_summary_answer_artifact_status_dict,
    evidence_summary_answer_artifact_summary_dict,
    evidence_summary_answer_observability_summary_gateway_dict,
    evidence_summary_answer_observability_summary_status_dict,
    evidence_summary_answer_result_status_dict,
    evidence_summary_answer_run_status_dict,
    evidence_summary_answer_run_summary_dict,
    evidence_summary_answer_trace_inspect_gateway_dict,
    evidence_summary_answer_trace_inspect_status_dict,
    evidence_summary_answer_trace_status_dict,
    evidence_summary_answer_trace_summary_dict,
)
from schemas.evidence_summary_answer import (
    EvidenceSummaryAnswerArtifactSchema,
    EvidenceSummaryAnswerObservabilitySummarySchema,
    EvidenceSummaryAnswerResultSchema,
    EvidenceSummaryAnswerRunSchema,
    EvidenceSummaryAnswerTraceSchema,
    EvidenceSummaryAnswerTraceInspectSchema,
    validate_evidence_summary_answer_artifact,
    validate_evidence_summary_answer_observability_summary,
    validate_evidence_summary_answer_result,
    validate_evidence_summary_answer_run,
    validate_evidence_summary_answer_trace,
    validate_evidence_summary_answer_trace_inspect,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
BUILDER_SOURCE = (
    REPO_ROOT
    / "packages"
    / "product_application_assembly"
    / "src"
    / "product_application_assembly"
    / "evidence_summary_answer_result.py"
)


def test_no_model_result_blocks_answerable_context_without_answer() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
    )

    result = build_no_model_evidence_summary_answer_result(context)
    status = evidence_summary_answer_result_status_dict(result)

    assert isinstance(result, EvidenceSummaryAnswerResultSchema)
    assert result.status == "blocked"
    assert result.answer is None
    assert result.answer_preview is None
    assert result.blocking_reasons == [
        "answer_generation_not_configured_for_answerable_context"
    ]
    assert result.evidence_refs_used == []
    assert result.digest_refs_used == ["governed-evidence-digest://digest-603"]
    assert result.additional_refs_used[0].ref == "governed-evidence-digest://digest-603"
    assert result.llm_call_allowed is False
    assert result.llm_call_attempted is False
    assert result.llm_runtime_call_performed is False
    assert (
        result.metadata["source"]
        == PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_SOURCE
    )
    assert (
        result.metadata["policy_ref"]
        == PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_POLICY_REF
    )
    assert result.metadata["context_payload_type"] == "evidence_summary_answer_context"
    assert (
        result.metadata["context_payload_version"]
        == "evidence_summary_answer_context_v1"
    )
    assert result.metadata["digest_count"] == 1
    assert result.metadata["no_model"] is True
    assert validate_evidence_summary_answer_result(status).request_id == "request-603"
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_answerability_preflight_blocks_over_scope_generation_request() -> None:
    digest = {
        **_ready_digest(),
        "total_excerpt_chars": 2200,
        "summary_facts": [
            "Cognition System is a controlled product for evidence-based answers.",
            "The product currently supports public material reading and governed QA.",
            "The public guide explains installation, usage, and safety boundaries.",
        ],
    }
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="请基于这份资料生成3000字完整产品白皮书，并补充未来路线图。",
        digests=[digest],
    )

    result = build_evidence_summary_answer_answerability_preflight_result(context)
    assert result is not None
    status = evidence_summary_answer_result_status_dict(result)

    assert result.status == "success"
    assert result.llm_call_allowed is False
    assert result.llm_call_attempted is False
    assert result.llm_runtime_call_performed is False
    assert "超出了受治理证据可直接支持的输出范围" in (result.answer or "")
    assert "未来路线图" in (result.answer or "")
    assert result.metadata["answerability_preflight_reason"] == (
        "over_scope_generation_request"
    )
    assert result.metadata["over_scope_requested"] is True
    assert validate_evidence_summary_answer_result(status).status == "success"
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_answerability_preflight_over_scope_answer_ends_at_sentence_boundary() -> None:
    digest = {
        **_ready_digest(),
        "total_excerpt_chars": 2400,
        "summary_facts": [
            (
                "Cognition System 是一个面向受治理 AI 协作的认知能力系统。"
                "它把大模型、工具生态、运行能力和治理规则组合起来。"
            ),
            (
                "当前可直接体验的能力是基于用户授权读取外部只读资料，"
                "并给出可复查回答。"
            ),
            (
                "回答会说明答案依据、证据引用和受限原因，资料不足时不会"
                "编造扩展内容。"
            ),
        ],
    }
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="请基于这份资料生成3000字完整产品白皮书，并补充未来路线图。",
        digests=[digest],
    )

    result = build_evidence_summary_answer_answerability_preflight_result(context)

    assert result is not None
    assert result.answer is not None
    assert result.answer.endswith(("。", "！", "？", "……"))
    assert "资料不。" not in result.answer


def test_answer_trace_wraps_result_without_runtime_backing() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
    )
    result = EvidenceSummaryAnswerResultSchema(
        request_id="request-603",
        status="success",
        answer="The governed evidence supports using a schema first.",
        answer_preview="The governed evidence supports using a schema first.",
        evidence_refs_used=list(context.evidence_refs),
        digest_refs_used=["governed-evidence-digest://digest-603"],
        additional_refs_used=list(context.additional_refs),
        llm_call_allowed=True,
        llm_call_attempted=True,
        llm_runtime_call_performed=True,
        metadata={
            "source": "unit-test",
            "llm_route_provider": "litellm",
            "llm_route_model": "ollama/gemma4-pro:latest",
        },
    )

    trace = build_evidence_summary_answer_trace(
        context,
        evidence_summary_answer_result_status_dict(result),
        readonly_refs_status="ready",
        metadata={
            "provider_profile_ref": "local_ollama",
            "model_profile_ref": "gemma4_pro_local",
            "output_governance_profile_ref": "adk_output_schema_gemma4_baseline",
        },
    )
    status = evidence_summary_answer_trace_status_dict(trace)
    summary = evidence_summary_answer_trace_summary_dict(trace)

    assert isinstance(trace, EvidenceSummaryAnswerTraceSchema)
    assert trace.answer_status == "success"
    assert trace.task_compatible is True
    assert trace.workflow_compatible is True
    assert trace.backed_by_adk_task_runtime is False
    assert trace.backed_by_adk_workflow_runtime is False
    assert trace.llm_route_provider == "litellm"
    assert trace.llm_route_model == "ollama/gemma4-pro:latest"
    assert trace.provider_profile_ref == "local_ollama"
    assert trace.model_profile_ref == "gemma4_pro_local"
    assert trace.output_governance_profile_ref == "adk_output_schema_gemma4_baseline"
    assert trace.answer_ref == f"{trace.trace_ref}/answer"
    assert summary["trace_ref"] == trace.trace_ref
    assert summary["trace_status"] == "success"
    assert summary["llm_runtime_call_performed"] is True
    assert summary["provider_profile_ref"] == "local_ollama"
    assert summary["model_profile_ref"] == "gemma4_pro_local"
    assert (
        summary["output_governance_profile_ref"]
        == "adk_output_schema_gemma4_baseline"
    )
    assert validate_evidence_summary_answer_trace(status).trace_id == trace.trace_id
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_product_output_assembly_owns_answer_facts_and_gateway_summary() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
    )
    result = EvidenceSummaryAnswerResultSchema(
        request_id="request-603",
        status="success",
        answer="The governed evidence supports using a schema first.",
        answer_preview="The governed evidence supports using a schema first.",
        evidence_refs_used=list(context.evidence_refs),
        digest_refs_used=["governed-evidence-digest://digest-603"],
        additional_refs_used=list(context.additional_refs),
        llm_call_allowed=True,
        llm_call_attempted=True,
        llm_runtime_call_performed=True,
        metadata={
            "source": "unit-test",
            "llm_route_provider": "litellm",
            "llm_route_model": "ollama/gemma4-pro:latest",
        },
    )

    assembled = assemble_evidence_summary_answer_product_output(
        context,
        evidence_summary_answer_result_status_dict(result),
        request_id="request-603",
        readonly_refs_status="ready",
        blocking_reasons=(),
        warnings=("review_scope_limited",),
        recovery_hints=("Use a more specific question.",),
        source_url_present=True,
        evidence_path_count=0,
        model_name="ollama/gemma4-pro:latest",
        llm_call_allowed=True,
        llm_call_attempted=True,
        llm_runtime_call_performed=True,
        external_readonly_fetch_performed=True,
        external_readonly_network_call_performed=True,
        external_network_call_performed=True,
        product_path="external_readonly_ask_product_path",
        metadata={
            "input_channel": "unit-test",
            "config_context": "must-not-leak",
            "raw_payload": "must-not-leak",
        },
    )

    assert isinstance(assembled, EvidenceSummaryAnswerProductOutputAssemblyResult)
    assert assembled.answer_trace["trace_ref"].startswith(
        "evidence-summary-answer-trace://"
    )
    assert assembled.answer_artifact["artifact_ref"].startswith(
        "evidence-summary-answer-artifact://"
    )
    assert assembled.observability_summary["summary_ref"].startswith(
        "evidence-summary-answer-observability-summary://"
    )
    assert assembled.trace_inspect["trace_inspect_ref"].startswith(
        "evidence-summary-answer-trace-inspect://"
    )
    assert assembled.answer_run["answer_run_ref"].startswith(
        "evidence-summary-answer-run://"
    )
    assert assembled.answer_run["answer_run_status"] == "success"
    assert assembled.answer_run["answer_trace_ref"] == assembled.answer_trace["trace_ref"]
    assert (
        assembled.answer_run["answer_artifact_ref"]
        == assembled.answer_artifact["artifact_ref"]
    )
    assert assembled.answer_run["runtime_backed"] is False
    assert assembled.answer_run["backed_by_adk_task_runtime"] is False
    assert assembled.runtime_visible_summary["runtime_summary_ref"].startswith(
        "continuable-evidence-session-summary://"
    )
    assert (
        assembled.runtime_visible_summary["runtime_binding_status"] == "probed"
    )
    assert (
        assembled.runtime_visible_summary["runtime_artifact_index"][0]["ref"]
        == assembled.answer_artifact["artifact_ref"]
    )
    assert (
        assembled.runtime_visible_summary["runtime_evaluation_summary"][
            "evaluation_status"
        ]
        == "passed"
    )
    assert (
        assembled.runtime_visible_summary["user_product_runtime_path_enabled"]
        is False
    )
    assert assembled.runtime_visible_summary["workflow_replay_enabled"] is False
    assert (
        assembled.runtime_visible_summary["task_runtime_implementation_enabled"]
        is False
    )

    summary = assembled.product_response_summary
    assert summary["entry_kind"] == "external_readonly_ask"
    assert summary["status"] == "success"
    assert summary["answer_run_ref"] == assembled.answer_run["answer_run_ref"]
    assert summary["answer_run_status"] == "success"
    assert summary["answer_run_summary"]["workflow_compatible"] is True
    assert summary["answer_run_summary"]["runtime_backed"] is False
    assert summary["answer_trace_ref"] == assembled.answer_trace["trace_ref"]
    assert summary["answer_artifact_ref"] == assembled.answer_artifact["artifact_ref"]
    assert summary["runtime_summary_ref"] == (
        assembled.runtime_visible_summary["runtime_summary_ref"]
    )
    assert summary["runtime_availability_hint"]["runtime_binding_status"] == "probed"
    assert summary["runtime_artifact_index"][0]["ref"] == (
        assembled.answer_artifact["artifact_ref"]
    )
    assert summary["runtime_evaluation_summary"]["evaluation_status"] == "passed"
    assert (
        summary["metadata"]["product_gateway_response_source"]
        == PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_PRODUCT_OUTPUT_SOURCE
    )
    assert summary["metadata"]["digest_count"] == 1
    assert summary["metadata"]["summary_fact_count"] == 1
    assert "config_context" not in str(summary)
    assert "raw_payload" not in str(summary)


def test_answer_run_aggregates_child_refs_without_runtime_backing() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
    )
    result = EvidenceSummaryAnswerResultSchema(
        request_id="request-603",
        status="success",
        answer="The governed evidence supports using a schema first.",
        answer_preview="The governed evidence supports using a schema first.",
        evidence_refs_used=list(context.evidence_refs),
        digest_refs_used=["governed-evidence-digest://digest-603"],
        additional_refs_used=list(context.additional_refs),
        llm_call_allowed=True,
        llm_call_attempted=True,
        llm_runtime_call_performed=True,
        metadata={"source": "unit-test"},
    )
    result_status = evidence_summary_answer_result_status_dict(result)
    trace = build_evidence_summary_answer_trace(
        context,
        result_status,
        readonly_refs_status="ready",
    )
    artifact = build_evidence_summary_answer_artifact(context, result_status, trace)
    observability_summary = build_evidence_summary_answer_observability_summary(
        request_id="request-603",
        answer_status="success",
        answer_result=result_status,
        answer_trace=trace,
        answer_artifact=artifact,
        evidence_refs=[ref.model_dump(mode="python") for ref in context.evidence_refs],
        additional_refs=[
            ref.model_dump(mode="python") for ref in context.additional_refs
        ],
        metadata={"source": "unit-test"},
    )
    trace_inspect = build_evidence_summary_answer_trace_inspect(
        request_id="request-603",
        answer_status="success",
        readonly_refs_status="ready",
        answer_trace=trace,
        answer_artifact=artifact,
        observability_summary=observability_summary,
        evidence_refs=[ref.model_dump(mode="python") for ref in context.evidence_refs],
        additional_refs=[
            ref.model_dump(mode="python") for ref in context.additional_refs
        ],
        metadata={"source": "unit-test"},
    )

    answer_run = build_evidence_summary_answer_run(
        request_id="request-603",
        answer_status="success",
        readonly_refs_status="ready",
        evidence_refs=[ref.model_dump(mode="python") for ref in context.evidence_refs],
        additional_refs=[
            ref.model_dump(mode="python") for ref in context.additional_refs
        ],
        answer_trace_ref=trace.trace_ref,
        answer_artifact_ref=artifact.artifact_ref,
        observability_summary_ref=observability_summary.summary_ref,
        trace_inspect_ref=trace_inspect.trace_inspect_ref,
        metadata={"source": "unit-test", "config_context": "must-not-leak"},
    )
    status = evidence_summary_answer_run_status_dict(answer_run)
    summary = evidence_summary_answer_run_summary_dict(answer_run)

    assert isinstance(answer_run, EvidenceSummaryAnswerRunSchema)
    assert answer_run.answer_run_status == "success"
    assert answer_run.metadata["policy_ref"] == (
        PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RUN_POLICY_REF
    )
    assert "config_context" not in str(answer_run.metadata)
    assert answer_run.runtime_backed is False
    assert summary["answer_run_ref"] == answer_run.answer_run_ref
    assert summary["task_compatible"] is True
    assert summary["backed_by_adk_event_stream"] is False
    assert validate_evidence_summary_answer_run(status).run_id == answer_run.run_id
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_answer_artifact_wraps_trace_without_runtime_backing() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
    )
    result = EvidenceSummaryAnswerResultSchema(
        request_id="request-603",
        status="success",
        answer="The governed evidence supports using a schema first.",
        answer_preview="The governed evidence supports using a schema first.",
        evidence_refs_used=list(context.evidence_refs),
        digest_refs_used=["governed-evidence-digest://digest-603"],
        additional_refs_used=list(context.additional_refs),
        llm_call_allowed=True,
        llm_call_attempted=True,
        llm_runtime_call_performed=True,
        metadata={"source": "unit-test"},
    )
    trace = build_evidence_summary_answer_trace(
        context,
        evidence_summary_answer_result_status_dict(result),
        readonly_refs_status="ready",
    )

    artifact = build_evidence_summary_answer_artifact(
        context,
        evidence_summary_answer_result_status_dict(result),
        trace,
    )
    status = evidence_summary_answer_artifact_status_dict(artifact)
    summary = evidence_summary_answer_artifact_summary_dict(artifact)

    assert isinstance(artifact, EvidenceSummaryAnswerArtifactSchema)
    assert artifact.answer_status == "success"
    assert artifact.artifact_status == "success"
    assert artifact.artifact_policy_ref == (
        PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ARTIFACT_POLICY_REF
    )
    assert artifact.trace_ref == trace.trace_ref
    assert artifact.answer == "The governed evidence supports using a schema first."
    assert artifact.task_compatible is True
    assert artifact.workflow_compatible is True
    assert artifact.backed_by_adk_task_runtime is False
    assert artifact.backed_by_adk_workflow_runtime is False
    assert artifact.export_allowed is False
    assert artifact.delete_supported is True
    assert summary["artifact_ref"] == artifact.artifact_ref
    assert summary["artifact_status"] == "success"
    assert summary["answer_present"] is True
    assert summary["task_compatible"] is True
    assert validate_evidence_summary_answer_artifact(status).artifact_id == (
        artifact.artifact_id
    )
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_answer_observability_summary_wraps_trace_and_artifact_safely() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
    )
    result = EvidenceSummaryAnswerResultSchema(
        request_id="request-603",
        status="success",
        answer="The governed evidence supports using a schema first.",
        answer_preview="The governed evidence supports using a schema first.",
        evidence_refs_used=list(context.evidence_refs),
        digest_refs_used=["governed-evidence-digest://digest-603"],
        additional_refs_used=list(context.additional_refs),
        llm_call_allowed=True,
        llm_call_attempted=True,
        llm_runtime_call_performed=True,
        metadata={"source": "unit-test"},
    )
    result_status = evidence_summary_answer_result_status_dict(result)
    trace = build_evidence_summary_answer_trace(
        context,
        result_status,
        readonly_refs_status="ready",
    )
    artifact = build_evidence_summary_answer_artifact(context, result_status, trace)

    summary = build_evidence_summary_answer_observability_summary(
        request_id="request-603",
        answer_status="success",
        answer_result=result_status,
        answer_trace=trace,
        answer_artifact=artifact,
        evidence_refs=[ref.model_dump(mode="python") for ref in context.evidence_refs],
        additional_refs=[
            ref.model_dump(mode="python") for ref in context.additional_refs
        ],
        metadata={"source": "unit-test"},
    )
    status = evidence_summary_answer_observability_summary_status_dict(summary)
    gateway_summary = evidence_summary_answer_observability_summary_gateway_dict(
        summary
    )

    assert isinstance(summary, EvidenceSummaryAnswerObservabilitySummarySchema)
    assert summary.reason == "answer_ready"
    assert summary.task_compatible is True
    assert summary.workflow_compatible is True
    assert summary.runtime_backed is False
    assert summary.backed_by_adk_task_runtime is False
    assert summary.backed_by_adk_workflow_runtime is False
    assert summary.raw_boundary_summary.restricted_payload_absent is True
    assert (
        summary.metadata["policy_ref"]
        == PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_POLICY_REF
    )
    assert gateway_summary["summary_ref"] == summary.summary_ref
    assert gateway_summary["reason"] == "answer_ready"
    assert gateway_summary["runtime_backed"] is False
    assert validate_evidence_summary_answer_observability_summary(
        status
    ).summary_id == summary.summary_id
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_answer_trace_inspect_builds_safe_product_view() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
    )
    result = EvidenceSummaryAnswerResultSchema(
        request_id="request-603",
        status="success",
        answer="The governed evidence supports using a schema first.",
        answer_preview="The governed evidence supports using a schema first.",
        evidence_refs_used=list(context.evidence_refs),
        digest_refs_used=["governed-evidence-digest://digest-603"],
        additional_refs_used=list(context.additional_refs),
        llm_call_allowed=True,
        llm_call_attempted=True,
        llm_runtime_call_performed=True,
        metadata={"source": "unit-test"},
    )
    result_status = evidence_summary_answer_result_status_dict(result)
    trace = build_evidence_summary_answer_trace(
        context,
        result_status,
        readonly_refs_status="ready",
    )
    artifact = build_evidence_summary_answer_artifact(context, result_status, trace)
    observability_summary = build_evidence_summary_answer_observability_summary(
        request_id="request-603",
        answer_status="success",
        answer_result=result_status,
        answer_trace=trace,
        answer_artifact=artifact,
        evidence_refs=[ref.model_dump(mode="python") for ref in context.evidence_refs],
        additional_refs=[
            ref.model_dump(mode="python") for ref in context.additional_refs
        ],
        metadata={"source": "unit-test"},
    )

    trace_inspect = build_evidence_summary_answer_trace_inspect(
        request_id="request-603",
        answer_status="success",
        readonly_refs_status="ready",
        answer_trace=trace,
        answer_artifact=artifact,
        observability_summary=observability_summary,
        evidence_refs=[ref.model_dump(mode="python") for ref in context.evidence_refs],
        additional_refs=[
            ref.model_dump(mode="python") for ref in context.additional_refs
        ],
        metadata={"source": "unit-test"},
    )
    status = evidence_summary_answer_trace_inspect_status_dict(trace_inspect)
    gateway_view = evidence_summary_answer_trace_inspect_gateway_dict(trace_inspect)

    assert isinstance(trace_inspect, EvidenceSummaryAnswerTraceInspectSchema)
    assert trace_inspect.inspect_status == "success"
    assert trace_inspect.inspect_reason == "answer_ready"
    assert trace_inspect.task_compatible is True
    assert trace_inspect.workflow_compatible is True
    assert trace_inspect.runtime_backed is False
    assert trace_inspect.raw_boundary_summary.restricted_payload_absent is True
    assert trace_inspect.raw_boundary_summary.restricted_boundary_intact is True
    assert (
        trace_inspect.metadata["policy_ref"]
        == PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_POLICY_REF
    )
    assert gateway_view["trace_inspect_ref"] == trace_inspect.trace_inspect_ref
    assert gateway_view["trace_inspect_status"] == "success"
    assert gateway_view["runtime_backed"] is False
    assert validate_evidence_summary_answer_trace_inspect(
        status
    ).trace_inspect_id == trace_inspect.trace_inspect_id
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_answer_observability_summary_explains_transport_block() -> None:
    summary = build_evidence_summary_answer_observability_summary(
        request_id="request-transport-blocked",
        answer_status="blocked",
        blocking_reasons=("transport_error", "http_status_not_success"),
        warnings=("content_type_missing",),
        readonly_refs_status="blocked",
    )
    gateway_summary = evidence_summary_answer_observability_summary_gateway_dict(
        summary
    )

    assert summary.reason == "transport_error"
    assert summary.user_explanation == (
        "本轮未能成功读取外部资料，可能是网络、远端服务或 URL "
        "临时不可用导致。请稍后重试，或确认 URL 可访问。"
    )
    assert gateway_summary["reason"] == "transport_error"
    assert gateway_summary["user_explanation"] == summary.user_explanation
    assert validate_evidence_summary_answer_observability_summary(
        evidence_summary_answer_observability_summary_status_dict(summary)
    ).summary_id == summary.summary_id


def test_answer_artifact_covers_non_success_statuses() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_empty_digest()],
    )
    cases = (
        (
            EvidenceSummaryAnswerResultSchema(
                request_id="request-603",
                status="blocked",
                blocking_reasons=["operator_approval_not_true"],
                digest_refs_used=["governed-evidence-digest://digest-603"],
                additional_refs_used=list(context.additional_refs),
            ),
            "blocked",
        ),
        (
            EvidenceSummaryAnswerResultSchema(
                request_id="request-603",
                status="insufficient_evidence",
                insufficient_evidence_reason="no_answerable_governed_evidence_digest",
                digest_refs_used=["governed-evidence-digest://digest-603"],
                additional_refs_used=list(context.additional_refs),
            ),
            "insufficient_evidence",
        ),
        (
            EvidenceSummaryAnswerResultSchema(
                request_id="request-603",
                status="failed",
                blocking_reasons=["llm_invocation_failure"],
                digest_refs_used=["governed-evidence-digest://digest-603"],
                additional_refs_used=list(context.additional_refs),
            ),
            "failed",
        ),
    )

    for result, expected_status in cases:
        result_status = evidence_summary_answer_result_status_dict(result)
        trace = build_evidence_summary_answer_trace(
            context,
            result_status,
            readonly_refs_status=expected_status,
        )
        artifact = build_evidence_summary_answer_artifact(
            context,
            result_status,
            trace,
        )
        status = evidence_summary_answer_artifact_status_dict(artifact)

        assert artifact.answer_status == expected_status
        assert artifact.artifact_status == expected_status
        assert artifact.answer is None
        assert artifact.backed_by_adk_task_runtime is False
        assert artifact.backed_by_adk_workflow_runtime is False
        assert validate_evidence_summary_answer_artifact(status).artifact_status == (
            expected_status
        )
        assert validate_evidence_summary_answer_guards(status).passed is True


def test_no_model_result_blocks_all_blocked_context_with_digest_reasons() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[
            _blocked_digest(
                digest_id="digest-603-a",
                reason="reference_review_not_ready",
            ),
            _blocked_digest(
                digest_id="digest-603-b",
                reason="external_readonly_evidence_not_written",
            ),
        ],
    )

    result = build_no_model_evidence_summary_answer_result(context)

    assert result.status == "blocked"
    assert result.blocking_reasons == [
        "reference_review_not_ready",
        "external_readonly_evidence_not_written",
    ]
    assert result.insufficient_evidence_reason is None
    assert validate_evidence_summary_answer_guards(
        evidence_summary_answer_result_status_dict(result)
    ).passed is True


def test_no_model_result_uses_blocked_fallback_when_reasons_are_absent() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_answerability_blocked_digest_without_reason()],
    )

    result = build_no_model_evidence_summary_answer_result(context)

    assert result.status == "blocked"
    assert result.blocking_reasons == ["all_governed_evidence_digests_blocked"]
    assert validate_evidence_summary_answer_guards(
        evidence_summary_answer_result_status_dict(result)
    ).passed is True


def test_no_model_result_marks_non_answerable_non_blocked_context_insufficient() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_empty_digest()],
    )

    result = build_no_model_evidence_summary_answer_result(context)

    assert result.status == "insufficient_evidence"
    assert result.insufficient_evidence_reason == "no_answerable_governed_evidence_digest"
    assert result.blocking_reasons == []
    assert result.answer is None
    assert result.answer_preview is None
    assert result.llm_call_allowed is False
    assert result.llm_call_attempted is False
    assert result.llm_runtime_call_performed is False
    assert validate_evidence_summary_answer_guards(
        evidence_summary_answer_result_status_dict(result)
    ).passed is True


def test_no_model_result_accepts_mapping_context_and_status_dict_accepts_mapping() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
    )

    result = build_no_model_evidence_summary_answer_result(
        context.model_dump(mode="json")
    )
    status = evidence_summary_answer_result_status_dict(
        result.model_dump(mode="json")
    )

    assert status["payload_type"] == "evidence_summary_answer_result"
    assert status["status"] == "blocked"
    assert status["answer"] is None
    assert status["answer_preview"] is None
    assert status["raw_boundary_flags"] == {}
    assert validate_evidence_summary_answer_result(status).status == "blocked"
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_no_model_result_filters_forbidden_metadata() -> None:
    context = build_evidence_summary_answer_context(
        request_id="request-603",
        user_question="What does the governed evidence say?",
        digests=[_ready_digest()],
    )

    result = build_no_model_evidence_summary_answer_result(
        context,
        metadata={
            "safe_label": "accepted",
            "prompt_marker": "ignored",
            "runtime_hint": "ignored",
            "raw_marker": "ignored",
            "safe_value_rejected": "response_text",
            "nested": {"safe": "ignored"},
        },
    )
    status = evidence_summary_answer_result_status_dict(result)

    assert result.metadata["safe_label"] == "accepted"
    assert "prompt_marker" not in result.metadata
    assert "runtime_hint" not in result.metadata
    assert "raw_marker" not in result.metadata
    assert "safe_value_rejected" not in result.metadata
    assert "nested" not in result.metadata
    assert validate_evidence_summary_answer_result(status).request_id == "request-603"
    assert validate_evidence_summary_answer_guards(status).passed is True


def test_no_model_result_never_produces_success_or_answer_fields() -> None:
    for digest in (_ready_digest(), _blocked_digest(), _empty_digest()):
        context = build_evidence_summary_answer_context(
            request_id="request-603",
            user_question="What does the governed evidence say?",
            digests=[digest],
        )

        result = build_no_model_evidence_summary_answer_result(context)

        assert result.status != "success"
        assert result.answer is None
        assert result.answer_preview is None


def test_no_model_result_is_exported_from_package_root() -> None:
    assert callable(build_no_model_evidence_summary_answer_result)
    assert callable(evidence_summary_answer_result_status_dict)


def test_no_model_result_source_has_no_forbidden_imports_or_inputs() -> None:
    source = BUILDER_SOURCE.read_text(encoding="utf-8")

    assert "from external_readonly" not in source
    assert "import external_readonly" not in source
    assert "behavior_contracts" not in source
    assert "contract_core" not in source
    assert "observability_hub" not in source
    assert "runtime_container" not in source
    assert "cognition_cli" not in source
    assert "cognition_operation_flows" not in source
    assert "product_runtime_assembly" not in source
    assert "google.adk" not in source
    assert "litellm" not in source
    assert "adk_adapter" not in source
    assert "provider_response" not in source
    assert "raw_provider_response" not in source
    assert "sanitized_excerpt" not in source
    assert "sanitized_excerpt_preview" not in source
    assert "model_context_items" not in source
    assert "ExternalReadonlyEvidenceEnvelope" not in source
    assert "ExternalReadonlyEvidenceSummary" not in source
    assert "ExternalReadonlyEvidenceReadContext" not in source
    assert "ProductGatewayResponse" not in source
    assert "observability_candidate_body" not in source
    assert "config_context" not in source


def _ready_digest() -> dict[str, object]:
    return {
        "product": "evidence_summary_answer",
        "payload_type": "governed_evidence_digest",
        "payload_version": "governed_evidence_digest_v1",
        "digest_id": "digest-603",
        "digest_ref": "governed-evidence-digest://digest-603",
        "evidence_ref": "evidence://external-readonly/item/603",
        "evidence_output_ref": "outputs/external-readonly/603.json",
        "source_url_host": "example.com",
        "source_url_scheme": "https",
        "runtime_status": "governed_summary_facts_ready",
        "status": "ready",
        "reference_review_ready": True,
        "allowed_for_model_context": True,
        "evidence_written": True,
        "content_hash": "c" * 64,
        "total_excerpt_chars": 45,
        "raw_boundary_flags": {},
        "blocking_reasons": [],
        "warnings": ["review_scope_limited"],
        "summary_facts": ["The source describes a governed answer context."],
        "topic_labels": ["contracts"],
        "risk_labels": [],
        "answerability": "answerable",
        "digest_generation_policy_ref": (
            "policy://product-application-assembly/governed-evidence-digest/minimal-v1"
        ),
        "digest_budget": 4000,
        "metadata": {"source": "product_application_assembly.test"},
    }


def _blocked_digest(
    *,
    digest_id: str = "digest-603",
    reason: str = "reference_review_not_ready",
) -> dict[str, object]:
    return {
        **_ready_digest(),
        "digest_id": digest_id,
        "digest_ref": f"governed-evidence-digest://{digest_id}",
        "evidence_ref": f"evidence://external-readonly/item/{digest_id}",
        "status": "blocked",
        "reference_review_ready": False,
        "allowed_for_model_context": False,
        "evidence_written": False,
        "total_excerpt_chars": 0,
        "blocking_reasons": [reason],
        "warnings": [],
        "summary_facts": [],
        "answerability": "blocked",
    }


def _answerability_blocked_digest_without_reason() -> dict[str, object]:
    return {
        **_ready_digest(),
        "status": "empty",
        "allowed_for_model_context": False,
        "evidence_written": False,
        "total_excerpt_chars": 0,
        "blocking_reasons": [],
        "warnings": [],
        "summary_facts": [],
        "answerability": "blocked",
    }


def _empty_digest() -> dict[str, object]:
    return {
        **_ready_digest(),
        "status": "empty",
        "allowed_for_model_context": False,
        "evidence_written": True,
        "total_excerpt_chars": 0,
        "blocking_reasons": [],
        "warnings": ["upstream_governed_summary_facts_empty"],
        "summary_facts": [],
        "answerability": "insufficient_evidence",
    }
