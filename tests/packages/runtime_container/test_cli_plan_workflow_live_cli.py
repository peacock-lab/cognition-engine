from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OLLAMA_API_BASE = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT_SECONDS = "180"


@pytest.mark.parametrize(
    ("case_id", "stdin_text", "required_terms", "domain_terms"),
    [
        (
            "fishpond",
            (
                "我想建一个鱼塘，500平米大，深度不低于3米，帮我设计个建设方案\n"
                "你能认真注意下方案的排版吗\n"
                "换行注意一下\n"
                "整个方案的排版，注意换行\n"
                "/exit\n"
            ),
            ("鱼塘", "500平米", "深度不低于3米"),
            ("防渗", "进排水", "增氧", "水质"),
        ),
        (
            "chicken",
            (
                "我要开个养鸡场，帮我设计个方案，规模500只鸡\n"
                "请直接输出方案\n"
                "你先给我重新做个排版吧，当前的有点乱\n"
                "所有的\n"
                "/exit\n"
            ),
            ("养鸡场", "500只鸡"),
            ("鸡舍", "通风", "防疫", "粪污", "饲喂"),
        ),
    ],
)
def test_cli_plan_workflow_real_ollama_cli_scenarios(
    case_id: str,
    stdin_text: str,
    required_terms: tuple[str, ...],
    domain_terms: tuple[str, ...],
) -> None:
    if os.getenv("CE_ENABLE_CLI_PLAN_LIVE_SMOKE") != "1":
        pytest.skip(
            "Set CE_ENABLE_CLI_PLAN_LIVE_SMOKE=1 to run real CLI Ollama plan workflow scenarios."
        )

    output = _run_real_cli_plan_smoke(case_id=case_id, stdin_text=stdin_text)

    for term in required_terms:
        assert term in output
    assert any(term in output for term in domain_terms)
    assert "\n1." in output or "\n1、" in output
    assert "session: closed" in output
    assert "assistant:" not in output
    assert "受控失败边界" not in output
    assert "raw_provider_response" not in output
    assert "system_context" not in output
    assert "response_strategy" not in output
    assert "protocol_support" not in output
    assert "```json" not in output
    assert "{" not in output


def _run_real_cli_plan_smoke(*, case_id: str, stdin_text: str) -> str:
    ollama_api_base = os.getenv("CE_OLLAMA_API_BASE", DEFAULT_OLLAMA_API_BASE)
    timeout_seconds = os.getenv(
        "CE_CLI_PLAN_LIVE_TIMEOUT_SECONDS",
        DEFAULT_TIMEOUT_SECONDS,
    )
    args = [
        "uv",
        "run",
        "cognition",
        "chat",
        "--chat-session-id",
        f"cli-plan-live-{case_id}-pytest",
        "--operator-approved",
        "--approval-ref",
        f"approval://cli-plan-live-{case_id}-pytest",
        "--audit-ref",
        f"audit://cli-plan-live-{case_id}-pytest",
        "--sanitized-evidence-ref",
        f"evidence://cli-plan-live-{case_id}-pytest",
        "--governance-summary-output-ref",
        f"artifact://cli-plan-live-{case_id}-pytest",
        "--request-live-llm",
        "--request-ollama",
        "--allow-live-llm",
        "--allow-ollama",
        "--live-llm-approval-ref",
        f"approval://cli-plan-live-llm-{case_id}-pytest",
        "--ollama-api-base",
        ollama_api_base,
        "--live-llm-timeout-seconds",
        timeout_seconds,
        "--no-banner",
    ]
    completed = subprocess.run(
        args,
        cwd=REPO_ROOT,
        input=stdin_text,
        text=True,
        capture_output=True,
        timeout=int(timeout_seconds) + 60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    return completed.stdout
