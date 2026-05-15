import pytest
from pydantic import ValidationError

from config_contexts.governance_candidate import (
    ActionCandidateConfigViewCandidate,
    AdkRunConfigViewCandidate,
    ReleaseGovernanceConfigViewCandidate,
    ServiceBundleViewCandidate,
)


def test_adk_run_config_view_candidate_expresses_mapped_fields() -> None:
    view = AdkRunConfigViewCandidate(
        max_llm_calls=12,
        response_modalities=("TEXT",),
        save_input_blobs_as_artifacts=True,
        support_cfc=False,
        streaming_mode="sse",
        get_session_num_recent_events=5,
        custom_metadata_keys=("workflow_name",),
    )

    assert view.config_view_semantics == "candidate_only"
    assert view.execution_enabled is False
    assert view.requires_operator_confirmation is True
    assert view.max_llm_calls == 12


def test_service_bundle_view_candidate_does_not_allow_service_instances() -> None:
    view = ServiceBundleViewCandidate(
        source="in_memory",
        artifact_service_source="in_memory",
        session_service_source="in_memory",
        service_lifecycle_policy="candidate_review_only",
    )

    assert view.external_service_instance_allowed is False

    with pytest.raises(ValidationError):
        ServiceBundleViewCandidate(external_service_instance_allowed=True)


def test_release_governance_config_view_candidate_keeps_secret_values_out() -> None:
    view = ReleaseGovernanceConfigViewCandidate(
        release_target="cognition-engine",
        target_version="0.6.0",
        phase="pre-release",
        provider_allowlist=("check_public_surface.py", "check_release_tokens.py"),
        token_presence_check_mode="presence_only",
        trusted_publishing_check_mode="configuration_check_only",
    )

    assert view.release_action_enabled is False
    assert view.credential_value_allowed is False

    with pytest.raises(ValidationError):
        ReleaseGovernanceConfigViewCandidate(credential_value_allowed=True)


def test_action_candidate_config_view_rejects_real_actions() -> None:
    view = ActionCandidateConfigViewCandidate(
        allowed_action_kinds=("prepare_release", "prepare_run_config_update"),
    )

    assert view.reviewer_executor_separation_required is True
    assert view.requires_decision_candidate_ref is True
    assert view.execution_enabled is False

    with pytest.raises(ValidationError):
        ActionCandidateConfigViewCandidate(allowed_action_kinds=("release",))

    with pytest.raises(ValidationError):
        ActionCandidateConfigViewCandidate(runtime_execution_enabled=True)
