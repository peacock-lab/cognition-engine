from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

from runtime_container.dev_entry.no_live_llm_invocation import (
    build_no_live_verification_payload,
    main,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_CONTAINER_ROOT = REPO_ROOT / "packages" / "runtime_container"
CLI_PACKAGE_ROOT = REPO_ROOT / "packages" / "cli"
DEV_ENTRY_ROOT = (
    RUNTIME_CONTAINER_ROOT / "src" / "runtime_container" / "dev_entry"
)


def test_no_live_dev_entry_returns_sanitized_payload() -> None:
    payload = build_no_live_verification_payload(
        request_id="dev-entry-test-request",
        model_name="ollama/gemma4-pro:latest",
    )

    assert payload["request_id"] == "dev-entry-test-request"
    assert payload["entry"]["facade_only"] is True
    assert payload["entry"]["dev_only"] is True
    assert payload["entry"]["product_cli"] is False
    assert payload["success"] is False
    assert payload["call_attempted"] is False
    assert payload["call_allowed"] is True
    assert payload["runtime_call_performed"] is False
    assert payload["failure_type"] == "live_disabled"
    assert payload["sanitized_response_preview"] is None
    assert payload["sanitized_response_length"] is None
    assert payload["route"] == {
        "model_name": "ollama/gemma4-pro:latest",
        "provider": "litellm",
        "backend_provider": "ollama",
        "route_kind": "adk_litellm",
        "route_target": "ollama/gemma4-pro:latest",
    }
    assert payload["governance"] == {
        "allowed": True,
        "decision": "continue",
        "reason": "no_live_verification_entry_allowed",
    }


def test_no_live_dev_entry_main_prints_json(capsys) -> None:
    exit_code = main(["--request-id", "dev-entry-main-test", "--pretty"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["request_id"] == "dev-entry-main-test"
    assert payload["runtime_call_performed"] is False
    assert payload["failure_type"] == "live_disabled"


def test_no_live_dev_entry_module_can_run_with_python_m() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "runtime_container.dev_entry.no_live_llm_invocation",
            "--request-id",
            "dev-entry-module-test",
            "--pretty",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["request_id"] == "dev-entry-module-test"
    assert payload["call_attempted"] is False
    assert payload["runtime_call_performed"] is False
    assert payload["failure_type"] == "live_disabled"


def test_no_live_dev_entry_is_inside_publishable_runtime_container_package() -> None:
    pyproject = tomllib.loads(
        (RUNTIME_CONTAINER_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    product_runtime_pyproject = tomllib.loads(
        (
            REPO_ROOT
            / "packages"
            / "product_runtime_assembly"
            / "pyproject.toml"
        ).read_text(encoding="utf-8")
    )

    assert pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "src/runtime_container"
    ]
    assert (
        DEV_ENTRY_ROOT / "no_live_llm_invocation.py"
    ).is_file(), "dev entry must live under the publishable package root"
    assert "scripts" not in pyproject["project"]
    assert product_runtime_pyproject["project"]["scripts"] == {
        "cognition": "product_runtime_assembly.entrypoints.cognition:main"
    }


def test_no_live_dev_entry_source_has_no_forbidden_dependencies_or_calls() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:runtime(?:\.|\s|$)|composition|adk_adapter|litellm|google\.adk)\b",
        re.MULTILINE,
    )
    forbidden_tokens = [
        "CE_ENABLE_LIVE_LLM_SMOKE",
        "live_enabled=True",
        "completion(",
        "acompletion(",
        "runner.run",
        "run_async",
        "ToolExecutor",
        "ActionCandidate",
        "RuntimeActionCandidate",
        "LLMClient",
        "ModelExecutor",
        "AgentModelRuntime",
    ]

    for source_path in DEV_ENTRY_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path
        for token in forbidden_tokens:
            assert token not in source, f"{token} found in {source_path}"
