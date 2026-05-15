from __future__ import annotations

from pathlib import Path

from config_assembly.runtime import assemble_runtime_config_payload
from config_contexts.runtime_builder import build_runtime_config_contexts
from runtime_container.cli_reference_reader import (
    REFERENCE_READER_TOOL_NAME,
    REFERENCE_READER_TOOLSET_NAME,
)
from runtime_container.cli_tool_exposure_profile import (
    CLI_TOOL_EXPOSURE_CONFIG_PRECEDENCE,
    cli_tool_exposure_profile_status_dict,
    resolve_cli_tool_exposure_profile,
)
from runtime_container.cli_toolset_admission import CliToolOperationFactsCandidate


def test_default_profile_exposes_local_reference_reader(tmp_path) -> None:
    resolution = resolve_cli_tool_exposure_profile(repo_root=tmp_path)
    status = cli_tool_exposure_profile_status_dict(resolution)

    assert resolution.status == "resolved"
    assert resolution.exposed_tool_names == (REFERENCE_READER_TOOL_NAME,)
    assert resolution.blocking_reasons == ()
    assert resolution.reference_reader_policy is not None
    assert resolution.reference_reader_policy.allowed_roots == (str(tmp_path.resolve()),)
    assert status["profile"]["config_precedence"] == list(
        CLI_TOOL_EXPOSURE_CONFIG_PRECEDENCE
    )
    assert status["reference_reader_policy"]["allowed_roots"] == [
        str(tmp_path.resolve())
    ]


def test_runtime_config_tool_exposure_mapping_feeds_profile_resolution(tmp_path) -> None:
    bundle = build_runtime_config_contexts(
        assemble_runtime_config_payload(Path("config"), environment="local")
    )
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()

    resolution = resolve_cli_tool_exposure_profile(
        repo_root=tmp_path,
        profile_name=bundle.tool_exposure.default_profile,
        profile_config=bundle.tool_exposure.to_profile_config(),
    )

    assert resolution.status == "resolved"
    assert resolution.exposed_tool_names == (REFERENCE_READER_TOOL_NAME,)
    assert resolution.reference_reader_policy is not None
    assert str(tasks_dir.resolve()) in resolution.reference_reader_policy.allowed_roots


def test_cli_selection_can_only_narrow_governance_allowlist(tmp_path) -> None:
    config = {
        "profiles": {
            "readonly_reference": {
                "toolsets": [
                    {
                        "toolset_name": REFERENCE_READER_TOOLSET_NAME,
                        "toolset_kind": "toolset",
                        "source_ref": "local-reference-reader://workspace",
                        "allowlist_tool_names": [REFERENCE_READER_TOOL_NAME],
                        "tool_filter": [REFERENCE_READER_TOOL_NAME],
                        "reference_reader": {"allowed_roots": ["tasks"]},
                    }
                ],
            }
        }
    }

    narrowed = resolve_cli_tool_exposure_profile(
        repo_root=tmp_path,
        profile_config=config,
        cli_explicit_args={"selected_tool_names": [REFERENCE_READER_TOOL_NAME]},
    )
    widened = resolve_cli_tool_exposure_profile(
        repo_root=tmp_path,
        profile_config=config,
        cli_explicit_args={"selected_tool_names": ["delete_everything"]},
    )

    assert narrowed.status == "resolved"
    assert narrowed.exposed_tool_names == (REFERENCE_READER_TOOL_NAME,)
    assert widened.status == "blocked"
    assert widened.exposed_tool_names == ()
    assert (
        "cli_explicit_args_selection_outside_governance_allowlist:delete_everything"
        in widened.blocking_reasons
    )


def test_session_args_cannot_override_managed_tool_exposure_parameters(tmp_path) -> None:
    resolution = resolve_cli_tool_exposure_profile(
        repo_root=tmp_path,
        session_args={"risk_level": "high"},
    )

    assert resolution.status == "blocked"
    assert (
        "session_args_overrides_managed_tool_exposure_parameter:risk_level"
        in resolution.blocking_reasons
    )


