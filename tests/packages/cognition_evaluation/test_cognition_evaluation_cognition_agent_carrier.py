from cognition_evaluation.cognition_agent_carrier import (
    evaluate_agent_carrier_contract_boundary,
    evaluate_agent_response_projection_boundary,
    evaluate_agent_resume_request_boundary,
    evaluate_material_consumption_contract_boundary,
)


AGENT_CARRIER_REF = "cognition-agent-carrier://carrier-1"
AGENT_RESUME_REQUEST_REF = "cognition-agent-resume-request://resume-1"
AGENT_RESPONSE_REF = "cognition-agent-response://response-1"
MATERIAL_CONSUMPTION_REF = "cognition-agent-material-consumption://material-1"
SESSION_REF = "continuable-evidence-session://session-1"
RUNTIME_BINDING_REF = "continuable-evidence-session-runtime-binding://binding-1"
EVIDENCE_REF = "evidence://external-readonly/source-1"
DIGEST_REF = "governed-evidence-digest://digest-1"
OBSERVABILITY_REF = "evidence-summary-answer-observability-summary://obs-1"
EVALUATION_REF = "evaluation://cognition-agent/response-1"


def test_agent_carrier_contract_boundary_passes_safe_candidate():
    result = evaluate_agent_carrier_contract_boundary(
        agent_carrier_ref=AGENT_CARRIER_REF,
        product_intent_summary="Continue a governed evidence session.",
        candidate_only=True,
        readonly=True,
        evidence_material_refs=[EVIDENCE_REF, DIGEST_REF],
        runtime_binding_refs=[RUNTIME_BINDING_REF],
    )

    assert result.status == "passed"
    assert result.findings == []


def test_agent_resume_request_boundary_fails_auto_resume_answer():
    result = evaluate_agent_resume_request_boundary(
        agent_resume_request_ref=AGENT_RESUME_REQUEST_REF,
        agent_carrier_ref=AGENT_CARRIER_REF,
        continuable_evidence_session_ref=SESSION_REF,
        requires_user_confirmation=True,
        requires_external_readonly_authorization=True,
        auto_resume_answer_enabled=True,
    )

    assert result.status == "failed"
    assert any(
        item.criterion == "agent_resume_request_auto_resume_answer_enabled"
        for item in result.findings
    )


def test_agent_response_projection_boundary_warns_without_summary_refs():
    result = evaluate_agent_response_projection_boundary(
        agent_response_ref=AGENT_RESPONSE_REF,
        agent_carrier_ref=AGENT_CARRIER_REF,
    )

    assert result.status == "warning"
    assert {
        item.criterion
        for item in result.findings
    } == {
        "agent_response_evaluation_summary_ref",
        "agent_response_observability_summary_ref",
    }


def test_agent_response_projection_boundary_fails_raw_provider_response():
    result = evaluate_agent_response_projection_boundary(
        agent_response_ref=AGENT_RESPONSE_REF,
        agent_carrier_ref=AGENT_CARRIER_REF,
        observability_summary_ref=OBSERVABILITY_REF,
        evaluation_summary_ref=EVALUATION_REF,
        raw_provider_response_included=True,
    )

    assert result.status == "failed"
    assert any(
        item.criterion == "agent_response_projection_raw_provider_response_included"
        for item in result.findings
    )


def test_material_consumption_contract_boundary_requires_refs_only():
    result = evaluate_material_consumption_contract_boundary(
        material_consumption_ref=MATERIAL_CONSUMPTION_REF,
        agent_carrier_ref=AGENT_CARRIER_REF,
        source_layer="external_readonly",
        evidence_refs=[EVIDENCE_REF],
        digest_refs=[DIGEST_REF],
        refs_only=False,
        provider_implementation_included=True,
    )

    assert result.status == "failed"
    assert {
        item.criterion
        for item in result.findings
    } >= {
        "material_consumption_refs_only",
        "material_consumption_provider_implementation_included",
    }
