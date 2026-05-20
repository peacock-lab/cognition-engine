"""Argument parser construction for the Cognition System CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from cognition_cli.constants import (
    CHAT_RESPONSE_PREVIEW_LIMIT,
    CHAT_RUN_WORKSPACE_CLEANUP_POLICIES,
    CHAT_RUN_WORKSPACE_RETENTION_POLICIES,
    CLI_COMMAND,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=CLI_COMMAND,
        description="Cognition System controlled runtime CLI.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON status output.",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Suppress the startup banner.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser(
        "run",
        help="Run a controlled workflow through the productized entry.",
        description="Run a controlled workflow through the productized entry.",
    )
    run_parser.add_argument("--config-root", type=Path, default=Path(".") / "config")
    run_parser.add_argument("--environment", default="local")
    run_parser.add_argument("--profile")
    run_parser.add_argument("--runtime-id")
    run_parser.add_argument("--workflow-id")
    run_parser.add_argument("--workflow-name")
    input_group = run_parser.add_mutually_exclusive_group()
    input_group.add_argument("--input-json")
    input_group.add_argument("--input-file", type=Path)
    input_group.add_argument("--input-text")
    run_parser.add_argument("--operator-approved", action="store_true")
    run_parser.add_argument("--approval-ref")
    run_parser.add_argument("--audit-ref")
    run_parser.add_argument("--sanitized-evidence-ref")
    run_parser.add_argument("--governance-summary-output-ref")
    run_parser.add_argument("--request-live-llm", action="store_true")
    run_parser.add_argument("--request-ollama", action="store_true")
    run_parser.add_argument("--allow-live-llm", action="store_true")
    run_parser.add_argument("--allow-ollama", action="store_true")
    run_parser.add_argument("--live-llm-approval-ref")
    run_parser.add_argument("--ollama-api-base")
    run_parser.add_argument("--live-llm-timeout-seconds", type=int)
    run_parser.add_argument("--format", choices=("text", "json"), default="text")
    run_parser.add_argument("--json", action="store_true")
    run_parser.add_argument("--output", type=Path)
    run_parser.add_argument("--no-banner", action="store_true")
    run_parser.add_argument("--preflight-only", action="store_true")

    chat_parser = subparsers.add_parser(
        "chat",
        help="Start a controlled multi-turn terminal chat.",
        description="Start a controlled multi-turn terminal chat.",
    )
    chat_parser.add_argument("--config-root", type=Path, default=Path(".") / "config")
    chat_parser.add_argument("--environment", default="local")
    chat_parser.add_argument("--profile")
    chat_parser.add_argument("--workflow-id")
    chat_parser.add_argument("--workflow-name")
    chat_parser.add_argument("--operator-approved", action="store_true")
    chat_parser.add_argument("--approval-ref")
    chat_parser.add_argument("--audit-ref")
    chat_parser.add_argument("--sanitized-evidence-ref")
    chat_parser.add_argument("--governance-summary-output-ref")
    chat_parser.add_argument("--request-live-llm", action="store_true")
    chat_parser.add_argument("--request-ollama", action="store_true")
    chat_parser.add_argument("--allow-live-llm", action="store_true")
    chat_parser.add_argument("--allow-ollama", action="store_true")
    chat_parser.add_argument("--live-llm-approval-ref")
    chat_parser.add_argument("--ollama-api-base")
    chat_parser.add_argument("--live-llm-timeout-seconds", type=int)
    chat_parser.add_argument("--chat-session-id")
    chat_parser.add_argument("--max-turns", type=int)
    chat_parser.add_argument("--history-limit", type=int, default=6)
    chat_parser.add_argument(
        "--reference-path",
        dest="reference_paths",
        action="append",
        default=[],
        help="Add a governed local reference path for plan workflow turns.",
    )
    chat_parser.add_argument(
        "--external-readonly-evidence-path",
        dest="external_readonly_evidence_paths",
        action="append",
        default=[],
        help=(
            "Add a controlled external-readonly evidence JSON path under "
            "outputs/external-readonly/."
        ),
    )
    chat_parser.add_argument(
        "--tool-exposure-profile",
        help="Select the configured readonly tool exposure profile for references.",
    )
    chat_parser.add_argument(
        "--enable-run-workspace",
        action="store_true",
        help="Create a governed run workspace for plan workflow turns.",
    )
    chat_parser.add_argument("--run-workspace-root", type=Path)
    chat_parser.add_argument(
        "--run-workspace-retention-policy",
        choices=CHAT_RUN_WORKSPACE_RETENTION_POLICIES,
    )
    chat_parser.add_argument(
        "--run-workspace-cleanup-policy",
        choices=CHAT_RUN_WORKSPACE_CLEANUP_POLICIES,
    )
    chat_parser.add_argument("--run-workspace-max-write-bytes", type=int)
    audit_target_group = chat_parser.add_mutually_exclusive_group()
    audit_target_group.add_argument(
        "--audit-run-workspace-path",
        type=Path,
        help="Read-only run workspace path to audit.",
    )
    audit_target_group.add_argument(
        "--audit-run-workspace-ref",
        help="Read-only run workspace ref to audit.",
    )
    chat_parser.add_argument(
        "--audit-run-workspace-root",
        type=Path,
        help="Root used to resolve --audit-run-workspace-ref.",
    )
    chat_parser.add_argument(
        "--audit-focus",
        action="append",
        default=[],
        help="Add a bounded audit focus for run workspace evidence audit.",
    )
    chat_parser.add_argument("--no-banner", action="store_true")

    external_readonly_parser = subparsers.add_parser(
        "external-readonly",
        help="Inspect controlled external read-only reference tools.",
        description="Inspect controlled external read-only reference tools.",
    )
    external_readonly_subparsers = external_readonly_parser.add_subparsers(
        dest="external_readonly_command",
        required=True,
    )
    external_readonly_fetch_parser = external_readonly_subparsers.add_parser(
        "fetch",
        help="Run a gated external-readonly URL fetch request.",
        description="Run a gated external-readonly URL fetch request.",
    )
    external_readonly_fetch_parser.add_argument("--source-url", required=True)
    external_readonly_fetch_parser.add_argument(
        "--confirm-external-readonly-fetch",
        help="Natural-language confirmation text required for the fetch channel.",
    )
    external_readonly_fetch_parser.add_argument(
        "--request-id",
        default="external-readonly-request://cli/fetch",
    )
    external_readonly_fetch_parser.add_argument(
        "--envelope-ref",
        default="evidence://external-readonly/envelope/cli-fetch",
    )
    external_readonly_fetch_parser.add_argument(
        "--evidence-ref",
        default="evidence://external-readonly/item/cli-fetch",
    )
    external_readonly_fetch_parser.add_argument(
        "--controlled-output-ref",
        default="outputs/external-readonly/cli-fetch.json",
    )
    external_readonly_fetch_parser.add_argument(
        "--sanitized-evidence-ref",
        default="evidence://external-readonly/cli-fetch",
    )
    external_readonly_fetch_parser.add_argument(
        "--governance-summary-ref",
        default="summary://external-readonly/cli-fetch",
    )
    external_readonly_fetch_parser.add_argument("--source-title")
    external_readonly_fetch_parser.add_argument(
        "--operator-approved",
        action="store_true",
    )
    external_readonly_fetch_parser.add_argument("--approval-ref")
    external_readonly_fetch_parser.add_argument("--runtime-fetch-approval-ref")
    external_readonly_fetch_parser.add_argument("--audit-ref")
    external_readonly_fetch_parser.add_argument(
        "--network-gate-open",
        action="store_true",
    )
    external_readonly_fetch_parser.add_argument(
        "--allow-runtime-fetch",
        action="store_true",
    )
    external_readonly_fetch_parser.add_argument(
        "--use-live-transport",
        action="store_true",
    )
    external_readonly_fetch_parser.add_argument("--max-bytes", type=int, default=20_000)
    external_readonly_fetch_parser.add_argument(
        "--max-excerpt-chars",
        type=int,
        default=2_000,
    )
    external_readonly_fetch_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=10,
    )
    external_readonly_fetch_parser.add_argument(
        "--redirect-limit",
        type=int,
        default=0,
    )
    external_readonly_fetch_parser.add_argument(
        "--evidence-output",
        help=(
            "Optional controlled JSON output path under "
            "outputs/external-readonly/cli-fetch/."
        ),
    )
    external_readonly_fetch_parser.add_argument(
        "--overwrite-evidence-output",
        action="store_true",
        help="Overwrite an existing controlled CLI fetch evidence output file.",
    )
    external_readonly_fetch_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )
    external_readonly_fetch_parser.add_argument("--json", action="store_true")

    external_readonly_refs_parser = external_readonly_subparsers.add_parser(
        "refs",
        help="Inspect archived external-readonly evidence refs.",
        description=(
            "Inspect archived external-readonly evidence refs without network, "
            "model, runtime, or tool execution."
        ),
    )
    external_readonly_refs_parser.add_argument(
        "--evidence-path",
        dest="evidence_paths",
        action="append",
        default=[],
        help="Archived evidence-output JSON path under outputs/external-readonly/.",
    )
    external_readonly_refs_parser.add_argument(
        "--request-id",
        default="external-readonly-refs-request://cli/refs",
    )
    external_readonly_refs_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )
    external_readonly_refs_parser.add_argument("--json", action="store_true")

    external_readonly_ask_parser = external_readonly_subparsers.add_parser(
        "ask",
        help="Ask a controlled live LLM over external-readonly governed facts.",
        description=(
            "Ask a controlled live LLM over external-readonly governed summary "
            "facts from either an explicit URL fetch or archived evidence output."
        ),
    )
    external_readonly_ask_parser.add_argument(
        "--source-url",
        help="External URL to fetch through the explicit external-readonly gate.",
    )
    external_readonly_ask_parser.add_argument(
        "--evidence-path",
        dest="evidence_paths",
        action="append",
        default=[],
        help="Archived evidence-output JSON path under outputs/external-readonly/.",
    )
    external_readonly_ask_parser.add_argument("--question")
    external_readonly_ask_parser.add_argument(
        "--guided",
        "--interactive",
        dest="guided",
        action="store_true",
        help=(
            "Prompt for missing first-use inputs and explicit governance "
            "confirmations in an interactive terminal."
        ),
    )
    external_readonly_ask_parser.add_argument(
        "--confirm-external-readonly-fetch",
        help="Natural-language confirmation text required for URL fetch input.",
    )
    external_readonly_ask_parser.add_argument(
        "--request-id",
        default="external-readonly-ask-request://cli/ask",
    )
    external_readonly_ask_parser.add_argument(
        "--envelope-ref",
        default="evidence://external-readonly/envelope/cli-ask",
    )
    external_readonly_ask_parser.add_argument(
        "--evidence-ref",
        default="evidence://external-readonly/item/cli-ask",
    )
    external_readonly_ask_parser.add_argument(
        "--controlled-output-ref",
        default="outputs/external-readonly/cli-ask.json",
    )
    external_readonly_ask_parser.add_argument(
        "--sanitized-evidence-ref",
        default="evidence://external-readonly/cli-ask",
    )
    external_readonly_ask_parser.add_argument(
        "--governance-summary-ref",
        default="summary://external-readonly/cli-ask",
    )
    external_readonly_ask_parser.add_argument("--source-title")
    external_readonly_ask_parser.add_argument(
        "--operator-approved",
        action="store_true",
    )
    external_readonly_ask_parser.add_argument("--approval-ref")
    external_readonly_ask_parser.add_argument("--runtime-fetch-approval-ref")
    external_readonly_ask_parser.add_argument("--audit-ref")
    external_readonly_ask_parser.add_argument(
        "--network-gate-open",
        action="store_true",
    )
    external_readonly_ask_parser.add_argument(
        "--allow-runtime-fetch",
        action="store_true",
    )
    external_readonly_ask_parser.add_argument(
        "--use-live-transport",
        action="store_true",
    )
    external_readonly_ask_parser.add_argument("--max-bytes", type=int, default=20_000)
    external_readonly_ask_parser.add_argument(
        "--max-excerpt-chars",
        type=int,
        default=2_000,
    )
    external_readonly_ask_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=10,
    )
    external_readonly_ask_parser.add_argument(
        "--redirect-limit",
        type=int,
        default=0,
    )
    external_readonly_ask_parser.add_argument(
        "--model-name",
        help="Controlled-live model name; defaults to RuntimeLiveLlmConfigView.",
    )
    external_readonly_ask_parser.add_argument(
        "--model",
        "--model-alias",
        dest="model_alias",
        choices=("gemma4", "deepseek"),
        help=(
            "Whitelisted model alias for product use; expands to configured "
            "provider/model/output-governance profile refs."
        ),
    )
    external_readonly_ask_parser.add_argument(
        "--prompt-provider-key",
        action="store_true",
        help=(
            "Prompt once for a missing DeepSeek API key; the key is only used "
            "in the current process unless the user explicitly chooses OS "
            "keychain storage."
        ),
    )
    external_readonly_ask_parser.add_argument(
        "--use-stored-provider-key",
        action="store_true",
        help=(
            "Use a previously saved DeepSeek API key from the OS keychain; "
            "all live/network/audit gates are still required."
        ),
    )
    external_readonly_ask_parser.add_argument(
        "--config-root",
        type=Path,
        default=Path(".") / "config",
    )
    external_readonly_ask_parser.add_argument("--environment", default="local")
    external_readonly_ask_parser.add_argument("--profile")
    external_readonly_ask_parser.add_argument("--llm-provider-profile-ref")
    external_readonly_ask_parser.add_argument("--llm-model-profile-ref")
    external_readonly_ask_parser.add_argument("--llm-output-governance-profile-ref")
    external_readonly_ask_parser.add_argument(
        "--request-live-llm",
        action="store_true",
    )
    external_readonly_ask_parser.add_argument(
        "--request-ollama",
        action="store_true",
    )
    external_readonly_ask_parser.add_argument(
        "--allow-live-llm",
        action="store_true",
    )
    external_readonly_ask_parser.add_argument(
        "--allow-ollama",
        action="store_true",
    )
    external_readonly_ask_parser.add_argument("--live-llm-approval-ref")
    external_readonly_ask_parser.add_argument("--ollama-api-base")
    external_readonly_ask_parser.add_argument(
        "--live-llm-timeout-seconds",
        type=int,
    )
    external_readonly_ask_parser.add_argument(
        "--live-llm-max-tokens",
        type=int,
    )
    external_readonly_ask_parser.add_argument(
        "--answer-preview-limit",
        type=int,
        default=CHAT_RESPONSE_PREVIEW_LIMIT,
    )
    external_readonly_ask_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )
    external_readonly_ask_parser.add_argument("--json", action="store_true")

    external_readonly_answer_parser = external_readonly_subparsers.add_parser(
        "answer",
        help="Run an explicit governed LLM smoke over archived evidence refs.",
        description=(
            "Run an explicit governed LLM smoke over archived external-readonly "
            "evidence refs without fetch/search or default chat/run changes."
        ),
    )
    external_readonly_answer_parser.add_argument(
        "--evidence-path",
        dest="evidence_paths",
        action="append",
        default=[],
        help="Archived evidence-output JSON path under outputs/external-readonly/.",
    )
    external_readonly_answer_parser.add_argument("--question", required=True)
    external_readonly_answer_parser.add_argument(
        "--request-id",
        default="external-readonly-answer-request://cli/answer",
    )
    external_readonly_answer_parser.add_argument(
        "--model-name",
        help="Controlled-live model name; defaults to RuntimeLiveLlmConfigView.",
    )
    external_readonly_answer_parser.add_argument(
        "--config-root",
        type=Path,
        default=Path(".") / "config",
    )
    external_readonly_answer_parser.add_argument("--environment", default="local")
    external_readonly_answer_parser.add_argument("--profile")
    external_readonly_answer_parser.add_argument(
        "--request-live-llm",
        action="store_true",
    )
    external_readonly_answer_parser.add_argument(
        "--request-ollama",
        action="store_true",
    )
    external_readonly_answer_parser.add_argument(
        "--allow-live-llm",
        action="store_true",
    )
    external_readonly_answer_parser.add_argument(
        "--allow-ollama",
        action="store_true",
    )
    external_readonly_answer_parser.add_argument("--live-llm-approval-ref")
    external_readonly_answer_parser.add_argument("--ollama-api-base")
    external_readonly_answer_parser.add_argument(
        "--live-llm-timeout-seconds",
        type=int,
    )
    external_readonly_answer_parser.add_argument(
        "--live-llm-max-tokens",
        type=int,
    )
    external_readonly_answer_parser.add_argument(
        "--answer-preview-limit",
        type=int,
        default=CHAT_RESPONSE_PREVIEW_LIMIT,
    )
    external_readonly_answer_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )
    external_readonly_answer_parser.add_argument("--json", action="store_true")

    config_parser = subparsers.add_parser(
        "config",
        help="Initialize and inspect the Cognition System config center.",
        description="Initialize and inspect the Cognition System config center.",
    )
    config_subparsers = config_parser.add_subparsers(
        dest="config_command",
        required=True,
    )
    config_init_parser = config_subparsers.add_parser(
        "init",
        help="Create a user-owned config/ directory from packaged defaults.",
        description="Create a user-owned config/ directory from packaged defaults.",
    )
    config_init_parser.add_argument(
        "--config-root",
        type=Path,
        default=Path(".") / "config",
        help="Target config root to initialize.",
    )
    config_init_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing packaged baseline files.",
    )
    config_init_parser.add_argument("--json", action="store_true")
    return parser
