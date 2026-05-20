from __future__ import annotations

import hashlib
import json
import os
from argparse import Namespace
from pathlib import Path
from typing import Any

import cognition_cli.external_readonly.ask as ask_module
from cognition_cli.entrypoints import cognition
from cognition_cli.external_readonly.ask import (
    EXTERNAL_READONLY_ASK_PRODUCT_PATH,
    external_readonly_ask_command,
)
from cognition_cli.external_readonly.fetch import (
    REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION,
)
from cognition_cli.parser import build_parser
from contract_core.llm_invocation import (
    GovernedLlmInvocationServiceResolution,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from external_readonly import (
    ExternalReadonlyEvidenceEnvelope,
    ExternalReadonlyUrlFetchResult,
)
from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayRef,
    ProductGatewayResponse,
    ProductGatewayStatus,
)
from product_gateway.external_readonly import (
    ExternalReadonlyFetchGatewayExecutionResult,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
ASK_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "external_readonly"
    / "ask.py"
)
KEYCHAIN_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "credentials"
    / "deepseek_keychain.py"
)


def test_external_readonly_ask_help_does_not_call_provider(capsys: Any) -> None:
    exit_code = cognition.run_cli(["external-readonly", "ask", "--help"])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "--source-url" in output
    assert "--evidence-path" in output
    assert "--request-live-llm" in output
    assert "--model" in output
    assert "--model-alias" in output
    assert "--guided" in output
    assert "--interactive" in output
    assert "--prompt-provider-key" in output
    assert "--use-stored-provider-key" in output
    assert "--llm-provider-profile-ref" in output
    assert "controlled live LLM" in output


def test_external_readonly_ask_requires_explicit_gates_before_refs(
    capsys: Any,
) -> None:
    def raising_refs_executor(*_: Any, **__: Any) -> Any:
        raise AssertionError("refs executor should not run before live gates")

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--question",
            "请基于证据回答",
            "--json",
        ],
        external_readonly_refs_application_executor=raising_refs_executor,
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == [
        "source_url_or_evidence_output_path_required",
        "request_live_llm_required",
        "request_ollama_required",
        "allow_live_llm_required",
        "allow_ollama_required",
        "live_llm_approval_ref_required",
        "external_readonly_ask_llm_provider_not_injected",
    ]
    assert payload["llm_call_attempted"] is False
    assert payload["external_readonly_fetch_performed"] is False
    assert payload["failure_explanation"] == (
        "当前请求缺少必要输入或显式授权，尚未进入模型回答。"
    )
    assert payload["recovery_hints"] == [
        "请补齐 source URL 或 evidence path。",
        "请显式提供 live LLM 与 Ollama 的请求、允许和 approval ref。",
    ]


def test_external_readonly_ask_invokes_product_path_from_archive(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    service = _FakeLlmService(
        "该资料可作为后续审查引用，证据见 evidence://external-readonly/cli-fetch/ask.json。"
    )
    factory = _FakeFactory(service)

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这条资料是否可用于后续审查？",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/unit",
            "--ollama-api-base",
            "http://127.0.0.1:11434",
            "--live-llm-timeout-seconds",
            "9",
            "--live-llm-max-tokens",
            "77",
            "--answer-preview-limit",
            "1000",
            "--json",
        ],
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    request = service.request
    assert request is not None
    context = request.metadata["evidence_summary_answer_context"]
    request_text = json.dumps(context, ensure_ascii=False, sort_keys=True)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["product_path"] == EXTERNAL_READONLY_ASK_PRODUCT_PATH
    assert payload["product_response_summary"]["entry_kind"] == "external_readonly_ask"
    assert payload["product_response_summary"]["llm_call_enabled"] is False
    assert payload["product_response_summary"]["refs_only"] is True
    assert payload["answer"].startswith("该资料可作为后续审查引用")
    assert payload["failure_explanation"] is None
    assert payload["recovery_hints"] == []
    assert payload["evidence_refs"] == [
        {
            "ref": "evidence://external-readonly/cli-fetch/ask.json",
            "kind": "external_readonly_evidence",
            "purpose": "answer_context",
        }
    ]
    assert payload["external_readonly_fetch_performed"] is False
    assert payload["llm_call_allowed"] is True
    assert payload["llm_call_attempted"] is True
    assert payload["llm_runtime_call_performed"] is True
    assert factory.captured["config_selection"].environment == "local"
    assert factory.captured["live_llm_options"].timeout_seconds == 9
    assert factory.captured["live_llm_options"].max_tokens == 77
    assert request.metadata["interaction_mode"] == (
        "evidence_summary_answer_generation"
    )
    assert request.metadata["service_ref"] == (
        "service://cognition-cli/external-readonly-ask/generation"
    )
    assert "smoke_only" not in request.metadata
    assert context["user_question"] == "这条资料是否可用于后续审查？"
    assert context["summary_facts"] == [
        "The reference is suitable for follow-up review."
    ]
    assert "Write only the final user-facing natural language answer." in context[
        "answer_constraints"
    ]
    assert any("visible reasoning" in item for item in context["answer_constraints"])
    assert "evidence://external-readonly/cli-fetch/ask.json" in request_text
    assert "sanitized reference" not in request_text
    assert "sanitized_excerpt_preview" not in output
    assert "ProductGatewayResponse" not in output


