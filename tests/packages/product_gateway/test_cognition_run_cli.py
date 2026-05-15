from __future__ import annotations

import json

from product_gateway.cli.cognition_run import run_cognition_run_cli
from product_gateway.cli.presenter import (
    product_gateway_response_to_json_text,
    product_gateway_response_to_text,
)
from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayResponse,
    ProductGatewayStatus,
)


def test_cognition_run_cli_blocked_json_output(capsys) -> None:
    exit_code = run_cognition_run_cli(
        [
            "--request-id",
            "cli-blocked-230",
            "--runtime-id",
            "runtime-cli-blocked-230",
            "--input-json",
            '{"input_summary":"缺少审批"}',
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 2
    assert payload["request_id"] == "cli-blocked-230"
    assert payload["entry_kind"] == "cognition_run"
    assert payload["status"] == "blocked"
    assert payload["exit_code"] == 2
    assert "operator_approval_not_true" in payload["blocking_reasons"]
    assert "raw_prompt" not in captured.out
    assert "raw_provider_response" not in captured.out
    assert "raw_tool_input" not in captured.out


def test_cognition_run_cli_allowed_no_live_text_output(capsys) -> None:
    exit_code = run_cognition_run_cli(
        [
            "--request-id",
            "cli-allowed-230",
            "--runtime-id",
            "runtime-cli-allowed-230",
            "--input-json",
            '{"input_summary":"已脱敏请求"}',
            "--operator-approved",
            "--approval-ref",
            "operator-approval://cli-allowed-230",
            "--audit-ref",
            "audit://cli-allowed-230",
            "--sanitized-evidence-ref",
            "evidence://cli-allowed-230",
            "--governance-summary-output-ref",
            "governance-summary://cli-allowed-230",
            "--format",
            "text",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "request_id: cli-allowed-230" in captured.out
    assert "entry_kind: cognition_run" in captured.out
    assert "status: success" in captured.out
    assert "exit_code: 0" in captured.out
    assert "governance_summary_ref: governance-summary://cli-allowed-230" in captured.out
    assert "evidence_refs:" in captured.out
    assert "audit_refs:" in captured.out
    assert "tool_audit_refs:" in captured.out
    assert "raw_prompt" not in captured.out
    assert "raw_provider_response" not in captured.out
    assert "raw_tool_input" not in captured.out


def test_cognition_run_cli_writes_output_file(tmp_path, capsys) -> None:
    output_path = tmp_path / "product-gateway-response.json"
    exit_code = run_cognition_run_cli(
        [
            "--request-id",
            "cli-output-230",
            "--runtime-id",
            "runtime-cli-output-230",
            "--operator-approved",
            "--approval-ref",
            "operator-approval://cli-output-230",
            "--audit-ref",
            "audit://cli-output-230",
            "--sanitized-evidence-ref",
            "evidence://cli-output-230",
            "--governance-summary-output-ref",
            "governance-summary://cli-output-230",
            "--json",
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert captured.out == ""
    assert payload["request_id"] == "cli-output-230"
    assert payload["status"] == "success"


def test_cognition_run_cli_rejects_non_object_input_json(capsys) -> None:
    exit_code = run_cognition_run_cli(
        [
            "--request-id",
            "cli-non-object-230",
            "--runtime-id",
            "runtime-cli-non-object-230",
            "--input-json",
            '["not", "an", "object"]',
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--input-json must be a JSON object" in captured.err


def test_cognition_run_cli_rejects_raw_input_payload(capsys) -> None:
    exit_code = run_cognition_run_cli(
        [
            "--request-id",
            "cli-raw-230",
            "--runtime-id",
            "runtime-cli-raw-230",
            "--input-json",
            '{"raw_prompt":"不要进入产品入口"}',
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "forbidden raw payload" in captured.err


def test_cognition_run_cli_does_not_accept_config_root(capsys) -> None:
    exit_code = run_cognition_run_cli(
        [
            "--request-id",
            "cli-config-root-230",
            "--runtime-id",
            "runtime-cli-config-root-230",
            "--config-root",
            "config",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "unrecognized arguments: --config-root" in captured.err


def test_product_gateway_presenter_renders_response() -> None:
    response = ProductGatewayResponse(
        request_id="presenter-230",
        entry_kind=ProductGatewayEntryKind.COGNITION_RUN,
        status=ProductGatewayStatus.SUCCESS,
        exit_code=0,
        governance_summary_ref="governance-summary://presenter-230",
        metadata={"runtime_id": "runtime-presenter-230"},
    )

    json_payload = json.loads(product_gateway_response_to_json_text(response))
    text_payload = product_gateway_response_to_text(response)

    assert json_payload["request_id"] == "presenter-230"
    assert json_payload["status"] == "success"
    assert "request_id: presenter-230" in text_payload
    assert "governance_summary_ref: governance-summary://presenter-230" in text_payload
