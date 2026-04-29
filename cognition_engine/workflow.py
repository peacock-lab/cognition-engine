"""Compatibility entrypoint for the insight-to-decision workflow."""

from __future__ import annotations

from cognition_engine.workflows.workflow import (
    COMMAND_NAME,
    COMMAND_USAGE,
    CONTRACT_VERSION,
    METADATA_TYPE,
    OUTPUT_SLUG,
    OUTPUT_TYPE,
    USER_ERROR_EXIT_CODE,
    WORKFLOW_NAME,
    WorkflowError,
    build_error_result,
    build_parser,
    build_workflow_markdown,
    build_workflow_result,
    list_available_insight_ids,
    main,
    print_workflow_error,
    print_workflow_result,
    run_workflow_loop,
    validate_workflow_request,
)

__all__ = [
    "COMMAND_NAME",
    "COMMAND_USAGE",
    "CONTRACT_VERSION",
    "METADATA_TYPE",
    "OUTPUT_SLUG",
    "OUTPUT_TYPE",
    "USER_ERROR_EXIT_CODE",
    "WORKFLOW_NAME",
    "WorkflowError",
    "build_error_result",
    "build_parser",
    "build_workflow_markdown",
    "build_workflow_result",
    "list_available_insight_ids",
    "main",
    "print_workflow_error",
    "print_workflow_result",
    "run_workflow_loop",
    "validate_workflow_request",
]


if __name__ == "__main__":
    raise SystemExit(main())
