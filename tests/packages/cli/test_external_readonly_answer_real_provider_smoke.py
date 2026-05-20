from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pytest
from behavior_contracts.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_QUALITY_BLOCKING_REASON,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
ENABLE_REAL_PROVIDER_SMOKE_ENV = (
    "CE_ENABLE_EXTERNAL_READONLY_ANSWER_REAL_PROVIDER_SMOKE"
)
DEFAULT_OLLAMA_API_BASE = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT_SECONDS = "180"
TIMEOUT_SECONDS_ENV = "CE_EXTERNAL_READONLY_ANSWER_TIMEOUT_SECONDS"


def test_external_readonly_answer_real_provider_smoke(tmp_path: Path) -> None:
    _skip_unless_real_provider_smoke_enabled()
    evidence_path = "outputs/external-readonly/cli-fetch/answer-smoke.json"
    _write_external_readonly_archive(tmp_path, evidence_path)

    completed = _run_real_external_readonly_answer_smoke(
        cwd=tmp_path,
        evidence_path=evidence_path,
    )
    output = completed.stdout
    payload = json.loads(output)

    assert completed.returncode == payload["exit_code"]
    assert payload["evidence_ref_count"] == 1
    assert payload["additional_ref_count"] >= 1
    assert payload["llm_call_attempted"] is True
    assert payload["llm_runtime_call_performed"] is True
    assert payload["external_readonly_fetch_performed"] is False
    assert payload["raw_html_included"] is False
    assert payload["raw_response_included"] is False
    assert payload["response_headers_included"] is False
    assert "provider_not_injected" not in output
    assert "sanitized reference" not in output
    assert "sanitized_excerpt_preview" not in output
    assert "ProductGatewayResponse" not in output
    _assert_controlled_live_output_boundary(output)
    _assert_success_or_quality_contract_failure(payload, completed.returncode)


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
def test_external_readonly_answer_real_provider_smoke_rejects_non_local_base(
    value: str,
) -> None:
    with pytest.raises(ValueError, match="local Ollama"):
        _local_ollama_api_base(value)


def _run_real_external_readonly_answer_smoke(
    *,
    cwd: Path,
    evidence_path: str,
) -> subprocess.CompletedProcess[str]:
    ollama_api_base = _local_ollama_api_base(
        os.getenv("CE_OLLAMA_API_BASE", DEFAULT_OLLAMA_API_BASE)
    )
    timeout_seconds = _timeout_seconds()
    args = [
        "uv",
        "run",
        "--project",
        str(REPO_ROOT),
        "cognition",
        "external-readonly",
        "answer",
        "--evidence-path",
        evidence_path,
        "--question",
        "请基于已治理证据摘要判断这条资料是否可作为后续审查引用。",
        "--config-root",
        str(REPO_ROOT / "config"),
        "--request-live-llm",
        "--request-ollama",
        "--allow-live-llm",
        "--allow-ollama",
        "--live-llm-approval-ref",
        "approval://external-readonly-answer-real-provider-pytest",
        "--ollama-api-base",
        ollama_api_base,
        "--live-llm-timeout-seconds",
        timeout_seconds,
        "--json",
    ]
    completed = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=int(timeout_seconds) + 60,
        check=False,
    )
    assert completed.stdout, completed.stderr
    return completed


def _assert_success_or_quality_contract_failure(
    payload: dict[str, object],
    returncode: int,
) -> None:
    result = payload["evidence_summary_answer_result"]
    assert isinstance(result, dict)
    if payload["status"] == "success":
        assert returncode == 0
        assert payload["success"] is True
        assert payload["answer"]
        assert result["status"] == "success"
        return

    assert payload["status"] == "failed"
    assert returncode == 4
    assert payload["success"] is False
    assert payload["answer"] is None
    assert payload["answer_preview"] is None
    assert EVIDENCE_SUMMARY_ANSWER_QUALITY_BLOCKING_REASON in payload[
        "blocking_reasons"
    ]
    assert result["status"] == "failed"
    assert EVIDENCE_SUMMARY_ANSWER_QUALITY_BLOCKING_REASON in result[
        "blocking_reasons"
    ]


