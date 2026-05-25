from __future__ import annotations

from typing import Any

from product_application_assembly import (
    EvidenceSummaryAnswerAskInteractionState,
    build_evidence_summary_answer_ask_follow_up_interaction,
    build_evidence_summary_answer_ask_initial_interaction,
)


def test_initial_ask_interaction_collects_channel_neutral_state() -> None:
    state = EvidenceSummaryAnswerAskInteractionState(
        request_id="request://ask",
        source_url="https://example.com",
        evidence_paths=(),
        evidence_bridge={"readonly_refs_status": "ready"},
        follow_up_seed="seed",
        service=object(),
        route_facts_factory=lambda: {"route": "facts"},
        governance_precondition_factory=lambda: {"governance": "precondition"},
    )

    def output_builder(
        args: Any,
        *,
        session_state_collector: Any = None,
    ) -> tuple[int, dict[str, Any]]:
        assert args == {"channel": "chat"}
        assert session_state_collector is not None
        session_state_collector(state)
        return 0, {"status": "success", "answer": "ok"}

    result = build_evidence_summary_answer_ask_initial_interaction(
        args={"channel": "chat"},
        output_builder=output_builder,
    )

    assert result.exit_code == 0
    assert result.output["status"] == "success"
    assert result.next_state == state
    assert result.next_state.route_facts() == {"route": "facts"}
    assert result.next_state.governance_precondition() == {
        "governance": "precondition"
    }


def test_follow_up_ask_interaction_returns_next_state() -> None:
    state = EvidenceSummaryAnswerAskInteractionState(
        request_id="request://ask",
        source_url=None,
        evidence_paths=("outputs/evidence.json",),
        evidence_bridge={"readonly_refs_status": "ready"},
        follow_up_seed="seed-1",
        service=object(),
    )
    next_state = EvidenceSummaryAnswerAskInteractionState(
        request_id="request://ask",
        source_url=None,
        evidence_paths=("outputs/evidence.json",),
        evidence_bridge={"readonly_refs_status": "ready"},
        follow_up_seed="seed-2",
        service=object(),
        follow_up_turn_index=1,
    )

    def output_builder(
        received_state: EvidenceSummaryAnswerAskInteractionState,
        follow_up_question: str,
    ) -> tuple[int, dict[str, Any], EvidenceSummaryAnswerAskInteractionState]:
        assert received_state == state
        assert follow_up_question == "继续说明"
        return 0, {"status": "success", "answer": "ok"}, next_state

    result = build_evidence_summary_answer_ask_follow_up_interaction(
        state=state,
        follow_up_question="继续说明",
        output_builder=output_builder,
    )

    assert result.exit_code == 0
    assert result.output["answer"] == "ok"
    assert result.next_state == next_state
