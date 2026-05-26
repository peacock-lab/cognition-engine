from __future__ import annotations

import sys
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "packages" / "operation_flows" / "src"

sys.path.insert(0, str(SOURCE_ROOT))

from cognition_operation_flows._requests.registry import (  # noqa: E402
    OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    OPERATION_FLOW_PLAN_WORKFLOW_NAME,
    OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
    OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
    OperationFlowTurnRequestCandidate,
    build_default_operation_flow_registry,
    list_operation_flow_descriptors,
    route_operation_flow_turn,
)
from cognition_operation_flows._core.control import (  # noqa: E402
    OPERATION_FLOW_CONFIG_PRECEDENCE,
    OPERATION_FLOW_CONTROL_STAGES,
)


def test_default_operation_flow_registry_lives_in_operation_flows() -> None:
    registry = build_default_operation_flow_registry()
    descriptors = list_operation_flow_descriptors(registry)
    descriptors_by_name = {
        descriptor.workflow_name: descriptor for descriptor in descriptors
    }

    assert registry.metadata["source"] == "cognition_operation_flows._requests.registry"
    assert len(descriptors) == 4
    assert tuple(descriptors_by_name) == (
        OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
        OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
        OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
        OPERATION_FLOW_PLAN_WORKFLOW_NAME,
    )

    plan_descriptor = descriptors_by_name[OPERATION_FLOW_PLAN_WORKFLOW_NAME]
    assert plan_descriptor.task_kind == "plan_design"
    assert plan_descriptor.config_precedence == OPERATION_FLOW_CONFIG_PRECEDENCE
    assert plan_descriptor.control_stages == OPERATION_FLOW_CONTROL_STAGES
    assert plan_descriptor.metadata["route_source"] == (
        "cognition_operation_flows._requests.intent_detectors"
    )


def test_router_matches_four_current_operation_flows() -> None:
    registry = build_default_operation_flow_registry()

    routes = [
        route_operation_flow_turn(
            registry,
            OperationFlowTurnRequestCandidate(
                user_text="请审查这些资料，指出是否符合当前主线",
                reference_paths=("tasks/b1/example.md",),
            ),
        ),
        route_operation_flow_turn(
            registry,
            OperationFlowTurnRequestCandidate(
                user_text="请解释当前配置为什么这样生效，尤其是 run workspace",
            ),
        ),
        route_operation_flow_turn(
            registry,
            OperationFlowTurnRequestCandidate(
                user_text="请审计 run workspace，检查证据完整吗",
                audit_run_workspace_requested=True,
            ),
        ),
        route_operation_flow_turn(
            registry,
            OperationFlowTurnRequestCandidate(
                user_text="我要建一个鱼塘，500平米大，帮我设计建设方案",
            ),
        ),
    ]

    assert [route.workflow_name for route in routes] == [
        OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
        OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
        OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
        OPERATION_FLOW_PLAN_WORKFLOW_NAME,
    ]
    assert all(route.matched for route in routes)
    assert all(route.source == "local_detector" for route in routes)


def test_plan_continuation_does_not_steal_plain_chat_confirmation() -> None:
    registry = build_default_operation_flow_registry()

    route = route_operation_flow_turn(
        registry,
        OperationFlowTurnRequestCandidate(
            user_text="可以吗？以礼为主题",
            previous_terminal_display_text="鱼塘建设方案\n需求事实\n...",
            history=(
                {
                    "user": "我要建一个鱼塘，500平米大，帮我设计建设方案",
                    "assistant": "鱼塘建设方案\n需求事实\n...",
                },
            ),
            live_model_requested=True,
        ),
    )

    assert route.matched is False
    assert route.route_reason == "no_registered_workflow_matched"


def test_plan_continuation_still_matches_explicit_detail_request() -> None:
    registry = build_default_operation_flow_registry()

    route = route_operation_flow_turn(
        registry,
        OperationFlowTurnRequestCandidate(
            user_text="能详细展开吗",
            previous_terminal_display_text="鱼塘建设方案\n需求事实\n...",
            history=(
                {
                    "user": "我要建一个鱼塘，500平米大，帮我设计建设方案",
                    "assistant": "鱼塘建设方案\n需求事实\n...",
                },
            ),
            live_model_requested=True,
        ),
    )

    assert route.matched is True
    assert route.workflow_name == OPERATION_FLOW_PLAN_WORKFLOW_NAME


def test_reference_review_matches_material_search_when_reference_paths_exist() -> None:
    registry = build_default_operation_flow_registry()

    route = route_operation_flow_turn(
        registry,
        OperationFlowTurnRequestCandidate(
            user_text="帮我查下材料中是否有编号为300的任务包",
            reference_paths=("tasks/b1",),
            live_model_requested=True,
        ),
    )

    assert route.matched is True
    assert route.workflow_name == OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME


def test_reference_review_matches_external_readonly_evidence_without_local_reader() -> None:
    registry = build_default_operation_flow_registry()

    route = route_operation_flow_turn(
        registry,
        OperationFlowTurnRequestCandidate(
            user_text="请审查这份外部只读证据摘要",
            external_readonly_evidence_paths=(
                "outputs/external-readonly/cli-fetch/example.json",
            ),
            live_model_requested=True,
        ),
    )

    assert route.matched is True
    assert route.workflow_name == OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME
    assert route.requires_tools == ()
    assert route.metadata["external_readonly_evidence_path_count"] == 1


def test_product_gateway_depends_on_operation_flows_and_channel_runtime_stay_thin() -> None:
    cli_pyproject = tomllib.loads(
        (REPO_ROOT / "packages" / "cli" / "pyproject.toml").read_text()
    )
    product_gateway_pyproject = tomllib.loads(
        (
            REPO_ROOT / "packages" / "product_gateway" / "pyproject.toml"
        ).read_text()
    )
    runtime_pyproject = tomllib.loads(
        (REPO_ROOT / "packages" / "runtime_container" / "pyproject.toml").read_text()
    )

    assert "cognition-system-operation-flows==0.8.3" not in cli_pyproject[
        "project"
    ]["dependencies"]
    assert "cognition-system-operation-flows==0.8.3" in product_gateway_pyproject[
        "project"
    ]["dependencies"]
    assert "cognition-system-operation-flows==0.8.3" not in runtime_pyproject[
        "project"
    ]["dependencies"]
