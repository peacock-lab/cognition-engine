"""Product application assembly package for Cognition System."""

from product_application_assembly.external_readonly_refs import (
    ExternalReadonlyRefsProductApplicationAssemblyResult,
    assemble_external_readonly_refs_product_application,
)
from product_application_assembly.evidence_summary_answer_context import (
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_ANSWER_POLICY_REF,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_CITATION_POLICY_REF,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_SOURCE,
    build_evidence_summary_answer_context,
    evidence_summary_answer_context_status_dict,
)
from product_application_assembly.evidence_summary_answer_generation import (
    EVIDENCE_SUMMARY_ANSWER_GENERATION_INTERACTION_MODE,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_GENERATED_RESULT_POLICY_REF,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_GENERATION_SOURCE,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_LLM_REQUEST_POLICY_REF,
    build_evidence_summary_answer_llm_invocation_request,
    build_evidence_summary_answer_result_from_llm_invocation_result,
)
from product_application_assembly.evidence_summary_answer_result import (
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_POLICY_REF,
    PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_SOURCE,
    build_no_model_evidence_summary_answer_result,
    evidence_summary_answer_result_status_dict,
)
from product_application_assembly.governed_evidence_digest import (
    PRODUCT_APPLICATION_GOVERNED_EVIDENCE_DIGEST_POLICY_REF,
    PRODUCT_APPLICATION_GOVERNED_EVIDENCE_DIGEST_SOURCE,
    build_governed_evidence_digest_from_external_readonly_facts,
    governed_evidence_digest_status_dict,
)

PRODUCT_APPLICATION_ASSEMBLY_PACKAGE = "product_application_assembly"
PRODUCT_APPLICATION_ASSEMBLY_STATUS = "skeleton"

__all__ = (
    "ExternalReadonlyRefsProductApplicationAssemblyResult",
    "EVIDENCE_SUMMARY_ANSWER_GENERATION_INTERACTION_MODE",
    "PRODUCT_APPLICATION_ASSEMBLY_PACKAGE",
    "PRODUCT_APPLICATION_ASSEMBLY_STATUS",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_ANSWER_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_CITATION_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_CONTEXT_SOURCE",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_GENERATED_RESULT_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_GENERATION_SOURCE",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_LLM_REQUEST_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_RESULT_SOURCE",
    "PRODUCT_APPLICATION_GOVERNED_EVIDENCE_DIGEST_POLICY_REF",
    "PRODUCT_APPLICATION_GOVERNED_EVIDENCE_DIGEST_SOURCE",
    "assemble_external_readonly_refs_product_application",
    "build_evidence_summary_answer_context",
    "build_evidence_summary_answer_llm_invocation_request",
    "build_evidence_summary_answer_result_from_llm_invocation_result",
    "build_governed_evidence_digest_from_external_readonly_facts",
    "build_no_model_evidence_summary_answer_result",
    "evidence_summary_answer_context_status_dict",
    "evidence_summary_answer_result_status_dict",
    "governed_evidence_digest_status_dict",
)
