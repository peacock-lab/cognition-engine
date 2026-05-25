"""Public cognition CLI control shell for controlled runtime execution."""

from __future__ import annotations

from collections.abc import Sequence
import argparse

from cognition_cli.chat.defaults import apply_default_local_live_chat_profile
from cognition_cli.chat.channel import _chat_command
from cognition_cli.config.init import config_init_command
from cognition_cli.constants import EXIT_OK, EXIT_USAGE_ERROR
from cognition_cli.external_readonly.ask import (
    ExternalReadonlyAskLlmInvocationServiceFactory,
    ExternalReadonlyAskProviderCredentialStoreFactory,
    external_readonly_ask_command,
    run_external_readonly_ask_follow_up_channel,
    run_external_readonly_ask_initial_channel,
)
from cognition_cli.external_readonly.fetch import external_readonly_fetch_command
from cognition_cli.external_readonly.refs import (
    ExternalReadonlyRefsApplicationExecutor,
    external_readonly_refs_command,
)
from cognition_cli.parser import build_parser
from cognition_cli.run.command import _run_command
from cognition_cli.services.runtime import (
    EntryRunner,
    RequestBuilder,
    RunGatewayExecutor,
    OperationFlowLlmInvocationServiceFactory,
    _known_cli_warning_discipline,
)
from cognition_cli.startup import print_startup


def main(argv: Sequence[str] | None = None) -> int:
    """Run the public cognition CLI."""

    return run_cli(argv)


def run_cli(
    argv: Sequence[str] | None = None,
    *,
    entry_runner: EntryRunner | None = None,
    request_builder: RequestBuilder | None = None,
    run_gateway_executor: RunGatewayExecutor | None = None,
    operation_flow_llm_invocation_service_factory: (
        OperationFlowLlmInvocationServiceFactory | None
    ) = None,
    external_readonly_refs_application_executor: (
        ExternalReadonlyRefsApplicationExecutor | None
    ) = None,
    external_readonly_ask_llm_invocation_service_factory: (
        ExternalReadonlyAskLlmInvocationServiceFactory | None
    ) = None,
    external_readonly_ask_provider_credential_store_factory: (
        ExternalReadonlyAskProviderCredentialStoreFactory | None
    ) = None,
) -> int:
    """Run the CLI with injectable execution hooks for tests."""

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return _exit_code(exc.code)

    if args.command is None and args.json:
        return print_startup(args)

    if args.command is None:
        args = _default_chat_args(parser, args)

    if args.command == "run":
        with _known_cli_warning_discipline():
            use_gateway_entry = request_builder is None
            return _run_command(
                args,
                entry_runner=entry_runner,
                request_builder=request_builder,
                use_gateway_entry=use_gateway_entry,
                run_gateway_executor=run_gateway_executor,
            )

    if args.command == "chat":
        with _known_cli_warning_discipline():
            use_gateway_entry = request_builder is None
            return _chat_command(
                args,
                entry_runner=entry_runner,
                request_builder=request_builder,
                use_gateway_entry=use_gateway_entry,
                run_gateway_executor=run_gateway_executor,
                operation_flow_llm_invocation_service_factory=(
                    operation_flow_llm_invocation_service_factory
                ),
                external_readonly_ask_llm_invocation_service_factory=(
                    external_readonly_ask_llm_invocation_service_factory
                ),
                external_readonly_ask_provider_credential_store_factory=(
                    external_readonly_ask_provider_credential_store_factory
                ),
                external_readonly_ask_initial_runner=(
                    run_external_readonly_ask_initial_channel
                ),
                external_readonly_ask_follow_up_runner=(
                    run_external_readonly_ask_follow_up_channel
                ),
            )

    if (
        args.command == "external-readonly"
        and args.external_readonly_command == "fetch"
    ):
        with _known_cli_warning_discipline():
            return external_readonly_fetch_command(args)

    if (
        args.command == "external-readonly"
        and args.external_readonly_command == "refs"
    ):
        with _known_cli_warning_discipline():
            return external_readonly_refs_command(
                args,
                executor=external_readonly_refs_application_executor,
            )

    if (
        args.command == "external-readonly"
        and args.external_readonly_command == "ask"
    ):
        with _known_cli_warning_discipline():
            return external_readonly_ask_command(
                args,
                refs_executor=external_readonly_refs_application_executor,
                llm_invocation_service_factory=(
                    external_readonly_ask_llm_invocation_service_factory
                ),
                provider_credential_store_factory=(
                    external_readonly_ask_provider_credential_store_factory
                ),
            )

    if args.command == "config" and args.config_command == "init":
        return config_init_command(args)

    parser.print_help()
    return EXIT_USAGE_ERROR


def _default_chat_args(
    parser: argparse.ArgumentParser,
    startup_args: argparse.Namespace,
) -> argparse.Namespace:
    args = parser.parse_args(["chat"])
    args.no_banner = startup_args.no_banner
    apply_default_local_live_chat_profile(args)
    return args


def _exit_code(code: object) -> int:
    if isinstance(code, int):
        return code
    if code is None:
        return EXIT_OK
    return EXIT_USAGE_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
