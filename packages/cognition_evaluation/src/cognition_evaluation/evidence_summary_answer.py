"""Evaluation helpers for evidence-summary-answer product behavior."""

from __future__ import annotations

import re
from typing import Literal

from cognition_evaluation.models import (
    EvaluationCriterion,
    EvaluationFinding,
    EvaluationInput,
    EvaluationProfileRef,
    EvaluationResult,
    EvaluationSubject,
)


RequestedOutputLanguage = Literal["chinese", "english", "korean", "japanese"]

_KOREAN_REQUEST_RE = re.compile(r"(?:韩语|韩文|韩国语|한국어|korean)", re.IGNORECASE)
_JAPANESE_REQUEST_RE = re.compile(r"(?:日语|日本语|日本語|japanese)", re.IGNORECASE)
_ENGLISH_REQUEST_RE = re.compile(
    r"(?:英文|英语|翻译成英文|translate\s+(?:it|this|the\s+summary)?.{0,20}english)",
    re.IGNORECASE,
)
_CHINESE_REQUEST_RE = re.compile(r"(?:中文|汉语|chinese)", re.IGNORECASE)
_OUTPUT_CHARS_RE = re.compile(r"(\d{2,5})\s*[字子]")
_CHINESE_SUMMARY_LENGTH_HINT_RE = re.compile(
    r"(\d{3,5})\s*(?:[dD]\s*)?(?:的)?\s*中文?\s*摘要"
)
_CHINESE_CONTENT_LENGTH_HINT_RE = re.compile(
    r"(\d{3,5})\s*(?:[dD]\s*)?(?:的)?\s*(?:中文?)?\s*(?:摘要|内容|扩写|改写)"
)


def requested_output_language(question: str | None) -> RequestedOutputLanguage | None:
    """Return the explicit output language requested by the question."""

    text = question or ""
    if _KOREAN_REQUEST_RE.search(text):
        return "korean"
    if _JAPANESE_REQUEST_RE.search(text):
        return "japanese"
    if _ENGLISH_REQUEST_RE.search(text):
        return "english"
    if _CHINESE_REQUEST_RE.search(text):
        return "chinese"
    return None


def requested_output_chars(question: str | None) -> int | None:
    """Return the requested character budget when present."""

    normalized = "".join((question or "").strip().split())
    if not normalized:
        return None
    matches = _OUTPUT_CHARS_RE.findall(normalized)
    if not matches:
        matches = _CHINESE_SUMMARY_LENGTH_HINT_RE.findall(normalized)
    if not matches:
        matches = _CHINESE_CONTENT_LENGTH_HINT_RE.findall(normalized)
    if not matches:
        return None
    return max(int(item) for item in matches)


def answer_matches_requested_output_language(
    answer: str,
    *,
    question: str | None = None,
    requested_language: str | None = None,
) -> bool:
    """Return whether answer satisfies the explicitly requested language."""

    language = requested_language or requested_output_language(question)
    if language is None:
        return True
    if language == "korean":
        return (
            re.search(r"[\uac00-\ud7af]", answer) is not None
            and re.search(r"[\u4e00-\u9fff]", answer) is None
        )
    if language == "japanese":
        return re.search(r"[\u3040-\u30ff]", answer) is not None
    if language == "english":
        return re.search(r"[A-Za-z]{3,}", answer) is not None
    if language == "chinese":
        return cjk_char_count(answer) >= 2
    return True


def answer_matches_requested_output_length(
    answer: str,
    *,
    question: str | None,
) -> bool:
    """Return whether answer satisfies concise character budget requests."""

    requested_chars = requested_output_chars(question)
    if requested_chars is None:
        return True
    if requested_chars <= 150:
        return len(answer.strip()) <= requested_chars * 2
    return True


def evaluate_requested_output_constraints(
    *,
    answer: str,
    question: str | None,
    evaluation_id: str = "evaluation://evidence-summary-answer/requested-output",
) -> EvaluationResult:
    """Evaluate requested language and concise length constraints."""

    findings: list[EvaluationFinding] = []
    language = requested_output_language(question)
    if not answer_matches_requested_output_language(
        answer,
        requested_language=language,
    ):
        findings.append(
            EvaluationFinding(
                criterion="requested_output_language",
                status="failed",
                severity="blocking",
                message="Answer does not use the explicitly requested output language.",
                metadata={"requested_language": language},
            )
        )
    requested_chars = requested_output_chars(question)
    if not answer_matches_requested_output_length(answer, question=question):
        findings.append(
            EvaluationFinding(
                criterion="requested_output_length",
                status="failed",
                severity="blocking",
                message="Answer exceeds the requested concise output length.",
                metadata={"requested_chars": requested_chars},
            )
        )
    return EvaluationResult(
        evaluation_id=evaluation_id,
        status="failed" if findings else "passed",
        findings=findings,
        profile_ref=EvaluationProfileRef(
            ref="evaluation-profile://evidence-summary-answer/requested-output-v1",
            name="evidence_summary_answer_requested_output",
            version="v1",
        ),
        summary=(
            "Requested output constraints failed."
            if findings
            else "Requested output constraints passed."
        ),
        metadata={
            "requested_language": language,
            "requested_chars": requested_chars,
            "evaluation_scope": "product_level",
        },
    )


def evaluation_input_for_answer(
    *,
    evaluation_id: str,
    answer_preview: str,
    question_preview: str | None = None,
) -> EvaluationInput:
    """Build a minimal product-level evaluation input for an answer."""

    return EvaluationInput(
        evaluation_id=evaluation_id,
        subject=EvaluationSubject(
            kind="evidence_summary_answer",
            answer_preview=answer_preview,
            question_preview=question_preview,
        ),
        criteria=[
            EvaluationCriterion(name="requested_output_language"),
            EvaluationCriterion(name="requested_output_length"),
        ],
    )


def cjk_char_count(value: str) -> int:
    """Count CJK unified ideographs in a string."""

    return sum(1 for char in value if "\u4e00" <= char <= "\u9fff")