def test_external_readonly_ask_invokes_explicit_deepseek_profile_without_ollama_gate(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-deepseek.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "placeholder-env-value")
    service = _FakeLlmService(
        "这个网页主要说明资料可用于后续审查，证据见 evidence://external-readonly/cli-fetch/ask-deepseek.json。"
    )
    factory = _FakeFactory(service)

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这个网页主要说明了什么？",
            "--model-name",
            "deepseek/deepseek-v4-flash",
            "--llm-provider-profile-ref",
            "deepseek_gated",
            "--llm-model-profile-ref",
            "deepseek_v4_flash_external",
            "--llm-output-governance-profile-ref",
            "adk_no_output_schema_candidate",
            "--request-live-llm",
            "--allow-live-llm",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/deepseek-unit",
            "--network-gate-open",
            "--operator-approved",
            "--audit-ref",
            "audit://external-readonly-ask/deepseek-unit",
            "--json",
        ],
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    payload = json.loads(capsys.readouterr().out)
    request = service.request

    assert request is not None
    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["model_name"] == "deepseek/deepseek-v4-flash"
    assert request.route_facts.metadata["backend_provider"] == "deepseek"
    assert request.route_facts.metadata["route_kind"] == (
        "adk_litellm_openai_compatible"
    )
    assert factory.captured["live_llm_options"].provider_profile_ref == (
        "deepseek_gated"
    )
    assert factory.captured["live_llm_options"].model_profile_ref == (
        "deepseek_v4_flash_external"
    )
    assert factory.captured[
        "live_llm_options"
    ].output_governance_profile_ref == "adk_no_output_schema_candidate"
    assert factory.captured["live_llm_options"].network_gate_open is True
    assert factory.captured["live_llm_options"].operator_approved is True
    assert factory.captured["live_llm_options"].audit_ref == (
        "audit://external-readonly-ask/deepseek-unit"
    )


def test_external_readonly_ask_invokes_deepseek_model_alias_without_ollama_gate(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-deepseek-alias.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "placeholder-env-value")
    service = _FakeLlmService(
        "这个网页主要说明资料可用于后续审查，证据见 evidence://external-readonly/cli-fetch/ask-deepseek-alias.json。"
    )
    factory = _FakeFactory(service)

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这个网页主要说明了什么？",
            "--model",
            "deepseek",
            "--request-live-llm",
            "--allow-live-llm",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/deepseek-alias-unit",
            "--network-gate-open",
            "--operator-approved",
            "--audit-ref",
            "audit://external-readonly-ask/deepseek-alias-unit",
            "--json",
        ],
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    payload = json.loads(capsys.readouterr().out)
    request = service.request

    assert request is not None
    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["model_name"] == "deepseek/deepseek-v4-flash"
    assert request.route_facts.metadata["backend_provider"] == "deepseek"
    assert request.route_facts.metadata["route_kind"] == (
        "adk_litellm_openai_compatible"
    )
    assert factory.captured["live_llm_options"].provider_profile_ref == (
        "deepseek_gated"
    )
    assert factory.captured["live_llm_options"].model_profile_ref == (
        "deepseek_v4_flash_external"
    )
    assert factory.captured[
        "live_llm_options"
    ].output_governance_profile_ref == "adk_no_output_schema_candidate"
    assert factory.captured["live_llm_options"].network_gate_open is True
    assert factory.captured["live_llm_options"].operator_approved is True


def test_external_readonly_ask_deepseek_model_alias_requires_provider_key(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-deepseek-key.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这个网页主要说明了什么？",
            "--model",
            "deepseek",
            "--request-live-llm",
            "--allow-live-llm",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/deepseek-key",
            "--network-gate-open",
            "--operator-approved",
            "--audit-ref",
            "audit://external-readonly-ask/deepseek-key",
            "--json",
        ],
        external_readonly_ask_llm_invocation_service_factory=_RaisingFactory(),
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == ["deepseek_provider_key_required"]
    assert payload["llm_call_attempted"] is False
    assert payload["failure_explanation"] == (
        "DeepSeek key 尚未通过安全输入或凭据检查，未进入模型回答。"
    )


def test_external_readonly_ask_prompt_provider_key_uses_current_process_only(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-deepseek-prompt.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(ask_module, "_provider_key_prompt_available", lambda: True)
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_secret",
        lambda: "placeholder-process-value",
    )
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_persistence_choice",
        lambda: "once",
    )
    service = _FakeLlmService(
        "这个网页主要说明资料可用于后续审查，证据见 evidence://external-readonly/cli-fetch/ask-deepseek-prompt.json。"
    )
    factory = _EnvCheckingFactory(service, expected_key="placeholder-process-value")

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这个网页主要说明了什么？",
            "--model",
            "deepseek",
            "--request-live-llm",
            "--allow-live-llm",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/deepseek-prompt",
            "--network-gate-open",
            "--operator-approved",
            "--audit-ref",
            "audit://external-readonly-ask/deepseek-prompt",
            "--prompt-provider-key",
        ],
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert service.request is not None
    assert "placeholder-process-value" not in captured.out
    assert "placeholder-process-value" not in captured.err
    assert os.getenv("DEEPSEEK_API_KEY") is None
    assert factory.captured[
        "live_llm_options"
    ].metadata["provider_key_supplied_by_prompt"] is True
    assert factory.captured[
        "live_llm_options"
    ].metadata["provider_key_persistent_save"] is False
    assert factory.captured[
        "live_llm_options"
    ].metadata["provider_key_source"] == "prompt_once"


def test_external_readonly_ask_prompt_provider_key_stores_in_fake_store(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-deepseek-store-key.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    fake_store = _FakeCredentialStore()
    monkeypatch.setattr(ask_module, "_deepseek_credential_store", lambda: fake_store)
    monkeypatch.setattr(ask_module, "_provider_key_prompt_available", lambda: True)
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_secret",
        lambda: "placeholder-store-value",
    )
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_persistence_choice",
        lambda: "store",
    )
    service = _FakeLlmService(
        "这个网页主要说明资料可用于后续审查，证据见 evidence://external-readonly/cli-fetch/ask-deepseek-store-key.json。"
    )
    factory = _EnvCheckingFactory(service, expected_key="placeholder-store-value")

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这个网页主要说明了什么？",
            "--model",
            "deepseek",
            "--request-live-llm",
            "--allow-live-llm",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/deepseek-store-key",
            "--network-gate-open",
            "--operator-approved",
            "--audit-ref",
            "audit://external-readonly-ask/deepseek-store-key",
            "--prompt-provider-key",
        ],
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert fake_store.saved == "placeholder-store-value"
    assert "placeholder-store-value" not in captured.out
    assert "placeholder-store-value" not in captured.err
    assert os.getenv("DEEPSEEK_API_KEY") is None
    metadata = factory.captured["live_llm_options"].metadata
    assert metadata["provider_key_source"] == "prompt_store"
    assert metadata["provider_key_supplied_by_prompt"] is True
    assert metadata["provider_key_persistent_save"] is True
    assert metadata["provider_key_store_backend"] == "fake_keychain"


