from __future__ import annotations

import asyncio

import pytest
from google.adk.tools import FunctionTool

from adk_adapter import (
    AdkControlledToolOptions,
    AdkFunctionToolOptions,
    AdkToolCallResult,
    build_deterministic_external_echo_function_tool,
    build_no_live_task_review_function_tool,
    create_adk_function_tool,
    deterministic_external_echo,
    review_task_context,
    run_adk_function_tool_no_live,
)


def test_create_adk_function_tool_wraps_native_function_tool() -> None:
    options = AdkFunctionToolOptions(
        tool_name="review_task_context",
        tool_kind="deterministic_no_live_task_review",
    )

    tool = create_adk_function_tool(review_task_context, options=options)

    assert isinstance(tool, FunctionTool)
    assert tool.name == "review_task_context"
    assert tool.custom_metadata == options.to_metadata()
    assert "Return a deterministic sanitized review summary" in tool.description


def test_create_adk_function_tool_rejects_name_mismatch() -> None:
    with pytest.raises(ValueError):
        create_adk_function_tool(
            review_task_context,
            options=AdkFunctionToolOptions(tool_name="wrong_name"),
        )


def test_run_adk_function_tool_no_live_returns_sanitized_result() -> None:
    tool = build_no_live_task_review_function_tool()

    result = asyncio.run(async_run_tool(tool))

    assert isinstance(result, AdkToolCallResult)
    assert result.tool_name == "review_task_context"
    assert result.tool_kind == "deterministic_no_live_task_review"
    assert result.tool_call_allowed is True
    assert result.tool_call_attempted is True
    assert result.tool_runtime_call_performed is True
    assert result.tool_confirmation_required is False
    assert result.tool_confirmation_granted is True
    assert result.adk_tool_confirmation_requested is False
    assert result.tool_approval_ref is None
    assert result.tool_failure_type is None
    assert result.tool_run_ref == "adk-function-tool-run://tool-run-001"
    assert result.session_id == "session://tool-test"
    assert result.tool_input_summary["argument_keys"] == [
        "evidence_ref",
        "task_kind",
        "task_ref",
    ]
    assert result.tool_output_summary["result_kind"] == (
        "deterministic_no_live_task_review"
    )
    assert result.tool_output_summary["recommendation"] == "review_ready"
    assert result.does_not_store_raw_tool_input is True
    assert result.does_not_store_raw_tool_output is True
    assert "task_ref_value" not in result.tool_input_summary
    observability_input = result.to_observability_input()
    assert "raw_tool_input" not in observability_input
    assert "raw_tool_output" not in observability_input


def test_run_adk_function_tool_no_live_blocks_without_allowed_flag() -> None:
    tool = build_no_live_task_review_function_tool()

    result = asyncio.run(
        run_adk_function_tool_no_live(
            tool,
            args={"task_ref": "task://blocked"},
            controlled_options=AdkControlledToolOptions(tool_call_allowed=False),
        )
    )

    assert result.tool_call_allowed is False
    assert result.tool_call_attempted is False
    assert result.tool_runtime_call_performed is False
    assert result.tool_failure_type == "tool_call_not_allowed"


def test_deterministic_external_echo_function_tool_returns_sanitized_smoke() -> None:
    tool = build_deterministic_external_echo_function_tool(
        options=AdkFunctionToolOptions(
            tool_name="deterministic_external_echo",
            tool_kind="deterministic_low_risk_external_smoke",
            require_confirmation=False,
        )
    )

    result = asyncio.run(
        run_adk_function_tool_no_live(
            tool,
            args={
                "message_ref": "message://217-secret-input",
                "message_kind": "external_smoke",
                "echo_label": "low-risk",
            },
            tool_options=AdkFunctionToolOptions(
                tool_name="deterministic_external_echo",
                tool_kind="deterministic_low_risk_external_smoke",
                require_confirmation=False,
            ),
            controlled_options=AdkControlledToolOptions(
                session_id="session://tool-smoke",
                tool_run_id="tool-run-217",
            ),
        )
    )

    assert tool.name == "deterministic_external_echo"
    assert result.tool_runtime_call_performed is True
    assert result.tool_output_summary["result_kind"] == (
        "deterministic_external_echo"
    )
    assert result.tool_output_summary["recommendation"] == (
        "external_tool_smoke_ready"
    )
    assert "message://217-secret-input" not in repr(result.to_observability_input())


def test_deterministic_external_echo_plain_function_avoids_raw_echo() -> None:
    result = deterministic_external_echo(
        message_ref="message://217-raw",
        message_kind="external_smoke",
        echo_label="label",
    )

    assert result["result_kind"] == "deterministic_external_echo"
    assert result["message_ref_present"] is True
    assert result["echo_label_present"] is True
    assert "message://217-raw" not in repr(result)


