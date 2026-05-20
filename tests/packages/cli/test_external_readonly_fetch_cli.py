from __future__ import annotations

import hashlib
import json
from argparse import Namespace
from pathlib import Path
from typing import Any

from cognition_cli.entrypoints import cognition
from cognition_cli.external_readonly import fetch as fetch_cli
from cognition_cli.external_readonly.fetch import (
    REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION,
    external_readonly_fetch_command,
    validate_external_readonly_fetch_evidence_output_path,
    write_external_readonly_fetch_evidence,
)
from cognition_cli.parser import build_parser
from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayRef,
    ProductGatewayResponse,
    ProductGatewayStatus,
)
from product_gateway.external_readonly import (
    ExternalReadonlyFetchGatewayExecutionResult,
)
from external_readonly import (
    ExternalReadonlyEvidenceEnvelope,
    ExternalReadonlyUrlFetchResult,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
FETCH_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "external_readonly"
    / "fetch.py"
)


def test_external_readonly_fetch_help_does_not_call_runtime(capsys: Any) -> None:
    exit_code = cognition.run_cli(["external-readonly", "fetch", "--help"])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "--source-url" in output
    assert "--confirm-external-readonly-fetch" in output
    assert "--evidence-output" in output
    assert "external-readonly URL fetch" in output