def test_external_readonly_ask_uses_stored_provider_key_without_prompt(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-deepseek-stored-key.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    fake_store = _FakeCredentialStore(load_value="placeholder-stored-value")
    monkeypatch.setattr(ask_module, "_deepseek_credential_store", lambda: fake_store)
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_secret",
        lambda: (_ for _ in ()).throw(AssertionError("prompt should not run")),
    )
    service = _FakeLlmService(
        "这个网页主要说明资料可用于后续审查，证据见 evidence://external-readonly/cli-fetch/ask-deepseek-stored-key.json。"
    )
    factory = _EnvCheckingFactory(service, expected_key="placeholder-stored-value")

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这个网页主要说明了什么？",
            "--model",
            "deepseek",
            "--request-live-llm",
            "--allow-live-llm",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/deepseek-stored-key",
            "--network-gate-open",
            "--operator-approved",
            "--audit-ref",
            "audit://external-readonly-ask/deepseek-stored-key",
            "--use-stored-provider-key",
            "--json",
        ],
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert "placeholder-stored-value" not in json.dumps(payload, ensure_ascii=False)
    assert os.getenv("DEEPSEEK_API_KEY") is None
    metadata = factory.captured["live_llm_options"].metadata
    assert metadata["provider_key_source"] == "stored_keychain"
    assert metadata["provider_key_loaded_from_store"] is True
    assert metadata["provider_key_supplied_by_prompt"] is False
    assert metadata["provider_key_persistent_save"] is True


def test_external_readonly_ask_stored_provider_key_blocks_missing(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-deepseek-stored-missing.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    fake_store = _FakeCredentialStore(load_value=None)
    monkeypatch.setattr(ask_module, "_deepseek_credential_store", lambda: fake_store)
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_secret",
        lambda: (_ for _ in ()).throw(AssertionError("prompt should not run")),
    )

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这个网页主要说明了什么？",
            "--model",
            "deepseek",
            "--request-live-llm",
            "--allow-live-llm",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/deepseek-stored-missing",
            "--network-gate-open",
            "--operator-approved",
            "--audit-ref",
            "audit://external-readonly-ask/deepseek-stored-missing",
            "--use-stored-provider-key",
            "--json",
        ],
        external_readonly_ask_llm_invocation_service_factory=_RaisingFactory(),
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == [
        "provider_key_stored_credential_not_found"
    ]
    assert payload["llm_call_attempted"] is False


def test_external_readonly_ask_prompt_provider_key_blocks_json_output(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-deepseek-json-key.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_secret",
        lambda: (_ for _ in ()).throw(AssertionError("prompt should not run")),
    )

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这个网页主要说明了什么？",
            "--model",
            "deepseek",
            "--request-live-llm",
            "--allow-live-llm",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/deepseek-json-key",
            "--network-gate-open",
            "--operator-approved",
            "--audit-ref",
            "audit://external-readonly-ask/deepseek-json-key",
            "--prompt-provider-key",
            "--json",
        ],
        external_readonly_ask_llm_invocation_service_factory=_RaisingFactory(),
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == [
        "provider_key_prompt_unavailable_for_json_output"
    ]
    assert payload["llm_call_attempted"] is False


def test_external_readonly_ask_prompt_provider_key_blocks_non_interactive(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-deepseek-noninteractive.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(ask_module, "_provider_key_prompt_available", lambda: False)
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_secret",
        lambda: (_ for _ in ()).throw(AssertionError("prompt should not run")),
    )

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这个网页主要说明了什么？",
            "--model",
            "deepseek",
            "--request-live-llm",
            "--allow-live-llm",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/deepseek-noninteractive",
            "--network-gate-open",
            "--operator-approved",
            "--audit-ref",
            "audit://external-readonly-ask/deepseek-noninteractive",
            "--prompt-provider-key",
        ],
        external_readonly_ask_llm_invocation_service_factory=_RaisingFactory(),
    )

    output = capsys.readouterr().out

    assert exit_code == 3
    assert "status: blocked" in output
    assert "provider_key_prompt_requires_interactive_terminal" in output
    assert "llm_call_attempted: false" in output


def test_external_readonly_ask_prompt_provider_key_blocks_unavailable_store(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-deepseek-store-unavailable.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    fake_store = _FakeCredentialStore(save_status="unavailable")
    monkeypatch.setattr(ask_module, "_deepseek_credential_store", lambda: fake_store)
    monkeypatch.setattr(ask_module, "_provider_key_prompt_available", lambda: True)
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_secret",
        lambda: "placeholder-store-value",
    )
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_persistence_choice",
        lambda: "store",
    )

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这个网页主要说明了什么？",
            "--model",
            "deepseek",
            "--request-live-llm",
            "--allow-live-llm",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/deepseek-store-unavailable",
            "--network-gate-open",
            "--operator-approved",
            "--audit-ref",
            "audit://external-readonly-ask/deepseek-store-unavailable",
            "--prompt-provider-key",
        ],
        external_readonly_ask_llm_invocation_service_factory=_RaisingFactory(),
    )

    output = capsys.readouterr().out

    assert exit_code == 3
    assert "provider_key_store_unavailable" in output
    assert "placeholder-store-value" not in output
    assert os.getenv("DEEPSEEK_API_KEY") is None


