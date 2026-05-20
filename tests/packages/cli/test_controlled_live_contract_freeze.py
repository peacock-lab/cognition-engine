from __future__ import annotations

from runtime_container.controlled_adk_run_entry import (
    _compact_live_profile,
    _llm_invocation_audit_summary,
    _tool_audit_summary,
)
from cognition_cli import constants as cognition_constants
from cognition_cli import output_boundary as cognition_output_boundary


FROZEN_CLI_TOP_LEVEL_FIELDS = {
    "product",
    "command",
    "execution_mode",
    "runtime_id",
    "invocation_id",
    "workflow_id",
    "workflow_name",
    "adk_run_allowed",
    "adk_run_performed",
    "execution_performed",
    "live_llm_call_performed",
    "ollama_call_performed",
    "blocking_reasons",
    "warnings",
    "final_preflight",
    "lifecycle_facts",
    "run_config_service_bundle_facts",
    "governance_summary_payload_ref",
    "llm_invocation_result_ref",
    "llm_invocation_observation_ref",
    "llm_invocation_summary_ref",
    "llm_invocation_call_allowed",
    "llm_invocation_call_attempted",
    "llm_invocation_runtime_call_performed",
    "llm_invocation_failure_type",
    "tool_evidence_ref",
    "tool_run_ref",
    "tool_status",
    "tool_failure_type",
    "tool_runtime_call_performed",
    "controlled_live_llm_preflight",
    "product_response_summary",
    "sanitized_evidence_ref",
    "audit_ref",
    "output_ref",
    "status",
    "exit_code",
}

FROZEN_FORBIDDEN_CLI_FIELDS = {
    "recorded_run",
    "raw_adk_object",
    "raw_state_value",
    "artifact_content",
    "secret",
    "token",
    "credential",
    "live_model_payload",
    "llm_invocation_result",
    "llm_call_observation_candidate",
    "agent_llm_invocation_summary_candidate",
    "llm_invocation_readonly_facts",
    "llm_invocation_audit",
    "agent_shell_audit",
    "tool_audit",
    "live_profile",
    "prompt",
    "messages",
    "raw_response",
    "raw_provider_response",
    "response_text",
}

FROZEN_LLM_INVOCATION_AUDIT_FIELDS = {
    "llm_invocation_result_ref",
    "llm_invocation_observation_ref",
    "llm_invocation_summary_ref",
    "call_allowed",
    "call_attempted",
    "runtime_call_performed",
    "failure_type",
    "controlled_live",
    "live_llm_call_performed",
    "ollama_call_performed",
    "live_profile",
    "readonly_facts_embedded",
    "does_not_store_prompt",
    "does_not_store_raw_provider_response",
}

FROZEN_LIVE_PROFILE_FIELDS = {
    "controlled_live",
    "live_options_source",
    "live_service_profile",
    "configured_model_name",
    "timeout_seconds",
    "temperature",
    "max_tokens",
    "local_no_proxy_applied",
}

FROZEN_TOOL_AUDIT_SUMMARY_FIELDS = {
    "tool_evidence_ref",
    "tool_run_ref",
    "tool_status",
    "tool_failure_type",
    "tool_runtime_call_performed",
}

FROZEN_AGENT_SHELL_CONTROLLED_LIVE_AUDIT_FIELDS = {
    "agent_shell_evidence_ref",
    "agent_shell_run_ref",
    "agent_name",
    "agent_type",
    "app_name",
    "status",
    "event_count",
    "controlled_live",
    "controlled_live_smoke",
    "controlled_live_smoke_enabled",
    "runtime_call_performed",
    "call_attempted",
    "failure_type",
    "error_message_sanitized",
    "live_profile",
    "does_not_store_prompt",
    "does_not_store_raw_response",
    "raw_adk_object_included",
    "raw_adk_event_included",
    "raw_adk_session_included",
}

