from __future__ import annotations

import hashlib
import json
import os
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

import pytest
from adk_adapter import (
    ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_NO_OUTPUT_SCHEMA,
    AdkEvidenceSummaryAnswerOutputGovernanceOptions,
    AdkEvidenceSummaryAnswerOutputGovernanceProbe,
)
from adk_adapter.models import (
    build_litellm_deepseek_model_route,
    build_litellm_ollama_model_route,
)
from product_application_assembly import (
    build_evidence_summary_answer_context,
    build_evidence_summary_answer_llm_invocation_request,
    build_evidence_summary_answer_result_from_llm_invocation_result,
    build_governed_evidence_digest_from_external_readonly_facts,
)
from schemas.llm_invocation import LlmGovernancePrecondition


ENABLE_REAL_PROVIDER_SMOKE_ENV = (
    "CE_ENABLE_EXTERNAL_READONLY_ASK_ADK_NATIVE_REAL_PROVIDER_SMOKE"
)
MODELS_ENV = "CE_EXTERNAL_READONLY_ASK_ADK_NATIVE_SMOKE_MODELS"
TIMEOUT_SECONDS_ENV = "CE_EXTERNAL_READONLY_ASK_ADK_NATIVE_TIMEOUT_SECONDS"
MAX_TOKENS_ENV = "CE_EXTERNAL_READONLY_ASK_ADK_NATIVE_MAX_TOKENS"
DEFAULT_OLLAMA_API_BASE = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_MAX_TOKENS = 256
DEFAULT_MODELS = (
    "ollama/gemma4-pro:latest",
    "ollama/gemma-governance-26b:latest",
    "ollama/gemma-governance-26b-64k:latest",
)
ENABLE_DEEPSEEK_PROVIDER_SMOKE_ENV = (
    "CE_ENABLE_EXTERNAL_READONLY_ASK_DEEPSEEK_PROVIDER_SMOKE"
)
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEEPSEEK_API_BASE_ENV = "CE_DEEPSEEK_API_BASE"
DEEPSEEK_MODEL_ENV = "CE_EXTERNAL_READONLY_ASK_DEEPSEEK_MODEL"
DEEPSEEK_NETWORK_GATE_ENV = "CE_EXTERNAL_READONLY_ASK_DEEPSEEK_NETWORK_GATE_OPEN"
DEEPSEEK_APPROVAL_REF_ENV = "CE_EXTERNAL_READONLY_ASK_DEEPSEEK_APPROVAL_REF"
DEEPSEEK_AUDIT_REF_ENV = "CE_EXTERNAL_READONLY_ASK_DEEPSEEK_AUDIT_REF"
DEEPSEEK_TIMEOUT_SECONDS_ENV = (
    "CE_EXTERNAL_READONLY_ASK_DEEPSEEK_TIMEOUT_SECONDS"
)
DEEPSEEK_MAX_TOKENS_ENV = "CE_EXTERNAL_READONLY_ASK_DEEPSEEK_MAX_TOKENS"
DEFAULT_DEEPSEEK_API_BASE = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek/deepseek-v4-flash"
SUPPORTED_DEEPSEEK_V4_MODELS = frozenset(
    {
        "deepseek/deepseek-v4-flash",
        "deepseek/deepseek-v4-pro",
    }
)


