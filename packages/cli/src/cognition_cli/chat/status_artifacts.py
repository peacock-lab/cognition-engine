"""Chat status artifact persistence for the Cognition System CLI."""

from __future__ import annotations

import argparse
from typing import Any

from cognition_cli.chat.status_payload import (
    _chat_status_payload,
)
from product_gateway.cli_surface import (
    persist_cli_twf_status_summary,
)


def _persist_chat_status_summary(
    args: argparse.Namespace,
    chat_session_id: str,
    turn_count: int,
    *,
    latest_plan_snapshot: Any | None,
) -> tuple[Any | None, str | None]:
    payload = _chat_status_payload(
        args,
        chat_session_id,
        turn_count,
        latest_plan_snapshot=latest_plan_snapshot,
    )
    persistence = persist_cli_twf_status_summary(
        latest_plan_snapshot=latest_plan_snapshot,
        status_summary_payload=payload,
    )
    if persistence.status != "succeeded":
        return latest_plan_snapshot, None
    return persistence.latest_plan_snapshot, persistence.status_summary_artifact_ref