FROZEN_AGENT_SHELL_LIVE_PROFILE_FIELDS = {
    "live_options_source",
    "live_service_profile",
    "configured_model_name",
    "ollama_api_base",
    "timeout_seconds",
    "temperature",
    "max_tokens",
    "enabled_by_default",
}


def test_cli_top_level_contract_is_frozen() -> None:
    assert cognition_constants.ALLOWED_TOP_LEVEL_FIELDS == FROZEN_CLI_TOP_LEVEL_FIELDS
    assert FROZEN_FORBIDDEN_CLI_FIELDS.issubset(cognition_constants.FORBIDDEN_TOP_LEVEL_FIELDS)
    assert cognition_constants.ALLOWED_TOP_LEVEL_FIELDS.isdisjoint(
        cognition_constants.FORBIDDEN_TOP_LEVEL_FIELDS
    )


def test_cli_output_boundary_rejects_nested_llm_audit_and_profile_payloads() -> None:
    output = {
        "product": "Cognition System / 认知系统",
        "final_preflight": {
            "allowed": True,
            "llm_invocation_audit": {"call_allowed": True},
            "agent_shell_audit": {"runtime_call_performed": True},
        },
    }

    assert cognition_output_boundary.violates_output_boundary(output) is True
    assert cognition_output_boundary.whitelist_output(output) == {
        "product": "Cognition System / 认知系统",
        "final_preflight": {"allowed": True},
    }


def test_llm_invocation_audit_contract_is_frozen() -> None:
    audit = _llm_invocation_audit_summary(
        {
            "llm_invocation_result_ref": "llm-invocation-result://request-1",
            "llm_invocation_observation_ref": "llm-call-observation://request-1",
            "llm_invocation_summary_ref": (
                "agent-llm-invocation-summary://request-1"
            ),
            "llm_invocation_call_allowed": True,
            "llm_invocation_call_attempted": True,
            "llm_invocation_runtime_call_performed": True,
            "llm_invocation_failure_type": None,
            "live_llm_call_performed": True,
            "ollama_call_performed": True,
            "llm_invocation_readonly_facts": {
                "live_profile": {
                    "controlled_live": True,
                    "live_options_source": (
                        "config_contexts.runtime.RuntimeLiveLlmConfigView"
                    ),
                    "live_service_profile": "adk_litellm_ollama",
                    "configured_model_name": "ollama/gemma4-pro:latest",
                    "timeout_seconds": 45,
                    "temperature": 0,
                    "max_tokens": 64,
                    "local_no_proxy_applied": True,
                    "ollama_api_base": "http://127.0.0.1:11434",
                    "raw_provider_response": "must not leak",
                }
            },
        }
    )

    assert audit is not None
    assert set(audit) == FROZEN_LLM_INVOCATION_AUDIT_FIELDS
    assert audit["live_profile"] == {
        "controlled_live": True,
        "live_options_source": "config_contexts.runtime.RuntimeLiveLlmConfigView",
        "live_service_profile": "adk_litellm_ollama",
        "configured_model_name": "ollama/gemma4-pro:latest",
        "timeout_seconds": 45,
        "temperature": 0,
        "max_tokens": 64,
        "local_no_proxy_applied": True,
    }
    assert audit["readonly_facts_embedded"] is False
    assert audit["does_not_store_prompt"] is True
    assert audit["does_not_store_raw_provider_response"] is True
    assert "llm_invocation_readonly_facts" not in audit
    assert "raw_provider_response" not in audit


