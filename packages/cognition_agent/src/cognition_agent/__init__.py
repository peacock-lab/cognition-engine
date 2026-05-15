"""Candidate-only cognition agent shell."""

from cognition_agent.agent_shell_audit_view import (
    AGENT_SHELL_AUDIT_READONLY_VIEW_SOURCE,
    AGENT_SHELL_AUDIT_READONLY_VIEW_VERSION,
    AgentShellAuditReadonlyViewCandidate,
    build_agent_shell_audit_readonly_view,
)
from cognition_agent.agent_tool_audit_view import (
    AGENT_TOOL_AUDIT_READONLY_VIEW_SOURCE,
    AGENT_TOOL_AUDIT_READONLY_VIEW_VERSION,
    AgentToolAuditReadonlyViewCandidate,
    build_agent_tool_audit_readonly_view,
)
from cognition_agent.governance_view import (
    AgentGovernanceViewCandidate,
    GOVERNANCE_PRECONDITION_SUMMARY_SOURCE,
    GOVERNANCE_PRECONDITION_SUMMARY_VERSION,
    build_agent_governance_view_from_precondition_summary,
    build_agent_governance_view_candidate,
)
from cognition_agent.governance_summary_view import (
    AgentGovernanceEvidenceSummaryViewCandidate,
    GOVERNANCE_EVIDENCE_SUMMARY_VIEW_SOURCE,
    GOVERNANCE_EVIDENCE_SUMMARY_VIEW_VERSION,
    build_agent_governance_evidence_summary_view,
)
from cognition_agent.governed_run_evidence_context_view import (
    AgentGovernedRunEvidenceContextCandidate,
    GOVERNED_RUN_EVIDENCE_CONTEXT_SOURCE,
    GOVERNED_RUN_EVIDENCE_CONTEXT_VERSION,
    build_agent_governed_run_evidence_context_candidate,
)
from cognition_agent.llm_invocation_view import (
    AgentLlmInvocationSummaryCandidate,
    LLM_CALL_OBSERVATION_SUMMARY_SOURCE,
    LLM_INVOCATION_RESULT_SUMMARY_SOURCE,
    LLM_INVOCATION_SUMMARY_VERSION,
    build_agent_llm_invocation_summary_from_invocation_result,
    build_agent_llm_invocation_summary_from_observation_candidate,
    build_agent_llm_invocation_summary_from_public_shape,
)
from cognition_agent.models import (
    AgentCapabilityViewCandidate,
    AgentContextCandidate,
    AgentInteractionCandidate,
    AgentTaskCandidate,
)
from cognition_agent.product_gateway_response_view import (
    AGENT_PRODUCT_GATEWAY_RESPONSE_VIEW_SOURCE,
    AGENT_PRODUCT_GATEWAY_RESPONSE_VIEW_VERSION,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION,
    AgentProductGatewayRefViewCandidate,
    AgentProductGatewayResponseViewCandidate,
    build_agent_product_gateway_response_view_candidate,
)
from cognition_agent.runtime_context_view import (
    AgentReadonlyRuntimeContextCandidate,
    READONLY_RUNTIME_CONTEXT_SOURCE,
    READONLY_RUNTIME_CONTEXT_VERSION,
    build_agent_readonly_runtime_context_candidate,
)
from cognition_agent.task_context import (
    AgentTaskAdviceCandidate,
    AgentTaskContextCandidate,
    TASK_ADVICE_SOURCE,
    TASK_ADVICE_VERSION,
    TASK_CONTEXT_SOURCE,
    TASK_CONTEXT_VERSION,
    build_agent_task_advice_candidate,
    build_agent_task_context_candidate,
)
from cognition_agent.task_advice_consumption import (
    TASK_ADVICE_CONSUMPTION_PAYLOAD_SOURCE,
    TASK_ADVICE_CONSUMPTION_PAYLOAD_VERSION,
    build_agent_task_advice_consumption_payload,
)

__all__ = [
    "AgentCapabilityViewCandidate",
    "AgentContextCandidate",
    "AgentGovernanceViewCandidate",
    "AgentGovernanceEvidenceSummaryViewCandidate",
    "AgentGovernedRunEvidenceContextCandidate",
    "AgentInteractionCandidate",
    "AgentLlmInvocationSummaryCandidate",
    "AgentProductGatewayRefViewCandidate",
    "AgentProductGatewayResponseViewCandidate",
    "AgentReadonlyRuntimeContextCandidate",
    "AgentShellAuditReadonlyViewCandidate",
    "AgentToolAuditReadonlyViewCandidate",
    "AgentTaskAdviceCandidate",
    "AgentTaskCandidate",
    "AgentTaskContextCandidate",
    "AGENT_SHELL_AUDIT_READONLY_VIEW_SOURCE",
    "AGENT_SHELL_AUDIT_READONLY_VIEW_VERSION",
    "AGENT_TOOL_AUDIT_READONLY_VIEW_SOURCE",
    "AGENT_TOOL_AUDIT_READONLY_VIEW_VERSION",
    "AGENT_PRODUCT_GATEWAY_RESPONSE_VIEW_SOURCE",
    "AGENT_PRODUCT_GATEWAY_RESPONSE_VIEW_VERSION",
    "GOVERNANCE_PRECONDITION_SUMMARY_SOURCE",
    "GOVERNANCE_PRECONDITION_SUMMARY_VERSION",
    "GOVERNANCE_EVIDENCE_SUMMARY_VIEW_SOURCE",
    "GOVERNANCE_EVIDENCE_SUMMARY_VIEW_VERSION",
    "GOVERNED_RUN_EVIDENCE_CONTEXT_SOURCE",
    "GOVERNED_RUN_EVIDENCE_CONTEXT_VERSION",
    "LLM_CALL_OBSERVATION_SUMMARY_SOURCE",
    "LLM_INVOCATION_RESULT_SUMMARY_SOURCE",
    "LLM_INVOCATION_SUMMARY_VERSION",
    "PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION",
    "READONLY_RUNTIME_CONTEXT_SOURCE",
    "READONLY_RUNTIME_CONTEXT_VERSION",
    "TASK_ADVICE_SOURCE",
    "TASK_ADVICE_VERSION",
    "TASK_ADVICE_CONSUMPTION_PAYLOAD_SOURCE",
    "TASK_ADVICE_CONSUMPTION_PAYLOAD_VERSION",
    "TASK_CONTEXT_SOURCE",
    "TASK_CONTEXT_VERSION",
    "build_agent_shell_audit_readonly_view",
    "build_agent_tool_audit_readonly_view",
    "build_agent_product_gateway_response_view_candidate",
    "build_agent_task_advice_candidate",
    "build_agent_task_advice_consumption_payload",
    "build_agent_task_context_candidate",
    "build_agent_governed_run_evidence_context_candidate",
    "build_agent_readonly_runtime_context_candidate",
    "build_agent_llm_invocation_summary_from_invocation_result",
    "build_agent_llm_invocation_summary_from_observation_candidate",
    "build_agent_llm_invocation_summary_from_public_shape",
    "build_agent_governance_evidence_summary_view",
    "build_agent_governance_view_from_precondition_summary",
    "build_agent_governance_view_candidate",
]