def test_external_readonly_ask_invokes_gemma4_model_alias_as_local_ollama(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-gemma4-alias.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    service = _FakeLlmService(
        "该资料可作为后续审查引用，证据见 evidence://external-readonly/cli-fetch/ask-gemma4-alias.json。"
    )
    factory = _FakeFactory(service)

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这条资料是否可用于后续审查？",
            "--model",
            "gemma4",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/gemma4-alias-unit",
            "--ollama-api-base",
            "http://127.0.0.1:11434",
            "--json",
        ],
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    payload = json.loads(capsys.readouterr().out)
    request = service.request

    assert request is not None
    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["model_name"] == "ollama/gemma4-pro:latest"
    assert request.route_facts.metadata["backend_provider"] == "ollama"
    assert request.route_facts.metadata["route_kind"] == "adk_litellm"
    assert factory.captured["live_llm_options"].provider_profile_ref == "local_ollama"
    assert factory.captured["live_llm_options"].model_profile_ref == (
        "gemma4_pro_local"
    )
    assert factory.captured[
        "live_llm_options"
    ].output_governance_profile_ref == "direct_controlled_live"


def test_external_readonly_ask_model_alias_conflict_blocks_before_provider_call(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-alias-conflict.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这个网页主要说明了什么？",
            "--model",
            "deepseek",
            "--model-name",
            "deepseek/deepseek-v4-flash",
            "--json",
        ],
        external_readonly_ask_llm_invocation_service_factory=_RaisingFactory(),
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == [
        "model_alias_conflicts_with_explicit_model_options"
    ]
    assert payload["llm_call_attempted"] is False
    assert payload["failure_explanation"] == (
        "模型别名参数未通过预检，尚未进入模型回答。"
    )


def test_external_readonly_ask_deepseek_alias_keeps_external_gates_required(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-deepseek-gates.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这个网页主要说明了什么？",
            "--model",
            "deepseek",
            "--request-live-llm",
            "--allow-live-llm",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/deepseek-alias-gates",
            "--json",
        ],
        external_readonly_ask_llm_invocation_service_factory=_RaisingFactory(),
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == [
        "external_llm_network_gate_open_required",
        "external_llm_operator_approved_required",
        "external_llm_audit_ref_required",
    ]
    assert payload["llm_call_attempted"] is False


