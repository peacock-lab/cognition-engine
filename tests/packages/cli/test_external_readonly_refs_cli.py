from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from cognition_cli.entrypoints import cognition
from cognition_cli.external_readonly import refs as refs_cli


REPO_ROOT = Path(__file__).resolve().parents[3]
REFS_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "external_readonly"
    / "refs.py"
)
PRODUCT_RUNTIME_ASSEMBLY_PYPROJECT = (
    REPO_ROOT / "packages" / "product_runtime_assembly" / "pyproject.toml"
)


def test_external_readonly_refs_help_does_not_call_executor(capsys: Any) -> None:
    exit_code = cognition.run_cli(["external-readonly", "refs", "--help"])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "--evidence-path" in output
    assert "external-readonly evidence refs" in output


def test_external_readonly_refs_requires_evidence_path_before_executor(
    capsys: Any,
) -> None:
    def raising_executor(*_: Any, **__: Any) -> Any:
        raise AssertionError("executor should not be called without evidence path")

    exit_code = cognition.run_cli(
        ["external-readonly", "refs", "--json"],
        external_readonly_refs_application_executor=raising_executor,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == ["evidence_output_path_required"]
    assert payload["product_response_summary"] is None
    assert payload["external_network_call_performed"] is False


def test_external_readonly_refs_blocks_uncontrolled_path_before_executor(
    capsys: Any,
) -> None:
    def raising_executor(*_: Any, **__: Any) -> Any:
        raise AssertionError("executor should not be called for unsafe paths")

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "refs",
            "--evidence-path",
            "outputs/external-readonly/../leak.json",
            "--json",
        ],
        external_readonly_refs_application_executor=raising_executor,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == [
        "outputs/external-readonly/../leak.json:evidence_output_path_unsafe"
    ]
    assert payload["evidence_ref_count"] == 0
    assert payload["additional_ref_count"] == 0


def test_external_readonly_refs_fake_executor_receives_read_context(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/manual.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    captured: dict[str, Any] = {}

    def fake_executor(read_context: Any, **kwargs: Any) -> Any:
        captured["status"] = read_context.status
        captured["evidence_refs"] = tuple(read_context.evidence_refs)
        captured.update(kwargs)
        return SimpleNamespace(
            product_response_summary={
                "entry_kind": "external_readonly_refs",
                "status": "success",
                "exit_code": 0,
                "evidence_refs": [
                    {
                        "ref": "evidence://external-readonly/cli-fetch/manual.json",
                        "kind": "external_readonly_evidence",
                        "purpose": "reference_review",
                        "metadata": {},
                    }
                ],
                "additional_refs": [
                    {
                        "ref": "external-readonly-evidence-observation://fake",
                        "kind": "external_readonly_evidence_observation",
                        "purpose": "reference_review",
                        "metadata": {},
                    }
                ],
                "blocking_reasons": [],
                "warnings": [],
            },
            readonly_public_refs_status={
                "external_readonly_evidence_readonly_facts": {
                    "status": "ready"
                }
            },
        )

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "refs",
            "--evidence-path",
            evidence_path,
            "--request-id",
            "external-readonly-refs-request://unit/fake",
            "--json",
        ],
        external_readonly_refs_application_executor=fake_executor,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["status"] == "ready"
    assert captured["request_id"] == "external-readonly-refs-request://unit/fake"
    assert captured["metadata"]["source"] == refs_cli.EXTERNAL_READONLY_REFS_SOURCE
    assert captured["metadata"]["evidence_path_count"] == 1
    assert captured["evidence_refs"] == (
        "evidence://external-readonly/cli-fetch/manual.json",
    )
    assert payload["status"] == "success"
    assert payload["evidence_ref_count"] == 1
    assert payload["additional_ref_count"] == 1
    assert payload["readonly_refs_status"] == "ready"


def test_external_readonly_refs_default_executor_outputs_summary_only(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/default.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "refs",
            "--evidence-path",
            evidence_path,
            "--json",
        ]
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["product_response_summary"]["entry_kind"] == (
        "external_readonly_refs"
    )
    assert payload["product_response_summary"]["status"] == "success"
    assert payload["evidence_ref_count"] == 1
    assert payload["additional_ref_count"] == 1
    assert payload["external_network_call_performed"] is False
    assert "sanitized reference" not in output
    assert "sanitized_excerpt_preview" not in output
    assert "ProductGatewayResponse" not in output


def test_external_readonly_refs_text_output_is_compact(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/text.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "refs",
            "--evidence-path",
            evidence_path,
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "status: success" in output
    assert "request_id: external-readonly-refs-request://cli/refs" in output
    assert "evidence_ref_count: 1" in output
    assert "additional_ref_count: 1" in output
    assert "sanitized reference" not in output


def test_external_readonly_refs_cli_keeps_channel_boundary() -> None:
    source = REFS_SOURCE.read_text(encoding="utf-8")
    product_runtime_pyproject = PRODUCT_RUNTIME_ASSEMBLY_PYPROJECT.read_text(
        encoding="utf-8"
    )

    assert "build_external_readonly_evidence_read_context" in source
    assert "from product_application_assembly import" in source
    assert "from composition" not in source
    assert "import composition" not in source
    assert "runtime_container" not in source
    assert "product_runtime_assembly" not in source
    assert "product_gateway.response_summary_projection" not in source
    assert "ProductGatewayResponse" not in source
    assert "sanitized_excerpt_preview" not in source
    assert "cognition-system-product-application-assembly" not in (
        product_runtime_pyproject
    )


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
    excerpt = "sanitized reference"
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
        "external_network_call_performed": True,
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
