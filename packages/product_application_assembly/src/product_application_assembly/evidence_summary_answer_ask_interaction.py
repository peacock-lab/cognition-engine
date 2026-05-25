"""Channel-neutral interaction facade for evidence-summary-answer ask."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class EvidenceSummaryAnswerAskInteractionState:
    """Temporary same-process ask state shared by channel adapters.

    This state is not a durable Session or Memory. It lets CLI, chat, and later
    TUI/GUI adapters continue the same governed evidence answer flow without
    carrying a CLI argparse namespace as product state.
    """

    request_id: str
    source_url: str | None
    evidence_paths: tuple[str, ...]
    evidence_bridge: Mapping[str, Any]
    follow_up_seed: Any | None
    service: Any | None
    route_facts_factory: Callable[[], Any] | None = None
    governance_precondition_factory: Callable[[], Any] | None = None
    follow_up_turn_index: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def route_facts(self) -> Any:
        """Return current route facts for an in-process follow-up."""

        if self.route_facts_factory is None:
            raise ValueError("evidence_summary_answer_route_facts_unavailable")
        return self.route_facts_factory()

    def governance_precondition(self) -> Any:
        """Return current governance precondition for an in-process follow-up."""

        if self.governance_precondition_factory is None:
            raise ValueError(
                "evidence_summary_answer_governance_precondition_unavailable"
            )
        return self.governance_precondition_factory()


@dataclass(frozen=True)
class EvidenceSummaryAnswerAskInteractionResult:
    """Result of a channel-neutral ask interaction step."""

    exit_code: int
    output: dict[str, Any]
    next_state: EvidenceSummaryAnswerAskInteractionState | None = None


class EvidenceSummaryAnswerAskInitialOutputBuilder(Protocol):
    """Initial ask output builder supplied by the runtime/channel adapter."""

    def __call__(
        self,
        args: Any,
        *,
        session_state_collector: (
            Callable[[EvidenceSummaryAnswerAskInteractionState], None] | None
        ) = None,
    ) -> tuple[int, dict[str, Any]]:
        """Build an initial ask output and optionally collect interaction state."""


class EvidenceSummaryAnswerAskFollowUpOutputBuilder(Protocol):
    """Follow-up output builder supplied by the runtime/channel adapter."""

    def __call__(
        self,
        state: EvidenceSummaryAnswerAskInteractionState,
        follow_up_question: str,
    ) -> tuple[int, dict[str, Any], EvidenceSummaryAnswerAskInteractionState]:
        """Build a follow-up output and return the next interaction state."""


def build_evidence_summary_answer_ask_initial_interaction(
    *,
    args: Any,
    output_builder: EvidenceSummaryAnswerAskInitialOutputBuilder,
) -> EvidenceSummaryAnswerAskInteractionResult:
    """Run an initial ask interaction through a channel-neutral facade."""

    collected: list[EvidenceSummaryAnswerAskInteractionState] = []
    exit_code, output = output_builder(
        args,
        session_state_collector=collected.append,
    )
    return EvidenceSummaryAnswerAskInteractionResult(
        exit_code=exit_code,
        output=output,
        next_state=collected[-1] if collected else None,
    )


def build_evidence_summary_answer_ask_follow_up_interaction(
    *,
    state: EvidenceSummaryAnswerAskInteractionState,
    follow_up_question: str,
    output_builder: EvidenceSummaryAnswerAskFollowUpOutputBuilder,
) -> EvidenceSummaryAnswerAskInteractionResult:
    """Run one same-process follow-up through a channel-neutral facade."""

    exit_code, output, next_state = output_builder(state, follow_up_question)
    return EvidenceSummaryAnswerAskInteractionResult(
        exit_code=exit_code,
        output=output,
        next_state=next_state,
    )


__all__ = (
    "EvidenceSummaryAnswerAskFollowUpOutputBuilder",
    "EvidenceSummaryAnswerAskInitialOutputBuilder",
    "EvidenceSummaryAnswerAskInteractionResult",
    "EvidenceSummaryAnswerAskInteractionState",
    "build_evidence_summary_answer_ask_follow_up_interaction",
    "build_evidence_summary_answer_ask_initial_interaction",
)
