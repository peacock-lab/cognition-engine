from __future__ import annotations

import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
ENABLE_REAL_PROVIDER_SMOKE_ENV = "CE_ENABLE_TWF_CONTROLLED_LIVE_REAL_PROVIDER_SMOKE"
DEFAULT_OLLAMA_API_BASE = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT_SECONDS = "180"
TIMEOUT_SECONDS_ENV = "CE_TWF_CONTROLLED_LIVE_REAL_PROVIDER_TIMEOUT_SECONDS"


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
def test_cli_twf_plan_workflow_real_provider_smoke(
    case_id: str,
    stdin_text: str,
    required_terms: tuple[str, ...],
    domain_terms: tuple[str, ...],
) -> None:
    _skip_unless_real_provider_smoke_enabled()

    output = _run_real_twf_plan_smoke(case_id=case_id, stdin_text=stdin_text)

    for term in required_terms:
        assert term in output
    assert any(term in output for term in domain_terms)
    assert "\n1." in output or "\n1、" in output
    assert "session: closed" in output
    assert "twf_live_llm_provider_not_injected" not in output
    assert "provider_not_injected" not in output
    assert "assistant:" not in output
    assert "受控失败边界" not in output
    assert "system_context" not in output
    assert "response_strategy" not in output
    assert "protocol_support" not in output
    assert "```json" not in output
    assert "{" not in output
    _assert_controlled_live_output_boundary(output)


def test_cli_twf_reference_review_real_provider_smoke() -> None:
    _skip_unless_real_provider_smoke_enabled()

    output = _run_real_twf_reference_review_smoke()

    assert "资料审查结果" in output
    assert "审查范围" in output
    assert "证据引用" in output
    assert "evidence://reference-reader/" in output
    assert "session: closed" in output
    assert "twf_live_llm_provider_not_injected" not in output
    assert "provider_not_injected" not in output
    assert "真实模型调用失败" not in output
    _assert_controlled_live_output_boundary(output)


@pytest.mark.parametrize(
    "value",
    (
        "https://127.0.0.1:11434",
        "http://192.168.1.10:11434",
        "http://10.0.0.8:11434",
        "http://example.com:11434",
        "http://0.0.0.0:11434",
    ),
)
def test_real_provider_smoke_rejects_non_local_ollama_base(value: str) -> None:
    with pytest.raises(ValueError, match="local Ollama"):
        _local_ollama_api_base(value)


def _run_real_twf_plan_smoke(*, case_id: str, stdin_text: str) -> str:
    ollama_api_base = _local_ollama_api_base(
        os.getenv("CE_OLLAMA_API_BASE", DEFAULT_OLLAMA_API_BASE)
    )
    timeout_seconds = _timeout_seconds()
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


def _run_real_twf_reference_review_smoke() -> str:
    ollama_api_base = _local_ollama_api_base(
        os.getenv("CE_OLLAMA_API_BASE", DEFAULT_OLLAMA_API_BASE)
    )
    timeout_seconds = _timeout_seconds()
    case_id = "reference-review"
    args = [
        "uv",
        "run",
        "cognition",
        "chat",
        "--chat-session-id",
        "cli-reference-review-live-provider-pytest",
        "--operator-approved",
        "--approval-ref",
        f"approval://cli-{case_id}-live-pytest",
        "--audit-ref",
        f"audit://cli-{case_id}-live-pytest",
        "--sanitized-evidence-ref",
        f"evidence://cli-{case_id}-live-pytest",
        "--governance-summary-output-ref",
        f"artifact://cli-{case_id}-live-pytest",
        "--reference-path",
        "docs/architecture/000-v0.7.0-认知系统源码包与配置中心定位索引-v1.zh-CN.md",
        "--request-live-llm",
        "--request-ollama",
        "--allow-live-llm",
        "--allow-ollama",
        "--live-llm-approval-ref",
        f"approval://cli-{case_id}-live-llm-pytest",
        "--ollama-api-base",
        ollama_api_base,
        "--live-llm-timeout-seconds",
        timeout_seconds,
        "--no-banner",
    ]
    completed = subprocess.run(
        args,
        cwd=REPO_ROOT,
        input=(
            "请审查这些资料，指出是否符合当前主线，并给出问题和建议\n"
            "/exit\n"
        ),
        text=True,
        capture_output=True,
        timeout=int(timeout_seconds) + 60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    return completed.stdout


def _skip_unless_real_provider_smoke_enabled() -> None:
    if os.getenv(ENABLE_REAL_PROVIDER_SMOKE_ENV) != "1":
        pytest.skip(
            "Set "
            f"{ENABLE_REAL_PROVIDER_SMOKE_ENV}=1 to run CLI controlled-live "
            "real provider smoke tests."
        )


def _local_ollama_api_base(value: str) -> str:
    parsed = urlparse(value)
    host = parsed.hostname
    if parsed.scheme != "http" or host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError(
            "CLI controlled-live real provider smoke only allows local Ollama "
            "base urls: http://127.0.0.1:*, http://localhost:* or http://[::1]:*."
        )
    return value


def _timeout_seconds() -> str:
    value = os.getenv(TIMEOUT_SECONDS_ENV, DEFAULT_TIMEOUT_SECONDS)
    if not value.isdecimal() or int(value) <= 0:
        raise ValueError(f"{TIMEOUT_SECONDS_ENV} must be a positive integer.")
    return value


def _assert_controlled_live_output_boundary(output: str) -> None:
    assert "raw_provider_response" not in output
    assert "raw_response" not in output
    assert "response_text" not in output
    assert "messages" not in output
    assert "live_model_payload" not in output
