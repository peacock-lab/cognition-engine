from behavior_contracts.cognition_agent_carrier import (
    guard_cognition_agent_carrier_raw_boundary,
    guard_cognition_agent_material_consumption_refs_only,
    guard_cognition_agent_resume_request_boundary,
    guard_cognition_agent_runtime_claims,
    validate_cognition_agent_carrier_guards,
)


AGENT_CARRIER_REF = "cognition-agent-carrier://carrier-1"
AGENT_RESUME_REQUEST_REF = "cognition-agent-resume-request://resume-1"
MATERIAL_CONSUMPTION_REF = "cognition-agent-material-consumption://material-1"
SESSION_REF = "continuable-evidence-session://session-1"
RUNTIME_BINDING_REF = "continuable-evidence-session-runtime-binding://binding-1"
EVIDENCE_REF = "evidence://external-readonly/source-1"
DIGEST_REF = "governed-evidence-digest://digest-1"


def test_cognition_agent_carrier_guards_allow_safe_carrier():
    result = validate_cognition_agent_carrier_guards(
        {
            "payload_type": "cognition_agent_carrier",
            "agent_carrier_ref": AGENT_CARRIER_REF,
            "agent_carrier_status": "contract_ready",
            "product_intent_summary": "Continue a governed evidence session.",
            "continuable_evidence_session_ref": SESSION_REF,
            "evidence_material_refs": [EVIDENCE_REF, DIGEST_REF],
            "runtime_binding_refs": [RUNTIME_BINDING_REF],
            "candidate_only": True,
            "readonly": True,
            "execution_enabled": False,
            "agent_runtime_enabled": False,
            "adk_raw_object_included": False,
        }
    )

    assert result.passed is True
    assert result.violations == ()


def test_cognition_agent_carrier_raw_boundary_blocks_sensitive_payload():
    result = guard_cognition_agent_carrier_raw_boundary(
        {
            "payload_type": "cognition_agent_carrier",
            "agent_carrier_ref": AGENT_CARRIER_REF,
            "raw_prompt": "do not store",
        }
    )

    assert result.passed is False
    assert any("forbidden_raw_boundary_key" in item for item in result.violations)


def test_cognition_agent_carrier_runtime_claims_block_model_call():
    result = guard_cognition_agent_runtime_claims(
        {
            "payload_type": "cognition_agent_resume_request",
            "agent_resume_request_ref": AGENT_RESUME_REQUEST_REF,
            "model_call_requested": True,
        }
    )

    assert result.passed is False
    assert result.violations == ("$.model_call_requested:runtime_claim_forbidden",)


def test_cognition_agent_resume_request_guard_blocks_auto_resume():
    result = guard_cognition_agent_resume_request_boundary(
        {
            "payload_type": "cognition_agent_resume_request",
            "agent_resume_request_ref": AGENT_RESUME_REQUEST_REF,
            "agent_carrier_ref": AGENT_CARRIER_REF,
            "continuable_evidence_session_ref": SESSION_REF,
            "requires_user_confirmation": True,
            "requires_external_readonly_authorization": True,
            "auto_resume_answer_enabled": True,
        }
    )

    assert result.passed is False
    assert "auto_resume_answer_enabled:must_be_false" in result.violations


def test_cognition_agent_material_consumption_guard_requires_refs_only():
    result = guard_cognition_agent_material_consumption_refs_only(
        {
            "payload_type": "cognition_agent_material_consumption",
            "material_consumption_ref": MATERIAL_CONSUMPTION_REF,
            "agent_carrier_ref": AGENT_CARRIER_REF,
            "source_layer": "external_readonly",
            "evidence_refs": [EVIDENCE_REF],
            "digest_refs": [DIGEST_REF],
            "refs_only": False,
            "provider_implementation_included": True,
        }
    )

    assert result.passed is False
    assert "refs_only:must_be_true" in result.violations
    assert "provider_implementation_included:must_be_false" in result.violations
