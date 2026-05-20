from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
ENABLE_SMOKE_ENV = "CE_ENABLE_EXTERNAL_READONLY_ASK_DEEPSEEK_PROVIDER_SMOKE"
DEEPSEEK_NETWORK_GATE_ENV = "DEEPSEEK_NETWORK_GATE_OPEN"
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEEPSEEK_APPROVAL_REF_ENV = "DEEPSEEK_APPROVAL_REF"
DEEPSEEK_AUDIT_REF_ENV = "DEEPSEEK_AUDIT_REF"
DEEPSEEK_MODEL_ENV = "DEEPSEEK_MODEL"
DEEPSEEK_TIMEOUT_SECONDS_ENV = "DEEPSEEK_TIMEOUT_SECONDS"
DEEPSEEK_MAX_TOKENS_ENV = "DEEPSEEK_MAX_TOKENS"
DEFAULT_DEEPSEEK_MODEL = "deepseek/deepseek-v4-flash"
SUPPORTED_DEEPSEEK_MODELS = {
    "deepseek/deepseek-v4-flash": "deepseek_v4_flash_external",
    "deepseek/deepseek-v4-pro": "deepseek_v4_pro_external",
}


def test_external_readonly_ask_deepseek_real_provider_smoke(tmp_path: Path) -> None:
    skip_reason = _skip_reason()
    if skip_reason is not None:
        pytest.skip(skip_reason)

    evidence_path = "outputs/external-readonly/cli-fetch/deepseek-ask-smoke.json"
    _write_archive(tmp_path, evidence_path)
    model_name = _model_name()
    model_profile_ref = SUPPORTED_DEEPSEEK_MODELS[model_name]
    model_args = ["--model", "deepseek"]
    if model_name != DEFAULT_DEEPSEEK_MODEL:
        model_args = [
            "--model-name",
            model_name,
            "--llm-provider-profile-ref",
            "deepseek_gated",
            "--llm-model-profile-ref",
            model_profile_ref,
            "--llm-output-governance-profile-ref",
            "adk_no_output_schema_candidate",
        ]
    timeout_seconds = os.getenv(DEEPSEEK_TIMEOUT_SECONDS_ENV, "180")
    max_tokens = os.getenv(DEEPSEEK_MAX_TOKENS_ENV, "256")

    completed = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(REPO_ROOT),
            "cognition",
            "external-readonly",
            "ask",
            "--config-root",
            str(REPO_ROOT / "config"),
            "--evidence-path",
            evidence_path,
            "--question",
            "这个网页主要说明了什么？",
            *model_args,
            "--request-live-llm",
            "--allow-live-llm",
            "--live-llm-approval-ref",
            os.environ[DEEPSEEK_APPROVAL_REF_ENV],
            "--network-gate-open",
            "--operator-approved",
            "--audit-ref",
            os.environ[DEEPSEEK_AUDIT_REF_ENV],
            "--live-llm-timeout-seconds",
            timeout_seconds,
            "--live-llm-max-tokens",
            max_tokens,
            "--answer-preview-limit",
            "800",
            "--json",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
    )

    assert completed.returncode == 0, completed.stderr + completed.stdout
    payload = json.loads(completed.stdout)

    assert payload["status"] == "success"
    assert payload["model_name"] == model_name
    assert payload["llm_call_attempted"] is True
    assert payload["llm_runtime_call_performed"] is True
    assert payload["external_readonly_network_call_performed"] is False
    assert payload["evidence_summary_answer_result"]["metadata"][
        "llm_route_model"
    ] == model_name
    assert payload["answer"]
    assert re.search(r"sk-[0-9a-fA-F]{32,}", completed.stdout) is None
    assert "DEEPSEEK_API_KEY" not in completed.stdout


def _skip_reason() -> str | None:
    if os.getenv(ENABLE_SMOKE_ENV) != "1":
        return f"Set {ENABLE_SMOKE_ENV}=1 to run DeepSeek ask product smoke."
    if os.getenv(DEEPSEEK_NETWORK_GATE_ENV) != "1":
        return f"Set {DEEPSEEK_NETWORK_GATE_ENV}=1 to open the DeepSeek gate."
    if not os.getenv(DEEPSEEK_API_KEY_ENV):
        return f"Set {DEEPSEEK_API_KEY_ENV} outside the repository."
    if not os.getenv(DEEPSEEK_APPROVAL_REF_ENV):
        return f"Set {DEEPSEEK_APPROVAL_REF_ENV} for approval facts."
    if not os.getenv(DEEPSEEK_AUDIT_REF_ENV):
        return f"Set {DEEPSEEK_AUDIT_REF_ENV} for audit facts."
    _model_name()
    return None


def _model_name() -> str:
    model_name = os.getenv(DEEPSEEK_MODEL_ENV, DEFAULT_DEEPSEEK_MODEL)
    if model_name not in SUPPORTED_DEEPSEEK_MODELS:
        raise ValueError("DeepSeek ask product smoke supports DeepSeek V4 only.")
    return model_name


def _write_archive(root: Path, evidence_path: str) -> None:
    fact = (
        "Example Domain Example Domain This domain is for use in documentation "
        "examples without needing permission. Avoid use in operations. Learn more"
    )
    evidence_ref = "evidence://external-readonly/item/cli-fetch"
    content_hash = hashlib.sha256(fact.encode()).hexdigest()
    target = root / evidence_path
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            {
                "allowed_for_model_context": True,
                "blocking_reasons": [],
                "command": "cognition external-readonly fetch",
                "status": "success",
                "success": True,
                "evidence_output_path": evidence_path,
                "evidence_ref": (
                    "evidence://external-readonly/cli-fetch/"
                    "deepseek-ask-smoke.json"
                ),
                "evidence_written": True,
                "external_network_call_performed": True,
                "raw_html_included": False,
                "raw_response_included": False,
                "response_headers_included": False,
                "runtime": {
                    "allowed_for_model_context": True,
                    "blocking_reasons": [],
                    "content_hash": content_hash,
                    "external_network_call_performed": True,
                    "runtime_fetch_performed": True,
                    "sanitized_excerpt_preview": fact,
                    "source_urls": ["https://example.com"],
                    "status": "completed",
                    "total_excerpt_chars": len(fact),
                    "transport_called": True,
                    "warnings": [],
                },
                "runtime_fetch_performed": True,
                "source_url": "https://example.com",
                "transport_called": True,
                "warnings": [],
                "writes_files": False,
                "governed_summary_facts": {
                    "payload_type": "external_readonly_governed_summary_facts",
                    "payload_version": (
                        "external_readonly_governed_summary_facts_v1"
                    ),
                    "status": "ready",
                    "evidence_ref": evidence_ref,
                    "evidence_output_path": evidence_path,
                    "reference_review_ready": True,
                    "allowed_for_model_context": True,
                    "evidence_written": True,
                    "content_hash": content_hash,
                    "facts": [
                        {
                            "fact_ref": (
                                "external-readonly-governed-summary-fact://"
                                "deepseek-smoke-1"
                            ),
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
                        "policy://external-readonly/governed-summary-facts/"
                        "minimal-v1"
                    ),
                    "metadata": {"source_package": "external_readonly"},
                },
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
