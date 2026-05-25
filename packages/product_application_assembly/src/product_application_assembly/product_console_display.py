"""Product console display facts candidate.

This module defines product-level display facts for a future TUI/GUI channel.
It is intentionally runtime-free: no CLI calls, no model routing, no file reads,
and no ProductGateway projection assembly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


PRODUCT_APPLICATION_PRODUCT_CONSOLE_DISPLAY_SOURCE = (
    "product_application_assembly.product_console_display"
)
PRODUCT_APPLICATION_PRODUCT_CONSOLE_DISPLAY_MODEL_POLICY_REF = (
    "policy://product-application-assembly/product-console/display-model-v1"
)
PRODUCT_CONSOLE_DISPLAY_MODEL_CANDIDATE_REF = (
    "product-console-display-model://candidate/v1"
)
ANSWER_SCOPED_TRANSFORMATION_UNAVAILABLE_REASON = (
    "answer_scoped_transformation_uses_previous_answer"
)


@dataclass(frozen=True)
class ProductConsoleActionDisplay:
    action_id: str
    label: str
    status: str
    scope: str
    ref: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProductConsoleAnswerRunDisplay:
    answer_run_ref: str | None = None
    status: str = "not_started"
    answer_trace_ref: str | None = None
    answer_artifact_ref: str | None = None
    observability_summary_ref: str | None = None
    trace_inspect_ref: str | None = None
    unavailable_reason: str = "answer_run_requires_completed_product_flow"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProductConsoleCapabilityDisplay:
    product_id: str
    title: str
    status: str
    entrypoint: str
    description: str
    actions: tuple[ProductConsoleActionDisplay, ...] = ()
    answer_run: ProductConsoleAnswerRunDisplay = field(
        default_factory=ProductConsoleAnswerRunDisplay
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProductConsoleHomeDisplay:
    display_model_ref: str
    display_model_status: str
    source: str
    runtime_backed: bool
    public_schema: bool
    task_api_semantic: str
    workflow_runtime_semantic: str
    products: tuple[ProductConsoleCapabilityDisplay, ...]
    boundary_hints: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProductConsoleAskReviewDisplay:
    answer_run_ref: str | None
    status: str
    explanation: str
    detail_available: bool
    answer_trace_ref: str | None = None
    answer_artifact_ref: str | None = None
    observability_summary_ref: str | None = None
    trace_inspect_ref: str | None = None
    unavailable_reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProductConsoleAskOutputDisplay:
    product_title: str
    command: str
    status: str
    answer: str | None
    review: ProductConsoleAskReviewDisplay
    blocking_reasons: tuple[str, ...] = ()
    failure_explanation: str | None = None
    recovery_hints: tuple[str, ...] = ()
    follow_up_available: bool = False
    follow_up_text: str | None = None
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


def build_product_console_home_display() -> ProductConsoleHomeDisplay:
    return ProductConsoleHomeDisplay(
        display_model_ref=PRODUCT_CONSOLE_DISPLAY_MODEL_CANDIDATE_REF,
        display_model_status="candidate",
        source=PRODUCT_APPLICATION_PRODUCT_CONSOLE_DISPLAY_SOURCE,
        runtime_backed=False,
        public_schema=False,
        task_api_semantic="semantic_placeholder_only",
        workflow_runtime_semantic="semantic_placeholder_only",
        products=(
            ProductConsoleCapabilityDisplay(
                product_id="reviewable-evidence-answer-pack",
                title="可复查资料问答包",
                status="available_as_product_console_ask_entry",
                entrypoint="cognition-console ask --guided",
                description=(
                    "基于受控外部只读资料形成可复查回答；产品控制台 ask 入口"
                    "在明确授权后调用 ask 产品入口服务。"
                ),
                actions=(
                    ProductConsoleActionDisplay(
                        action_id="start_external_readonly_ask",
                        label="启动可复查资料问答",
                        status="available",
                        scope="product_console_ask_entry",
                        ref="cognition-console ask --guided",
                    ),
                    ProductConsoleActionDisplay(
                        action_id="view_answer_run_refs",
                        label="查看回答运行引用",
                        status="candidate_display_only",
                        scope="requires_completed_answer_run",
                    ),
                    ProductConsoleActionDisplay(
                        action_id="inspect_failure_reason",
                        label="查看失败或阻断原因",
                        status="candidate_display_only",
                        scope="requires_completed_answer_run",
                    ),
                ),
            ),
        ),
        boundary_hints=(
            "product_console 不调用 cognition_cli 内部 builder。",
            "product_console 不执行模型路由、产品事实装配或密钥后端策略。",
            "display facts 不是 schemas / behavior_contracts 公共契约。",
            "当前入口不打开 ADK Task API、Workflow Runtime、Session 或 Memory。",
        ),
        metadata={
            "policy_ref": PRODUCT_APPLICATION_PRODUCT_CONSOLE_DISPLAY_MODEL_POLICY_REF,
            "product_strategy": "ADK2.x main-axis semantics first; runtime decision later",
        },
    )


def product_console_home_display_dict(
    display: ProductConsoleHomeDisplay,
) -> dict[str, Any]:
    return {
        "display_model_ref": display.display_model_ref,
        "display_model_status": display.display_model_status,
        "source": display.source,
        "runtime_backed": display.runtime_backed,
        "public_schema": display.public_schema,
        "task_api_semantic": display.task_api_semantic,
        "workflow_runtime_semantic": display.workflow_runtime_semantic,
        "products": tuple(
            {
                "product_id": product.product_id,
                "title": product.title,
                "status": product.status,
                "entrypoint": product.entrypoint,
                "description": product.description,
                "actions": tuple(
                    {
                        "action_id": action.action_id,
                        "label": action.label,
                        "status": action.status,
                        "scope": action.scope,
                        "ref": action.ref,
                        "metadata": dict(action.metadata),
                    }
                    for action in product.actions
                ),
                "answer_run": {
                    "answer_run_ref": product.answer_run.answer_run_ref,
                    "status": product.answer_run.status,
                    "answer_trace_ref": product.answer_run.answer_trace_ref,
                    "answer_artifact_ref": product.answer_run.answer_artifact_ref,
                    "observability_summary_ref": (
                        product.answer_run.observability_summary_ref
                    ),
                    "trace_inspect_ref": product.answer_run.trace_inspect_ref,
                    "unavailable_reason": product.answer_run.unavailable_reason,
                    "metadata": dict(product.answer_run.metadata),
                },
                "metadata": dict(product.metadata),
            }
            for product in display.products
        ),
        "boundary_hints": display.boundary_hints,
        "metadata": dict(display.metadata),
    }


def build_product_console_ask_output_display(
    output: Mapping[str, Any],
    *,
    command: str,
) -> ProductConsoleAskOutputDisplay:
    """Project ask product output into product-console display facts."""

    answer_run_ref = _optional_str(output.get("answer_run_ref"))
    answer_scoped = _is_answer_scoped_transformation(output)
    unavailable_reason = _first_optional_str(
        output.get("answer_run_unavailable_reason"),
        output.get("answer_trace_unavailable_reason"),
        output.get("answer_artifact_unavailable_reason"),
        output.get("observability_summary_unavailable_reason"),
        output.get("trace_inspect_unavailable_reason"),
    )
    detail_refs = {
        "answer_trace_ref": _optional_str(output.get("answer_trace_ref")),
        "answer_artifact_ref": _optional_str(output.get("answer_artifact_ref")),
        "observability_summary_ref": _optional_str(
            output.get("observability_summary_ref")
        ),
        "trace_inspect_ref": _optional_str(output.get("trace_inspect_ref")),
    }
    detail_available = any(detail_refs.values())
    if answer_scoped:
        review_status = "answer_scoped_transformation"
        explanation = (
            "本轮只基于上一轮可见答案变换，不重新抓取资料，"
            "也不生成新的资料问答运行引用。"
        )
    elif answer_run_ref:
        review_status = _optional_str(output.get("answer_run_status")) or "available"
        explanation = "本轮已形成问答运行引用，可作为默认复查入口。"
    else:
        review_status = _optional_str(output.get("answer_run_status")) or "unavailable"
        explanation = _review_unavailable_explanation(unavailable_reason)

    return ProductConsoleAskOutputDisplay(
        product_title="可复查资料问答包",
        command=command,
        status=_optional_str(output.get("status")) or "unknown",
        answer=_optional_str(output.get("answer")),
        review=ProductConsoleAskReviewDisplay(
            answer_run_ref=answer_run_ref,
            status=review_status,
            explanation=explanation,
            detail_available=detail_available,
            answer_trace_ref=detail_refs["answer_trace_ref"],
            answer_artifact_ref=detail_refs["answer_artifact_ref"],
            observability_summary_ref=detail_refs["observability_summary_ref"],
            trace_inspect_ref=detail_refs["trace_inspect_ref"],
            unavailable_reason=unavailable_reason,
            metadata={
                "answer_run_status": output.get("answer_run_status"),
                "answer_trace_status": output.get("answer_trace_status"),
                "answer_artifact_status": output.get("answer_artifact_status"),
                "observability_summary_status": output.get(
                    "observability_summary_status"
                ),
                "trace_inspect_status": output.get("trace_inspect_status"),
                "answer_run_unavailable_reason": output.get(
                    "answer_run_unavailable_reason"
                ),
                "answer_trace_unavailable_reason": output.get(
                    "answer_trace_unavailable_reason"
                ),
                "answer_artifact_unavailable_reason": output.get(
                    "answer_artifact_unavailable_reason"
                ),
                "observability_summary_unavailable_reason": output.get(
                    "observability_summary_unavailable_reason"
                ),
                "trace_inspect_unavailable_reason": output.get(
                    "trace_inspect_unavailable_reason"
                ),
            },
        ),
        blocking_reasons=_string_tuple(output.get("blocking_reasons")),
        failure_explanation=_optional_str(output.get("failure_explanation")),
        recovery_hints=_string_tuple(output.get("recovery_hints")),
        follow_up_available=output.get("follow_up_available") is True,
        follow_up_text=(
            "可继续围绕同一证据追问，或对上一轮答案做摘要、翻译、"
            "排版、改写等变换；仅当前进程内有效。"
            if output.get("follow_up_available") is True
            else None
        ),
        warnings=_string_tuple(output.get("warnings")),
        metadata={
            "request_id": output.get("request_id"),
            "readonly_refs_status": output.get("readonly_refs_status"),
            "llm_call_attempted": output.get("llm_call_attempted"),
            "llm_runtime_call_performed": output.get("llm_runtime_call_performed"),
            "answer_scoped_transformation": answer_scoped,
        },
    )


def product_console_ask_output_display_dict(
    display: ProductConsoleAskOutputDisplay,
) -> dict[str, Any]:
    return {
        "product": display.product_title,
        "command": display.command,
        "status": display.status,
        "answer": display.answer,
        "review": {
            "answer_run_ref": display.review.answer_run_ref,
            "status": display.review.status,
            "explanation": display.review.explanation,
            "detail_available": display.review.detail_available,
            "answer_trace_ref": display.review.answer_trace_ref,
            "answer_artifact_ref": display.review.answer_artifact_ref,
            "observability_summary_ref": display.review.observability_summary_ref,
            "trace_inspect_ref": display.review.trace_inspect_ref,
            "unavailable_reason": display.review.unavailable_reason,
            "metadata": dict(display.review.metadata),
        },
        "blocking_reasons": display.blocking_reasons,
        "failure_explanation": display.failure_explanation,
        "recovery_hints": display.recovery_hints,
        "follow_up_available": display.follow_up_available,
        "follow_up": display.follow_up_text,
        "warnings": display.warnings,
        "metadata": dict(display.metadata),
    }


def _is_answer_scoped_transformation(output: Mapping[str, Any]) -> bool:
    if output.get("answer_scoped_transformation") is True:
        return True
    return any(
        output.get(key) == ANSWER_SCOPED_TRANSFORMATION_UNAVAILABLE_REASON
        for key in (
            "answer_run_unavailable_reason",
            "answer_trace_unavailable_reason",
            "answer_artifact_unavailable_reason",
            "observability_summary_unavailable_reason",
            "trace_inspect_unavailable_reason",
        )
    )


def _review_unavailable_explanation(reason: str | None) -> str:
    if reason == ANSWER_SCOPED_TRANSFORMATION_UNAVAILABLE_REASON:
        return (
            "本轮只基于上一轮可见答案变换，不重新抓取资料，"
            "也不生成新的资料问答运行引用。"
        )
    if reason and "requires_answer_context" in reason:
        return "本轮尚未形成可回答上下文，因此没有生成问答运行引用。"
    if reason:
        return f"本轮暂未形成问答运行引用，原因：{reason}。"
    return "本轮暂未形成问答运行引用。"


def _first_optional_str(*values: Any) -> str | None:
    for value in values:
        optional = _optional_str(value)
        if optional is not None:
            return optional
    return None


def _optional_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(item) for item in value)


__all__ = (
    "PRODUCT_APPLICATION_PRODUCT_CONSOLE_DISPLAY_MODEL_POLICY_REF",
    "PRODUCT_APPLICATION_PRODUCT_CONSOLE_DISPLAY_SOURCE",
    "PRODUCT_CONSOLE_DISPLAY_MODEL_CANDIDATE_REF",
    "ProductConsoleActionDisplay",
    "ProductConsoleAskOutputDisplay",
    "ProductConsoleAskReviewDisplay",
    "ProductConsoleAnswerRunDisplay",
    "ProductConsoleCapabilityDisplay",
    "ProductConsoleHomeDisplay",
    "build_product_console_ask_output_display",
    "build_product_console_home_display",
    "product_console_ask_output_display_dict",
    "product_console_home_display_dict",
)
