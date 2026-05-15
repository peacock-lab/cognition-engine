from behavior_contracts.governance_candidate import (
    CandidateOnlyGuard,
    DEFAULT_GOVERNANCE_CANDIDATE_GUARDS,
    NoAdkNativeObjectLeakageGuard,
    NoExecutionGuard,
    NoReleaseActionGuard,
    NoRuntimeActionGuard,
    OperatorConfirmationRequiredGuard,
    ProductAgentOutputGovernanceDomainGuard,
    ReviewerExecutorSeparationGuard,
    SensitiveOutputRedactionGuard,
    validate_governance_candidate_guards,
)


def test_candidate_guards_accept_safe_action_candidate() -> None:
    candidate = {
        "action_semantics": "candidate_only",
        "execution_enabled": False,
        "requires_operator_confirmation": True,
        "reviewer": "reviewer-a",
        "executor": "executor-b",
        "action_kind": "prepare_pypi_upload",
        "metadata": {"raw_output_digest": "sha256:abc"},
    }

    result = validate_governance_candidate_guards(candidate)

    assert result.passed is True
    assert result.violations == ()


def test_candidate_only_guard_requires_candidate_semantics() -> None:
    result = CandidateOnlyGuard().validate({"execution_enabled": False})

    assert result.passed is False
    assert "candidate_only" in result.violations[0]


def test_no_execution_guard_rejects_enabled_execution() -> None:
    result = NoExecutionGuard().validate({"execution_enabled": True})

    assert result.passed is False
    assert "execution_enabled" in result.violations[0]


def test_operator_confirmation_guard_requires_true() -> None:
    result = OperatorConfirmationRequiredGuard().validate(
        {"requires_operator_confirmation": False}
    )

    assert result.passed is False
    assert "requires_operator_confirmation" in result.violations[0]


def test_reviewer_executor_separation_guard_rejects_same_actor() -> None:
    result = ReviewerExecutorSeparationGuard().validate(
        {"reviewer": "operator-a", "executor": "operator-a"}
    )

    assert result.passed is False
    assert "separate" in result.violations[0]


def test_release_and_runtime_action_guards_reject_formal_actions() -> None:
    release_result = NoReleaseActionGuard().validate({"action_kind": "release"})
    runtime_result = NoRuntimeActionGuard().validate({"action_kind": "runtime_fix"})

    assert release_result.passed is False
    assert runtime_result.passed is False


def test_adk_native_object_guard_rejects_runtime_object_marker() -> None:
    result = NoAdkNativeObjectLeakageGuard().validate(
        {"metadata": {"run_config": {"object_module": "google.adk.runners"}}}
    )

    assert result.passed is False
    assert "Runtime object leakage" in result.violations[0]


def test_sensitive_output_guard_rejects_raw_and_secret_fields() -> None:
    result = SensitiveOutputRedactionGuard().validate(
        {"metadata": {"stdout": "raw output", "api_token": "secret"}}
    )

    assert result.passed is False
    assert len(result.violations) == 2


def _safe_product_agent_output_candidate() -> dict[str, object]:
    return {
        "policy_domain": "product_agent_output_governance",
        "candidate_scope": "product_agent_output_governance_decision_candidate",
        "decision_semantics": "candidate_only",
        "formal_decision_enabled": False,
        "formal_outcome_enabled": False,
        "policy_execution_enabled": False,
        "governance_outcome_enabled": False,
        "release_action_enabled": False,
        "requires_operator_confirmation": True,
        "domain_metadata": {
            "product_gateway_request_id": "request-product-agent-1",
            "product_gateway_entry_kind": "agent_shell",
            "product_gateway_status": "success",
            "product_gateway_exit_code": 0,
            "agent_advice_candidate_id": "agent-advice-1",
            "agent_advice_status": "ready_for_product_gateway_review",
            "agent_advice_recommendation": "continue_with_product_gateway_review",
            "ready_for_review": True,
            "evidence_statuses": ["success"],
            "missing_evidence": [],
            "warning_candidates": [],
            "block_candidates": [],
            "human_review_reasons": [],
            "summary_only": True,
            "refs_only": True,
            "candidate_only": True,
        },
    }


def test_product_agent_output_governance_guard_accepts_safe_candidate() -> None:
    result = validate_governance_candidate_guards(_safe_product_agent_output_candidate())

    assert result.passed is True
    assert result.violations == ()


def test_product_agent_output_governance_guard_rejects_unknown_metadata_key() -> None:
    candidate = _safe_product_agent_output_candidate()
    candidate["domain_metadata"] = {
        "summary_only": True,
        "refs_only": True,
        "candidate_only": True,
        "internal_payload_ref": "not-public",
    }

    result = ProductAgentOutputGovernanceDomainGuard().validate(candidate)

    assert result.passed is False
    assert "internal_payload_ref" in result.violations[0]


def test_product_agent_output_governance_guard_rejects_false_boundary_flags() -> None:
    candidate = _safe_product_agent_output_candidate()
    candidate["domain_metadata"] = {
        "summary_only": True,
        "refs_only": False,
        "candidate_only": True,
    }

    result = ProductAgentOutputGovernanceDomainGuard().validate(candidate)

    assert result.passed is False
    assert "refs_only" in result.violations[0]


def test_product_agent_output_governance_guard_rejects_raw_output_keys() -> None:
    candidate = _safe_product_agent_output_candidate()
    candidate["metadata"] = {
        "prompt": "raw prompt",
        "provider_response": "raw provider response",
        "tool_input": "raw tool input",
        "tool_output": "raw tool output",
        "message": "raw message",
    }

    result = ProductAgentOutputGovernanceDomainGuard().validate(candidate)

    assert result.passed is False
    assert len(result.violations) == 5


def test_product_agent_output_governance_guard_rejects_action_fields() -> None:
    candidate = _safe_product_agent_output_candidate()
    candidate.update(
        {
            "action_kind": "prepare_product_agent_action",
            "release_action_kind": "release",
            "runtime_action_kind": "execute_workflow",
            "release_action_result": "released",
            "execution_result": "executed",
            "can_release": True,
            "can_publish": True,
            "tag_release_and_publish": True,
        }
    )

    result = ProductAgentOutputGovernanceDomainGuard().validate(candidate)

    assert result.passed is False
    assert len(result.violations) == 8


def test_product_agent_output_governance_guard_rejects_release_reason() -> None:
    candidate = _safe_product_agent_output_candidate()
    candidate["blocked_formal_outcome_reasons"] = [
        "Release action boundary review is pending."
    ]

    result = ProductAgentOutputGovernanceDomainGuard().validate(candidate)

    assert result.passed is False
    assert "release action boundary" in result.violations[0]


def test_default_guards_include_product_agent_output_governance_guard() -> None:
    assert any(
        isinstance(guard, ProductAgentOutputGovernanceDomainGuard)
        for guard in DEFAULT_GOVERNANCE_CANDIDATE_GUARDS
    )


def test_product_agent_output_governance_guard_noops_for_other_domains() -> None:
    result = ProductAgentOutputGovernanceDomainGuard().validate(
        {
            "policy_domain": "release_governance",
            "domain_metadata": {"target_version": "0.7.0"},
            "action_kind": "release",
        }
    )

    assert result.passed is True
    assert result.violations == ()