def test_run_adk_function_tool_confirmation_required_does_not_execute() -> None:
    calls: list[str] = []

    def confirmable_task_review(task_ref: str) -> dict[str, object]:
        """Return a task review after operator confirmation."""

        calls.append(task_ref)
        return {"recommendation": "review_ready"}

    tool_options = AdkFunctionToolOptions(
        tool_name="confirmable_task_review",
        tool_kind="deterministic_no_live_task_review",
        require_confirmation=True,
    )
    tool = create_adk_function_tool(confirmable_task_review, options=tool_options)

    result = asyncio.run(
        run_adk_function_tool_no_live(
            tool,
            args={"task_ref": "task://214"},
            tool_options=tool_options,
            controlled_options=AdkControlledToolOptions(
                confirmation_granted=None,
                tool_approval_ref="approval://tool-214",
                confirmation_decision_source="test.operator_approval",
                tool_run_id="tool-run-214-required",
            ),
        )
    )

    assert calls == []
    assert result.tool_call_allowed is True
    assert result.tool_call_attempted is True
    assert result.tool_runtime_call_performed is False
    assert result.tool_confirmation_required is True
    assert result.tool_confirmation_granted is False
    assert result.adk_tool_confirmation_requested is True
    assert result.tool_approval_ref == "approval://tool-214"
    assert result.tool_confirmation_decision_source == "test.operator_approval"
    assert result.tool_failure_type == "tool_confirmation_required"
    assert result.tool_run_ref == "adk-function-tool-run://tool-run-214-required"
    assert "raw_tool_input" not in result.to_observability_input()
    assert result.metadata["adk_tool_confirmation_experimental"] is True


def test_run_adk_function_tool_confirmation_granted_executes() -> None:
    calls: list[str] = []

    def confirmable_task_review(task_ref: str) -> dict[str, object]:
        """Return a task review after operator confirmation."""

        calls.append(task_ref)
        return {"result_kind": "confirmation_smoke", "recommendation": "ready"}

    tool_options = AdkFunctionToolOptions(
        tool_name="confirmable_task_review",
        tool_kind="deterministic_no_live_task_review",
        require_confirmation=True,
    )
    tool = create_adk_function_tool(confirmable_task_review, options=tool_options)

    result = asyncio.run(
        run_adk_function_tool_no_live(
            tool,
            args={"task_ref": "task://214"},
            tool_options=tool_options,
            controlled_options=AdkControlledToolOptions(
                confirmation_granted=True,
                tool_approval_ref="approval://tool-214",
                confirmation_decision_source="test.operator_approval",
                tool_run_id="tool-run-214-granted",
            ),
        )
    )

    assert calls == ["task://214"]
    assert result.tool_runtime_call_performed is True
    assert result.tool_confirmation_required is True
    assert result.tool_confirmation_granted is True
    assert result.adk_tool_confirmation_requested is False
    assert result.tool_output_summary["result_kind"] == "confirmation_smoke"
    assert result.tool_output_summary["recommendation"] == "ready"
    assert result.tool_failure_type is None


def test_run_adk_function_tool_confirmation_rejected_does_not_execute() -> None:
    calls: list[str] = []

    def confirmable_task_review(task_ref: str) -> dict[str, object]:
        """Return a task review after operator confirmation."""

        calls.append(task_ref)
        return {"recommendation": "review_ready"}

    tool_options = AdkFunctionToolOptions(
        tool_name="confirmable_task_review",
        tool_kind="deterministic_no_live_task_review",
        require_confirmation=True,
    )
    tool = create_adk_function_tool(confirmable_task_review, options=tool_options)

    result = asyncio.run(
        run_adk_function_tool_no_live(
            tool,
            args={"task_ref": "task://214"},
            tool_options=tool_options,
            controlled_options=AdkControlledToolOptions(
                confirmation_granted=False,
                tool_approval_ref="approval://tool-214",
                confirmation_decision_source="test.operator_approval",
            ),
        )
    )

    assert calls == []
    assert result.tool_runtime_call_performed is False
    assert result.tool_confirmation_required is True
    assert result.tool_confirmation_granted is False
    assert result.adk_tool_confirmation_requested is False
    assert result.tool_failure_type == "tool_confirmation_rejected"


async def async_run_tool(tool: FunctionTool) -> AdkToolCallResult:
    return await run_adk_function_tool_no_live(
        tool,
        args={
            "task_ref": "task://211",
            "task_kind": "implementation_task",
            "evidence_ref": "evidence://211",
        },
        controlled_options=AdkControlledToolOptions(
            session_id="session://tool-test",
            tool_run_id="tool-run-001",
        ),
    )