def _skip_unless_real_provider_smoke_enabled() -> None:
    if os.getenv(ENABLE_REAL_PROVIDER_SMOKE_ENV) != "1":
        pytest.skip(
            "Set "
            f"{ENABLE_REAL_PROVIDER_SMOKE_ENV}=1 to run external-readonly "
            "answer real provider smoke tests."
        )


def _local_ollama_api_base(value: str) -> str:
    parsed = urlparse(value)
    host = parsed.hostname
    if parsed.scheme != "http" or host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError(
            "external-readonly answer real provider smoke only allows local "
            "Ollama base urls."
        )
    return value


def _timeout_seconds() -> str:
    value = os.getenv(TIMEOUT_SECONDS_ENV, DEFAULT_TIMEOUT_SECONDS)
    if not value.isdecimal() or int(value) <= 0:
        raise ValueError(f"{TIMEOUT_SECONDS_ENV} must be a positive integer.")
    return value


def _assert_controlled_live_output_boundary(output: str) -> None:
    assert "raw_provider_response" not in output
    assert "response_text" not in output
    assert "messages" not in output
    assert "live_model_payload" not in output


def _write_external_readonly_archive(root: Path, evidence_path: str) -> None:
    target = root / evidence_path
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            _external_readonly_archive(evidence_path),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _external_readonly_archive(evidence_path: str) -> dict[str, object]:
    excerpt = "sanitized reference for external-readonly answer smoke"
    evidence_ref = (
        "evidence://external-readonly/"
        f"{Path(evidence_path).relative_to('outputs/external-readonly')}"
    )
    return {
        "allow_runtime_fetch": True,
        "allowed_for_model_context": True,
        "blocking_reasons": [],
        "command": "cognition external-readonly fetch",
        "evidence_output_path": evidence_path,
        "evidence_ref": evidence_ref,
        "evidence_written": True,
        "external_network_call_performed": True,
        "governed_summary_facts": _governed_summary_facts(
            evidence_path,
            evidence_ref=evidence_ref,
        ),
        "raw_html_included": False,
        "raw_response_included": False,
        "response_headers_included": False,
        "runtime": {
            "allowed_for_model_context": True,
            "blocking_reasons": [],
            "content_hash": hashlib.sha256(excerpt.encode()).hexdigest(),
            "external_network_call_performed": True,
            "runtime_fetch_performed": True,
            "sanitized_excerpt_preview": excerpt,
            "source_urls": ["https://example.com/reference"],
            "status": "completed",
            "total_excerpt_chars": len(excerpt),
            "transport_called": True,
            "warnings": [],
        },
        "runtime_fetch_performed": True,
        "source_url": "https://example.com/reference",
        "status": "success",
        "success": True,
        "transport_called": True,
        "uploads_content": False,
        "warnings": [],
        "writes_files": False,
    }


def _governed_summary_facts(
    evidence_path: str,
    *,
    evidence_ref: str,
) -> dict[str, object]:
    fact = "The reference is suitable for follow-up review."
    content_hash = hashlib.sha256(fact.encode()).hexdigest()
    return {
        "payload_type": "external_readonly_governed_summary_facts",
        "payload_version": "external_readonly_governed_summary_facts_v1",
        "status": "ready",
        "evidence_ref": evidence_ref,
        "evidence_output_path": evidence_path,
        "source_url_host": "example.com",
        "source_url_scheme": "https",
        "reference_review_ready": True,
        "allowed_for_model_context": True,
        "evidence_written": True,
        "content_hash": content_hash,
        "facts": [
            {
                "fact_ref": "external-readonly-governed-summary-fact://real-smoke-1",
                "fact_text": fact,
                "fact_index": 1,
                "evidence_ref": evidence_ref,
                "source_url_host": "example.com",
                "content_hash": content_hash,
                "metadata": {"citation_index": 1},
            }
        ],
        "fact_count": 1,
        "total_fact_chars": len(fact),
        "blocking_reasons": [],
        "warnings": [],
        "generation_policy_ref": (
            "policy://external-readonly/governed-summary-facts/minimal-v1"
        ),
        "metadata": {"source_package": "external_readonly"},
    }
