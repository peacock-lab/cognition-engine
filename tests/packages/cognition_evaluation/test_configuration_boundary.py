from __future__ import annotations

import pytest
from pydantic import ValidationError

from cognition_evaluation import (
    ConfigurationBoundarySnapshot,
    evaluate_configuration_boundary,
    evaluation_summary_from_result,
)


def test_configuration_boundary_passes_clean_snapshot() -> None:
    result = evaluate_configuration_boundary(
        ConfigurationBoundarySnapshot(
            config_ref="config://single-source/publication-boundary",
            install_default_config_owner="config_assembly/default_config",
        )
    )

    assert result.status == "passed"
    assert result.profile_ref is not None
    assert result.profile_ref.ref == "evaluation-profile://configuration-boundary/v1"
    assert result.metadata["governance_decision"] is False

    summary = evaluation_summary_from_result(result)
    assert summary.status == "passed"
    assert summary.finding_count == 0


def test_configuration_boundary_flags_private_root_config_publication() -> None:
    result = evaluate_configuration_boundary(
        ConfigurationBoundarySnapshot(
            config_ref="config://release-boundary",
            root_config_published_as_package=True,
            root_config_synced_to_public_repo=True,
            release_distribution_includes_root_config=True,
        )
    )

    assert result.status == "failed"
    criteria = {finding.criterion for finding in result.findings}
    assert "root_config_private_source_boundary" in criteria
    assert "public_repository_config_boundary" in criteria
    assert "config_release_boundary" in criteria
    assert any(finding.severity == "blocking" for finding in result.findings)


def test_configuration_boundary_flags_context_and_assembly_misuse() -> None:
    result = evaluate_configuration_boundary(
        ConfigurationBoundarySnapshot(
            config_ref="config://default-resource-boundary",
            install_default_config_owner="config_contexts/default_config",
            config_contexts_contains_default_resources=["default_config/providers.yaml"],
            config_contexts_used_as_fact_source=["provider profile fact source"],
        )
    )

    assert result.status == "failed"
    criteria = {finding.criterion for finding in result.findings}
    assert "install_state_default_config_boundary" in criteria
    assert "config_contexts_contract_view_boundary" in criteria


def test_configuration_boundary_flags_stable_consumption_and_public_paths() -> None:
    result = evaluate_configuration_boundary(
        ConfigurationBoundarySnapshot(
            config_ref="config://provider-profile",
            direct_root_config_consumers=["packages/product_runtime_assembly"],
            provider_profiles_without_config_contexts=["gemma4_pro_local"],
            provider_profiles_without_config_assembly_defaults=["deepseek_v4_flash"],
            public_repo_forbidden_config_paths=["config/local.yaml"],
            stable_config_consumption_without_contexts=["provider.model_aliases"],
        )
    )

    assert result.status == "failed"
    criteria = {finding.criterion for finding in result.findings}
    assert "config_single_source_of_truth" in criteria
    assert "provider_profile_config_boundary" in criteria
    assert "config_assembly_default_resource_boundary" in criteria
    assert "public_repository_config_boundary" in criteria
    assert "config_fact_stable_consumption" in criteria


def test_configuration_boundary_rejects_secret_markers() -> None:
    with pytest.raises(ValidationError):
        ConfigurationBoundarySnapshot(
            config_ref="config://bad",
            secret_or_local_only_config_paths=["config/provider_token.yaml"],
        )
