"""Shared constants for the Cognition System CLI."""

PRODUCT_NAME = "Cognition System / 认知系统"
PRODUCT_DEFINITION = "受控运行与智能体治理系统"
CLI_COMMAND = "cognition"
BACKEND = "cognition-system v0.8.0"
AGENT_FRAMEWORK = "Google ADK 2.0.0"
ADAPTER = "adk_adapter"
MODE = "controlled · no-live · observable"
DEFAULT_WORKFLOW_NAME = "controlled-adk-run"
DEFAULT_WORKFLOW_ID = "workflow-controlled-adk-run"
CHAT_NO_LIVE_ASSISTANT_MESSAGE = "no-live 模式已完成受控运行，本轮未调用本地模型。"
CHAT_LIVE_NO_PREVIEW_MESSAGE = "controlled-live 模型调用已完成，但未返回可展示的脱敏预览。"
CHAT_LIVE_LLM_MAX_TOKENS = 2048
CHAT_RESPONSE_PREVIEW_LIMIT = 4000
CHAT_RUN_WORKSPACE_RETENTION_POLICIES = ("keep", "ephemeral", "delete_on_success")
CHAT_RUN_WORKSPACE_CLEANUP_POLICIES = (
    "manual",
    "delete_on_success",
    "delete_always",
)

EXIT_OK = 0
EXIT_USAGE_ERROR = 2
EXIT_BLOCKING = 3
EXIT_RUNTIME_FAILURE = 4
EXIT_OUTPUT_WRITE_FAILURE = 5
EXIT_OUTPUT_BOUNDARY_FAILURE = 6

FORBIDDEN_TOP_LEVEL_FIELDS = {
    "recorded_run",
    "raw_adk_object",
    "raw_adk_object_included",
    "raw_state_value",
    "raw_state_values_included",
    "artifact_content",
    "artifact_content_included",
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
ALLOWED_TOP_LEVEL_FIELDS = {
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