def test_external_readonly_ask_can_fetch_then_answer_with_fake_transport(
    capsys: Any,
) -> None:
    service = _FakeLlmService(
        "这个页面说明 Example Domain 用于文档示例，证据见 evidence://external-readonly/item/cli-ask。"
    )
    factory = _FakeFactory(service)
    captured_fetch: dict[str, Any] = {}
    args = _parse_ask_args(
        "--source-url",
        "https://example.com/reference",
        "--confirm-external-readonly-fetch",
        REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION,
        "--question",
        "这个网页主要说明了什么？",
        "--operator-approved",
        "--approval-ref",
        "approval://external-readonly/cli-ask",
        "--runtime-fetch-approval-ref",
        "approval://external-readonly/runtime-fetch/cli-ask",
        "--audit-ref",
        "audit://external-readonly/cli-ask",
        "--network-gate-open",
        "--allow-runtime-fetch",
        "--request-live-llm",
        "--request-ollama",
        "--allow-live-llm",
        "--allow-ollama",
        "--live-llm-approval-ref",
        "approval://external-readonly-ask/unit",
        "--ollama-api-base",
        "http://127.0.0.1:11434",
        "--json",
    )

    def fake_fetch(gateway_input: Any) -> ExternalReadonlyFetchGatewayExecutionResult:
        captured_fetch.update(dict(gateway_input))
        return _fake_fetch_success_execution()

    exit_code = external_readonly_ask_command(
        args,
        fetch_executor=fake_fetch,
        llm_invocation_service_factory=factory,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured_fetch["allow_runtime_fetch"] is True
    assert captured_fetch["use_live_transport"] is False
    assert captured_fetch["network_gate"]["status"] == "passed"
    assert payload["status"] == "success"
    assert payload["source_url_present"] is True
    assert payload["external_readonly_fetch_performed"] is True
    assert payload["external_network_call_performed"] is False
    assert payload["evidence_ref_count"] == 1
    assert service.request is not None
    context = service.request.metadata["evidence_summary_answer_context"]
    assert context["user_question"] == "这个网页主要说明了什么？"
    assert context["summary_facts"] == ["Example Domain is for documentation examples."]


def test_external_readonly_ask_guided_deepseek_url_uses_stored_key(
    monkeypatch: Any,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(ask_module, "_guided_prompt_available", lambda: True)
    monkeypatch.setattr(
        ask_module,
        "_read_guided_source",
        lambda: "https://example.com/reference",
    )
    monkeypatch.setattr(
        ask_module,
        "_read_guided_question",
        lambda: "这个网页主要说明了什么？",
    )
    monkeypatch.setattr(ask_module, "_read_guided_model_alias", lambda: "deepseek")
    monkeypatch.setattr(ask_module, "_guided_confirm", lambda _prompt: True)
    monkeypatch.setattr(ask_module, "_read_guided_provider_key_mode", lambda: "stored")
    fake_store = _FakeCredentialStore(load_value="placeholder-guided-stored-value")
    monkeypatch.setattr(ask_module, "_deepseek_credential_store", lambda: fake_store)
    service = _FakeLlmService(
        "这个页面说明 Example Domain 用于文档示例，证据见 evidence://external-readonly/item/cli-ask。"
    )
    factory = _EnvCheckingFactory(
        service,
        expected_key="placeholder-guided-stored-value",
    )
    captured_fetch: dict[str, Any] = {}
    args = _parse_ask_args("--guided")

    def fake_fetch(gateway_input: Any) -> ExternalReadonlyFetchGatewayExecutionResult:
        captured_fetch.update(dict(gateway_input))
        return _fake_fetch_success_execution()

    exit_code, payload = ask_module.build_external_readonly_ask_cli_output(
        args,
        fetch_executor=fake_fetch,
        llm_invocation_service_factory=factory,
    )

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["source_url"] == "https://example.com/reference"
    assert captured_fetch["network_gate"]["status"] == "passed"
    assert captured_fetch["operator_approved"] is True
    assert captured_fetch["allow_runtime_fetch"] is True
    assert captured_fetch["use_live_transport"] is True
    assert captured_fetch["approval_ref"] == "approval://external-readonly-ask/guided"
    assert captured_fetch["runtime_fetch_approval_ref"] == (
        "approval://external-readonly-ask/guided-runtime-fetch"
    )
    assert captured_fetch["audit_ref"] == "audit://external-readonly-ask/guided"
    assert factory.captured["live_llm_options"].network_gate_open is True
    assert factory.captured["live_llm_options"].operator_approved is True
    assert factory.captured["live_llm_options"].approval_ref == (
        "approval://external-readonly-ask/guided-live-llm"
    )
    assert factory.captured["live_llm_options"].audit_ref == (
        "audit://external-readonly-ask/guided"
    )
    assert factory.captured[
        "live_llm_options"
    ].metadata["provider_key_source"] == "stored_keychain"
    assert "placeholder-guided-stored-value" not in json.dumps(
        payload,
        ensure_ascii=False,
    )
    assert os.getenv("DEEPSEEK_API_KEY") is None


def test_external_readonly_ask_guided_deepseek_archive_prompts_key_once(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-guided-deepseek-once.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(ask_module, "_guided_prompt_available", lambda: True)
    monkeypatch.setattr(
        ask_module,
        "_read_guided_question",
        lambda: "这个网页主要说明了什么？",
    )
    monkeypatch.setattr(ask_module, "_read_guided_model_alias", lambda: "deepseek")
    monkeypatch.setattr(ask_module, "_guided_confirm", lambda _prompt: True)
    monkeypatch.setattr(ask_module, "_read_guided_provider_key_mode", lambda: "prompt")
    monkeypatch.setattr(ask_module, "_provider_key_prompt_available", lambda: True)
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_secret",
        lambda: "placeholder-guided-once-value",
    )
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_persistence_choice",
        lambda: "once",
    )
    service = _FakeLlmService(
        "这个网页主要说明资料可用于后续审查，证据见 evidence://external-readonly/cli-fetch/ask-guided-deepseek-once.json。"
    )
    factory = _EnvCheckingFactory(
        service,
        expected_key="placeholder-guided-once-value",
    )
    args = _parse_ask_args("--guided", "--evidence-path", evidence_path)

    exit_code, payload = ask_module.build_external_readonly_ask_cli_output(
        args,
        llm_invocation_service_factory=factory,
    )

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["external_readonly_fetch_performed"] is False
    assert factory.captured["live_llm_options"].network_gate_open is True
    assert factory.captured["live_llm_options"].operator_approved is True
    assert factory.captured["live_llm_options"].metadata["provider_key_source"] == (
        "prompt_once"
    )
    assert "placeholder-guided-once-value" not in json.dumps(
        payload,
        ensure_ascii=False,
    )
    assert os.getenv("DEEPSEEK_API_KEY") is None


def test_external_readonly_ask_guided_deepseek_url_stores_key_in_fake_store(
    monkeypatch: Any,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(ask_module, "_guided_prompt_available", lambda: True)
    monkeypatch.setattr(
        ask_module,
        "_read_guided_source",
        lambda: "https://example.com/reference",
    )
    monkeypatch.setattr(
        ask_module,
        "_read_guided_question",
        lambda: "这个网页主要说明了什么？",
    )
    monkeypatch.setattr(ask_module, "_read_guided_model_alias", lambda: "deepseek")
    monkeypatch.setattr(ask_module, "_guided_confirm", lambda _prompt: True)
    monkeypatch.setattr(ask_module, "_read_guided_provider_key_mode", lambda: "prompt")
    monkeypatch.setattr(ask_module, "_provider_key_prompt_available", lambda: True)
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_secret",
        lambda: "placeholder-guided-store-value",
    )
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_persistence_choice",
        lambda: "store",
    )
    fake_store = _FakeCredentialStore()
    monkeypatch.setattr(ask_module, "_deepseek_credential_store", lambda: fake_store)
    service = _FakeLlmService(
        "这个页面说明 Example Domain 用于文档示例，证据见 evidence://external-readonly/item/cli-ask。"
    )
    factory = _EnvCheckingFactory(
        service,
        expected_key="placeholder-guided-store-value",
    )
    captured_fetch: dict[str, Any] = {}
    args = _parse_ask_args("--guided")

    def fake_fetch(gateway_input: Any) -> ExternalReadonlyFetchGatewayExecutionResult:
        captured_fetch.update(dict(gateway_input))
        return _fake_fetch_success_execution()

    exit_code, payload = ask_module.build_external_readonly_ask_cli_output(
        args,
        fetch_executor=fake_fetch,
        llm_invocation_service_factory=factory,
    )

    assert exit_code == 0
    assert payload["status"] == "success"
    assert fake_store.saved == "placeholder-guided-store-value"
    assert captured_fetch["network_gate"]["status"] == "passed"
    assert factory.captured["live_llm_options"].metadata["provider_key_source"] == (
        "prompt_store"
    )
    assert factory.captured[
        "live_llm_options"
    ].metadata["provider_key_persistent_save"] is True
    assert "placeholder-guided-store-value" not in json.dumps(
        payload,
        ensure_ascii=False,
    )
    assert os.getenv("DEEPSEEK_API_KEY") is None


