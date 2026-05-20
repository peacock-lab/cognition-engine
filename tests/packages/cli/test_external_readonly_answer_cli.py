from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from behavior_contracts.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_QUALITY_BLOCKING_REASON,
    validate_evidence_summary_answer_llm_request_boundary,
)
from cognition_cli.entrypoints import cognition
from contract_core.llm_invocation import (
    GovernedLlmInvocationServiceResolution,
    LlmInvocationRequest,
    LlmInvocationResult,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
ANSWER_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "external_readonly"
    / "answer.py"
)


def test_external_readonly_answer_help_does_not_call_provider(
    capsys: Any,
) -> None:
    exit_code = cognition.run_cli(["external-readonly", "answer", "--help"])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "--evidence-path" in output
    assert "--request-live-llm" in output
    assert "governed LLM smoke" in output


def test_external_readonly_answer_requires_explicit_live_gate_before_refs(
    capsys: Any,
) -> None:
    def raising_refs_executor(*_: Any, **__: Any) -> Any:
        raise AssertionError("refs executor should not run before live gates")

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "answer",
            "--question",
            "请基于证据回答",
            "--json",
        ],
        external_readonly_refs_application_executor=raising_refs_executor,
        external_readonly_answer_llm_invocation_service_factory=(
            _RaisingFactory()
        ),
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == [
        "evidence_output_path_required",
        "request_live_llm_required",
        "request_ollama_required",
        "allow_live_llm_required",
        "allow_ollama_required",
        "live_llm_approval_ref_required",
    ]
    assert payload["llm_call_attempted"] is False
    assert payload["external_readonly_fetch_performed"] is False
    assert payload["product_response_summary"] is None


def test_external_readonly_answer_blocks_without_provider_factory(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/provider-missing.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "answer",
            "--evidence-path",
            evidence_path,
            "--question",
            "请基于证据回答",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://external-readonly-answer/unit",
            "--json",
        ]
    )

    output = capsys.readouterr().out
    payload = json.loads(output)

    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == [
        "external_readonly_answer_llm_provider_not_injected"
    ]
    assert payload["evidence_ref_count"] == 1
    assert payload["additional_ref_count"] == 1
    assert payload["llm_call_attempted"] is False
    assert "sanitized reference" not in output
    assert "sanitized_excerpt_preview" not in output


