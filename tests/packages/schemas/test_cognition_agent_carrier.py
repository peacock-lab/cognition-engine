import pytest

from schemas.cognition_agent_carrier import (
    CognitionAgentCarrierSchema,
    CognitionAgentMaterialConsumptionSchema,
    CognitionAgentResponseProjectionSchema,
    CognitionAgentResumeRequestSchema,
)


AGENT_CARRIER_REF = "cognition-agent-carrier://carrier-1"
AGENT_RESUME_REQUEST_REF = "cognition-agent-resume-request://resume-1"
AGENT_RESPONSE_REF = "cognition-agent-response://response-1"
MATERIAL_CONSUMPTION_REF = "cognition-agent-material-consumption://material-1"
SESSION_REF = "continuable-evidence-session://session-1"
RUNTIME_BINDING_REF = "continuable-evidence-session-runtime-binding://binding-1"
EVIDENCE_REF = "evidence://external-readonly/source-1"
DIGEST_REF = "governed-evidence-digest://digest-1"
ANSWER_CONTEXT_REF = "evidence-summary-answer-context://context-1"
ANSWER_RUN_REF = "evidence-summary-answer-run://run-1"
ANSWER_ARTIFACT_REF = "evidence-summary-answer-artifact://artifact-1"
TRACE_INSPECT_REF = "evidence-summary-answer-trace-inspect://inspect-1"
OBSERVABILITY_REF = "evidence-summary-answer-observability-summary://obs-1"
EVALUATION_REF = "evaluation://cognition-agent/response-1"


def test_cognition_agent_carrier_contracts_validate():
    carrier = CognitionAgentCarrierSchema(
        agent_carrier_id="carrier-1",
        agent_carrier_ref=AGENT_CARRIER_REF,
        agent_carrier_status="contract_ready",
        product_intent_summary="Continue a governed evidence session.",
        continuable_evidence_session_ref=SESSION_REF,
        evidence_material_refs=[EVIDENCE_REF, DIGEST_REF],
        runtime_binding_refs=[RUNTIME_BINDING_REF],
        response_projection_refs=[AGENT_RESPONSE_REF],
    )
    resume_request = CognitionAgentResumeRequestSchema(
        agent_resume_request_id="resume-1",
        agent_resume_request_ref=AGENT_RESUME_REQUEST_REF,
        agent_carrier_ref=AGENT_CARRIER_REF,
        continuable_evidence_session_ref=SESSION_REF,
        resume_authorization_state="requires_confirmation",
        evidence_material_refs=[EVIDENCE_REF, DIGEST_REF],
        runtime_binding_refs=[RUNTIME_BINDING_REF],
        requested_user_action="prepare_resume",
    )
    response_projection = CognitionAgentResponseProjectionSchema(
        agent_response_id="response-1",
        agent_response_ref=AGENT_RESPONSE_REF,
        agent_carrier_ref=AGENT_CARRIER_REF,
        agent_resume_request_ref=AGENT_RESUME_REQUEST_REF,
        answer_run_ref=ANSWER_RUN_REF,
        answer_artifact_ref=ANSWER_ARTIFACT_REF,
        trace_inspect_ref=TRACE_INSPECT_REF,
        observability_summary_ref=OBSERVABILITY_REF,
        evaluation_summary_ref=EVALUATION_REF,
        recovery_hints=["Ask the user to confirm before resume."],
        boundary_hints=["Preview only; no model call has been performed."],
    )
    material_consumption = CognitionAgentMaterialConsumptionSchema(
        material_consumption_id="material-1",
        material_consumption_ref=MATERIAL_CONSUMPTION_REF,
        agent_carrier_ref=AGENT_CARRIER_REF,
        evidence_refs=[EVIDENCE_REF],
        digest_refs=[DIGEST_REF],
        answer_context_refs=[ANSWER_CONTEXT_REF],
        answer_run_refs=[ANSWER_RUN_REF],
        artifact_refs=[ANSWER_ARTIFACT_REF],
        trace_inspect_refs=[TRACE_INSPECT_REF],
        observability_summary_refs=[OBSERVABILITY_REF],
    )

    assert carrier.candidate_only is True
    assert resume_request.auto_resume_answer_enabled is False
    assert response_projection.raw_provider_response_included is False
    assert material_consumption.refs_only is True


def test_cognition_agent_carrier_rejects_invalid_ref_prefix():
    with pytest.raises(ValueError):
        CognitionAgentCarrierSchema(
            agent_carrier_id="carrier-1",
            agent_carrier_ref="adk-agent://raw",
            product_intent_summary="Continue a governed evidence session.",
        )


def test_cognition_agent_carrier_rejects_non_candidate_runtime_claim():
    with pytest.raises(ValueError):
        CognitionAgentCarrierSchema(
            agent_carrier_id="carrier-1",
            agent_carrier_ref=AGENT_CARRIER_REF,
            product_intent_summary="Continue a governed evidence session.",
            candidate_only=False,
        )


def test_cognition_agent_resume_request_rejects_auto_resume_answer():
    with pytest.raises(ValueError):
        CognitionAgentResumeRequestSchema(
            agent_resume_request_id="resume-1",
            agent_resume_request_ref=AGENT_RESUME_REQUEST_REF,
            agent_carrier_ref=AGENT_CARRIER_REF,
            continuable_evidence_session_ref=SESSION_REF,
            requested_user_action="prepare_resume",
            auto_resume_answer_enabled=True,
        )


def test_cognition_agent_response_projection_rejects_raw_provider_response():
    with pytest.raises(ValueError):
        CognitionAgentResponseProjectionSchema(
            agent_response_id="response-1",
            agent_response_ref=AGENT_RESPONSE_REF,
            agent_carrier_ref=AGENT_CARRIER_REF,
            raw_provider_response_included=True,
        )


def test_cognition_agent_material_consumption_requires_refs_only():
    with pytest.raises(ValueError):
        CognitionAgentMaterialConsumptionSchema(
            material_consumption_id="material-1",
            material_consumption_ref=MATERIAL_CONSUMPTION_REF,
            agent_carrier_ref=AGENT_CARRIER_REF,
            evidence_refs=[EVIDENCE_REF],
            digest_refs=[DIGEST_REF],
            refs_only=False,
        )
