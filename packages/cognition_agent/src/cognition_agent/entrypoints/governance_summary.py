"""Read sanitized governance summary input and print an agent-safe view."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from cognition_agent.governance_summary_view import (
    AgentGovernanceEvidenceSummaryViewCandidate,
    build_agent_governance_evidence_summary_view,
)


DEFAULT_CANDIDATE_ID = "agent-governance-summary-cli-view"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = _load_json(args.input)
        view = _build_view(payload)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"cognition_agent governance summary error: {exc}", file=sys.stderr)
        return 2

    if args.text:
        print(view.summary)
        return 0

    print(_json_output(view, pretty=bool(args.pretty)))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m cognition_agent.entrypoints.governance_summary",
        description="Print a read-only agent governance summary from sanitized JSON.",
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to sanitized governance summary JSON.",
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--json",
        action="store_true",
        help="Print compact JSON. This is the default output mode.",
    )
    output_group.add_argument(
        "--text",
        action="store_true",
        help="Print the sanitized one-line summary.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    return parser


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("Input JSON must be an object.")
    return data


def _build_view(data: dict[str, Any]) -> AgentGovernanceEvidenceSummaryViewCandidate:
    if data.get("candidate_type") == "agent_governance_evidence_summary_view_candidate":
        return AgentGovernanceEvidenceSummaryViewCandidate.model_validate(data)

    return build_agent_governance_evidence_summary_view(
        candidate_id=_candidate_id(data),
        governance_evidence_metadata=data,
    )


def _candidate_id(data: dict[str, Any]) -> str:
    candidate_id = data.get("candidate_id")
    if isinstance(candidate_id, str) and candidate_id:
        return candidate_id

    evidence_id = data.get("evidence_id")
    if isinstance(evidence_id, str) and evidence_id:
        return f"{DEFAULT_CANDIDATE_ID}:{evidence_id}"

    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        metadata_evidence_id = metadata.get("evidence_id")
        if isinstance(metadata_evidence_id, str) and metadata_evidence_id:
            return f"{DEFAULT_CANDIDATE_ID}:{metadata_evidence_id}"

    return DEFAULT_CANDIDATE_ID


def _json_output(
    view: AgentGovernanceEvidenceSummaryViewCandidate,
    *,
    pretty: bool,
) -> str:
    return json.dumps(
        view.model_dump(mode="python"),
        ensure_ascii=False,
        indent=2 if pretty else None,
        sort_keys=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