@pytest.mark.parametrize("model_name", DEFAULT_MODELS)
def test_evidence_summary_answer_output_governance_real_provider_smoke(
    model_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _skip_unless_real_provider_smoke_enabled()
    model_names = _smoke_models()
    if model_name not in model_names:
        pytest.skip(f"{model_name} not selected by {MODELS_ENV}.")

    ollama_api_base = _local_ollama_api_base(
        os.getenv("CE_OLLAMA_API_BASE", DEFAULT_OLLAMA_API_BASE)
    )
    _ensure_local_no_proxy(monkeypatch, ollama_api_base)
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    if _ollama_tag_name(model_name) not in _local_ollama_tags(ollama_api_base):
        pytest.skip(f"{model_name} is not available from local Ollama tags.")

    from google.adk.models.lite_llm import LiteLlm

    model = LiteLlm(
        model=model_name,
        api_base=ollama_api_base,
        timeout=_positive_int_env(
            TIMEOUT_SECONDS_ENV,
            default=DEFAULT_TIMEOUT_SECONDS,
        ),
        temperature=0,
        max_tokens=_positive_int_env(
            MAX_TOKENS_ENV,
            default=DEFAULT_MAX_TOKENS,
        ),
    )
    request, context = _request_and_context(model_name)
    probe = AdkEvidenceSummaryAnswerOutputGovernanceProbe(
        options=AdkEvidenceSummaryAnswerOutputGovernanceOptions(
            model=model,
            model_name=model_name,
            app_name=f"cognition_engine_esa_output_governance_{_safe_id(model_name)}",
            response_preview_limit=600,
            metadata={
                "real_provider_smoke": True,
                "model_name": model_name,
                "ollama_api_base_host": urlparse(ollama_api_base).hostname,
            },
        )
    )

    invocation_result = probe.invoke(request)
    answer_result = build_evidence_summary_answer_result_from_llm_invocation_result(
        context,
        invocation_result,
        generation_policy_facts=_generation_policy_facts(),
        metadata={
            "source": (
                "adk_adapter.test."
                "evidence_summary_answer_output_governance_real_provider_smoke"
            ),
            "real_provider_smoke": True,
        },
    )
    summary = _smoke_summary(model_name, invocation_result, answer_result)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))

    assert invocation_result.call_attempted is True
    assert invocation_result.call_allowed is True
    assert invocation_result.runtime_call_performed is True
    assert invocation_result.metadata["adk_native_output_governance_probe"] is True
    assert invocation_result.metadata["adk_runner_used"] is True
    if invocation_result.success:
        assert invocation_result.metadata["after_model_callback_invoked"] is True
        assert isinstance(invocation_result.metadata["draft_schema_parsed"], bool)
        assert isinstance(invocation_result.metadata["answer_quality_passed"], bool)
        assert invocation_result.metadata["repair_retry_max_once"] is True
    else:
        assert invocation_result.failure_type is not None
        if (
            invocation_result.failure_type.value
            == "output_schema_validation_failure"
        ):
            assert invocation_result.metadata["exception_classification"] == (
                "adk_output_schema_validation_exception"
            )
    assert answer_result.status in {"success", "failed"}
    if answer_result.status == "success":
        assert answer_result.answer
        assert answer_result.evidence_refs_used
    else:
        assert answer_result.blocking_reasons
    _assert_no_raw_boundary_leak(invocation_result.model_dump(mode="json"))
    _assert_no_raw_boundary_leak(answer_result.model_dump(mode="json"))


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


def test_deepseek_provider_smoke_gate_requires_explicit_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        ENABLE_DEEPSEEK_PROVIDER_SMOKE_ENV,
        DEEPSEEK_API_KEY_ENV,
        DEEPSEEK_NETWORK_GATE_ENV,
        DEEPSEEK_APPROVAL_REF_ENV,
        DEEPSEEK_AUDIT_REF_ENV,
    ):
        monkeypatch.delenv(key, raising=False)

    assert ENABLE_DEEPSEEK_PROVIDER_SMOKE_ENV in _deepseek_smoke_skip_reason()

    monkeypatch.setenv(ENABLE_DEEPSEEK_PROVIDER_SMOKE_ENV, "1")
    assert DEEPSEEK_NETWORK_GATE_ENV in _deepseek_smoke_skip_reason()

    monkeypatch.setenv(DEEPSEEK_NETWORK_GATE_ENV, "1")
    assert DEEPSEEK_API_KEY_ENV in _deepseek_smoke_skip_reason()

    monkeypatch.setenv(DEEPSEEK_API_KEY_ENV, "test-placeholder")
    assert DEEPSEEK_APPROVAL_REF_ENV in _deepseek_smoke_skip_reason()

    monkeypatch.setenv(DEEPSEEK_APPROVAL_REF_ENV, "approval://manual/deepseek-smoke")
    assert DEEPSEEK_AUDIT_REF_ENV in _deepseek_smoke_skip_reason()

    monkeypatch.setenv(DEEPSEEK_AUDIT_REF_ENV, "audit://manual/deepseek-smoke")
    assert _deepseek_smoke_skip_reason() is None


def test_deepseek_provider_smoke_rejects_legacy_model_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(DEEPSEEK_MODEL_ENV, "deepseek-chat")

    with pytest.raises(ValueError, match="DeepSeek V4"):
        _deepseek_model_name()


