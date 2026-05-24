"""Evaluation contracts and helpers for Cognition System."""

from cognition_evaluation.adk_native import detect_adk_native_evaluation_capability
from cognition_evaluation.architecture_boundary import (
    ARCHITECTURE_BOUNDARY_EVALUATION_PROFILE,
    ArchitectureBoundarySnapshot,
    evaluate_architecture_boundary,
)
from cognition_evaluation.configuration_boundary import (
    CONFIGURATION_BOUNDARY_EVALUATION_PROFILE,
    ConfigurationBoundarySnapshot,
    evaluate_configuration_boundary,
)
from cognition_evaluation.contract_boundary import (
    CONTRACT_BOUNDARY_EVALUATION_PROFILE,
    ContractBoundarySnapshot,
    evaluate_contract_boundary,
)
from cognition_evaluation.evidence_summary_answer import (
    answer_matches_requested_output_language,
    answer_matches_requested_output_length,
    evaluate_requested_output_constraints,
    evaluation_input_for_answer,
    requested_output_chars,
    requested_output_language,
)
from cognition_evaluation.models import (
    AdkNativeEvaluationCapability,
    EvaluationCriterion,
    EvaluationFinding,
    EvaluationInput,
    EvaluationProfileRef,
    EvaluationRef,
    EvaluationResult,
    EvaluationSubject,
    EvaluationSummary,
    evaluation_summary_from_result,
)

__all__ = (
    "ARCHITECTURE_BOUNDARY_EVALUATION_PROFILE",
    "AdkNativeEvaluationCapability",
    "ArchitectureBoundarySnapshot",
    "CONFIGURATION_BOUNDARY_EVALUATION_PROFILE",
    "CONTRACT_BOUNDARY_EVALUATION_PROFILE",
    "ConfigurationBoundarySnapshot",
    "ContractBoundarySnapshot",
    "EvaluationCriterion",
    "EvaluationFinding",
    "EvaluationInput",
    "EvaluationProfileRef",
    "EvaluationRef",
    "EvaluationResult",
    "EvaluationSubject",
    "EvaluationSummary",
    "answer_matches_requested_output_language",
    "answer_matches_requested_output_length",
    "detect_adk_native_evaluation_capability",
    "evaluate_architecture_boundary",
    "evaluate_configuration_boundary",
    "evaluate_contract_boundary",
    "evaluate_requested_output_constraints",
    "evaluation_input_for_answer",
    "evaluation_summary_from_result",
    "requested_output_chars",
    "requested_output_language",
)
