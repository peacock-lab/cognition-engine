"""CLI plan workflow skeleton for task-style terminal requests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any

from contract_core.llm_invocation import (
    GovernedLlmInvocationService,
    LlmGovernancePrecondition,
    LlmInvocationResult,
)
from contract_core.model_routing import ModelRouteFacts
from runtime_container.cli_task_control import (
    CliTaskRunContextCandidate,
    build_cli_task_run_context,
    cli_task_run_context_status_dict,
    finalize_cli_task_run_context,
)
from runtime_container.cli_reference_reader import (
    REFERENCE_READER_TOOL_NAME,
    CliReferenceReadRequestCandidate,
    read_cli_reference,
)
from runtime_container.cli_run_workspace import (
    CliRunWorkspaceStateCandidate,
    build_cli_run_workspace_policy,
    cleanup_cli_run_workspace,
    cli_run_workspace_status_dict,
    create_cli_run_workspace,
    finalize_cli_run_workspace,
    write_cli_run_workspace_json,
    write_cli_run_workspace_text,
)
from runtime_container.cli_tool_loading_validation import (
    cli_tool_loading_gate_status_dict,
    validate_cli_tool_loading_gate,
)
from runtime_container.cli_tool_exposure_profile import (
    cli_tool_exposure_profile_status_dict,
    resolve_cli_tool_exposure_profile,
)
from runtime_container.llm_invocation_facade import (
    RuntimeContainerLlmInvocationFacade,
    build_runtime_container_llm_invocation_request,
)


DEFAULT_PLAN_MODEL_NAME = "ollama/gemma4-pro:latest"
PLAN_PROMPT_PREVIEW_LIMIT = 80
PLAN_DISPLAY_PREVIEW_LIMIT = 4000
PLAN_REFERENCE_CONTEXT_TOTAL_CHAR_LIMIT = 1200
PLAN_WORKFLOW_NO_LIVE_MESSAGE = (
    "plan workflow 已识别方案类请求；当前为 no-live 路径，未生成方案。"
)
PLAN_WORKFLOW_FAIL_SAFE_MESSAGE = (
    "plan workflow 已进入受控失败边界：本轮未展示 raw provider response。"
)

PLAN_REQUEST_KEYWORDS = (
    "方案",
    "设计",
    "规划",
    "建设",
    "搭建",
    "实施",
    "部署",
    "开个",
    "建一个",
)
PLAN_DOMAIN_KEYWORDS = (
    "鱼塘",
    "养鸡场",
    "鸡场",
    "农场",
    "厂房",
    "门店",
)
FORMAT_REQUEST_KEYWORDS = ("排版", "换行", "重排", "整理", "太乱", "格式")
PLAN_CONTINUATION_KEYWORDS = (
    "所有的",
    "全部",
    "完整",
    "继续",
    "展开",
    "详细",
    "细节",
    "深入",
    "发给我",
    "发给我吧",
    "给我吧",
    "可以吗",
    "全面展开",
)
DEFLECTION_PATTERNS = (
    "请提供更多",
    "需要更多信息",
    "无法",
    "不能",
    "不清楚",
    "请先",
    "你想从哪里开始",
    "请告诉我",
)
JSON_LEAK_PATTERNS = (
    "{",
    "}",
    "```json",
    "system_context",
    "response_strategy",
    "protocol_support",
    "raw_provider_response",
)
TOOL_MOUNT_METADATA = {
    "quality_review_tool_mount": "reserved",
    "evidence_tool_mount": "reserved",
    "file_output_tool_mount": "reserved",
    "reference_reader_tool_mount": "reserved",
}


@dataclass(frozen=True)
class CliPlanWorkflowRequestCandidate:
    """Candidate request entering the CLI plan workflow skeleton."""

    user_text: str
    chat_session_id: str | None = None
    turn_index: int | None = None
    history: tuple[Mapping[str, str], ...] = ()
    previous_plan_text: str | None = None
    live_model_allowed: bool = False
    llm_invocation_service: GovernedLlmInvocationService | None = None
    approval_ref: str | None = None
    audit_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    risk_level: str = "low"
    output_budget: int | None = PLAN_DISPLAY_PREVIEW_LIMIT
    live_gate: str | None = None
    user_passthrough_parameters: Mapping[str, Any] = field(default_factory=dict)
    reference_paths: tuple[str, ...] = ()
    reference_repo_root: str | None = None
    reference_profile_name: str = "readonly_reference"
    reference_profile_config: Mapping[str, Any] | None = None
    reference_session_args: Mapping[str, Any] = field(default_factory=dict)
    reference_cli_explicit_args: Mapping[str, Any] = field(default_factory=dict)
    run_workspace_root: str | None = None
    run_workspace_enabled: bool = False
    run_workspace_retention_policy: str = "keep"
    run_workspace_cleanup_policy: str = "manual"
    run_workspace_max_write_bytes: int = 65536
    model_name: str = DEFAULT_PLAN_MODEL_NAME
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliPlanRequirementFactsCandidate:
    """Minimal requirement facts extracted before plan generation."""

    original_text: str
    request_kind: str
    entities: tuple[str, ...] = ()
    scales: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    format_requests: tuple[str, ...] = ()
    stage_instructions: dict[str, str] = field(default_factory=dict)
    output_policy: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliPlanDraftCandidate:
    """Plan draft candidate before terminal formatting and local review."""

    draft_text: str
    prompt_preview_sanitized: str | None
    model_call_count: int = 0
    source: str = "local"
    stage_instructions: dict[str, str] = field(default_factory=dict)
    output_policy: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliTerminalFormattedPlanCandidate:
    """Terminal-readable plan candidate."""

    formatted_text: str
    source: str = "local_formatter"
    stage_instructions: dict[str, str] = field(default_factory=dict)
    output_policy: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliPlanQualityReviewCandidate:
    """Local rule-based review result for the terminal plan candidate."""

    entity_coverage_ok: bool
    scale_coverage_ok: bool
    constraint_coverage_ok: bool
    format_ok: bool
    no_json_leak_ok: bool
    no_deflection_ok: bool
    terminal_readable_ok: bool
    passed: bool
    failure_reasons: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliPlanReferenceContextCandidate:
    """Bounded reference context consumed by the CLI plan workflow."""

    status: str
    requested_references: tuple[str, ...] = ()
    consumed_reference_count: int = 0
    reference_excerpts: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliPlanWorkflowResultCandidate:
    """Final workflow result returned to the CLI chat entrypoint."""

    triggered: bool
    terminal_display_text: str
    request: CliPlanWorkflowRequestCandidate
    requirement_facts: CliPlanRequirementFactsCandidate
    draft: CliPlanDraftCandidate | None
    formatted_plan: CliTerminalFormattedPlanCandidate | None
    quality_review: CliPlanQualityReviewCandidate | None
    model_call_count: int = 0
    no_live: bool = False
    fail_safe: bool = False
    task_run_context: CliTaskRunContextCandidate | None = None
    reference_context: CliPlanReferenceContextCandidate | None = None
    run_workspace: CliRunWorkspaceStateCandidate | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def detect_cli_plan_request(
    user_text: str,
    *,
    history: Sequence[Mapping[str, str]] | None = None,
    previous_plan_text: str | None = None,
) -> bool:
    """Return whether chat should route this turn into the plan workflow."""

    normalized = _compact_text(user_text)
    if not normalized:
        return False
    has_plan_intent = any(keyword in normalized for keyword in PLAN_REQUEST_KEYWORDS)
    has_domain = any(keyword in normalized for keyword in PLAN_DOMAIN_KEYWORDS)
    if has_plan_intent and (has_domain or "方案" in normalized):
        return True
    has_previous_plan = bool(previous_plan_text) or _history_contains_plan(history or ())
    if has_previous_plan and any(
        keyword in normalized for keyword in FORMAT_REQUEST_KEYWORDS
    ):
        return True
    if has_previous_plan and any(
        keyword in normalized for keyword in PLAN_CONTINUATION_KEYWORDS
    ):
        return True
    return False


def extract_cli_plan_requirements(
    request: CliPlanWorkflowRequestCandidate,
) -> CliPlanRequirementFactsCandidate:
    """Extract minimal facts while preserving user-provided entities and scales."""

    source_text = _requirement_source_text(request)
    entities = _ordered_unique(_extract_entities(source_text))
    scales = _ordered_unique(_extract_scales(source_text))
    constraints = _ordered_unique(_extract_constraints(source_text))
    format_requests = _ordered_unique(_extract_format_requests(request.user_text))
    request_kind = _plan_request_kind(request)
    return CliPlanRequirementFactsCandidate(
        original_text=request.user_text,
        request_kind=request_kind,
        entities=tuple(entities),
        scales=tuple(scales),
        constraints=tuple(constraints),
        format_requests=tuple(format_requests),
        stage_instructions={
            "requirement_extraction": (
                "Preserve user entities, scale numbers, units, and constraints."
            ),
            "skill_ready": "reserved_for_requirement_extraction_skill",
        },
        output_policy={
            "entity_policy": "must_not_rewrite_or_drop_user_entities",
            "scale_policy": "must_preserve_numbers_and_units",
        },
        metadata={
            "workflow_stage": "requirement_extraction",
            **TOOL_MOUNT_METADATA,
        },
    )


def build_cli_plan_draft_prompt(
    facts: CliPlanRequirementFactsCandidate,
    *,
    previous_plan_text: str | None = None,
    reference_context: CliPlanReferenceContextCandidate | None = None,
) -> str:
    """Build the compact prompt preview consumed by the governed LLM boundary."""

    if previous_plan_text:
        parts = [
            "重排已有方案",
            _join_or_default(facts.entities, "原对象"),
            _join_or_default(facts.scales, "原规模"),
            "保留标题编号换行",
        ]
    else:
        parts = [
            _join_or_default(facts.entities, "项目"),
            _join_or_default(facts.scales, "规模未明"),
            _join_or_default(facts.constraints, "约束未明"),
            _domain_specific_section_hint(facts.entities),
            "输出建设方案，编号换行",
        ]
    if reference_context and reference_context.consumed_reference_count:
        parts.append(
            "参考资料"
            + _join_or_default(
                tuple(reference_context.metadata.get("reference_labels", ())),
                "已读取",
            )
        )
    return _preview_text("，".join(parts), PLAN_PROMPT_PREVIEW_LIMIT)


def build_cli_plan_draft(
    request: CliPlanWorkflowRequestCandidate,
    facts: CliPlanRequirementFactsCandidate,
    reference_context: CliPlanReferenceContextCandidate | None = None,
) -> CliPlanDraftCandidate:
    """Generate or reuse a draft through the controlled-live LLM boundary."""

    prompt_preview = build_cli_plan_draft_prompt(
        facts,
        previous_plan_text=request.previous_plan_text,
        reference_context=reference_context,
    )
    if request.previous_plan_text and facts.request_kind == "format_existing_plan":
        return CliPlanDraftCandidate(
            draft_text=request.previous_plan_text,
            prompt_preview_sanitized=prompt_preview,
            model_call_count=0,
            source="previous_plan_context",
            stage_instructions={
                "plan_generation": "reuse_previous_plan_for_reformat_turn",
            },
            output_policy={
                "format_followup": "do_not_call_model_when_reformatting_existing_plan",
            },
            metadata={
                "workflow_stage": "plan_generation",
                "previous_plan_reused": True,
                **TOOL_MOUNT_METADATA,
            },
        )
    if not request.live_model_allowed:
        return CliPlanDraftCandidate(
            draft_text="",
            prompt_preview_sanitized=None,
            source="no_live_boundary",
            stage_instructions={
                "plan_generation": "reserved_for_plan_design_skill",
            },
            output_policy={
                "no_live": "do_not_fabricate_plan_without_live_model",
            },
            metadata={
                "workflow_stage": "plan_generation",
                "no_live": True,
                **TOOL_MOUNT_METADATA,
            },
        )

    result = _invoke_plan_llm(
        request,
        prompt_preview=prompt_preview,
        purpose="plan_draft",
        reference_context=reference_context,
    )
    model_text = _display_text_from_llm_result(result)
    if not result.success:
        return CliPlanDraftCandidate(
            draft_text="",
            prompt_preview_sanitized=prompt_preview,
            model_call_count=1,
            source="controlled_live_failed",
            stage_instructions={
                "plan_generation": "reserved_for_plan_design_skill",
            },
            output_policy={
                "failure": "fail_safe_without_raw_provider_response",
            },
            metadata={
                "workflow_stage": "plan_generation",
                "failure_type": (
                    str(result.failure_type.value)
                    if result.failure_type is not None
                    else None
                ),
                **TOOL_MOUNT_METADATA,
            },
        )
    if not model_text:
        return CliPlanDraftCandidate(
            draft_text=_local_plan_body(facts),
            prompt_preview_sanitized=prompt_preview,
            model_call_count=1,
            source="controlled_live_empty_display",
            stage_instructions={
                "plan_generation": "reserved_for_plan_design_skill",
            },
            output_policy={
                "empty_display": "render_requirement_facts_without_raw_provider_payload",
            },
            metadata={
                "workflow_stage": "plan_generation",
                "llm_invocation_success": True,
                "display_text_empty_after_sanitization": True,
                **TOOL_MOUNT_METADATA,
            },
        )

    return CliPlanDraftCandidate(
        draft_text=_merge_model_and_local_plan_body(model_text, facts),
        prompt_preview_sanitized=prompt_preview,
        model_call_count=1,
        source="controlled_live_llm",
        stage_instructions={
            "plan_generation": "reserved_for_plan_design_skill",
        },
        output_policy={
            "draft_policy": "plain_chinese_no_json_no_raw_provider_payload",
        },
        metadata={
            "workflow_stage": "plan_generation",
            "llm_invocation_success": True,
            **TOOL_MOUNT_METADATA,
        },
    )


def format_cli_plan_for_terminal(
    draft: CliPlanDraftCandidate,
    facts: CliPlanRequirementFactsCandidate,
    *,
    previous_plan_text: str | None = None,
    reference_context: CliPlanReferenceContextCandidate | None = None,
) -> CliTerminalFormattedPlanCandidate:
    """Format plan text for terminal display while preserving line breaks."""

    if previous_plan_text and facts.request_kind == "format_existing_plan":
        source_text = previous_plan_text
    else:
        source_text = draft.draft_text

    sanitized = _strip_json_fences(source_text).strip()
    body = _normalize_terminal_lines(sanitized)
    facts_block = _facts_block(facts)
    domain_block = _domain_block(facts)
    reference_block = _reference_block(reference_context)
    title = _plan_title(facts)
    if (
        previous_plan_text
        and facts.request_kind == "format_existing_plan"
        and "需求事实" in body
        and "建设方案" in body
    ):
        formatted = body
    else:
        formatted = "\n".join(
            item
            for item in (
                title,
                "",
                facts_block,
                "",
                domain_block,
                "",
                reference_block,
                "",
                body,
            )
            if item is not None
        ).strip()
    return CliTerminalFormattedPlanCandidate(
        formatted_text=formatted,
        stage_instructions={
            "terminal_formatting": "reserved_for_formatting_skill",
        },
        output_policy={
            "terminal_policy": "preserve_headings_numbering_and_line_breaks",
            "json_policy": "plain_text_only",
        },
        metadata={
            "workflow_stage": "terminal_formatting",
            **TOOL_MOUNT_METADATA,
        },
    )


def review_cli_plan_quality(
    formatted: CliTerminalFormattedPlanCandidate,
    facts: CliPlanRequirementFactsCandidate,
) -> CliPlanQualityReviewCandidate:
    """Review the formatted plan with local, deterministic rules."""

    text = formatted.formatted_text
    compact = _compact_text(text)
    entity_coverage_ok = all(entity in compact for entity in facts.entities)
    scale_coverage_ok = all(_compact_text(scale) in compact for scale in facts.scales)
    constraint_coverage_ok = all(
        _compact_text(constraint) in compact for constraint in facts.constraints
    )
    format_ok = "\n" in text and _has_heading_or_numbering(text)
    no_json_leak_ok = not any(pattern in text for pattern in JSON_LEAK_PATTERNS)
    no_deflection_ok = not any(pattern in text for pattern in DEFLECTION_PATTERNS)
    terminal_readable_ok = _terminal_readable(text)
    checks = {
        "entity_coverage_ok": entity_coverage_ok,
        "scale_coverage_ok": scale_coverage_ok,
        "constraint_coverage_ok": constraint_coverage_ok,
        "format_ok": format_ok,
        "no_json_leak_ok": no_json_leak_ok,
        "no_deflection_ok": no_deflection_ok,
        "terminal_readable_ok": terminal_readable_ok,
    }
    failure_reasons = tuple(name for name, ok in checks.items() if not ok)
    return CliPlanQualityReviewCandidate(
        entity_coverage_ok=entity_coverage_ok,
        scale_coverage_ok=scale_coverage_ok,
        constraint_coverage_ok=constraint_coverage_ok,
        format_ok=format_ok,
        no_json_leak_ok=no_json_leak_ok,
        no_deflection_ok=no_deflection_ok,
        terminal_readable_ok=terminal_readable_ok,
        passed=not failure_reasons,
        failure_reasons=failure_reasons,
        metadata={
            "workflow_stage": "quality_review",
            "review_kind": "local_rules",
            **TOOL_MOUNT_METADATA,
        },
    )


def build_cli_plan_terminal_display(
    formatted: CliTerminalFormattedPlanCandidate,
    review: CliPlanQualityReviewCandidate,
) -> str:
    """Build final safe terminal display text."""

    if not review.passed:
        return "\n".join(
            [
                PLAN_WORKFLOW_FAIL_SAFE_MESSAGE,
                "failure_reasons: " + ", ".join(review.failure_reasons),
            ]
        )
    return formatted.formatted_text


def run_cli_plan_workflow(
    request: CliPlanWorkflowRequestCandidate,
) -> CliPlanWorkflowResultCandidate:
    """Run the five-stage CLI plan workflow skeleton."""

    facts = extract_cli_plan_requirements(request)
    task_context = _build_plan_task_context(request, facts)
    if not task_context.preflight.allowed:
        task_context = finalize_cli_task_run_context(
            task_context,
            status="blocked",
            metadata={"blocked_before_model_call": True},
        )
        return CliPlanWorkflowResultCandidate(
            triggered=True,
            terminal_display_text=_preflight_blocked_terminal_display(task_context),
            request=request,
            requirement_facts=facts,
            draft=None,
            formatted_plan=None,
            quality_review=None,
            fail_safe=True,
            task_run_context=task_context,
            reference_context=None,
            run_workspace=None,
            metadata={
                "workflow": "cli_plan_workflow",
                "workflow_skeleton": True,
                **_task_context_metadata(task_context),
                **TOOL_MOUNT_METADATA,
            },
        )

    run_workspace = _create_plan_run_workspace(request, task_context)
    if run_workspace is not None and not run_workspace.workspace_created:
        task_context = _finalize_task_context_with_run_workspace(
            task_context,
            status="blocked",
            run_workspace=run_workspace,
            metadata={
                "blocked_before_model_call": True,
                "failure_stage": "run_workspace",
            },
        )
        return CliPlanWorkflowResultCandidate(
            triggered=True,
            terminal_display_text=_workspace_blocked_terminal_display(
                task_context,
                run_workspace,
            ),
            request=request,
            requirement_facts=facts,
            draft=None,
            formatted_plan=None,
            quality_review=None,
            fail_safe=True,
            task_run_context=task_context,
            reference_context=None,
            run_workspace=run_workspace,
            metadata={
                "workflow": "cli_plan_workflow",
                "workflow_skeleton": True,
                **_task_context_metadata(task_context),
                **_run_workspace_metadata(run_workspace),
                **TOOL_MOUNT_METADATA,
            },
        )

    if not request.live_model_allowed:
        task_context = finalize_cli_task_run_context(
            task_context,
            status="no_live_boundary",
            metadata={"no_live": True},
        )
        reference_context = _build_plan_reference_context(request, task_context)
        if reference_context.status == "blocked":
            display = _reference_blocked_terminal_display(
                task_context,
                reference_context,
            )
            run_workspace = _finalize_plan_run_workspace(
                run_workspace,
                status="blocked",
                terminal_display_text=display,
                facts=facts,
                reference_context=reference_context,
                model_call_count=0,
                fail_safe=True,
            )
            task_context = finalize_cli_task_run_context(
                task_context,
                status="blocked",
                evidence_refs=reference_context.evidence_refs,
                artifact_refs=_run_workspace_artifact_and_result_refs(run_workspace),
                workspace_ref=run_workspace.workspace_ref if run_workspace else None,
                workspace_created=(
                    run_workspace.workspace_created if run_workspace else None
                ),
                retention_policy=(
                    run_workspace.retention_policy if run_workspace else None
                ),
                cleanup_policy=run_workspace.cleanup_policy if run_workspace else None,
                workspace_metadata=cli_run_workspace_status_dict(run_workspace),
                metadata={
                    "blocked_before_model_call": True,
                    "failure_stage": "reference_context",
                },
            )
            return CliPlanWorkflowResultCandidate(
                triggered=True,
                terminal_display_text=display,
                request=request,
                requirement_facts=facts,
                draft=None,
                formatted_plan=None,
                quality_review=None,
                no_live=True,
                fail_safe=True,
                task_run_context=task_context,
                reference_context=reference_context,
                run_workspace=run_workspace,
                metadata={
                    "workflow": "cli_plan_workflow",
                    "workflow_skeleton": True,
                    **_task_context_metadata(task_context),
                    **_reference_context_metadata(reference_context),
                    **_run_workspace_metadata(run_workspace),
                    **TOOL_MOUNT_METADATA,
                },
            )
        display = _no_live_terminal_display(facts)
        run_workspace = _finalize_plan_run_workspace(
            run_workspace,
            status="no_live_boundary",
            terminal_display_text=display,
            facts=facts,
            reference_context=reference_context,
            model_call_count=0,
            fail_safe=False,
        )
        task_context = finalize_cli_task_run_context(
            task_context,
            status="no_live_boundary",
            evidence_refs=(
                *reference_context.evidence_refs,
                *(run_workspace.evidence_refs if run_workspace else ()),
            ),
            artifact_refs=_run_workspace_artifact_and_result_refs(run_workspace),
            workspace_ref=run_workspace.workspace_ref if run_workspace else None,
            workspace_created=run_workspace.workspace_created if run_workspace else None,
            retention_policy=run_workspace.retention_policy if run_workspace else None,
            cleanup_policy=run_workspace.cleanup_policy if run_workspace else None,
            workspace_metadata=cli_run_workspace_status_dict(run_workspace),
        )
        return CliPlanWorkflowResultCandidate(
            triggered=True,
            terminal_display_text=display,
            request=request,
            requirement_facts=facts,
            draft=None,
            formatted_plan=None,
            quality_review=None,
            no_live=True,
            task_run_context=task_context,
            reference_context=reference_context,
            run_workspace=run_workspace,
            metadata={
                "workflow": "cli_plan_workflow",
                "workflow_skeleton": True,
                **_task_context_metadata(task_context),
                **_reference_context_metadata(reference_context),
                **_run_workspace_metadata(run_workspace),
                **TOOL_MOUNT_METADATA,
            },
        )

    reference_context = _build_plan_reference_context(request, task_context)
    if reference_context.status == "blocked":
        display = _reference_blocked_terminal_display(
            task_context,
            reference_context,
        )
        run_workspace = _finalize_plan_run_workspace(
            run_workspace,
            status="blocked",
            terminal_display_text=display,
            facts=facts,
            reference_context=reference_context,
            model_call_count=0,
            fail_safe=True,
        )
        task_context = finalize_cli_task_run_context(
            task_context,
            status="blocked",
            evidence_refs=(
                *reference_context.evidence_refs,
                *(run_workspace.evidence_refs if run_workspace else ()),
            ),
            artifact_refs=_run_workspace_artifact_and_result_refs(run_workspace),
            workspace_ref=run_workspace.workspace_ref if run_workspace else None,
            workspace_created=run_workspace.workspace_created if run_workspace else None,
            retention_policy=run_workspace.retention_policy if run_workspace else None,
            cleanup_policy=run_workspace.cleanup_policy if run_workspace else None,
            workspace_metadata=cli_run_workspace_status_dict(run_workspace),
            metadata={
                "blocked_before_model_call": True,
                "failure_stage": "reference_context",
            },
        )
        return CliPlanWorkflowResultCandidate(
            triggered=True,
            terminal_display_text=display,
            request=request,
            requirement_facts=facts,
            draft=None,
            formatted_plan=None,
            quality_review=None,
            model_call_count=0,
            fail_safe=True,
            task_run_context=task_context,
            reference_context=reference_context,
            run_workspace=run_workspace,
            metadata={
                "workflow": "cli_plan_workflow",
                "workflow_skeleton": True,
                **_task_context_metadata(task_context),
                **_reference_context_metadata(reference_context),
                **_run_workspace_metadata(run_workspace),
                **TOOL_MOUNT_METADATA,
            },
        )

    draft = build_cli_plan_draft(request, facts, reference_context)
    if draft.source == "controlled_live_failed":
        display = _failed_terminal_display(facts)
        run_workspace = _finalize_plan_run_workspace(
            run_workspace,
            status="failed",
            terminal_display_text=display,
            facts=facts,
            reference_context=reference_context,
            model_call_count=draft.model_call_count,
            fail_safe=True,
        )
        task_context = finalize_cli_task_run_context(
            task_context,
            status="failed",
            evidence_refs=run_workspace.evidence_refs if run_workspace else (),
            artifact_refs=_run_workspace_artifact_and_result_refs(run_workspace),
            workspace_ref=run_workspace.workspace_ref if run_workspace else None,
            workspace_created=run_workspace.workspace_created if run_workspace else None,
            retention_policy=run_workspace.retention_policy if run_workspace else None,
            cleanup_policy=run_workspace.cleanup_policy if run_workspace else None,
            workspace_metadata=cli_run_workspace_status_dict(run_workspace),
            metadata={"failure_stage": "plan_generation"},
        )
        return CliPlanWorkflowResultCandidate(
            triggered=True,
            terminal_display_text=display,
            request=request,
            requirement_facts=facts,
            draft=draft,
            formatted_plan=None,
            quality_review=None,
            model_call_count=draft.model_call_count,
            fail_safe=True,
            task_run_context=task_context,
            reference_context=reference_context,
            run_workspace=run_workspace,
            metadata={
                "workflow": "cli_plan_workflow",
                "workflow_skeleton": True,
                **_task_context_metadata(task_context),
                **_reference_context_metadata(reference_context),
                **_run_workspace_metadata(run_workspace),
                **TOOL_MOUNT_METADATA,
            },
        )

    formatted = format_cli_plan_for_terminal(
        draft,
        facts,
        previous_plan_text=request.previous_plan_text,
        reference_context=reference_context,
    )
    review = review_cli_plan_quality(formatted, facts)
    display = build_cli_plan_terminal_display(formatted, review)
    run_workspace = _finalize_plan_run_workspace(
        run_workspace,
        status="succeeded" if review.passed else "failed",
        terminal_display_text=display,
        facts=facts,
        reference_context=reference_context,
        model_call_count=draft.model_call_count,
        fail_safe=not review.passed,
    )
    task_context = finalize_cli_task_run_context(
        task_context,
        status="succeeded" if review.passed else "failed",
        artifact_refs=(
            f"candidate-artifact://{task_context.run_id}/terminal_display",
            *_run_workspace_artifact_and_result_refs(run_workspace),
        ),
        evidence_refs=(
            *reference_context.evidence_refs,
            *(run_workspace.evidence_refs if run_workspace else ()),
        ),
        workspace_ref=run_workspace.workspace_ref if run_workspace else None,
        workspace_created=run_workspace.workspace_created if run_workspace else None,
        retention_policy=run_workspace.retention_policy if run_workspace else None,
        cleanup_policy=run_workspace.cleanup_policy if run_workspace else None,
        workspace_metadata=cli_run_workspace_status_dict(run_workspace),
        metadata={"failure_stage": "quality_review"} if not review.passed else {},
    )
    return CliPlanWorkflowResultCandidate(
        triggered=True,
        terminal_display_text=display,
        request=request,
        requirement_facts=facts,
        draft=draft,
        formatted_plan=formatted,
        quality_review=review,
        model_call_count=draft.model_call_count,
        fail_safe=not review.passed,
        task_run_context=task_context,
        reference_context=reference_context,
        run_workspace=run_workspace,
        metadata={
            "workflow": "cli_plan_workflow",
            "workflow_skeleton": True,
            "max_model_calls": 2,
            **_task_context_metadata(task_context),
            **_reference_context_metadata(reference_context),
            **_run_workspace_metadata(run_workspace),
            **TOOL_MOUNT_METADATA,
        },
    )


def _invoke_plan_llm(
    request: CliPlanWorkflowRequestCandidate,
    *,
    prompt_preview: str,
    purpose: str,
    reference_context: CliPlanReferenceContextCandidate | None = None,
) -> LlmInvocationResult:
    service = request.llm_invocation_service
    if service is None:
        raise ValueError("llm_invocation_service is required for controlled-live plan workflow")
    facade = RuntimeContainerLlmInvocationFacade(
        service=service,
        metadata={
            "source": "runtime_container.cli_plan_workflow",
            "workflow": "cli_plan_workflow",
            "purpose": purpose,
        },
    )
    invocation_request = build_runtime_container_llm_invocation_request(
        request_id=f"cli-plan-{request.chat_session_id or 'session'}-{request.turn_index or 0}-{purpose}",
        route_facts=ModelRouteFacts(
            model_name=request.model_name,
            provider="litellm",
            source="runtime_container.cli_plan_workflow",
            metadata={
                "backend_provider": "ollama",
                "route_target": request.model_name,
                "route_kind": "adk_litellm",
                "does_not_call_model": True,
            },
        ),
        governance_precondition=LlmGovernancePrecondition(
            allowed=True,
            reason="cli_plan_workflow_controlled_live_allowed",
            decision="continue",
            governance_decision_ref=request.approval_ref,
            metadata={
                "audit_ref_present": bool(request.audit_ref),
                "sanitized_evidence_ref_present": bool(request.sanitized_evidence_ref),
                "risk_level": request.risk_level,
                "output_budget": request.output_budget,
            },
        ),
        prompt_ref=f"cli-plan-input://{request.chat_session_id or 'session'}/{request.turn_index or 0}",
        prompt_preview_sanitized=prompt_preview,
        metadata={
            "source": "runtime_container.cli_plan_workflow",
            "interaction_mode": "cli_plan_workflow",
            "workflow_stage": purpose,
            "controlled_live": True,
            "live_llm_allowed": True,
            "ollama_allowed": True,
            "risk_level": request.risk_level,
            "output_budget": request.output_budget,
            "reference_context_status": (
                reference_context.status if reference_context else None
            ),
            "reference_context_evidence_ref_count": (
                len(reference_context.evidence_refs) if reference_context else 0
            ),
        },
    )
    return facade.run(invocation_request)


def _build_plan_task_context(
    request: CliPlanWorkflowRequestCandidate,
    facts: CliPlanRequirementFactsCandidate,
) -> CliTaskRunContextCandidate:
    return build_cli_task_run_context(
        workflow_name="cli_plan_workflow",
        task_kind=facts.request_kind,
        session_id=request.chat_session_id,
        turn_index=request.turn_index,
        live_model_allowed=request.live_model_allowed,
        approval_ref=request.approval_ref,
        audit_ref=request.audit_ref,
        sanitized_evidence_ref=request.sanitized_evidence_ref,
        risk_level=request.risk_level,
        output_budget=request.output_budget,
        live_gate=request.live_gate,
        user_passthrough_parameters=request.user_passthrough_parameters,
        metadata={
            "source": "runtime_container.cli_plan_workflow",
            "plan_entities": list(facts.entities),
            "plan_scales": list(facts.scales),
        },
    )


def _task_context_metadata(
    task_context: CliTaskRunContextCandidate,
) -> dict[str, Any]:
    return {
        "task_control": cli_task_run_context_status_dict(task_context),
    }


def _create_plan_run_workspace(
    request: CliPlanWorkflowRequestCandidate,
    task_context: CliTaskRunContextCandidate,
) -> CliRunWorkspaceStateCandidate | None:
    if not request.run_workspace_enabled and not request.run_workspace_root:
        return None
    workspace_root = request.run_workspace_root or ".cognition-runs"
    policy = build_cli_run_workspace_policy(
        workspace_root=workspace_root,
        retention_policy=request.run_workspace_retention_policy,
        cleanup_policy=request.run_workspace_cleanup_policy,
        max_write_bytes=request.run_workspace_max_write_bytes,
    )
    return create_cli_run_workspace(
        policy=policy,
        workflow_name=task_context.workflow_name,
        run_id=task_context.run_id,
    )


def _finalize_plan_run_workspace(
    run_workspace: CliRunWorkspaceStateCandidate | None,
    *,
    status: str,
    terminal_display_text: str,
    facts: CliPlanRequirementFactsCandidate,
    reference_context: CliPlanReferenceContextCandidate | None,
    model_call_count: int,
    fail_safe: bool,
) -> CliRunWorkspaceStateCandidate | None:
    if run_workspace is None or not run_workspace.workspace_created:
        return run_workspace
    max_write_bytes = int(run_workspace.metadata.get("max_write_bytes") or 65536)
    if reference_context is not None and reference_context.status != "not_requested":
        run_workspace, _ = write_cli_run_workspace_json(
            run_workspace,
            relative_path="evidence/reference_context.json",
            payload=_reference_context_workspace_payload(reference_context),
            kind="evidence",
            max_write_bytes=max_write_bytes,
        )
        for index, excerpt in enumerate(reference_context.reference_excerpts, start=1):
            run_workspace, _ = write_cli_run_workspace_text(
                run_workspace,
                relative_path=f"references/reference-{index:03d}.txt",
                text=excerpt,
                kind="reference",
                max_write_bytes=max_write_bytes,
            )
    run_workspace, _ = write_cli_run_workspace_text(
        run_workspace,
        relative_path="artifacts/terminal_display.txt",
        text=terminal_display_text + "\n",
        kind="artifact",
        max_write_bytes=max_write_bytes,
    )
    run_workspace, _ = write_cli_run_workspace_json(
        run_workspace,
        relative_path="results/workflow_result.json",
        payload={
            "workflow": "cli_plan_workflow",
            "status": status,
            "request_kind": facts.request_kind,
            "entities": list(facts.entities),
            "scales": list(facts.scales),
            "constraints": list(facts.constraints),
            "model_call_count": model_call_count,
            "fail_safe": fail_safe,
            "reference_context_status": (
                reference_context.status if reference_context else None
            ),
            "reference_evidence_refs": (
                list(reference_context.evidence_refs) if reference_context else []
            ),
        },
        kind="result",
        max_write_bytes=max_write_bytes,
    )
    run_workspace = finalize_cli_run_workspace(
        run_workspace,
        status=status,
        metadata={
            "workflow": "cli_plan_workflow",
            "model_call_count": model_call_count,
            "fail_safe": fail_safe,
        },
    )
    run_workspace, _ = cleanup_cli_run_workspace(run_workspace, status=status)
    return run_workspace


def _finalize_task_context_with_run_workspace(
    task_context: CliTaskRunContextCandidate,
    *,
    status: str,
    run_workspace: CliRunWorkspaceStateCandidate | None,
    metadata: Mapping[str, Any] | None = None,
) -> CliTaskRunContextCandidate:
    return finalize_cli_task_run_context(
        task_context,
        status=status,
        artifact_refs=_run_workspace_artifact_and_result_refs(run_workspace),
        evidence_refs=run_workspace.evidence_refs if run_workspace else (),
        workspace_ref=run_workspace.workspace_ref if run_workspace else None,
        workspace_created=run_workspace.workspace_created if run_workspace else None,
        retention_policy=run_workspace.retention_policy if run_workspace else None,
        cleanup_policy=run_workspace.cleanup_policy if run_workspace else None,
        workspace_metadata=cli_run_workspace_status_dict(run_workspace),
        metadata=metadata,
    )


def _run_workspace_metadata(
    run_workspace: CliRunWorkspaceStateCandidate | None,
) -> dict[str, Any]:
    status = cli_run_workspace_status_dict(run_workspace)
    return {"run_workspace": status} if status is not None else {}


def _run_workspace_artifact_and_result_refs(
    run_workspace: CliRunWorkspaceStateCandidate | None,
) -> tuple[str, ...]:
    if run_workspace is None:
        return ()
    return (*run_workspace.artifact_refs, *run_workspace.result_refs)


def _reference_context_workspace_payload(
    reference_context: CliPlanReferenceContextCandidate,
) -> dict[str, Any]:
    return {
        "status": reference_context.status,
        "requested_references": list(reference_context.requested_references),
        "consumed_reference_count": reference_context.consumed_reference_count,
        "evidence_refs": list(reference_context.evidence_refs),
        "blocking_reasons": list(reference_context.blocking_reasons),
        "warnings": list(reference_context.warnings),
        "reference_labels": list(reference_context.metadata.get("reference_labels", ())),
        "tool_loading_gate": dict(
            reference_context.metadata.get("tool_loading_gate", {})
        ),
        "read_statuses": list(reference_context.metadata.get("read_statuses", ())),
    }


def _workspace_blocked_terminal_display(
    task_context: CliTaskRunContextCandidate,
    run_workspace: CliRunWorkspaceStateCandidate,
) -> str:
    reasons = ", ".join(run_workspace.blocking_reasons)
    return "\n".join(
        [
            "CLI run workspace 已阻止本轮执行。",
            f"run_id: {task_context.run_id}",
            f"blocking_reasons: {reasons or 'unknown'}",
            "未调用模型，未执行外部工具。",
        ]
    )


def _build_plan_reference_context(
    request: CliPlanWorkflowRequestCandidate,
    task_context: CliTaskRunContextCandidate,
) -> CliPlanReferenceContextCandidate:
    requested_references = tuple(_ordered_unique(request.reference_paths))
    if not requested_references:
        return CliPlanReferenceContextCandidate(
            status="not_requested",
            metadata={
                "workflow_stage": "reference_context",
                "reference_reader_requested": False,
            },
        )

    repo_root = Path(request.reference_repo_root or Path.cwd()).expanduser().resolve()
    exposure = resolve_cli_tool_exposure_profile(
        profile_name=request.reference_profile_name,
        profile_config=request.reference_profile_config,
        repo_root=repo_root,
        session_args=request.reference_session_args,
        cli_explicit_args=request.reference_cli_explicit_args,
    )
    exposure_status = cli_tool_exposure_profile_status_dict(exposure)
    loading_gate = validate_cli_tool_loading_gate(
        exposure,
        operator_approved=bool(request.approval_ref),
        approval_ref=request.approval_ref,
    )
    loading_gate_status = cli_tool_loading_gate_status_dict(loading_gate)
    blocking: list[str] = list(exposure.blocking_reasons)
    warnings: list[str] = list(exposure.warnings)
    if exposure.status != "resolved":
        blocking.append("reference_tool_exposure_profile_blocked")
    blocking.extend(
        f"tool_loading_gate:{reason}"
        for reason in loading_gate.blocking_reasons
    )
    warnings.extend(loading_gate.warnings)
    if loading_gate.status != "passed":
        blocking.append("tool_loading_validation_blocked")
    if REFERENCE_READER_TOOL_NAME not in exposure.exposed_tool_names:
        blocking.append("reference_reader_not_exposed")
    if REFERENCE_READER_TOOL_NAME not in loading_gate.allowed_tool_names:
        blocking.append("reference_reader_not_allowed_by_risk_gate")
    if exposure.reference_reader_policy is None:
        blocking.append("reference_reader_policy_missing")

    read_results = []
    reference_excerpts: list[str] = []
    evidence_refs: list[str] = []
    reference_labels: list[str] = []
    if not blocking and exposure.reference_reader_policy is not None:
        for reference in requested_references:
            read_result = read_cli_reference(
                CliReferenceReadRequestCandidate(
                    reference=reference,
                    policy=exposure.reference_reader_policy,
                    purpose="cli_plan_reference_context",
                    task_run_id=task_context.run_id,
                )
            )
            read_results.append(read_result)
            reference_labels.append(_reference_label(read_result.resolved_path, reference))
            warnings.extend(read_result.warnings)
            if read_result.evidence_ref:
                evidence_refs.append(read_result.evidence_ref)
            if not read_result.allowed:
                blocking.extend(
                    f"reference_read_blocked:{reason}"
                    for reason in read_result.blocking_reasons
                )
            else:
                reference_excerpts.append(
                    _reference_excerpt(
                        reference_label=reference_labels[-1],
                        excerpt=read_result.content_excerpt,
                    )
                )

    bounded_excerpts = tuple(_bounded_reference_excerpts(reference_excerpts))
    status = "blocked" if blocking else "succeeded"
    return CliPlanReferenceContextCandidate(
        status=status,
        requested_references=requested_references,
        consumed_reference_count=0 if blocking else len(bounded_excerpts),
        reference_excerpts=() if blocking else bounded_excerpts,
        evidence_refs=tuple(_ordered_unique(evidence_refs)),
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "workflow_stage": "reference_context",
            "reference_reader_requested": True,
            "tool_exposure_profile": exposure_status,
            "tool_loading_gate": loading_gate_status,
            "reference_labels": tuple(reference_labels),
            "read_statuses": [
                {
                    "reference": result.reference,
                    "status": result.status,
                    "resolved_path": result.resolved_path,
                    "evidence_ref": result.evidence_ref,
                    "digest": result.reference_digest,
                    "line_count": result.line_count,
                    "char_count": result.char_count,
                    "truncated": result.truncated,
                    "redacted_line_count": result.redacted_line_count,
                    "blocking_reasons": list(result.blocking_reasons),
                    "warnings": list(result.warnings),
                }
                for result in read_results
            ],
            "does_not_execute_external_tools": True,
            "does_not_access_network": True,
        },
    )


def _reference_context_metadata(
    reference_context: CliPlanReferenceContextCandidate | None,
) -> dict[str, Any]:
    if reference_context is None:
        return {}
    return {
        "reference_context": {
            "status": reference_context.status,
            "requested_references": list(reference_context.requested_references),
            "consumed_reference_count": reference_context.consumed_reference_count,
            "evidence_refs": list(reference_context.evidence_refs),
            "blocking_reasons": list(reference_context.blocking_reasons),
            "warnings": list(reference_context.warnings),
            "reference_labels": list(
                reference_context.metadata.get("reference_labels", ())
            ),
        },
    }


def _reference_blocked_terminal_display(
    task_context: CliTaskRunContextCandidate,
    reference_context: CliPlanReferenceContextCandidate,
) -> str:
    reasons = ", ".join(reference_context.blocking_reasons)
    return "\n".join(
        [
            "CLI plan workflow 的 reference reader 已阻止本轮执行。",
            f"run_id: {task_context.run_id}",
            f"blocking_reasons: {reasons or 'unknown'}",
            "未调用模型，未执行外部工具。",
        ]
    )


def _reference_block(
    reference_context: CliPlanReferenceContextCandidate | None,
) -> str | None:
    if (
        reference_context is None
        or reference_context.status != "succeeded"
        or reference_context.consumed_reference_count <= 0
    ):
        return None
    labels = tuple(reference_context.metadata.get("reference_labels", ()))
    lines = ["参考资料"]
    for index, label in enumerate(labels, start=0):
        evidence_ref = (
            reference_context.evidence_refs[index]
            if index < len(reference_context.evidence_refs)
            else "evidence_ref未生成"
        )
        lines.append(f"- {label}：{evidence_ref}")
    return "\n".join(lines)


def _reference_excerpt(*, reference_label: str, excerpt: str) -> str:
    return "\n".join(
        item
        for item in (
            f"reference: {reference_label}",
            excerpt.strip(),
        )
        if item
    )


def _bounded_reference_excerpts(excerpts: Sequence[str]) -> list[str]:
    remaining = PLAN_REFERENCE_CONTEXT_TOTAL_CHAR_LIMIT
    bounded: list[str] = []
    for excerpt in excerpts:
        if remaining <= 0:
            break
        normalized = excerpt[:remaining]
        bounded.append(normalized)
        remaining -= len(normalized)
    return bounded


def _reference_label(resolved_path: str | None, requested_reference: str) -> str:
    path = Path(resolved_path) if resolved_path else Path(requested_reference)
    return path.name or requested_reference


def _domain_specific_section_hint(entities: Sequence[str]) -> str:
    return "、".join(_domain_specific_sections(entities))


def _domain_specific_sections(entities: Sequence[str]) -> tuple[str, ...]:
    entity_text = "、".join(entities)
    if "鱼塘" in entity_text:
        return (
            "选址与土方",
            "防渗处理",
            "池底坡度",
            "进排水系统",
            "增氧设备",
            "水质管理",
            "安全围护",
            "施工步骤",
            "预算项",
            "运维巡检",
        )
    if "养鸡场" in entity_text or "鸡场" in entity_text:
        return (
            "鸡舍布局",
            "通风温控",
            "饮水饲喂",
            "防疫消毒",
            "粪污处理",
            "人员配置",
            "设备清单",
            "成本项",
            "建设步骤",
            "日常运营",
        )
    return (
        "目标",
        "场地",
        "设施",
        "流程",
        "设备",
        "成本",
        "风险",
        "实施步骤",
        "运维复盘",
    )


def _display_text_from_llm_result(result: LlmInvocationResult) -> str:
    display = result.metadata.get("sanitized_response_display")
    if isinstance(display, str) and display.strip():
        return _meaningful_model_text(_plain_text_from_possible_json(display))
    preview = result.sanitized_response_preview
    if isinstance(preview, str) and preview.strip():
        return _meaningful_model_text(_plain_text_from_possible_json(preview))
    return ""


def _no_live_terminal_display(facts: CliPlanRequirementFactsCandidate) -> str:
    lines = [
        PLAN_WORKFLOW_NO_LIVE_MESSAGE,
        "",
        "boundary facts:",
        f"- request_kind: {facts.request_kind}",
        f"- entities: {_join_or_default(facts.entities, '未抽取到')}",
        f"- scales: {_join_or_default(facts.scales, '未抽取到')}",
        f"- constraints: {_join_or_default(facts.constraints, '未抽取到')}",
        "",
        "需要启用 controlled-live Ollama 后，workflow 才会进入方案生成阶段。",
    ]
    return "\n".join(lines)


def _failed_terminal_display(facts: CliPlanRequirementFactsCandidate) -> str:
    return "\n".join(
        [
            PLAN_WORKFLOW_FAIL_SAFE_MESSAGE,
            _plan_title(facts),
            "",
            _facts_block(facts),
            "",
            _domain_block(facts),
        ]
    ).strip()


def _preflight_blocked_terminal_display(
    task_context: CliTaskRunContextCandidate,
) -> str:
    reasons = ", ".join(task_context.preflight.blocking_reasons)
    return "\n".join(
        [
            "CLI task preflight 已阻止本轮执行。",
            f"run_id: {task_context.run_id}",
            f"blocking_reasons: {reasons or 'unknown'}",
            "未调用模型，未执行外部工具。",
        ]
    )


def _requirement_source_text(request: CliPlanWorkflowRequestCandidate) -> str:
    parts = [request.user_text]
    if request.previous_plan_text:
        parts.append(request.previous_plan_text)
    return "\n".join(parts)


def _plan_request_kind(request: CliPlanWorkflowRequestCandidate) -> str:
    if not request.previous_plan_text:
        return "new_plan"
    normalized = _compact_text(request.user_text)
    if any(keyword in normalized for keyword in FORMAT_REQUEST_KEYWORDS):
        return "format_existing_plan"
    if any(keyword in normalized for keyword in PLAN_CONTINUATION_KEYWORDS):
        return "expand_existing_plan"
    return "expand_existing_plan"


def _extract_entities(text: str) -> list[str]:
    entities = [keyword for keyword in PLAN_DOMAIN_KEYWORDS if keyword in text]
    if "500只鸡" in text and "养鸡场" not in entities and "鸡场" not in entities:
        entities.append("养鸡场")
    return entities


def _extract_scales(text: str) -> list[str]:
    pattern = re.compile(r"\d+(?:\.\d+)?\s*(?:平方米|平米|只鸡|只|米)")
    return [_compact_text(match.group(0)) for match in pattern.finditer(text)]


def _extract_constraints(text: str) -> list[str]:
    constraints: list[str] = []
    for match in re.finditer(
        r"(?:深度|水深|高度|面积)[^，。；\n]*?(?:不低于|不少于|至少|大于|小于)[^，。；\n]*?\d+(?:\.\d+)?\s*(?:米|平米|平方米)",
        text,
    ):
        constraints.append(_compact_text(match.group(0)))
    return constraints


def _extract_format_requests(text: str) -> list[str]:
    return [keyword for keyword in FORMAT_REQUEST_KEYWORDS if keyword in text]


def _merge_model_and_local_plan_body(
    model_text: str,
    facts: CliPlanRequirementFactsCandidate,
) -> str:
    local_body = _local_plan_body(facts)
    clean_model_text = _normalize_terminal_lines(model_text)
    if not clean_model_text:
        return local_body
    if _looks_like_local_plan_body(clean_model_text, facts):
        return clean_model_text
    return "\n\n".join([local_body, "模型补充", clean_model_text])


def _local_plan_body(facts: CliPlanRequirementFactsCandidate) -> str:
    sections = _domain_specific_sections(facts.entities)
    entity = _join_or_default(facts.entities, "项目")
    scale = _join_or_default(facts.scales, "规模未明确")
    constraint = _join_or_default(facts.constraints, "约束未明确")
    lines = [
        "实施展开",
        f"1. 建设对象：围绕{entity}展开，规模按{scale}控制。",
        f"2. 硬约束：施工和验收时必须保留“{constraint}”。",
    ]
    for index, section in enumerate(sections, start=3):
        lines.append(f"{index}. {section}：{_section_action_text(section, scale, constraint)}")
    return "\n".join(lines)


def _looks_like_local_plan_body(
    text: str,
    facts: CliPlanRequirementFactsCandidate,
) -> bool:
    compact = _compact_text(text)
    return (
        all(entity in compact for entity in facts.entities)
        and all(_compact_text(scale) in compact for scale in facts.scales)
        and any(section in compact for section in _domain_specific_sections(facts.entities))
        and _has_heading_or_numbering(text)
    )


def _section_action_text(section: str, scale: str, constraint: str) -> str:
    actions = {
        "选址与土方": f"先复核场地边界、标高和外运路径，再按{scale}组织开挖。",
        "防渗处理": "优先设置防渗层或防渗膜，接缝、边角和穿管位置要单独验收。",
        "池底坡度": f"池底应留出排污和排水坡向，同时不得破坏{constraint}。",
        "进排水系统": "进水、排水和溢流分开布置，阀门和过滤口要便于日常维护。",
        "增氧设备": "按水体体积和养殖密度预留增氧机位、电源和检修空间。",
        "水质管理": "建立溶氧、pH、氨氮和透明度巡检表，异常时先调水再补料。",
        "安全围护": "设置围栏、警示牌、防滑通道和电气防水措施。",
        "施工步骤": "按测量放线、土方、防渗、管线、设备、注水试运行顺序推进。",
        "预算项": "拆分土方、防渗、管线、设备、电气、人工和预备费。",
        "运维巡检": "日巡设备和水位，周巡水质，月巡防渗、边坡和电气系统。",
        "鸡舍布局": f"按{scale}规划分区，至少区分育雏、采食、饮水、通道和隔离区。",
        "通风温控": "布置可调通风、遮阳和保温措施，避免局部高温或氨气积累。",
        "饮水饲喂": "饮水线和料槽要覆盖全部鸡群，预留清洗和检修通道。",
        "防疫消毒": "入口设置消毒点，鸡舍、器具、人员动线要分级管理。",
        "粪污处理": "规划干湿分离、临时堆放、防渗和外运处理路径。",
        "人员配置": "明确日常巡检、投喂、消毒、设备维护和记录责任。",
        "设备清单": "至少列入饮水、饲喂、通风、温控、照明、消毒和备用电源。",
        "成本项": "拆分鸡舍建设、设备、鸡苗、饲料、防疫、人工和周转资金。",
        "建设步骤": "先完成场地与鸡舍，再进设备，最后空舍消毒、试运行和进鸡。",
        "日常运营": "建立投喂、防疫、死淘、温湿度、产出和成本台账。",
    }
    return actions.get(section, "明确责任、材料、步骤、验收点和日常维护要求。")


def _facts_block(facts: CliPlanRequirementFactsCandidate) -> str:
    return "\n".join(
        [
            "需求事实",
            f"- 对象：{_join_or_default(facts.entities, '未明确')}",
            f"- 规模：{_join_or_default(facts.scales, '未明确')}",
            f"- 约束：{_join_or_default(facts.constraints, '未明确')}",
        ]
    )


def _domain_block(facts: CliPlanRequirementFactsCandidate) -> str:
    sections = _domain_specific_sections(facts.entities)
    return "\n".join(
        [
            "专项章节",
            *[f"{index}. {section}" for index, section in enumerate(sections, start=1)],
        ]
    )


def _plan_title(facts: CliPlanRequirementFactsCandidate) -> str:
    entity = facts.entities[0] if facts.entities else "项目"
    return f"{entity}建设方案"


def _normalize_terminal_lines(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized.count("\n") < 3:
        normalized = _expand_dense_terminal_text(normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    lines: list[str] = []
    for line in normalized.split("\n"):
        lines.extend(_wrap_terminal_line(line.rstrip()))
    return "\n".join(lines).strip()


def _strip_json_fences(text: str) -> str:
    stripped = _plain_text_from_possible_json(text).strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped


def _plain_text_from_possible_json(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        return ""
    try:
        decoded = json.loads(normalized)
    except json.JSONDecodeError:
        return normalized
    if isinstance(decoded, Mapping):
        for key in ("response", "answer", "content", "description", "text"):
            value = decoded.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""
    if isinstance(decoded, list):
        return ""
    return normalized


def _meaningful_model_text(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        return ""
    if normalized.lower() in {
        "description",
        "text",
        "content",
        "response",
        "structured construction plan",
    }:
        return ""
    if any(pattern in normalized for pattern in JSON_LEAK_PATTERNS):
        return ""
    if len(_compact_text(normalized)) < 20:
        return ""
    return normalized


def _history_contains_plan(history: Sequence[Mapping[str, str]]) -> bool:
    for item in history:
        assistant = item.get("assistant")
        if isinstance(assistant, str) and "建设方案" in assistant:
            return True
    return False


def _has_heading_or_numbering(text: str) -> bool:
    return bool(re.search(r"(^|\n)(?:#{1,3}\s*)?\S+方案|(^|\n)\s*(?:\d+[.、]|- )", text))


def _terminal_readable(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 4:
        return False
    return all(len(line) <= 160 for line in lines)


def _expand_dense_terminal_text(text: str) -> str:
    expanded = re.sub(r"([。；;])\s*", "\\1\n", text)
    expanded = re.sub(r"\s+(?=\d+[.、])", "\n", expanded)
    expanded = re.sub(r"\s+(?=[一二三四五六七八九十]+[、.])", "\n", expanded)
    return expanded


def _wrap_terminal_line(line: str, *, limit: int = 120) -> list[str]:
    if len(line) <= limit:
        return [line]
    chunks: list[str] = []
    current = line
    while len(current) > limit:
        split_at = current.rfind("，", 0, limit)
        if split_at < limit // 2:
            split_at = current.rfind("、", 0, limit)
        if split_at < limit // 2:
            split_at = limit
        chunks.append(current[: split_at + 1].rstrip())
        current = current[split_at + 1 :].lstrip()
    if current:
        chunks.append(current)
    return chunks


def _join_or_default(values: Sequence[str], default: str) -> str:
    return "、".join(values) if values else default


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _compact_text(value: str) -> str:
    return "".join(value.strip().split())


def _preview_text(value: str, limit: int) -> str:
    normalized = " ".join(value.strip().split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit]