def test_evidence_summary_answer_output_governance_deepseek_provider_smoke() -> None:
    skip_reason = _deepseek_smoke_skip_reason()
    if skip_reason is not None:
        pytest.skip(skip_reason)

    api_key = os.environ[DEEPSEEK_API_KEY_ENV]
    api_base = os.getenv(DEEPSEEK_API_BASE_ENV, DEFAULT_DEEPSEEK_API_BASE)
    model_name = _deepseek_model_name()
    model, route_facts = build_litellm_deepseek_model_route(
        model_name=model_name,
        api_base=api_base,
        api_key=api_key,
        secret_ref=f"secret-ref://env/{DEEPSEEK_API_KEY_ENV}",
        network_gate_open=True,
        operator_approved=True,
        approval_ref=os.environ[DEEPSEEK_APPROVAL_REF_ENV],
        audit_ref=os.environ[DEEPSEEK_AUDIT_REF_ENV],
        timeout=_positive_int_env(
            DEEPSEEK_TIMEOUT_SECONDS_ENV,
            default=DEFAULT_TIMEOUT_SECONDS,
        ),
        temperature=0,
        max_tokens=_positive_int_env(
            DEEPSEEK_MAX_TOKENS_ENV,
            default=DEFAULT_MAX_TOKENS,
        ),
    )
    request, context = _request_and_context(
        model_name,
        route_facts=route_facts.to_public_model_route_facts(),
        smoke_source="deepseek-provider-smoke",
    )
    probe = AdkEvidenceSummaryAnswerOutputGovernanceProbe(
        options=AdkEvidenceSummaryAnswerOutputGovernanceOptions(
            model=model,
            model_name=model_name,
            app_name="cognition_engine_esa_output_governance_deepseek",
            output_governance_mode=(
                ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_NO_OUTPUT_SCHEMA
            ),
            response_preview_limit=600,
            metadata={
                "real_provider_smoke": True,
                "deepseek_provider_smoke": True,
                "model_name": model_name,
                "api_base_host": urlparse(api_base).hostname if api_base else None,
                "network_gate_open": True,
                "approval_ref_present": True,
                "audit_ref_present": True,
                "secret_ref_present": True,
            },
        )
    )

    invocation_result = probe.invoke(request)
    answer_result = build_evidence_summary_answer_result_from_llm_invocation_result(
        context,
        invocation_result,
        generation_policy_facts=_generation_policy_facts(),
        metadata={
            "source": (
                "adk_adapter.test."
                "evidence_summary_answer_output_governance_deepseek_provider_smoke"
            ),
            "real_provider_smoke": True,
            "deepseek_provider_smoke": True,
        },
    )
    summary = _smoke_summary(model_name, invocation_result, answer_result)
    summary["deepseek_provider_smoke"] = True
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))

    assert invocation_result.call_attempted is True
    assert invocation_result.call_allowed is True
    assert invocation_result.runtime_call_performed is True
    assert invocation_result.metadata["adk_native_output_governance_probe"] is True
    assert invocation_result.metadata["output_governance_mode"] == "no_output_schema"
    assert answer_result.status in {"success", "failed"}
    if answer_result.status == "success":
        assert answer_result.answer
        assert answer_result.evidence_refs_used
    else:
        assert answer_result.blocking_reasons
    _assert_no_raw_boundary_leak(invocation_result.model_dump(mode="json"))
    _assert_no_raw_boundary_leak(answer_result.model_dump(mode="json"))


def _request_and_context(
    model_name: str,
    *,
    route_facts=None,
    smoke_source: str = "adk-native-real-provider-smoke",
):
    if route_facts is None:
        route_facts = build_litellm_ollama_model_route(
            model_name=model_name
        )[1].to_public_model_route_facts()
    digest = build_governed_evidence_digest_from_external_readonly_facts(
        _governed_summary_facts_payload(),
        digest_id=smoke_source,
        metadata={
            "source": (
                "adk_adapter.test."
                "evidence_summary_answer_output_governance_real_provider_smoke"
            ),
            "real_provider_smoke": True,
        },
    )
    context = build_evidence_summary_answer_context(
        request_id="external-readonly-ask-request://adk-native-real-provider/context",
        user_question="这个网页主要说明了什么？",
        digests=[digest],
        metadata={
            "source": (
                "adk_adapter.test."
                "evidence_summary_answer_output_governance_real_provider_smoke"
            ),
            "real_provider_smoke": True,
        },
    )
    request = build_evidence_summary_answer_llm_invocation_request(
        context,
        route_facts=route_facts,
        governance_precondition=LlmGovernancePrecondition(
            allowed=True,
            reason="external_readonly_ask_adk_native_real_provider_smoke",
            decision="allow",
            governance_decision_ref=(
                "approval://external-readonly-ask-adk-native-real-provider-smoke"
            ),
        ),
        request_id="external-readonly-ask-request://adk-native-real-provider/llm",
        generation_policy_facts=_generation_policy_facts(),
        metadata={
            "source": (
                "adk_adapter.test."
                "evidence_summary_answer_output_governance_real_provider_smoke"
            ),
            "real_provider_smoke": True,
        },
    )
    return request, context


