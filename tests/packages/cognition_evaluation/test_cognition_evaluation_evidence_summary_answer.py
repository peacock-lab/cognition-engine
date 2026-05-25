from __future__ import annotations

import pytest
from pydantic import ValidationError

from cognition_evaluation import (
    EvaluationSubject,
    answer_matches_requested_output_format,
    answer_matches_requested_output_language,
    answer_matches_requested_output_length,
    evaluate_requested_output_constraints,
    evaluation_input_for_answer,
    evaluation_summary_from_result,
    requested_output_chars,
    requested_output_format,
    requested_output_language,
)


def test_requested_output_language_detects_public_user_terms() -> None:
    assert requested_output_language("请用英文输出") == "english"
    assert requested_output_language("100字以内，韩文输出") == "korean"
    assert requested_output_language("日本語で出力") == "japanese"
    assert requested_output_language("请输出中文摘要") == "chinese"
    assert requested_output_language("普通问题") is None


def test_requested_output_format_detects_public_user_terms() -> None:
    assert requested_output_format("请做个三点式摘要") == "three_point_list"
    assert requested_output_format("请整理成3条要点") == "three_point_list"
    assert requested_output_format("请分点说明") == "list"
    assert requested_output_format("请做排版优化") == "structured"
    assert requested_output_format("普通问题") is None


def test_requested_output_constraints_evaluate_language_and_length() -> None:
    passed = evaluate_requested_output_constraints(
        answer="Cognition System provides reviewable answers.",
        question="请用英文输出，100字以内",
    )
    assert passed.status == "passed"
    assert passed.passed is True

    failed = evaluate_requested_output_constraints(
        answer="这是中文输出，不符合要求。",
        question="请用韩文输出，100字以内",
    )
    assert failed.status == "failed"
    assert [finding.criterion for finding in failed.findings] == [
        "requested_output_language"
    ]
    assert failed.findings[0].severity == "blocking"


def test_requested_output_constraints_evaluate_format() -> None:
    passed = evaluate_requested_output_constraints(
        answer="1. 读取资料。\n2. 回答问题。\n3. 保持安全边界。",
        question="请基于以上答案内容做个三点式摘要",
    )
    assert passed.status == "passed"
    assert answer_matches_requested_output_format(
        "1. 读取资料。\n2. 回答问题。\n3. 保持安全边界。",
        question="请做个三点式摘要",
    )

    failed = evaluate_requested_output_constraints(
        answer="这是一段普通摘要，没有按三点式排版。",
        question="请基于以上答案内容做个三点式摘要",
    )
    assert failed.status == "failed"
    assert [finding.criterion for finding in failed.findings] == [
        "requested_output_format"
    ]
    assert failed.findings[0].metadata == {"requested_format": "three_point_list"}


def test_requested_output_length_uses_concise_budget_only() -> None:
    assert requested_output_chars("请生成100字以内摘要") == 100
    assert requested_output_chars("请生成100子以内摘要") == 100
    assert answer_matches_requested_output_length("短摘要", question="100字以内")
    assert not answer_matches_requested_output_length(
        "很长" * 120,
        question="100字以内",
    )
    assert answer_matches_requested_output_length(
        "很长" * 120,
        question="500字摘要",
    )


def test_language_matching_rejects_korean_mixed_with_cjk() -> None:
    assert answer_matches_requested_output_language(
        "이 시스템은 검토 가능한 답변을 제공합니다.",
        requested_language="korean",
    )
    assert not answer_matches_requested_output_language(
        "이 시스템은 검토 가능한 답변을 제공합니다。中文夹杂。",
        requested_language="korean",
    )


def test_evaluation_input_and_summary_are_safe_contracts() -> None:
    evaluation_input = evaluation_input_for_answer(
        evaluation_id="evaluation://unit/requested-output",
        answer_preview="可复查回答",
        question_preview="请输出中文",
    )
    assert evaluation_input.subject.kind == "evidence_summary_answer"
    assert [criterion.name for criterion in evaluation_input.criteria] == [
        "requested_output_language",
        "requested_output_length",
        "requested_output_format",
    ]

    result = evaluate_requested_output_constraints(
        answer="English output",
        question="请输出中文",
    )
    summary = evaluation_summary_from_result(
        result,
        evaluation_ref="evaluation://unit/result",
    )
    assert summary.evaluation_ref == "evaluation://unit/result"
    assert summary.status == "failed"
    assert summary.blocking_finding_count == 1


def test_evaluation_subject_rejects_forbidden_preview_markers() -> None:
    with pytest.raises(ValidationError):
        EvaluationSubject(
            kind="answer",
            answer_preview="raw_provider_response should not be exposed",
        )
