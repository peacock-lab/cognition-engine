from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_SRC = REPO_ROOT / "packages" / "cognition_agent" / "src"
sys.path.insert(0, str(PACKAGE_SRC))

from cognition_agent.entrypoints import governance_summary  # noqa: E402


ENTRYPOINT_SOURCE = (
    PACKAGE_SRC / "cognition_agent" / "entrypoints" / "governance_summary.py"
)


def test_governance_summary_entrypoint_prints_sanitized_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "governance-summary.json"
    input_path.write_text(json.dumps(_governance_summary_payload()), encoding="utf-8")

    exit_code = governance_summary.main(["--input", str(input_path), "--json"])

    captured = capsys.readouterr()
    public_view = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert public_view["candidate_type"] == (
        "agent_governance_evidence_summary_view_candidate"
    )
    assert public_view["readonly"] is True
    assert public_view["candidate_only"] is True
    assert public_view["execution_enabled"] is False
    assert public_view["runtime_container_call_enabled"] is False
    assert public_view["service_invoke_enabled"] is False
    assert public_view["llm_call_enabled"] is False
    assert public_view["action_execution_enabled"] is False
    assert public_view["runtime_action_enabled"] is False
    assert public_view["lifecycle_summary_id"] == "lifecycle-cli-1"
    assert public_view["run_config_service_bundle_summary_id"] == (
        "run-config-service-bundle-cli-1"
    )
    assert public_view["run_config_no_live_mode"] is True
    assert public_view["run_config_call_attempted"] is False
    assert "raw" not in captured.out.lower()
    assert "full_response" not in captured.out


def test_governance_summary_entrypoint_prints_pretty_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "metadata-wrapped-governance-summary.json"
    input_path.write_text(
        json.dumps({"metadata": _governance_summary_payload()}),
        encoding="utf-8",
    )

    exit_code = governance_summary.main(["--input", str(input_path), "--pretty"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.startswith("{\n  ")
    assert json.loads(captured.out)["artifact_count"] == 1


def test_governance_summary_entrypoint_prints_text_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "governance-summary.json"
    input_path.write_text(json.dumps(_governance_summary_payload()), encoding="utf-8")

    exit_code = governance_summary.main(["--input", str(input_path), "--text"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Read-only governance evidence summary" in captured.out
    assert "This view is not execution permission." in captured.out
    assert "raw" not in captured.out.lower()


def test_governance_summary_entrypoint_accepts_existing_agent_summary_view(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "governance-summary.json"
    input_path.write_text(json.dumps(_governance_summary_payload()), encoding="utf-8")
    assert governance_summary.main(["--input", str(input_path), "--json"]) == 0
    public_view = json.loads(capsys.readouterr().out)

    view_path = tmp_path / "agent-governance-summary-view.json"
    view_path.write_text(json.dumps(public_view), encoding="utf-8")
    assert governance_summary.main(["--input", str(view_path), "--json"]) == 0

    assert json.loads(capsys.readouterr().out)["candidate_id"] == (
        "agent-governance-summary-cli-view:evidence-cli-1"
    )


def test_governance_summary_entrypoint_rejects_unsafe_payload(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "unsafe-governance-summary.json"
    unsafe_payload = _governance_summary_payload()
    unsafe_payload["lifecycle_summary"]["metadata"] = {"prompt": "unsafe"}
    input_path.write_text(json.dumps(unsafe_payload), encoding="utf-8")

    exit_code = governance_summary.main(["--input", str(input_path), "--json"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "forbidden" in captured.err


def test_governance_summary_entrypoint_rejects_live_like_options(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "governance-summary.json"
    input_path.write_text(json.dumps(_governance_summary_payload()), encoding="utf-8")

    with pytest.raises(SystemExit):
        governance_summary.main(["--input", str(input_path), "--live"])


def test_governance_summary_entrypoint_has_no_execution_dependencies() -> None:
    source = ENTRYPOINT_SOURCE.read_text(encoding="utf-8")
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:runtime_container|runtime|adk_adapter|litellm|google\.adk|"
        r"composition|cognition_governance|observability_hub|subprocess)\b",
        re.MULTILINE,
    )
    forbidden_calls = re.compile(
        r"\b(?:completion|acompletion|service\.invoke|run_async|runner\.run)\s*\("
    )

    assert forbidden_imports.search(source) is None
    assert forbidden_calls.search(source) is None
    assert "live_enabled=True" not in source
    assert "ActionCandidate" not in source
    assert "RuntimeActionCandidate" not in source
    assert "AgentRuntime" not in source
    assert "ToolExecutor" not in source
    assert "Chat" not in source
    assert "Gateway" not in source


def test_governance_summary_entrypoint_is_not_registered_as_console_script() -> None:
    pyprojects = [REPO_ROOT / "pyproject.toml"]
    pyprojects.extend((REPO_ROOT / "packages").glob("*/pyproject.toml"))
    for pyproject in pyprojects:
        text = pyproject.read_text(encoding="utf-8")
        assert "cognition_agent.entrypoints.governance_summary" not in text


def _governance_summary_payload() -> dict[str, object]:
    return {
        "evidence_id": "evidence-cli-1",
        "lifecycle_summary": {
            "summary_id": "lifecycle-cli-1",
            "runtime_id": "runtime-cli-1",
            "workflow_id": "workflow-cli-1",
            "workflow_name": "workflow-cli",
            "status": "success",
            "session": {
                "session_id": "session-cli-1",
                "service_type_name": "InMemorySessionService",
                "metadata": {"sanitized": True},
            },
            "events": {
                "event_count": 1,
                "event_types": ["node_completed"],
                "metadata": {"sanitized": True},
            },
            "artifacts": [
                {
                    "artifact_id": "artifact-cli-1",
                    "service_type_name": "InMemoryArtifactService",
                    "metadata": {"sanitized": True},
                }
            ],
            "metadata": {"sanitized": True},
        },
        "run_config_service_bundle_summary": {
            "summary_id": "run-config-service-bundle-cli-1",
            "runtime_id": "runtime-cli-1",
            "workflow_id": "workflow-cli-1",
            "workflow_name": "workflow-cli",
            "status": "success",
            "run_config": {
                "mapped_fields": ["max_llm_calls"],
                "unmapped_fields": ["tool_thread_pool_config"],
                "no_live_mode": True,
                "call_attempted": False,
                "metadata": {"sanitized": True},
            },
            "service_bundle": {
                "service_bundle_source": "in_memory",
                "artifact_service_present": True,
                "session_service_present": True,
                "artifact_service_type_name": "InMemoryArtifactService",
                "session_service_type_name": "InMemorySessionService",
                "metadata": {"sanitized": True},
            },
            "metadata": {"sanitized": True},
        },
    }
