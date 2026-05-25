from __future__ import annotations

from product_application_assembly.evidence_summary_answer_transform import (
    local_evidence_summary_answer_transform_text,
)


def test_three_point_summary_skips_short_markdown_heading_questions() -> None:
    previous_answer = (
        "Cognition System 是一个面向受治理 AI 协作的认知能力系统。"
        "**它能做什么？** 系统最核心的能力是基于用户授权读取外部只读资料。"
        "**如何使用？** 用户通过交互式命令行输入资料、问题和授权确认。"
        "**安全边界是什么？** 系统默认不会静默联网或静默调用模型。"
    )

    answer = local_evidence_summary_answer_transform_text(
        previous_answer=previous_answer,
        question="请基于以上答案内容做个三点式摘要",
    )

    assert answer is not None
    assert "1. Cognition System 是一个面向受治理 AI 协作的认知能力系统" in answer
    assert "2. 系统最核心的能力是基于用户授权读取外部只读资料" in answer
    assert "3. 用户通过交互式命令行输入资料、问题和授权确认" in answer
    assert "它能做什么" not in answer
    assert "如何使用" not in answer


def test_format_answer_splits_inline_numbered_list() -> None:
    previous_answer = (
        "1. Cognition System 面向受治理 AI 协作。 "
        "2. 当前版本为 v0.8.1。 "
        "3. 核心能力是读取外部只读资料并回答问题。"
    )

    answer = local_evidence_summary_answer_transform_text(
        previous_answer=previous_answer,
        question="请基于以上答案内容做个排版优化",
    )

    assert answer is not None
    assert answer.startswith("## 排版优化\n\n### 要点")
    assert "1. Cognition System 面向受治理 AI 协作" in answer
    assert "2. 当前版本为 v0.8.1" in answer
    assert "3. 核心能力是读取外部只读资料并回答问题" in answer
    assert " 2. " not in answer
