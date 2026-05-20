"""Thin facade package for Cognition Engine contract-core entries."""

from contract_core import (
    controlled_execution,
    evidence_summary_answer,
    external_readonly_archive,
    external_readonly_evidence,
    external_readonly_governed_summary_facts,
    governance,
    llm_invocation,
    model_routing,
    product_gateway_cli,
    product_gateway_response_summary,
    runtime,
)

__all__ = [
    "controlled_execution",
    "evidence_summary_answer",
    "external_readonly_archive",
    "external_readonly_evidence",
    "external_readonly_governed_summary_facts",
    "governance",
    "llm_invocation",
    "model_routing",
    "product_gateway_cli",
    "product_gateway_response_summary",
    "runtime",
]
