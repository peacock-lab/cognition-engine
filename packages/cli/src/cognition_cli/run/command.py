"""Run command orchestration for the Cognition System CLI."""

from __future__ import annotations

import argparse
import json
import sys

from cognition_cli.constants import (
    EXIT_BLOCKING,
    EXIT_OK,
    EXIT_OUTPUT_BOUNDARY_FAILURE,
    EXIT_RUNTIME_FAILURE,
    EXIT_USAGE_ERROR,
)
from cognition_cli.output_boundary import (
    violates_output_boundary as _violates_output_boundary,
)
from cognition_cli.run.controls import _apply_run_defaults, _cli_blocking_reasons
from cognition_cli.run.gateway import _run_via_product_gateway
from cognition_cli.run.input import _load_input_payload
from cognition_cli.run.output import (
    _blocking_output,
    _cli_output_from_entry_result,
    _emit_run_output,
    _preflight_only_output,
)
from cognition_cli.services.runtime import (
    EntryRunner,
    RequestBuilder,
    RunGatewayExecutor,
)


def _run_command(
    args: argparse.Namespace,
    *,
    entry_runner: EntryRunner | None,
    request_builder: RequestBuilder | None,
    use_gateway_entry: bool = False,
    run_gateway_executor: RunGatewayExecutor | None = None,
) -> int:
    try:
        input_payload = _load_input_payload(args)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"cognition run error: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    _apply_run_defaults(args)
    blocking_reasons = _cli_blocking_reasons(args)
    if args.preflight_only:
        output = _preflight_only_output(args, blocking_reasons)
        exit_code = EXIT_OK if not blocking_reasons else EXIT_BLOCKING
        output["exit_code"] = exit_code
        return _emit_run_output(args, output, exit_code=exit_code)

    if blocking_reasons:
        output = _blocking_output(args, blocking_reasons)
        return _emit_run_output(args, output, exit_code=EXIT_BLOCKING)

    try:
        if use_gateway_entry:
            entry_result = _run_via_product_gateway(
                args,
                input_payload,
                entry_runner=entry_runner,
                run_gateway_executor=run_gateway_executor,
            )
        else:
            if entry_runner is None or request_builder is None:
                raise ValueError(
                    "entry_runner and request_builder are required for "
                    "direct test execution."
                )
            request = request_builder(args, input_payload)
            entry_result = dict(entry_runner(request))
    except Exception as exc:  # pragma: no cover - defensive runtime boundary.
        print(f"cognition run runtime error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_FAILURE

    output = _cli_output_from_entry_result(args, entry_result)
    if _violates_output_boundary(output):
        print("cognition run output boundary violation", file=sys.stderr)
        return EXIT_OUTPUT_BOUNDARY_FAILURE

    if output["blocking_reasons"]:
        exit_code = EXIT_BLOCKING
    elif output["execution_performed"] is True:
        exit_code = EXIT_OK
    else:
        exit_code = EXIT_RUNTIME_FAILURE
    output["exit_code"] = exit_code
    return _emit_run_output(args, output, exit_code=exit_code)
