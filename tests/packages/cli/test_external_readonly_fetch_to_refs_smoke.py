from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from cognition_cli.constants import EXIT_BLOCKING, EXIT_OK


REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCT_RUNTIME_ENTRYPOINT = (
    REPO_ROOT
    / "packages"
    / "product_runtime_assembly"
    / "src"
    / "product_runtime_assembly"
    / "entrypoints"
    / "cognition.py"
)


def test_external_readonly_fetch_to_refs_blocked_smoke_uses_product_runtime_entrypoint(
    tmp_path: Path,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/574-blocked.json"

    fetch_result = _run_cognition(
        tmp_path,
        "external-readonly",
        "fetch",
        "--source-url",
        "https://example.com/reference",
        "--evidence-output",
        evidence_path,
        "--json",
    )

    assert fetch_result.returncode == EXIT_BLOCKING
    assert "Traceback" not in fetch_result.stderr
    fetch_payload = _json_stdout(fetch_result)
    archived = _read_archive(tmp_path, evidence_path)
    assert archived == fetch_payload
    assert fetch_payload["status"] == "blocked"
    assert fetch_payload["evidence_written"] is True
    assert fetch_payload["natural_language_confirmation_satisfied"] is False
    assert fetch_payload["runtime_fetch_performed"] is False
    assert fetch_payload["transport_called"] is False
    assert fetch_payload["external_network_call_performed"] is False
    assert fetch_payload["raw_response_included"] is False
    assert fetch_payload["raw_html_included"] is False
    assert fetch_payload["response_headers_included"] is False

    refs_result = _run_cognition(
        tmp_path,
        "external-readonly",
        "refs",
        "--evidence-path",
        evidence_path,
        "--json",
    )

    assert refs_result.returncode == EXIT_BLOCKING
    assert "Traceback" not in refs_result.stderr
    refs_payload = _json_stdout(refs_result)
    summary = refs_payload["product_response_summary"]
    assert refs_payload["status"] == "blocked"
    assert refs_payload["readonly_refs_status"] == "blocked"
    assert refs_payload["external_network_call_performed"] is False
    assert summary["entry_kind"] == "external_readonly_refs"
    assert summary["status"] == "blocked"
    assert _contains_reason(summary["blocking_reasons"], "evidence_status_not_success")
    assert _contains_reason(
        refs_payload["blocking_reasons"],
        "evidence_status_not_success",
    )
    _assert_refs_output_is_summary_only(refs_result.stdout)


def test_external_readonly_refs_success_smoke_consumes_prepared_evidence(
    tmp_path: Path,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/574-success.json"
    excerpt = "prepared reference excerpt for the refs smoke"
    _write_success_archive(tmp_path, evidence_path, excerpt=excerpt)

    refs_result = _run_cognition(
        tmp_path,
        "external-readonly",
        "refs",
        "--evidence-path",
        evidence_path,
        "--json",
    )

    assert refs_result.returncode == EXIT_OK
    assert "Traceback" not in refs_result.stderr
    refs_payload = _json_stdout(refs_result)
    summary = refs_payload["product_response_summary"]
    assert refs_payload["status"] == "success"
    assert refs_payload["readonly_refs_status"] == "ready"
    assert refs_payload["evidence_ref_count"] == 1
    assert refs_payload["additional_ref_count"] == 1
    assert refs_payload["external_network_call_performed"] is False
    assert summary["entry_kind"] == "external_readonly_refs"
    assert summary["status"] == "success"
    assert summary["evidence_refs"][0]["kind"] == "external_readonly_evidence"
    assert summary["additional_refs"][0]["kind"] == (
        "external_readonly_evidence_observation"
    )
    assert summary["additional_refs"][0]["ref"].startswith(
        "external-readonly-evidence-observation://"
    )
    _assert_refs_output_is_summary_only(refs_result.stdout, forbidden_excerpt=excerpt)


def test_external_readonly_fetch_to_refs_smoke_keeps_default_entrypoint_boundary() -> None:
    source = PRODUCT_RUNTIME_ENTRYPOINT.read_text(encoding="utf-8")

    assert "execute_cognition_run_with_default_runtime" in source
    assert "build_twf_default_llm_invocation_service_factory" in source
    assert "product_application_assembly" not in source
    assert "external_readonly_refs_application_executor" not in source
    assert "composition" not in source


def _run_cognition(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "product_runtime_assembly.entrypoints.cognition",
            *args,
        ],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _json_stdout(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - assertion detail.
        raise AssertionError(
            f"stdout was not JSON: {result.stdout!r}; stderr={result.stderr!r}"
        ) from exc
    assert isinstance(payload, dict)
    return payload


def _read_archive(root: Path, evidence_path: str) -> dict[str, Any]:
    target = root / evidence_path
    assert target.exists()
    return json.loads(target.read_text(encoding="utf-8"))


def _write_success_archive(
    root: Path,
    evidence_path: str,
    *,
    excerpt: str,
) -> None:
    target = root / evidence_path
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            _success_archive(evidence_path, excerpt=excerpt),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _success_archive(evidence_path: str, *, excerpt: str) -> dict[str, object]:
    return {
        "allow_runtime_fetch": True,
        "allowed_for_model_context": True,
        "blocking_reasons": [],
        "command": "cognition external-readonly fetch",
        "evidence_output_path": evidence_path,
        "evidence_ref": (
            "evidence://external-readonly/"
            f"{Path(evidence_path).relative_to('outputs/external-readonly')}"
        ),
        "evidence_written": True,
        "external_network_call_performed": False,
        "raw_html_included": False,
        "raw_response_included": False,
        "response_headers_included": False,
        "runtime": {
            "allowed_for_model_context": True,
            "blocking_reasons": [],
            "content_hash": hashlib.sha256(excerpt.encode()).hexdigest(),
            "external_network_call_performed": False,
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


def _assert_refs_output_is_summary_only(
    output: str,
    *,
    forbidden_excerpt: str | None = None,
) -> None:
    assert "ProductGatewayResponse" not in output
    assert '"sanitized_excerpt_preview":' not in output
    assert '"raw_response":' not in output
    assert '"raw_html":' not in output
    assert '"response_headers":' not in output
    if forbidden_excerpt:
        assert forbidden_excerpt not in output


def _contains_reason(reasons: list[Any], expected: str) -> bool:
    return any(expected in str(reason) for reason in reasons)