def test_external_readonly_fetch_requires_confirmation_before_gateway(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    def raising_executor(_: Any) -> Any:
        raise AssertionError("gateway should not be called without confirmation")

    monkeypatch.setattr(
        fetch_cli,
        "execute_external_readonly_fetch_gateway_request",
        raising_executor,
    )

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "fetch",
            "--source-url",
            "https://example.com/reference",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["natural_language_confirmation_satisfied"] is False
    assert payload["runtime_fetch_performed"] is False
    assert payload["transport_called"] is False
    assert payload["external_network_call_performed"] is False
    assert payload["blocking_reasons"] == [
        "external_readonly_natural_language_confirmation_required"
    ]


def test_external_readonly_fetch_preflight_uses_product_gateway_without_network(
    capsys: Any,
) -> None:
    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "fetch",
            "--source-url",
            "https://example.com/reference",
            "--confirm-external-readonly-fetch",
            REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION,
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["natural_language_confirmation_satisfied"] is True
    assert payload["allow_runtime_fetch"] is False
    assert payload["runtime_fetch_performed"] is False
    assert payload["transport_called"] is False
    assert payload["external_network_call_performed"] is False
    assert "external_readonly_runtime_fetch_not_allowed" in payload["blocking_reasons"]


def test_external_readonly_fetch_blocks_live_transport_until_refs_are_explicit(
    capsys: Any,
) -> None:
    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "fetch",
            "--source-url",
            "https://example.com/reference",
            "--confirm-external-readonly-fetch",
            REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION,
            "--allow-runtime-fetch",
            "--use-live-transport",
            "--network-gate-open",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["allow_runtime_fetch"] is True
    assert payload["use_live_transport"] is True
    assert payload["runtime_fetch_performed"] is False
    assert payload["transport_called"] is False
    assert payload["external_network_call_performed"] is False
    assert "operator_approval_not_true" in payload["blocking_reasons"]
    assert "approval_ref_required" in payload["blocking_reasons"]
    assert "runtime_fetch_approval_ref_required" in payload["blocking_reasons"]


def test_external_readonly_fetch_command_can_render_fake_success_without_network(
    capsys: Any,
) -> None:
    captured: dict[str, Any] = {}
    args = _parse_fetch_args(
        "--source-url",
        "https://example.com/reference",
        "--confirm-external-readonly-fetch",
        REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION,
        "--operator-approved",
        "--approval-ref",
        "approval://external-readonly/cli-fetch",
        "--runtime-fetch-approval-ref",
        "approval://external-readonly/runtime-fetch/cli-fetch",
        "--audit-ref",
        "audit://external-readonly/cli-fetch",
        "--network-gate-open",
        "--allow-runtime-fetch",
        "--json",
    )

    def fake_executor(gateway_input: Any) -> Any:
        captured.update(dict(gateway_input))
        return _fake_success_execution()

    exit_code = external_readonly_fetch_command(args, executor=fake_executor)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["allow_runtime_fetch"] is True
    assert captured["use_live_transport"] is False
    assert captured["network_gate"]["status"] == "passed"
    assert captured["metadata"]["natural_language_confirmation_satisfied"] is True
    assert payload["status"] == "success"
    assert payload["success"] is True
    assert payload["external_network_call_performed"] is False
    assert payload["evidence_refs"] == ["evidence://external-readonly/item/cli-fetch"]
    assert payload["runtime"]["sanitized_excerpt_preview"] == "sanitized reference"


def test_external_readonly_fetch_command_writes_controlled_evidence_json(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.chdir(tmp_path)
    args = _parse_fetch_args(
        "--source-url",
        "https://example.com/reference",
        "--confirm-external-readonly-fetch",
        REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION,
        "--operator-approved",
        "--approval-ref",
        "approval://external-readonly/cli-fetch",
        "--runtime-fetch-approval-ref",
        "approval://external-readonly/runtime-fetch/cli-fetch",
        "--audit-ref",
        "audit://external-readonly/cli-fetch",
        "--network-gate-open",
        "--allow-runtime-fetch",
        "--evidence-output",
        "outputs/external-readonly/cli-fetch/manual.json",
        "--json",
    )

    exit_code = external_readonly_fetch_command(
        args,
        executor=lambda _: _fake_success_execution(),
    )

    target = tmp_path / "outputs" / "external-readonly" / "cli-fetch" / "manual.json"
    printed = json.loads(capsys.readouterr().out)
    archived = json.loads(target.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert printed == archived
    assert archived["status"] == "success"
    assert archived["evidence_written"] is True
    assert archived["evidence_output_path"] == (
        "outputs/external-readonly/cli-fetch/manual.json"
    )
    assert archived["evidence_ref"] == (
        "evidence://external-readonly/cli-fetch/manual.json"
    )
    assert archived["external_network_call_performed"] is False
    assert archived["raw_response_included"] is False
    assert archived["response_headers_included"] is False
    facts = archived["governed_summary_facts"]
    assert facts["status"] == "ready"
    assert facts["evidence_output_path"] == (
        "outputs/external-readonly/cli-fetch/manual.json"
    )
    assert facts["fact_count"] == 1
    assert facts["facts"][0]["fact_text"] == "sanitized reference"
    serialized_facts = json.dumps(facts, ensure_ascii=False, sort_keys=True)
    assert "model_context_items" not in serialized_facts
    assert "sanitized_excerpt" not in serialized_facts


def test_external_readonly_fetch_command_can_archive_confirmation_block(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.chdir(tmp_path)
    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "fetch",
            "--source-url",
            "https://example.com/reference",
            "--evidence-output",
            "outputs/external-readonly/cli-fetch/blocked.json",
            "--json",
        ]
    )

    target = tmp_path / "outputs" / "external-readonly" / "cli-fetch" / "blocked.json"
    printed = json.loads(capsys.readouterr().out)
    archived = json.loads(target.read_text(encoding="utf-8"))
    assert exit_code == 3
    assert printed == archived
    assert archived["status"] == "blocked"
    assert archived["evidence_written"] is True
    assert archived["runtime_fetch_performed"] is False
    assert archived["external_network_call_performed"] is False


def test_external_readonly_fetch_blocks_invalid_evidence_output_before_gateway(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.chdir(tmp_path)
    args = _parse_fetch_args(
        "--source-url",
        "https://example.com/reference",
        "--confirm-external-readonly-fetch",
        REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION,
        "--operator-approved",
        "--approval-ref",
        "approval://external-readonly/cli-fetch",
        "--runtime-fetch-approval-ref",
        "approval://external-readonly/runtime-fetch/cli-fetch",
        "--audit-ref",
        "audit://external-readonly/cli-fetch",
        "--network-gate-open",
        "--allow-runtime-fetch",
        "--use-live-transport",
        "--evidence-output",
        "outputs/external-readonly/../leak.json",
        "--json",
    )

    def raising_executor(_: Any) -> Any:
        raise AssertionError("gateway should not be called for invalid evidence output")

    exit_code = external_readonly_fetch_command(args, executor=raising_executor)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["evidence_written"] is False
    assert "evidence_output_path_unsafe" in payload["blocking_reasons"]
    assert payload["runtime_fetch_performed"] is False
    assert payload["transport_called"] is False
    assert payload["external_network_call_performed"] is False
    assert not (tmp_path / "outputs" / "leak.json").exists()


def test_external_readonly_fetch_blocks_unsafe_evidence_output(
    tmp_path: Path,
) -> None:
    output = {
        "product": "Cognition System / 认知系统",
        "command": "cognition external-readonly fetch",
        "status": "success",
        "success": True,
        "blocking_reasons": [],
    }

    blocked = write_external_readonly_fetch_evidence(
        output,
        root=tmp_path,
        evidence_output="outputs/external-readonly/../leak.json",
    )

    assert blocked["status"] == "blocked"
    assert blocked["evidence_written"] is False
    assert "evidence_output_path_unsafe" in blocked["blocking_reasons"]
    assert not (tmp_path / "outputs" / "leak.json").exists()


def test_external_readonly_fetch_blocks_existing_output_without_overwrite(
    tmp_path: Path,
) -> None:
    output = {
        "product": "Cognition System / 认知系统",
        "command": "cognition external-readonly fetch",
        "status": "blocked",
        "success": False,
        "blocking_reasons": ["preflight_only"],
    }
    evidence_output = "outputs/external-readonly/cli-fetch/existing.json"
    target = tmp_path / evidence_output
    target.parent.mkdir(parents=True)
    target.write_text('{"old": true}\n', encoding="utf-8")

    blocked = write_external_readonly_fetch_evidence(
        output,
        root=tmp_path,
        evidence_output=evidence_output,
    )
    archived = write_external_readonly_fetch_evidence(
        output,
        root=tmp_path,
        evidence_output=evidence_output,
        overwrite=True,
    )

    assert blocked["status"] == "blocked"
    assert "evidence_output_exists" in blocked["blocking_reasons"]
    assert archived["evidence_written"] is True
    assert json.loads(target.read_text(encoding="utf-8"))["command"] == (
        "cognition external-readonly fetch"
    )


def test_external_readonly_fetch_validates_evidence_output_path(
    tmp_path: Path,
) -> None:
    assert (
        validate_external_readonly_fetch_evidence_output_path(
            root=tmp_path,
            evidence_output="outputs/external-readonly/cli-fetch/ok.json",
        )
        is None
    )
    assert validate_external_readonly_fetch_evidence_output_path(
        root=tmp_path,
        evidence_output="outputs/external-readonly/cli-fetch/not-json.txt",
    ) == "evidence_output_path_must_be_json"
    assert validate_external_readonly_fetch_evidence_output_path(
        root=tmp_path,
        evidence_output="outputs/external-readonly/live-smoke/nope.json",
    ) == "evidence_output_path_outside_controlled_root"
    assert validate_external_readonly_fetch_evidence_output_path(
        root=tmp_path,
        evidence_output=str(
            tmp_path / "outputs" / "external-readonly" / "cli-fetch" / "abs.json"
        ),
    ) == "evidence_output_path_must_be_relative"


def test_external_readonly_fetch_output_boundary_rejects_raw_payload_keys() -> None:
    assert fetch_cli._violates_external_readonly_fetch_output_boundary(
        {"raw_response": "must not leak"}
    ) is True
    assert fetch_cli._violates_external_readonly_fetch_output_boundary(
        {"runtime": {"response_headers": {"set-cookie": "nope"}}}
    ) is True


def test_external_readonly_fetch_cli_keeps_channel_boundary() -> None:
    source = FETCH_SOURCE.read_text(encoding="utf-8")

    assert "execute_external_readonly_fetch_gateway_request" in source
    assert "from contract_core.external_readonly_archive import" in source
    assert "from external_readonly.governed_summary_facts import" in source
    assert "external_readonly.evidence_archive" not in source
    assert "runtime_container.external_readonly" not in source
    assert "google.adk" not in source
    assert "adk_adapter" not in source
    assert "litellm" not in source
    assert "composition" not in source
    assert "urllib" not in source
    assert "REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION" in source


def _parse_fetch_args(*items: str) -> Namespace:
    return build_parser().parse_args(["external-readonly", "fetch", *items])


def _fake_success_execution() -> ExternalReadonlyFetchGatewayExecutionResult:
    excerpt = "sanitized reference"
    envelope = ExternalReadonlyEvidenceEnvelope(
        envelope_ref="evidence://external-readonly/envelope/cli-fetch",
        request_ref="external-readonly-request://cli/fetch",
        status="valid",
        allowed_for_model_context=True,
        model_context_items=(
            {
                "citation_index": 1,
                "evidence_ref": "evidence://external-readonly/item/cli-fetch",
                "source_url": "https://example.com/reference",
                "source_title": None,
                "retrieved_at": "2026-05-16T00:00:00+00:00",
                "item_type": "fetched_excerpt",
                "sanitized_excerpt": excerpt,
                "content_hash": hashlib.sha256(excerpt.encode()).hexdigest(),
            },
        ),
        evidence_refs=("evidence://external-readonly/item/cli-fetch",),
        source_urls=("https://example.com/reference",),
        total_excerpt_chars=len(excerpt),
    )
    runtime_result = ExternalReadonlyUrlFetchResult(
        status="completed",
        request_ref="external-readonly-request://cli/fetch",
        source_url="https://example.com/reference",
        envelope_ref="evidence://external-readonly/envelope/cli-fetch",
        allowed_for_model_context=True,
        envelope=envelope,
        transport_called=True,
        runtime_fetch_performed=True,
        external_network_call_performed=False,
        tool_execution_performed=False,
    )
    response = ProductGatewayResponse(
        request_id="external-readonly-request://cli/fetch",
        entry_kind=ProductGatewayEntryKind.EXTERNAL_READONLY_FETCH,
        status=ProductGatewayStatus.SUCCESS,
        exit_code=0,
        evidence_refs=[
            ProductGatewayRef(
                ref="evidence://external-readonly/item/cli-fetch",
                kind="external_readonly_evidence",
            )
        ],
        metadata={
            "runtime_fetch_performed": True,
            "transport_called": True,
            "external_network_call_performed": False,
            "allowed_for_model_context": True,
            "raw_response_included": False,
            "response_headers_included": False,
        },
    )
    return ExternalReadonlyFetchGatewayExecutionResult(
        product_request=None,  # type: ignore[arg-type]
        product_response=response,
        runtime_result=runtime_result,
    )
