"""Thin facade for external-readonly governed summary facts contracts."""

from behavior_contracts.external_readonly_governed_summary_facts import (
    DEFAULT_EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_GUARDS,
    ExternalReadonlyGovernedSummaryFactsContentGuard,
    ExternalReadonlyGovernedSummaryFactsHeaderGuard,
    ExternalReadonlyGovernedSummaryFactsNoRawBoundaryGuard,
    validate_external_readonly_governed_summary_facts_guards,
)
from schemas.external_readonly_governed_summary_facts import (
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_PAYLOAD_TYPE,
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_STATUSES,
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_VERSION,
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX,
    ExternalReadonlyGovernedSummaryFactSchema,
    ExternalReadonlyGovernedSummaryFactsRawBoundaryFlagsSchema,
    ExternalReadonlyGovernedSummaryFactsSchema,
    ExternalReadonlyGovernedSummaryFactsStatus,
    validate_external_readonly_governed_summary_facts,
)

__all__ = [
    "DEFAULT_EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_GUARDS",
    "EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_PAYLOAD_TYPE",
    "EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_STATUSES",
    "EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_VERSION",
    "EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX",
    "ExternalReadonlyGovernedSummaryFactSchema",
    "ExternalReadonlyGovernedSummaryFactsContentGuard",
    "ExternalReadonlyGovernedSummaryFactsHeaderGuard",
    "ExternalReadonlyGovernedSummaryFactsNoRawBoundaryGuard",
    "ExternalReadonlyGovernedSummaryFactsRawBoundaryFlagsSchema",
    "ExternalReadonlyGovernedSummaryFactsSchema",
    "ExternalReadonlyGovernedSummaryFactsStatus",
    "validate_external_readonly_governed_summary_facts",
    "validate_external_readonly_governed_summary_facts_guards",
]
