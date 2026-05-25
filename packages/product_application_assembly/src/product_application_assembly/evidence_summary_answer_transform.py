"""Product-level answer-scoped transformation helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import re

from cognition_evaluation.evidence_summary_answer import (
    answer_matches_requested_output_format,
    answer_matches_requested_output_language,
    answer_matches_requested_output_length,
    requested_output_format,
)
from schemas.llm_invocation import LlmInvocationRequest


PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRANSFORM_SOURCE = (
    "product_application_assembly.evidence_summary_answer_transform"
)
ANSWER_SCOPED_TRANSFORMATION_UNAVAILABLE_REASON = (
    "answer_scoped_transformation_uses_previous_answer"
)


def evidence_summary_answer_transform_question_matches(question: str) -> bool:
    """Return whether a question targets the previous visible answer."""

    normalized = "".join(question.strip().split()).lower()
    if not normalized:
        return False
    evidence_source_target = _has_evidence_source_target(normalized)
    answer_target = (
        _has_answer_scoped_target(normalized)
        or ("摘要" in normalized and not evidence_source_target)
        or (
            "信息" in normalized
            and any(keyword in normalized for keyword in ("英文", "english", "英语"))
            and not evidence_source_target
        )
    )
    if not answer_target:
        return False
    if evidence_source_target and not _has_answer_object_target(normalized):
        return False
    return _has_answer_scoped_transform_intent(normalized)


def local_evidence_summary_answer_transform_text(
    *,
    previous_answer: str,
    question: str,
) -> str | None:
    """Return deterministic local transform text when no LLM is needed."""

    normalized = "".join(question.strip().split()).lower()
    if not normalized:
        return None
    if requested_output_format(question) == "three_point_list":
        return _three_point_summary_for_display(previous_answer)
    if any(
        keyword in normalized
        for keyword in ("排版", "格式", "格式化", "美化", "整理", "分段")
    ):
        return _format_answer_for_display(previous_answer)
    return None


def build_evidence_summary_answer_transform_llm_request(
    *,
    request_id: str,
    question: str,
    previous_answer: str,
    route_facts: Any,
    governance_precondition: Any,
    answer_ref: str,
    evidence_refs: tuple[str, ...],
    source: str,
    product_path: str,
    answer_ref_kind: str = "external_readonly_ask_answer_snapshot",
    evidence_ref_kind: str = "source_external_readonly_ref",
) -> LlmInvocationRequest:
    """Build an LLM request for answer-scoped transformation."""

    return LlmInvocationRequest(
        request_id=request_id,
        route_facts=route_facts,
        governance_precondition=governance_precondition,
        prompt_ref=f"prompt://evidence-summary-answer-transform/{_safe_ref_part(request_id)}",
        prompt_preview_sanitized=_preview(question, limit=80),
        metadata={
            "source": source,
            "interaction_mode": "evidence_summary_answer_generation",
            "product_path": product_path,
            "answer_scoped_transformation": True,
            "temporary_only": True,
            "durable_session": False,
            "memory_enabled": False,
            "evidence_summary_answer_context": {
                "user_question": _normalized_optional_text(question) or question,
                "summary_facts": [previous_answer],
                "evidence_refs": [
                    {
                        "kind": answer_ref_kind,
                        "ref": answer_ref,
                        "purpose": "answer_scoped_transformation",
                    }
                ],
                "additional_refs": [
                    {
                        "kind": evidence_ref_kind,
                        "ref": ref,
                        "purpose": "source_answer_context",
                    }
                    for ref in evidence_refs
                ],
            },
        },
    )


def evidence_summary_answer_transform_text_from_llm_result(result: Any) -> str | None:
    """Extract sanitized answer text from a governed LLM result."""

    metadata = _mapping(getattr(result, "metadata", None))
    display = metadata.get("sanitized_response_display")
    if isinstance(display, str) and display.strip():
        return _normalized_optional_text(display)
    preview = getattr(result, "sanitized_response_preview", None)
    if isinstance(preview, str) and preview.strip():
        return _normalized_optional_text(preview)
    return None


def evidence_summary_answer_transform_quality_passed(
    answer: str,
    *,
    question: str | None = None,
    require_length_match: bool = True,
) -> bool:
    """Return whether answer-scoped transformation output is display safe."""

    normalized = answer.strip()
    if not normalized:
        return False
    if normalized.startswith(("{", "[", "```")):
        return False
    lowered = normalized.lower()
    forbidden = (
        "thought",
        "analysis",
        "reasoning",
        "scratchpad",
        "chain_of_thought",
        "system prompt",
        "raw_provider_response",
    )
    if any(marker in lowered for marker in forbidden):
        return False
    length_ok = True
    if require_length_match:
        length_ok = answer_matches_requested_output_length(
            normalized,
            question=question,
        )
    return (
        answer_matches_requested_output_language(normalized, question=question)
        and answer_matches_requested_output_format(normalized, question=question)
        and length_ok
    )


def build_evidence_summary_answer_transform_output(
    *,
    request_id: str,
    command: str,
    interaction_mode: str,
    product_path: str,
    question: str,
    previous_output: Mapping[str, Any],
    llm_request: LlmInvocationRequest | None,
    llm_result: Any | None,
    status: str,
    answer: str | None,
    blocking_reasons: tuple[str, ...],
    seed: Any = None,
    follow_up_seed_status_dict: Any | None = None,
    warning_code: str = "external_readonly_ask_answer_scoped_transformation",
    failure_type: str = "external_readonly_ask_answer_scoped_transformation_failed",
) -> dict[str, Any]:
    """Build a product-level answer-scoped transformation output."""

    evidence_refs = _list_value(previous_output.get("evidence_refs"))
    additional_refs = _list_value(previous_output.get("additional_refs"))
    follow_up_seed_payload = (
        follow_up_seed_status_dict(seed)
        if follow_up_seed_status_dict is not None
        else {"follow_up_allowed": bool(answer)}
    )
    llm_call_attempted = bool(llm_result and llm_result.call_attempted)
    llm_runtime_call_performed = bool(
        llm_result and llm_result.runtime_call_performed
    )
    warnings = list(previous_output.get("warnings") or [])
    if status == "success":
        warnings.append(warning_code)
    explanation = (
        "本轮只是基于上一轮可见答案做变换，不重新抓取资料或生成新的证据问答运行摘要。"
    )
    return {
        "product": "Cognition System / 认知系统",
        "command": command,
        "interaction_mode": interaction_mode,
        "product_path": product_path,
        "status": status,
        "success": status == "success",
        "failure_type": None if status == "success" else failure_type,
        "request_id": request_id,
        "llm_request_id": llm_request.request_id if llm_request is not None else None,
        "model_name": (
            llm_request.route_facts.model_name if llm_request is not None else None
        ),
        "source_url_present": previous_output.get("source_url_present") is True,
        "evidence_path_count": previous_output.get("evidence_path_count") or 0,
        "evidence_ref_count": len(evidence_refs),
        "additional_ref_count": len(additional_refs),
        "evidence_refs": evidence_refs,
        "additional_refs": additional_refs,
        "readonly_refs_status": previous_output.get("readonly_refs_status") or "ready",
        "answer_trace_ref": None,
        "answer_trace_status": None,
        "answer_trace_summary": {},
        "answer_trace_unavailable_reason": (
            ANSWER_SCOPED_TRANSFORMATION_UNAVAILABLE_REASON
        ),
        "answer_artifact_ref": None,
        "answer_artifact_status": None,
        "answer_artifact_summary": {},
        "answer_artifact_unavailable_reason": (
            ANSWER_SCOPED_TRANSFORMATION_UNAVAILABLE_REASON
        ),
        "observability_summary_ref": None,
        "observability_summary_status": None,
        "safe_observability_summary": {},
        "observability_summary_unavailable_reason": (
            ANSWER_SCOPED_TRANSFORMATION_UNAVAILABLE_REASON
        ),
        "observability_explanation": explanation,
        "trace_inspect_ref": None,
        "trace_inspect_status": "unavailable",
        "trace_inspect_summary": {},
        "trace_inspect_unavailable_reason": (
            ANSWER_SCOPED_TRANSFORMATION_UNAVAILABLE_REASON
        ),
        "answer_run_ref": None,
        "answer_run_status": "unavailable",
        "answer_run_summary": {},
        "answer_run_unavailable_reason": (
            ANSWER_SCOPED_TRANSFORMATION_UNAVAILABLE_REASON
        ),
        "question_preview": _preview(question, limit=120),
        "answer": answer,
        "answer_preview": _preview(answer, limit=120) if answer else None,
        "answer_length": len(answer) if answer else None,
        "answer_scoped_transformation": True,
        "answer_scope": (
            "answer_scoped; temporary_only; durable_session=false; "
            "memory_enabled=false"
        ),
        "llm_call_allowed": bool(llm_result and llm_result.call_allowed),
        "llm_call_attempted": llm_call_attempted,
        "llm_runtime_call_performed": llm_runtime_call_performed,
        "external_readonly_fetch_performed": False,
        "external_readonly_network_call_performed": False,
        "external_network_call_performed": False,
        "raw_response_included": False,
        "raw_html_included": False,
        "response_headers_included": False,
        "uploads_content": False,
        "writes_files": False,
        "failure_explanation": (
            None if status == "success" else "本轮答案范围变换未形成可展示答案。"
        ),
        "recovery_hints": (
            []
            if status == "success"
            else ["请重新完成一次 external-readonly 问答，或缩短变换请求后重试。"]
        ),
        "blocking_reasons": blocking_reasons,
        "citation_failures": (),
        "warnings": warnings,
        "exit_code": 0 if status == "success" else 1,
        "follow_up": False,
        "follow_up_turn_index": None,
        "follow_up_available": follow_up_seed_payload.get("follow_up_allowed") is True,
        "follow_up_seed": follow_up_seed_payload,
        "temporary_follow_up": True,
        "durable_session": False,
        "memory_enabled": False,
        "product_response_summary": {
            "request_id": request_id,
            "status": status,
            "answer_scoped_transformation": True,
            "observability_summary_ref": None,
            "observability_summary_status": None,
            "observability_summary_unavailable_reason": (
                ANSWER_SCOPED_TRANSFORMATION_UNAVAILABLE_REASON
            ),
            "observability_explanation": explanation,
            "trace_inspect_ref": None,
            "trace_inspect_status": "unavailable",
            "trace_inspect_unavailable_reason": (
                ANSWER_SCOPED_TRANSFORMATION_UNAVAILABLE_REASON
            ),
            "answer_run_ref": None,
            "answer_run_status": "unavailable",
            "answer_run_unavailable_reason": (
                ANSWER_SCOPED_TRANSFORMATION_UNAVAILABLE_REASON
            ),
            "readonly_refs_status": previous_output.get("readonly_refs_status")
            or "ready",
            "llm_call_attempted": llm_call_attempted,
            "llm_runtime_call_performed": llm_runtime_call_performed,
        },
    }


def _has_answer_scoped_target(normalized: str) -> bool:
    direct_targets = (
        "该摘要",
        "这个摘要",
        "上述摘要",
        "这段摘要",
        "该回答",
        "这个回答",
        "上述回答",
        "该答案",
        "这个答案",
        "这段答案",
        "该表述",
        "这个表述",
        "上述表述",
        "该回复",
        "这个回复",
        "上述回复",
        "回答文本",
        "回复文本",
    )
    if any(keyword in normalized for keyword in direct_targets):
        return True
    relative_prefixes = (
        "以上",
        "上述",
        "上面",
        "前面",
        "前述",
        "刚才",
        "刚刚",
        "上一轮",
        "上轮",
        "上一个",
        "上一条",
    )
    answer_objects = (
        "信息",
        "表述",
        "内容",
        "回答",
        "答案",
        "摘要",
        "回复",
        "文本",
    )
    if any(
        f"{prefix}{connector}{target}" in normalized
        for prefix in relative_prefixes
        for connector in ("", "的")
        for target in answer_objects
    ):
        return True
    speaker_prefixes = (
        "你给我的",
        "你刚才给我的",
        "你刚刚给我的",
        "你上面给我的",
    )
    return any(
        f"{prefix}{target}" in normalized
        for prefix in speaker_prefixes
        for target in answer_objects
    )


def _has_answer_object_target(normalized: str) -> bool:
    return any(
        keyword in normalized
        for keyword in (
            "回答",
            "答案",
            "回复",
            "表述",
            "该摘要",
            "这个摘要",
            "上述摘要",
        )
    )


def _has_evidence_source_target(normalized: str) -> bool:
    return any(
        keyword in normalized
        for keyword in (
            "这份资料",
            "这个资料",
            "这份证据",
            "这个证据",
            "这个网页",
            "首页内容",
            "网页内容",
            "原始资料",
            "原始证据",
        )
    )


def _has_answer_scoped_transform_intent(normalized: str) -> bool:
    if "摘要" in normalized and _has_answer_scoped_target(normalized):
        return True
    return any(
        keyword in normalized
        for keyword in (
            "翻译",
            "译成",
            "输出",
            "英文",
            "english",
            "英语",
            "韩语",
            "韩国语",
            "korean",
            "日语",
            "日本语",
            "japanese",
            "中文",
            "压缩",
            "浓缩",
            "改写",
            "改成",
            "总结",
            "三点",
            "三条",
            "分点",
            "分条",
            "一句话",
            "要点",
            "要点式",
            "列表",
            "表格",
            "标题",
            "排版",
            "格式",
            "格式化",
            "美化",
            "优化",
            "整理",
            "分段",
            "适合",
            "五言",
            "七言",
            "诗",
            "文案",
            "口语",
            "正式",
        )
    )


def _format_answer_for_display(answer: str) -> str:
    text = re.sub(r"\s+", " ", answer.strip())
    if not text:
        return "## 排版优化\n\n暂无可排版的上一轮答案。"
    split_parts = re.split(r"\s*\*\*([^*]+)\*\*\s*", text)
    if len(split_parts) > 1:
        lines = ["## 排版优化"]
        lead = split_parts[0].strip()
        if lead:
            lines.extend(["", _format_inline_numbered_body(lead)])
        for index in range(1, len(split_parts), 2):
            title = split_parts[index].strip().strip("：:")
            body = (
                split_parts[index + 1].strip()
                if index + 1 < len(split_parts)
                else ""
            )
            if title:
                lines.extend(["", f"### {title}"])
            if body:
                lines.extend(["", _format_inline_numbered_body(body)])
        return "\n".join(lines).strip()
    numbered_body = _format_inline_numbered_body(text)
    if numbered_body != text:
        return f"## 排版优化\n\n### 要点\n\n{numbered_body}"
    sentences = [
        item.strip()
        for item in re.split(r"(?<=[。！？!?])\s*", text)
        if item.strip()
    ]
    if len(sentences) <= 1:
        return f"## 排版优化\n\n{text}"
    lines = ["## 排版优化", "", "### 要点", ""]
    lines.extend(f"- {sentence}" for sentence in sentences)
    return "\n".join(lines).strip()


def _format_inline_numbered_body(text: str) -> str:
    matches = list(re.finditer(r"(?:^|\s)(\d{1,2})[.．、]\s*", text))
    if len(matches) < 2:
        return text
    items: list[str] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip(" ；;。")
        if body:
            items.append(f"{match.group(1)}. {body}")
    if len(items) < 2:
        return text
    return "\n".join(items)


def _three_point_summary_for_display(answer: str) -> str:
    text = re.sub(r"\s+", " ", answer.strip())
    if not text:
        return "1. 暂无可摘要的上一轮答案。\n2. 请先完成一次问答。\n3. 再请求三点式摘要。"
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    parts = [
        item.strip(" ；;。")
        for item in re.split(r"(?<=[。！？!?；;])\s*|\s+[;；]\s*", text)
        if item.strip(" ；;。")
    ]
    if len(parts) < 3:
        parts = [
            item.strip(" ：:，,；;。")
            for item in re.split(r"[：:，,；;。]\s*", text)
            if item.strip(" ：:，,；;。")
        ]
    filtered_parts = [part for part in parts if _three_point_summary_part_ok(part)]
    if len(filtered_parts) >= 3:
        parts = filtered_parts
    while len(parts) < 3:
        parts.append(parts[-1] if parts else text)
    return "\n".join(f"{index}. {part}" for index, part in enumerate(parts[:3], 1))


def _three_point_summary_part_ok(part: str) -> bool:
    normalized = part.strip()
    if not normalized:
        return False
    if len(normalized) <= 24 and normalized.endswith(("?", "？")):
        return False
    return True


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list | tuple) else []


def _normalized_optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return text or None


def _preview(value: str | None, *, limit: int) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip()


def _safe_ref_part(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-") or "ref"