def test_external_readonly_answer_invokes_model_with_governed_summary_facts(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/answer.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    service = _FakeLlmService(
        "证据摘要只提供了引用，需人工查看 evidence://external-readonly/cli-fetch/answer.json。"
    )
    factory = _FakeFactory(service)

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "answer",
            "--evidence-path",
            evidence_path,
            "--question",
            "请基于证据回答这条资料是否可用",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://external-readonly-answer/unit",
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
        external_readonly_answer_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    request = service.request
    assert request is not None
    context = request.metadata["evidence_summary_answer_context"]
    request_text = json.dumps(context, ensure_ascii=False, sort_keys=True)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["success"] is True
    assert payload["answer"].startswith("证据摘要只提供了引用")
    assert payload["evidence_summary_answer_result"]["status"] == "success"
    assert payload["evidence_summary_answer_result"]["evidence_refs_used"] == [
        {
            "kind": "external_readonly_evidence",
            "metadata": {},
            "purpose": "answer_context",
            "ref": "evidence://external-readonly/cli-fetch/answer.json",
        }
    ]
    assert payload["evidence_ref_count"] == 1
    assert payload["additional_ref_count"] == 1
    assert payload["external_readonly_fetch_performed"] is False
    assert payload["llm_call_allowed"] is True
    assert payload["llm_call_attempted"] is True
    assert payload["llm_runtime_call_performed"] is True
    assert factory.captured["config_context"] is None
    assert factory.captured["config_selection"].environment == "local"
    assert factory.captured["live_llm_options"].ollama_api_base == (
        "http://127.0.0.1:11434"
    )
    assert factory.captured["live_llm_options"].timeout_seconds == 9
    assert factory.captured["live_llm_options"].max_tokens == 77
    assert request.metadata["interaction_mode"] == (
        "evidence_summary_answer_generation"
    )
    assert request.prompt_ref == (
        "prompt://evidence-summary-answer/"
        "external-readonly-answer-request://cli/answer/context"
    )
    assert validate_evidence_summary_answer_llm_request_boundary(
        request.model_dump(mode="python")
    ).passed
    assert "external_readonly_answer_context" not in request.metadata
    assert "product_response_summary" not in request.metadata
    assert context["user_question"] == "请基于证据回答这条资料是否可用"
    assert context["summary_facts"] == [
        "The reference is suitable for follow-up review."
    ]
    assert "evidence://external-readonly/cli-fetch/answer.json" in request_text
    assert "governed-evidence-digest://" in request_text
    assert "sanitized reference" not in request_text
    assert "sanitized_excerpt_preview" not in request_text
    assert "ProductGatewayResponse" not in request_text
    assert "raw_payload" not in request_text
    assert "config-secret-value" not in request_text
    assert "observability_candidate_body" not in request_text
    assert "sanitized reference" not in output
    assert "sanitized_excerpt_preview" not in output
    assert "ProductGatewayResponse" not in output


def test_external_readonly_answer_fails_visible_reasoning_answer(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/answer.json"
    _write_external_readonly_archive(tmp_path, evidence_path)
    monkeypatch.chdir(tmp_path)
    service = _FakeLlmService('{ "thought": "The user wants a concise answer."')
    factory = _FakeFactory(service)

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "answer",
            "--evidence-path",
            evidence_path,
            "--question",
            "请基于证据回答这条资料是否可用",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://external-readonly-answer/unit",
            "--ollama-api-base",
            "http://127.0.0.1:11434",
            "--json",
        ],
        external_readonly_answer_llm_invocation_service_factory=factory,
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code != 0
    assert payload["status"] == "failed"
    assert payload["success"] is False
    assert payload["answer"] is None
    assert payload["answer_preview"] is None
    assert payload["blocking_reasons"] == [
        EVIDENCE_SUMMARY_ANSWER_QUALITY_BLOCKING_REASON
    ]
    assert payload["evidence_summary_answer_result"]["status"] == "failed"
    assert service.request is not None


def test_external_readonly_answer_blocks_legacy_archive_without_governed_facts(
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
            "answer",
            "--evidence-path",
            evidence_path,
            "--question",
            "请基于证据回答",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://external-readonly-answer/unit",
            "--json",
        ],
        external_readonly_answer_llm_invocation_service_factory=_RaisingFactory(),
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["llm_call_attempted"] is False
    assert payload["evidence_summary_answer_result"]["status"] == "blocked"
    assert payload["blocking_reasons"] == [
        "external_readonly_governed_summary_facts_required"
    ]


def test_external_readonly_answer_rejects_non_local_ollama_base_before_refs(
    capsys: Any,
) -> None:
    def raising_refs_executor(*_: Any, **__: Any) -> Any:
        raise AssertionError("refs executor should not run for non-local ollama")

    exit_code = cognition.run_cli(
        [
            "external-readonly",
            "answer",
            "--evidence-path",
            "outputs/external-readonly/cli-fetch/answer.json",
            "--question",
            "请基于证据回答",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://external-readonly-answer/unit",
            "--ollama-api-base",
            "https://models.example.com",
            "--json",
        ],
        external_readonly_refs_application_executor=raising_refs_executor,
        external_readonly_answer_llm_invocation_service_factory=(
            _RaisingFactory()
        ),
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == ["ollama_api_base_must_be_local"]
    assert payload["llm_call_attempted"] is False


def test_external_readonly_answer_cli_keeps_channel_boundary() -> None:
    source = ANSWER_SOURCE.read_text(encoding="utf-8")

    assert "build_external_readonly_refs_cli_output" in source
    assert "runtime_container" not in source
    assert "from composition" not in source
    assert "product_runtime_assembly" not in source
    assert "ProductGatewayResponse" not in source
    assert "sanitized_excerpt_preview" not in source


class _FakeFactory:
    def __init__(self, service: "_FakeLlmService") -> None:
        self.service = service
        self.captured: dict[str, Any] = {}

    def resolve(self, **kwargs: Any) -> GovernedLlmInvocationServiceResolution:
        self.captured = dict(kwargs)
        return GovernedLlmInvocationServiceResolution(service=self.service)


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
        "allow_runtime_fetch": True,
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
        "transport_called": True,
        "uploads_content": False,
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