def test_profile_max_risk_blocks_medium_external_readonly_tool(tmp_path) -> None:
    config = {
        "profiles": {
            "external_readonly": {
                "toolsets": [
                    {
                        "toolset_name": "api_hub_customer",
                        "toolset_kind": "api_hub",
                        "source_ref": "apihub://customer",
                        "allowlist_tool_names": ["list_customers"],
                        "tool_filter": ["list_customers"],
                        "max_risk_level": "low",
                        "discovery_credential_ref": "credential://discovery",
                        "execution_credential_ref": "credential://execution",
                    }
                ],
            }
        }
    }
    operations = {
        "api_hub_customer": (
            CliToolOperationFactsCandidate(
                tool_name="list_customers",
                toolset_name="api_hub_customer",
                toolset_kind="api_hub",
                operation_id="listCustomers",
                http_method="GET",
                path="/customers",
                requires_auth=True,
                touches_external_system=True,
            ),
        )
    }

    resolution = resolve_cli_tool_exposure_profile(
        profile_name="external_readonly",
        profile_config=config,
        repo_root=tmp_path,
        operation_facts_by_toolset=operations,
    )

    assert resolution.status == "resolved"
    assert resolution.exposed_tool_names == ()
    assert resolution.blocked_tool_names == ("list_customers",)
    assert (
        "selected_tool_exceeds_profile_max_risk:list_customers"
        in resolution.warnings
    )


def test_profile_max_risk_medium_allows_external_readonly_tool(tmp_path) -> None:
    config = {
        "profiles": {
            "external_readonly": {
                "toolsets": [
                    {
                        "toolset_name": "api_hub_customer",
                        "toolset_kind": "api_hub",
                        "source_ref": "apihub://customer",
                        "allowlist_tool_names": ["list_customers"],
                        "tool_filter": ["list_customers"],
                        "max_risk_level": "medium",
                        "discovery_credential_ref": "credential://discovery",
                        "execution_credential_ref": "credential://execution",
                    }
                ],
            }
        }
    }
    operations = {
        "api_hub_customer": (
            CliToolOperationFactsCandidate(
                tool_name="list_customers",
                toolset_name="api_hub_customer",
                toolset_kind="api_hub",
                operation_id="listCustomers",
                http_method="GET",
                path="/customers",
                requires_auth=True,
                touches_external_system=True,
            ),
        )
    }

    resolution = resolve_cli_tool_exposure_profile(
        profile_name="external_readonly",
        profile_config=config,
        repo_root=tmp_path,
        operation_facts_by_toolset=operations,
    )

    assert resolution.status == "resolved"
    assert resolution.exposed_tool_names == ("list_customers",)
    assert resolution.blocked_tool_names == ()


def test_profile_raw_credential_material_is_blocked_and_not_serialized(tmp_path) -> None:
    config = {
        "profiles": {
            "raw_secret_profile": {
                "toolsets": [
                    {
                        "toolset_name": "api_hub_customer",
                        "toolset_kind": "api_hub",
                        "source_ref": "apihub://customer",
                        "allowlist_tool_names": ["list_customers"],
                        "tool_filter": ["list_customers"],
                        "raw_config": {"api_key": "should-not-leak"},
                    }
                ],
            }
        }
    }

    resolution = resolve_cli_tool_exposure_profile(
        profile_name="raw_secret_profile",
        profile_config=config,
        repo_root=tmp_path,
        operation_facts_by_toolset={
            "api_hub_customer": (
                CliToolOperationFactsCandidate(
                    tool_name="list_customers",
                    toolset_name="api_hub_customer",
                    toolset_kind="api_hub",
                    operation_id="listCustomers",
                    http_method="GET",
                ),
            )
        },
    )
    status_text = str(cli_tool_exposure_profile_status_dict(resolution))

    assert resolution.status == "blocked"
    assert "raw_credential_material_forbidden" in resolution.blocking_reasons
    assert "should-not-leak" not in status_text
    assert "api_key" not in status_text


def test_reference_reader_roots_must_remain_under_repo_root(tmp_path) -> None:
    outside = tmp_path.parent / "outside-reference-root"
    config = {
        "profiles": {
            "readonly_reference": {
                "toolsets": [
                    {
                        "toolset_name": REFERENCE_READER_TOOLSET_NAME,
                        "toolset_kind": "toolset",
                        "source_ref": "local-reference-reader://workspace",
                        "allowlist_tool_names": [REFERENCE_READER_TOOL_NAME],
                        "tool_filter": [REFERENCE_READER_TOOL_NAME],
                        "reference_reader": {"allowed_roots": [str(outside)]},
                    }
                ],
            }
        }
    }

    resolution = resolve_cli_tool_exposure_profile(
        repo_root=tmp_path,
        profile_config=config,
    )

    assert resolution.status == "blocked"
    assert "reference_reader_allowed_roots_outside_repo" in resolution.blocking_reasons