def test_live_profile_compact_digest_contract_is_frozen() -> None:
    profile = _compact_live_profile(
        {
            "controlled_live": True,
            "live_options_source": "config_contexts.runtime.RuntimeLiveLlmConfigView",
            "live_service_profile": "adk_litellm_ollama",
            "configured_model_name": "ollama/gemma4-pro:latest",
            "timeout_seconds": 45,
            "temperature": 0,
            "max_tokens": 64,
            "local_no_proxy_applied": True,
            "ollama_api_base": "http://127.0.0.1:11434",
            "NO_PROXY": "127.0.0.1",
            "api_key": "secret",
            "prompt": "raw prompt",
            "messages": [{"role": "user", "content": "raw"}],
            "response_text": "raw response",
            "raw_provider_response": "raw provider response",
        }
    )

    assert profile is not None
    assert set(profile) == FROZEN_LIVE_PROFILE_FIELDS
    assert "ollama_api_base" not in profile
    assert "NO_PROXY" not in profile
    assert "api_key" not in profile
    assert "prompt" not in profile
    assert "messages" not in profile
    assert "response_text" not in profile
    assert "raw_provider_response" not in profile


def test_tool_audit_top_level_summary_contract_is_frozen() -> None:
    summary = _tool_audit_summary(
        {
            "tool_evidence_ref": "adk-tool-evidence://adk-tool-evidence-1",
            "tool_run_ref": "adk-tool-run://tool-run-1",
            "status": "success",
            "tool_failure_type": None,
            "tool_runtime_call_performed": True,
            "tool_input_summary": {"argument_keys": ["task_ref"]},
            "tool_output_summary": {"result_kind": "task_review_candidate"},
            "raw_tool_input": {"task_ref": "must not leak"},
            "raw_tool_output": {"result": "must not leak"},
        }
    )

    assert set(summary) == FROZEN_TOOL_AUDIT_SUMMARY_FIELDS
    assert summary == {
        "tool_evidence_ref": "adk-tool-evidence://adk-tool-evidence-1",
        "tool_run_ref": "adk-tool-run://tool-run-1",
        "tool_status": "success",
        "tool_failure_type": None,
        "tool_runtime_call_performed": True,
    }
    assert "tool_input_summary" not in summary
    assert "tool_output_summary" not in summary
    assert "raw_tool_input" not in summary
    assert "raw_tool_output" not in summary


def test_agent_shell_controlled_live_audit_contract_is_frozen() -> None:
    audit = {
        "agent_shell_evidence_ref": (
            "adk-agent-shell-evidence://adk-agent-shell-evidence-1"
        ),
        "agent_shell_run_ref": "adk-agent-shell-run://agent-shell-live-1",
        "agent_name": "cognition_agent_shell",
        "agent_type": "LlmAgent",
        "app_name": "cognition_agent_shell_controlled_live_smoke",
        "status": "success",
        "event_count": 2,
        "controlled_live": True,
        "controlled_live_smoke": True,
        "controlled_live_smoke_enabled": True,
        "runtime_call_performed": True,
        "call_attempted": True,
        "failure_type": None,
        "error_message_sanitized": None,
        "live_profile": {
            "live_options_source": "config_contexts.runtime.RuntimeLiveLlmConfigView",
            "live_service_profile": "adk_litellm_ollama",
            "configured_model_name": "ollama/gemma4-pro:latest",
            "ollama_api_base": "http://127.0.0.1:11434",
            "timeout_seconds": 45,
            "temperature": 0,
            "max_tokens": 64,
            "enabled_by_default": False,
        },
        "does_not_store_prompt": True,
        "does_not_store_raw_response": True,
        "raw_adk_object_included": False,
        "raw_adk_event_included": False,
        "raw_adk_session_included": False,
    }

    assert set(audit) == FROZEN_AGENT_SHELL_CONTROLLED_LIVE_AUDIT_FIELDS
    assert set(audit["live_profile"]) == FROZEN_AGENT_SHELL_LIVE_PROFILE_FIELDS
    assert audit["controlled_live"] is True
    assert audit["runtime_call_performed"] is True
    assert audit["call_attempted"] is True
    assert audit["does_not_store_prompt"] is True
    assert audit["does_not_store_raw_response"] is True
    assert audit["raw_adk_object_included"] is False
    assert audit["raw_adk_event_included"] is False
    assert audit["raw_adk_session_included"] is False