def _governed_summary_facts_payload() -> dict[str, object]:
    fact = (
        "Example Domain is for use in documentation examples without needing "
        "permission."
    )
    content_hash = hashlib.sha256(fact.encode()).hexdigest()
    evidence_ref = "evidence://external-readonly/item/adk-native-real-provider-smoke"
    evidence_output_path = (
        "outputs/external-readonly/cli-fetch/adk-native-real-provider-smoke.json"
    )
    return {
        "payload_type": "external_readonly_governed_summary_facts",
        "payload_version": "external_readonly_governed_summary_facts_v1",
        "status": "ready",
        "evidence_ref": evidence_ref,
        "evidence_output_path": evidence_output_path,
        "source_url_host": "example.com",
        "source_url_scheme": "https",
        "reference_review_ready": True,
        "allowed_for_model_context": True,
        "evidence_written": True,
        "content_hash": content_hash,
        "facts": [
            {
                "fact_ref": (
                    "external-readonly-governed-summary-fact://"
                    "adk-native-real-provider-smoke-1"
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
        "facts_budget": 4000,
        "total_fact_chars": len(fact),
        "blocking_reasons": [],
        "warnings": [],
        "generation_policy_ref": (
            "policy://external-readonly/governed-summary-facts/minimal-v1"
        ),
        "metadata": {"source_package": "external_readonly"},
    }


def _generation_policy_facts() -> dict[str, object]:
    return {
        "profile": "controlled_live_answer_generation",
        "allow_answer_generation_success": True,
        "answer_generation_service_ref": (
            "service://adk-adapter/evidence-summary-answer/"
            "output-governance-real-provider-smoke"
        ),
        "answer_policy_ref": (
            "policy://product-application-assembly/evidence-summary-answer/"
            "answer/minimal-v1"
        ),
        "citation_policy_ref": (
            "policy://product-application-assembly/evidence-summary-answer/"
            "citation/minimal-v1"
        ),
        "llm_provider_factory_ref": (
            "provider-factory://adk-adapter/evidence-summary-answer/"
            "output-governance-real-provider-smoke"
        ),
    }


def _smoke_summary(
    model_name: str,
    invocation_result,
    answer_result,
) -> dict[str, object]:
    metadata = invocation_result.metadata
    route_metadata = getattr(invocation_result.route_facts, "metadata", {})
    return {
        "model_name": model_name,
        "backend_provider": route_metadata.get("backend_provider"),
        "route_kind": route_metadata.get("route_kind"),
        "thinking_mode": route_metadata.get("thinking_mode"),
        "status": "completed",
        "answer_status": answer_result.status,
        "llm_call_attempted": invocation_result.call_attempted,
        "llm_runtime_call_performed": invocation_result.runtime_call_performed,
        "llm_invocation_success": invocation_result.success,
        "llm_invocation_failure_type": (
            str(invocation_result.failure_type.value)
            if invocation_result.failure_type is not None
            else None
        ),
        "after_model_callback_invoked": metadata.get("after_model_callback_invoked"),
        "callback_quality_passed": metadata.get("callback_quality_passed"),
        "draft_schema_parsed": metadata.get("draft_schema_parsed"),
        "answer_quality_passed": metadata.get("answer_quality_passed"),
        "repair_retry_attempted": metadata.get("repair_retry_attempted"),
        "repair_retry_performed": metadata.get("repair_retry_performed"),
        "repair_retry_failed": metadata.get("repair_retry_failed"),
        "blocking_reasons": list(answer_result.blocking_reasons),
        "answer_preview": answer_result.answer_preview,
        "evidence_refs_used": [
            ref.model_dump(mode="json") for ref in answer_result.evidence_refs_used
        ],
        "digest_refs_used": list(answer_result.digest_refs_used),
        "raw_boundary_ok": _raw_boundary_ok(
            invocation_result.model_dump(mode="json"),
            answer_result.model_dump(mode="json"),
        ),
    }


def _skip_unless_real_provider_smoke_enabled() -> None:
    if os.getenv(ENABLE_REAL_PROVIDER_SMOKE_ENV) != "1":
        pytest.skip(
            "Set "
            f"{ENABLE_REAL_PROVIDER_SMOKE_ENV}=1 to run external-readonly "
            "ask ADK-native real provider smoke tests."
        )


def _smoke_models() -> tuple[str, ...]:
    value = os.getenv(MODELS_ENV)
    if not value:
        return DEFAULT_MODELS
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _deepseek_smoke_skip_reason() -> str | None:
    if os.getenv(ENABLE_DEEPSEEK_PROVIDER_SMOKE_ENV) != "1":
        return (
            "Set "
            f"{ENABLE_DEEPSEEK_PROVIDER_SMOKE_ENV}=1 to run DeepSeek "
            "external-readonly ask provider smoke tests."
        )
    if os.getenv(DEEPSEEK_NETWORK_GATE_ENV) != "1":
        return f"Set {DEEPSEEK_NETWORK_GATE_ENV}=1 to open the DeepSeek network gate."
    if not os.getenv(DEEPSEEK_API_KEY_ENV):
        return f"Set {DEEPSEEK_API_KEY_ENV} outside the repository."
    if not os.getenv(DEEPSEEK_APPROVAL_REF_ENV):
        return f"Set {DEEPSEEK_APPROVAL_REF_ENV} for DeepSeek smoke approval facts."
    if not os.getenv(DEEPSEEK_AUDIT_REF_ENV):
        return f"Set {DEEPSEEK_AUDIT_REF_ENV} for DeepSeek smoke audit facts."
    _deepseek_model_name()
    return None


def _deepseek_model_name() -> str:
    model_name = os.getenv(DEEPSEEK_MODEL_ENV, DEFAULT_DEEPSEEK_MODEL)
    if model_name not in SUPPORTED_DEEPSEEK_V4_MODELS:
        raise ValueError(
            "DeepSeek provider smoke currently supports DeepSeek V4 models only."
        )
    return model_name


def _local_ollama_api_base(value: str) -> str:
    parsed = urlparse(value)
    host = parsed.hostname
    if parsed.scheme != "http" or host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError(
            "external-readonly ask ADK-native real provider smoke only allows "
            "local Ollama base urls."
        )
    return value


def _ensure_local_no_proxy(
    monkeypatch: pytest.MonkeyPatch,
    api_base: str,
) -> None:
    host = urlparse(api_base).hostname
    if host not in {"127.0.0.1", "localhost", "::1"}:
        return
    for key in ("NO_PROXY", "no_proxy"):
        existing = [
            item.strip()
            for item in os.environ.get(key, "").split(",")
            if item.strip()
        ]
        merged = existing + [
            item
            for item in ("127.0.0.1", "localhost", "::1")
            if item not in existing
        ]
        monkeypatch.setenv(key, ",".join(merged))
    monkeypatch.setenv("OLLAMA_API_BASE", api_base)


def _local_ollama_tags(api_base: str) -> set[str]:
    try:
        with urlopen(f"{api_base.rstrip('/')}/api/tags", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError) as exc:
        pytest.fail(f"could not query local Ollama tags: {exc}")
    models = payload.get("models")
    if not isinstance(models, list):
        pytest.fail("local Ollama /api/tags returned an invalid models payload.")
    tags: set[str] = set()
    for item in models:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str) and name:
            tags.add(name)
    return tags


def _ollama_tag_name(model_name: str) -> str:
    return model_name.removeprefix("ollama/")


def _positive_int_env(name: str, *, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    if not value.isdecimal() or int(value) <= 0:
        raise ValueError(f"{name} must be a positive integer.")
    return int(value)


def _safe_id(value: str) -> str:
    return (
        value.replace("/", "_")
        .replace(":", "_")
        .replace("-", "_")
        .replace(".", "_")
    )


def _assert_no_raw_boundary_leak(payload: object) -> None:
    assert _raw_boundary_ok(payload)


def _raw_boundary_ok(*payloads: object) -> bool:
    return not any(_raw_boundary_violation(payload) for payload in payloads)


def _raw_boundary_violation(value: object) -> bool:
    forbidden_keys = {
        "raw_provider_response",
        "raw_response",
        "response_text",
        "messages",
        "system_prompt",
        "full_prompt",
        "internal_draft",
        "sanitized_excerpt_preview",
        "live_model_payload",
    }
    forbidden_value_markers = (
        "raw_provider_response",
        "raw_response",
        "response_text",
        "system_prompt",
        "full_prompt",
        "internal_draft",
        "sanitized_excerpt_preview",
        "ProductGatewayResponse",
        "live_model_payload",
    )
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key) in forbidden_keys:
                return True
            if _raw_boundary_violation(item):
                return True
        return False
    if isinstance(value, list | tuple):
        return any(_raw_boundary_violation(item) for item in value)
    if isinstance(value, str):
        return any(marker in value for marker in forbidden_value_markers)
    return False