def test_external_readonly_ask_guided_deepseek_stored_key_missing_blocks(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    evidence_path = (
        "outputs/external-readonly/cli-fetch/ask-guided-deepseek-stored-missing.json"
    )
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(ask_module, "_guided_prompt_available", lambda: True)
    monkeypatch.setattr(
        ask_module,
        "_read_guided_question",
        lambda: "这个网页主要说明了什么？",
    )
    monkeypatch.setattr(ask_module, "_read_guided_model_alias", lambda: "deepseek")
    monkeypatch.setattr(ask_module, "_guided_confirm", lambda _prompt: True)
    monkeypatch.setattr(ask_module, "_read_guided_provider_key_mode", lambda: "stored")
    fake_store = _FakeCredentialStore(load_value=None)
    monkeypatch.setattr(ask_module, "_deepseek_credential_store", lambda: fake_store)
    args = _parse_ask_args("--guided", "--evidence-path", evidence_path)

    exit_code, payload = ask_module.build_external_readonly_ask_cli_output(
        args,
        llm_invocation_service_factory=_RaisingFactory(),
    )

    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == [
        "provider_key_stored_credential_not_found"
    ]
    assert payload["llm_call_attempted"] is False
    assert payload["recovery_hints"]


def test_external_readonly_ask_guided_deepseek_store_unavailable_blocks(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    evidence_path = (
        "outputs/external-readonly/cli-fetch/ask-guided-deepseek-store-unavailable.json"
    )
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(ask_module, "_guided_prompt_available", lambda: True)
    monkeypatch.setattr(
        ask_module,
        "_read_guided_question",
        lambda: "这个网页主要说明了什么？",
    )
    monkeypatch.setattr(ask_module, "_read_guided_model_alias", lambda: "deepseek")
    monkeypatch.setattr(ask_module, "_guided_confirm", lambda _prompt: True)
    monkeypatch.setattr(ask_module, "_read_guided_provider_key_mode", lambda: "prompt")
    monkeypatch.setattr(ask_module, "_provider_key_prompt_available", lambda: True)
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_secret",
        lambda: "placeholder-guided-unavailable-value",
    )
    monkeypatch.setattr(
        ask_module,
        "_read_provider_key_persistence_choice",
        lambda: "store",
    )
    fake_store = _FakeCredentialStore(save_status="unavailable")
    monkeypatch.setattr(ask_module, "_deepseek_credential_store", lambda: fake_store)
    args = _parse_ask_args("--guided", "--evidence-path", evidence_path)

    exit_code, payload = ask_module.build_external_readonly_ask_cli_output(
        args,
        llm_invocation_service_factory=_RaisingFactory(),
    )

    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == ["provider_key_store_unavailable"]
    assert "placeholder-guided-unavailable-value" not in json.dumps(
        payload,
        ensure_ascii=False,
    )
    assert os.getenv("DEEPSEEK_API_KEY") is None


def test_external_readonly_ask_guided_gemma4_url_fetches_and_answers(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(ask_module, "_guided_prompt_available", lambda: True)
    monkeypatch.setattr(
        ask_module,
        "_read_guided_source",
        lambda: "https://example.com/reference",
    )
    monkeypatch.setattr(
        ask_module,
        "_read_guided_question",
        lambda: "这个网页主要说明了什么？",
    )
    monkeypatch.setattr(ask_module, "_read_guided_model_alias", lambda: "gemma4")
    monkeypatch.setattr(ask_module, "_guided_confirm", lambda _prompt: True)
    service = _FakeLlmService(
        "这个页面说明 Example Domain 用于文档示例，证据见 evidence://external-readonly/item/cli-ask。"
    )
    factory = _FakeFactory(service)
    captured_fetch: dict[str, Any] = {}
    args = _parse_ask_args("--guided")

    def fake_fetch(gateway_input: Any) -> ExternalReadonlyFetchGatewayExecutionResult:
        captured_fetch.update(dict(gateway_input))
        return _fake_fetch_success_execution()

    exit_code, payload = ask_module.build_external_readonly_ask_cli_output(
        args,
        fetch_executor=fake_fetch,
        llm_invocation_service_factory=factory,
    )

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["model_name"] == "ollama/gemma4-pro:latest"
    assert captured_fetch["network_gate"]["status"] == "passed"
    assert captured_fetch["use_live_transport"] is True
    assert factory.captured["live_llm_options"].provider_profile_ref == "local_ollama"
    assert factory.captured["live_llm_options"].model_profile_ref == (
        "gemma4_pro_local"
    )
    assert factory.captured[
        "live_llm_options"
    ].output_governance_profile_ref == "direct_controlled_live"


def test_external_readonly_ask_guided_provider_resolution_failure_is_sanitized(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-guided-provider-failure.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ask_module, "_guided_prompt_available", lambda: True)
    monkeypatch.setattr(
        ask_module,
        "_read_guided_question",
        lambda: "这条资料是否可用于后续审查？",
    )
    monkeypatch.setattr(ask_module, "_read_guided_model_alias", lambda: "gemma4")
    monkeypatch.setattr(ask_module, "_guided_confirm", lambda _prompt: True)
    args = _parse_ask_args("--guided", "--evidence-path", evidence_path)

    exit_code, payload = ask_module.build_external_readonly_ask_cli_output(
        args,
        llm_invocation_service_factory=_RaisingFactory(),
    )

    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == [
        "external_readonly_ask_llm_provider_resolution_failed"
    ]
    assert payload["llm_call_attempted"] is False
    assert payload["warnings"] == ["external_readonly_ask_llm_provider_exception"]


def test_external_readonly_ask_guided_gemma4_archive_sets_local_gates(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-guided-gemma4.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ask_module, "_guided_prompt_available", lambda: True)
    monkeypatch.setattr(
        ask_module,
        "_read_guided_question",
        lambda: "这条资料是否可用于后续审查？",
    )
    monkeypatch.setattr(ask_module, "_read_guided_model_alias", lambda: "gemma4")
    monkeypatch.setattr(ask_module, "_guided_confirm", lambda _prompt: True)
    service = _FakeLlmService(
        "该资料可作为后续审查引用，证据见 evidence://external-readonly/cli-fetch/ask-guided-gemma4.json。"
    )
    factory = _FakeFactory(service)
    args = _parse_ask_args("--guided", "--evidence-path", evidence_path)

    exit_code, payload = ask_module.build_external_readonly_ask_cli_output(
        args,
        llm_invocation_service_factory=factory,
    )

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["model_name"] == "ollama/gemma4-pro:latest"
    assert payload["external_readonly_fetch_performed"] is False
    assert factory.captured["live_llm_options"].provider_profile_ref == "local_ollama"
    assert factory.captured["live_llm_options"].network_gate_open is False
    assert factory.captured["live_llm_options"].operator_approved is False
    assert service.request is not None
    assert service.request.metadata["evidence_summary_answer_context"][
        "user_question"
    ] == "这条资料是否可用于后续审查？"


def test_external_readonly_ask_guided_blocks_json_without_prompt(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    monkeypatch.setattr(
        ask_module,
        "_read_guided_source",
        lambda: (_ for _ in ()).throw(AssertionError("guided prompt should not run")),
    )

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--guided",
            "--json",
        ],
        external_readonly_ask_llm_invocation_service_factory=_RaisingFactory(),
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == [
        "external_readonly_ask_guided_unavailable_for_json_output"
    ]
    assert payload["llm_call_attempted"] is False


def test_external_readonly_ask_guided_blocks_non_interactive(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    monkeypatch.setattr(ask_module, "_guided_prompt_available", lambda: False)
    monkeypatch.setattr(
        ask_module,
        "_read_guided_source",
        lambda: (_ for _ in ()).throw(AssertionError("guided prompt should not run")),
    )

    exit_code = cognition.run_cli(
        ["external-readonly", "ask", "--guided"],
        external_readonly_ask_llm_invocation_service_factory=_RaisingFactory(),
    )

    output = capsys.readouterr().out

    assert exit_code == 3
    assert "status: blocked" in output
    assert "external_readonly_ask_guided_requires_interactive_terminal" in output
    assert "llm_call_attempted: false" in output


def test_external_readonly_ask_blocks_legacy_archive_without_provider_call(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/legacy.json"
    _write_external_readonly_archive(tmp_path, evidence_path, governed_facts=False)
    monkeypatch.chdir(tmp_path)

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "请基于证据回答",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/unit",
            "--json",
        ],
        external_readonly_ask_llm_invocation_service_factory=_RaisingFactory(),
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["llm_call_attempted"] is False
    assert payload["evidence_summary_answer_result"]["status"] == "blocked"
    assert payload["blocking_reasons"] == [
        "external_readonly_governed_summary_facts_required"
    ]
    assert payload["failure_explanation"] == (
        "本次请求被治理条件拦截，未形成可返回答案。"
    )


def test_external_readonly_ask_explains_quality_violation_in_json(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-quality.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    service = _FakeLlmService('{ "thought": "The user wants a concise answer."')
    factory = _FakeFactory(service)

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这条资料是否可用于后续审查？",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/unit",
            "--json",
        ],
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 4
    assert payload["status"] == "failed"
    assert payload["answer"] is None
    assert payload["blocking_reasons"] == ["llm_answer_quality_contract_violation"]
    assert payload["failure_explanation"] == (
        "模型输出未通过回答质量检查，因此没有作为成功答案返回。"
    )
    assert payload["recovery_hints"] == [
        "请重试一次，或换用更稳定的本地模型。",
        "请缩短问题，并明确要求只基于证据给出最终答案。",
        "若持续失败，请保留 request_id 供后续 prompt/profile 修补。",
    ]
    assert payload["evidence_refs"][0]["ref"] == (
        "evidence://external-readonly/cli-fetch/ask-quality.json"
    )
    assert payload["additional_refs"][0]["kind"] == "governed_evidence_digest"


def test_external_readonly_ask_quality_violation_text_output_has_hints_and_refs(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/ask-quality-text.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    service = _FakeLlmService('{ "thought": "The user wants a concise answer."')
    factory = _FakeFactory(service)

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "ask",
            "--evidence-path",
            evidence_path,
            "--question",
            "这条资料是否可用于后续审查？",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://external-readonly-ask/unit",
        ],
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 4
    assert "status: failed" in output
    assert "failure_explanation: 模型输出未通过回答质量检查" in output
    assert "recovery_hints:" in output
    assert "请重试一次" in output
    assert "evidence_refs:" in output
    assert "evidence://external-readonly/cli-fetch/ask-quality-text.json" in output
    assert "additional_refs:" in output
    assert "governed-evidence-digest://" in output
    assert "sanitized_excerpt_preview" not in output
    assert "ProductGatewayResponse" not in output


def test_external_readonly_ask_cli_keeps_product_boundary() -> None:
    source = ASK_SOURCE.read_text(encoding="utf-8")

    assert "execute_external_readonly_ask_gateway_request" in source
    assert "execute_external_readonly_fetch_gateway_request" in source
    assert "runtime_container" not in source
    assert "from composition" not in source
    assert "product_runtime_assembly" not in source
    assert "ProductGatewayResponse" not in source
    assert "sanitized_excerpt_preview" not in source


def test_deepseek_keychain_store_does_not_shell_out_with_key() -> None:
    source = KEYCHAIN_SOURCE.read_text(encoding="utf-8")

    assert "ctypes.CDLL" in source
    assert "subprocess" not in source
    assert "os.system" not in source
    assert "security add-generic-password" not in source
    assert "DEEPSEEK_API_KEY" not in source


class _FakeCredentialResult:
    def __init__(
        self,
        *,
        status: str,
        backend: str = "fake_keychain",
        blocking_reason: str | None = None,
        secret_value: str | None = None,
    ) -> None:
        self.status = status
        self.backend = backend
        self.blocking_reason = blocking_reason
        self.secret_value = secret_value


class _FakeCredentialStore:
    backend = "fake_keychain"

    def __init__(
        self,
        *,
        load_value: str | None = None,
        save_status: str = "success",
    ) -> None:
        self.load_value = load_value
        self.save_status = save_status
        self.saved: str | None = None

    def load_api_key(self) -> _FakeCredentialResult:
        if self.load_value is None:
            return _FakeCredentialResult(
                status="not_found",
                backend=self.backend,
                blocking_reason="provider_key_stored_credential_not_found",
            )
        return _FakeCredentialResult(
            status="success",
            backend=self.backend,
            secret_value=self.load_value,
        )

    def save_api_key(self, secret_value: str) -> _FakeCredentialResult:
        if self.save_status == "success":
            self.saved = secret_value
            return _FakeCredentialResult(status="success", backend=self.backend)
        return _FakeCredentialResult(
            status=self.save_status,
            backend=self.backend,
            blocking_reason="provider_key_store_unavailable",
        )


class _FakeFactory:
    def __init__(self, service: "_FakeLlmService") -> None:
        self.service = service
        self.captured: dict[str, Any] = {}

    def resolve(self, **kwargs: Any) -> GovernedLlmInvocationServiceResolution:
        self.captured = dict(kwargs)
        return GovernedLlmInvocationServiceResolution(service=self.service)


class _EnvCheckingFactory(_FakeFactory):
    def __init__(self, service: "_FakeLlmService", *, expected_key: str) -> None:
        super().__init__(service)
        self.expected_key = expected_key

    def resolve(self, **kwargs: Any) -> GovernedLlmInvocationServiceResolution:
        assert os.getenv("DEEPSEEK_API_KEY") == self.expected_key
        return super().resolve(**kwargs)


class _RaisingFactory:
    def resolve(self, **_: Any) -> GovernedLlmInvocationServiceResolution:
        raise AssertionError("provider factory should not be called")


class _FakeLlmService:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.request: LlmInvocationRequest | None = None

    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        self.request = request
        return LlmInvocationResult(
            request_id=request.request_id,
            route_facts=request.route_facts,
            governance_precondition=request.governance_precondition,
            call_attempted=True,
            call_allowed=True,
            runtime_call_performed=True,
            success=True,
            response_non_empty=True,
            sanitized_response_length=len(self.answer),
            sanitized_response_preview=self.answer[:120],
            latency_ms=3,
            failure_type=None,
            metadata={"sanitized_response_display": self.answer},
        )


def _parse_ask_args(*items: str) -> Namespace:
    return build_parser().parse_args(["external-readonly", "ask", *items])


def _fake_fetch_success_execution() -> ExternalReadonlyFetchGatewayExecutionResult:
    fact = "Example Domain is for documentation examples."
    envelope = ExternalReadonlyEvidenceEnvelope(
        envelope_ref="evidence://external-readonly/envelope/cli-ask",
        request_ref="external-readonly-ask-request://cli/ask/fetch",
        status="valid",
        allowed_for_model_context=True,
        model_context_items=(
            {
                "citation_index": 1,
                "evidence_ref": "evidence://external-readonly/item/cli-ask",
                "source_url": "https://example.com/reference",
                "source_title": None,
                "retrieved_at": "2026-05-16T00:00:00+00:00",
                "item_type": "fetched_excerpt",
                "sanitized_excerpt": fact,
                "content_hash": hashlib.sha256(fact.encode()).hexdigest(),
            },
        ),
        evidence_refs=("evidence://external-readonly/item/cli-ask",),
        source_urls=("https://example.com/reference",),
        total_excerpt_chars=len(fact),
    )
    runtime_result = ExternalReadonlyUrlFetchResult(
        status="completed",
        request_ref="external-readonly-ask-request://cli/ask/fetch",
        source_url="https://example.com/reference",
        envelope_ref="evidence://external-readonly/envelope/cli-ask",
        allowed_for_model_context=True,
        envelope=envelope,
        transport_called=True,
        runtime_fetch_performed=True,
        external_network_call_performed=False,
        tool_execution_performed=False,
    )
    response = ProductGatewayResponse(
        request_id="external-readonly-ask-request://cli/ask/fetch",
        entry_kind=ProductGatewayEntryKind.EXTERNAL_READONLY_FETCH,
        status=ProductGatewayStatus.SUCCESS,
        exit_code=0,
        evidence_refs=[
            ProductGatewayRef(
                ref="evidence://external-readonly/item/cli-ask",
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


def _write_external_readonly_archive(
    root: Path,
    evidence_path: str,
    *,
    governed_facts: bool = True,
) -> None:
    target = root / evidence_path
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            _external_readonly_archive(evidence_path, governed_facts=governed_facts),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _external_readonly_archive(
    evidence_path: str,
    *,
    governed_facts: bool = True,
) -> dict[str, object]:
    excerpt = (
        "sanitized reference with ProductGatewayResponse and "
        "observability_candidate_body marker"
    )
    evidence_ref = (
        "evidence://external-readonly/"
        f"{Path(evidence_path).relative_to('outputs/external-readonly')}"
    )
    archive: dict[str, object] = {
        "allowed_for_model_context": True,
        "blocking_reasons": [],
        "command": "cognition external-readonly fetch",
        "evidence_output_path": evidence_path,
        "evidence_ref": evidence_ref,
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
        "warnings": [],
        "writes_files": False,
    }
    if governed_facts:
        archive["governed_summary_facts"] = _governed_summary_facts(
            evidence_path,
            evidence_ref=evidence_ref,
        )
    return archive


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
                "fact_ref": "external-readonly-governed-summary-fact://unit-1",
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
