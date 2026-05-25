"""External-readonly controlled question-answering product channel."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cognition_cli.constants import (
    EXIT_BLOCKING,
    EXIT_OUTPUT_BOUNDARY_FAILURE,
    EXIT_RUNTIME_FAILURE,
    EXIT_OK,
    PRODUCT_NAME,
)
from cognition_cli.external_readonly.fetch import (
    REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION,
)
from contract_core.external_readonly_archive import (
    external_readonly_fetch_output_boundary_violated,
)
from contract_core.llm_invocation import (
    GovernedLlmInvocationServiceFactory,
)
from product_application_assembly.evidence_summary_answer_ask_entry import (
    EvidenceSummaryAnswerAskEntryRequest,
    EvidenceSummaryAnswerAskEntryServices,
    run_evidence_summary_answer_ask_entry,
    run_evidence_summary_answer_ask_follow_up_entry,
)
from product_application_assembly.evidence_summary_answer_ask_interaction import (
    EvidenceSummaryAnswerAskInteractionResult,
    EvidenceSummaryAnswerAskInteractionState,
    build_evidence_summary_answer_ask_initial_interaction,
)
from product_application_assembly.evidence_summary_answer_ask_policy import (
    apply_evidence_summary_answer_ask_model_selection_to_channel_options,
    resolve_evidence_summary_answer_ask_llm_service,
    resolve_evidence_summary_answer_ask_model_selection_from_channel_options,
)
from product_application_assembly.evidence_summary_answer_generation import (
    EVIDENCE_SUMMARY_ANSWER_GENERATION_INTERACTION_MODE,
)
from product_application_assembly.evidence_summary_answer_provider_key_setup import (
    EvidenceSummaryAnswerProviderKeyPromptHandlers,
    EvidenceSummaryAnswerProviderKeySetupInput,
    resolve_evidence_summary_answer_provider_key_setup,
)


EXTERNAL_READONLY_ASK_COMMAND = "cognition external-readonly ask"
EXTERNAL_READONLY_ASK_SOURCE = "cognition_cli.external_readonly.ask"
EXTERNAL_READONLY_ASK_REQUEST_ID = "external-readonly-ask-request://cli/ask"
EXTERNAL_READONLY_ASK_INTERACTION_MODE = (
    EVIDENCE_SUMMARY_ANSWER_GENERATION_INTERACTION_MODE
)
EXTERNAL_READONLY_ASK_PRODUCT_PATH = "external_readonly_ask_product_path"
EXTERNAL_READONLY_ASK_ANSWER_TRANSFORMATION_WARNING = (
    "external_readonly_ask_answer_scoped_transformation"
)
EXTERNAL_READONLY_ASK_MODEL_ALIAS_CONFLICT = (
    "model_alias_conflicts_with_explicit_model_options"
)
EXTERNAL_READONLY_ASK_MODEL_ALIAS_UNKNOWN = "model_alias_unknown"
EXTERNAL_READONLY_ASK_GUIDED_UNAVAILABLE_FOR_JSON_OUTPUT = (
    "external_readonly_ask_guided_unavailable_for_json_output"
)
EXTERNAL_READONLY_ASK_GUIDED_REQUIRES_INTERACTIVE_TERMINAL = (
    "external_readonly_ask_guided_requires_interactive_terminal"
)
EXTERNAL_READONLY_ASK_GUIDED_CANCELLED = "external_readonly_ask_guided_cancelled"
EXTERNAL_READONLY_ASK_GUIDED_EXTERNAL_FETCH_DECLINED = (
    "external_readonly_ask_guided_external_fetch_declined"
)
EXTERNAL_READONLY_ASK_GUIDED_LIVE_LLM_DECLINED = (
    "external_readonly_ask_guided_live_llm_declined"
)
EXTERNAL_READONLY_ASK_GUIDED_EXTERNAL_PROVIDER_DECLINED = (
    "external_readonly_ask_guided_external_provider_declined"
)
EXTERNAL_READONLY_ASK_GUIDED_QUESTION_REQUIRED = (
    "external_readonly_ask_guided_question_required"
)
EXTERNAL_READONLY_ASK_GUIDED_INPUT_REQUIRED = (
    "external_readonly_ask_guided_input_required"
)
EXTERNAL_READONLY_ASK_GUIDED_FOLLOW_UP_QUESTION_REQUIRED = (
    "external_readonly_ask_guided_follow_up_question_required"
)
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEEPSEEK_PROVIDER_KEY_REQUIRED = "deepseek_provider_key_required"
PROVIDER_KEY_PROMPT_UNAVAILABLE_FOR_JSON_OUTPUT = (
    "provider_key_prompt_unavailable_for_json_output"
)
PROVIDER_KEY_PROMPT_REQUIRES_INTERACTIVE_TERMINAL = (
    "provider_key_prompt_requires_interactive_terminal"
)
PROVIDER_KEY_INPUT_REQUIRED = "provider_key_input_required"
PROVIDER_KEY_PROMPT_CANCELLED = "provider_key_prompt_cancelled"
PROVIDER_KEY_STORE_UNAVAILABLE = "provider_key_store_unavailable"
PROVIDER_KEY_STORED_CREDENTIAL_NOT_FOUND = (
    "provider_key_stored_credential_not_found"
)
PROVIDER_KEY_STORED_CREDENTIAL_LOAD_FAILED = (
    "provider_key_stored_credential_load_failed"
)
PROVIDER_KEY_PERSISTENT_SAVE_FAILED = "provider_key_persistent_save_failed"

ExternalReadonlyAskLlmInvocationServiceFactory = GovernedLlmInvocationServiceFactory
ExternalReadonlyAskFetchExecutor = Callable[[Mapping[str, Any]], Any]
ExternalReadonlyAskProviderCredentialStoreFactory = Callable[[], Any]


def external_readonly_ask_command(
    args: argparse.Namespace,
    *,
    refs_executor: ExternalReadonlyRefsApplicationExecutor | None = None,
    fetch_executor: ExternalReadonlyAskFetchExecutor | None = None,
    llm_invocation_service_factory: (
        ExternalReadonlyAskLlmInvocationServiceFactory | None
    ) = None,
    provider_credential_store_factory: (
        ExternalReadonlyAskProviderCredentialStoreFactory | None
    ) = None,
) -> int:
    """Run an explicit controlled external-readonly QA product path."""

    try:
        exit_code, output = build_external_readonly_ask_cli_output(
            args,
            refs_executor=refs_executor,
            fetch_executor=fetch_executor,
            llm_invocation_service_factory=llm_invocation_service_factory,
            provider_credential_store_factory=provider_credential_store_factory,
        )
    except Exception as exc:  # pragma: no cover - defensive product boundary.
        print(f"{EXTERNAL_READONLY_ASK_COMMAND} error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_FAILURE
    return _emit_external_readonly_ask_output(args, output, exit_code=exit_code)


def run_external_readonly_ask_initial_channel(
    args: argparse.Namespace,
    *,
    refs_executor: ExternalReadonlyRefsApplicationExecutor | None = None,
    fetch_executor: ExternalReadonlyAskFetchExecutor | None = None,
    llm_invocation_service_factory: (
        ExternalReadonlyAskLlmInvocationServiceFactory | None
    ) = None,
    provider_credential_store_factory: (
        ExternalReadonlyAskProviderCredentialStoreFactory | None
    ) = None,
) -> EvidenceSummaryAnswerAskInteractionResult:
    """Run one initial ask interaction from the terminal/chat channel."""

    def _output_builder(
        builder_args: argparse.Namespace,
        *,
        session_state_collector: (
            Callable[[EvidenceSummaryAnswerAskInteractionState], None] | None
        ) = None,
    ) -> tuple[int, dict[str, Any]]:
        return build_external_readonly_ask_cli_output(
            builder_args,
            refs_executor=refs_executor,
            fetch_executor=fetch_executor,
            llm_invocation_service_factory=llm_invocation_service_factory,
            provider_credential_store_factory=provider_credential_store_factory,
            session_state_collector=session_state_collector,
        )

    return build_evidence_summary_answer_ask_initial_interaction(
        args=args,
        output_builder=_output_builder,
    )


def run_external_readonly_ask_follow_up_channel(
    session_state: EvidenceSummaryAnswerAskInteractionState,
    follow_up_question: str,
    *,
    previous_output: Mapping[str, Any] | None = None,
    turns: tuple[Mapping[str, Any], ...] = (),
    request_id: str | None = None,
    follow_up_index: int | None = None,
) -> EvidenceSummaryAnswerAskInteractionResult:
    """Run one follow-up ask interaction from the terminal/chat channel."""

    action_result = run_evidence_summary_answer_ask_follow_up_entry(
        session_state,
        follow_up_question=follow_up_question,
        previous_output=previous_output,
        turns=turns,
        request_id=request_id,
        follow_up_index=follow_up_index,
    )
    return EvidenceSummaryAnswerAskInteractionResult(
        exit_code=action_result.exit_code,
        output=action_result.output,
        next_state=action_result.next_state,
    )


def build_external_readonly_ask_cli_output(
    args: argparse.Namespace,
    *,
    refs_executor: ExternalReadonlyRefsApplicationExecutor | None = None,
    fetch_executor: ExternalReadonlyAskFetchExecutor | None = None,
    llm_invocation_service_factory: (
        ExternalReadonlyAskLlmInvocationServiceFactory | None
    ) = None,
    provider_credential_store_factory: (
        ExternalReadonlyAskProviderCredentialStoreFactory | None
    ) = None,
    session_state_collector: (
        Callable[[EvidenceSummaryAnswerAskInteractionState], None] | None
    ) = None,
) -> tuple[int, dict[str, Any]]:
    """Build the external-readonly QA product output without printing it."""

    request_id = str(args.request_id or EXTERNAL_READONLY_ASK_REQUEST_ID)
    guided_reasons = _apply_guided_onboarding(args)
    evidence_paths = tuple(getattr(args, "evidence_paths", ()) or ())
    source_url = _normalized_optional_text(getattr(args, "source_url", None))
    question = _normalized_question(getattr(args, "question", None))
    follow_up_questions = _normalized_follow_up_questions(
        getattr(args, "follow_up_questions", ()) or ()
    )
    provider_key: str | None = None
    provider_key_metadata: dict[str, Any] = {}
    preflight_reasons = guided_reasons or _ensure_model_selection(args)
    if not preflight_reasons:
        preflight_reasons = _external_provider_gate_blocking_reasons(args)
    if not preflight_reasons:
        provider_key_result = _collect_provider_key(
            args,
            provider_credential_store_factory=provider_credential_store_factory,
        )
        provider_key = provider_key_result.provider_key
        provider_key_metadata = dict(provider_key_result.metadata)
        preflight_reasons = tuple(provider_key_result.blocking_reasons)
    if preflight_reasons:
        entry_result = run_evidence_summary_answer_ask_entry(
            _entry_request_from_args(
                args,
                request_id=request_id,
                source_url=source_url,
                evidence_paths=evidence_paths,
                question=question,
                follow_up_questions=(),
                provider_key=provider_key,
                provider_key_metadata=provider_key_metadata,
                channel_blocking_reasons=preflight_reasons,
            ),
            services=EvidenceSummaryAnswerAskEntryServices(
                refs_executor=refs_executor,
                fetch_executor=fetch_executor,
                llm_invocation_service_factory=llm_invocation_service_factory,
            ),
        )
        output = dict(entry_result.output)
        if guided_reasons:
            output["blocking_reasons"] = list(preflight_reasons)
        return _exit_code_from_output(output), output

    entry_result = run_evidence_summary_answer_ask_entry(
        _entry_request_from_args(
            args,
            request_id=request_id,
            source_url=source_url,
            evidence_paths=evidence_paths,
            question=question,
            follow_up_questions=follow_up_questions,
            provider_key=provider_key,
            provider_key_metadata=provider_key_metadata,
        ),
        services=EvidenceSummaryAnswerAskEntryServices(
            refs_executor=refs_executor,
            fetch_executor=fetch_executor,
            llm_invocation_service_factory=llm_invocation_service_factory,
        ),
    )
    output = dict(entry_result.output)
    if session_state_collector is not None and entry_result.next_state is not None:
        session_state_collector(entry_result.next_state)
    guided_follow_up = (
        getattr(args, "guided", False) is True
        and not follow_up_questions
        and _guided_follow_up_prompt_available()
    )
    follow_up_service_available = (
        entry_result.next_state is not None
        and entry_result.next_state.service is not None
    )
    if (
        entry_result.next_state is not None
        and guided_follow_up
        and follow_up_service_available
    ):
        output = _output_with_follow_up_turns(
            output,
            follow_up_questions=(),
            session_state=entry_result.next_state,
            request_id=request_id,
            guided_follow_up=guided_follow_up,
        )
    return _exit_code_from_output(output), output


def _entry_request_from_args(
    args: argparse.Namespace,
    *,
    request_id: str,
    source_url: str | None,
    evidence_paths: tuple[str, ...],
    question: str,
    follow_up_questions: tuple[str, ...],
    provider_key: str | None,
    provider_key_metadata: Mapping[str, Any],
    channel_blocking_reasons: tuple[str, ...] = (),
) -> EvidenceSummaryAnswerAskEntryRequest:
    selection = _model_selection(args)
    return EvidenceSummaryAnswerAskEntryRequest(
        request_id=request_id,
        source_url=source_url,
        evidence_paths=evidence_paths,
        question=question,
        follow_up_questions=follow_up_questions,
        repo_root=str(Path.cwd()),
        product_name=PRODUCT_NAME,
        command=EXTERNAL_READONLY_ASK_COMMAND,
        product_path=EXTERNAL_READONLY_ASK_PRODUCT_PATH,
        input_channel="cli",
        source=EXTERNAL_READONLY_ASK_SOURCE,
        model_name=None if selection.model_alias else selection.model_name,
        model_alias=selection.model_alias,
        provider_profile_ref=(
            None if selection.model_alias else selection.provider_profile_ref
        ),
        model_profile_ref=None if selection.model_alias else selection.model_profile_ref,
        output_governance_profile_ref=(
            None
            if selection.model_alias
            else selection.output_governance_profile_ref
        ),
        request_live_llm=bool(getattr(args, "request_live_llm", False)),
        allow_live_llm=bool(getattr(args, "allow_live_llm", False)),
        request_ollama=bool(getattr(args, "request_ollama", False)),
        allow_ollama=bool(getattr(args, "allow_ollama", False)),
        live_llm_approval_ref=getattr(args, "live_llm_approval_ref", None),
        config_root=str(args.config_root) if args.config_root else None,
        environment=getattr(args, "environment", None),
        profile=getattr(args, "profile", None),
        ollama_api_base=getattr(args, "ollama_api_base", None),
        live_llm_timeout_seconds=getattr(args, "live_llm_timeout_seconds", None),
        live_llm_max_tokens=getattr(args, "live_llm_max_tokens", None),
        answer_preview_limit=int(getattr(args, "answer_preview_limit", 400) or 400),
        network_gate_open=bool(getattr(args, "network_gate_open", False)),
        operator_approved=bool(getattr(args, "operator_approved", False)),
        approval_ref=getattr(args, "approval_ref", None),
        runtime_fetch_approval_ref=getattr(args, "runtime_fetch_approval_ref", None),
        audit_ref=getattr(args, "audit_ref", None),
        envelope_ref=getattr(args, "envelope_ref", None),
        evidence_ref=getattr(args, "evidence_ref", None),
        controlled_output_ref=getattr(args, "controlled_output_ref", None),
        sanitized_evidence_ref=getattr(args, "sanitized_evidence_ref", None),
        governance_summary_ref=getattr(args, "governance_summary_ref", None),
        source_title=getattr(args, "source_title", None),
        allow_runtime_fetch=bool(getattr(args, "allow_runtime_fetch", False)),
        use_live_transport=bool(getattr(args, "use_live_transport", False)),
        max_bytes=int(getattr(args, "max_bytes", 20_000) or 20_000),
        max_excerpt_chars=int(
            getattr(args, "max_excerpt_chars", 2_000) or 2_000
        ),
        timeout_seconds=int(getattr(args, "timeout_seconds", 10) or 10),
        redirect_limit=int(getattr(args, "redirect_limit", 0) or 0),
        confirm_external_readonly_fetch=getattr(
            args,
            "confirm_external_readonly_fetch",
            None,
        ),
        provider_key=provider_key,
        provider_key_metadata=provider_key_metadata,
        channel_blocking_reasons=channel_blocking_reasons,
    )


def build_external_readonly_ask_follow_up_cli_output(
    session_state: EvidenceSummaryAnswerAskInteractionState,
    follow_up_question: str,
) -> tuple[int, dict[str, Any], EvidenceSummaryAnswerAskInteractionState]:
    """Run one same-process follow-up over an existing ask session state."""

    action_result = run_evidence_summary_answer_ask_follow_up_entry(
        session_state,
        follow_up_question,
    )
    next_state = action_result.next_state or session_state
    return action_result.exit_code, action_result.output, next_state


def _apply_guided_onboarding(args: argparse.Namespace) -> tuple[str, ...]:
    if getattr(args, "guided", False) is not True:
        return ()
    if args.format == "json" or args.json:
        return (EXTERNAL_READONLY_ASK_GUIDED_UNAVAILABLE_FOR_JSON_OUTPUT,)
    if not _guided_prompt_available():
        return (EXTERNAL_READONLY_ASK_GUIDED_REQUIRES_INTERACTIVE_TERMINAL,)
    try:
        return _fill_guided_first_use_args(args)
    except (EOFError, KeyboardInterrupt):
        return (EXTERNAL_READONLY_ASK_GUIDED_CANCELLED,)


def _fill_guided_first_use_args(args: argparse.Namespace) -> tuple[str, ...]:
    if not _normalized_optional_text(getattr(args, "source_url", None)) and not tuple(
        getattr(args, "evidence_paths", ()) or ()
    ):
        source = _read_guided_source()
        if source is None:
            return (EXTERNAL_READONLY_ASK_GUIDED_CANCELLED,)
        source = _normalize_guided_source_input(source)
        if not source:
            return (EXTERNAL_READONLY_ASK_GUIDED_INPUT_REQUIRED,)
        if source.startswith(("http://", "https://")):
            args.source_url = source
        else:
            args.evidence_paths = [source]

    if not _normalized_question(getattr(args, "question", None)):
        question = _read_guided_question()
        if question is None:
            return (EXTERNAL_READONLY_ASK_GUIDED_CANCELLED,)
        question = _normalize_guided_question_input(question)
        if not question:
            return (EXTERNAL_READONLY_ASK_GUIDED_QUESTION_REQUIRED,)
        args.question = question

    if not _model_alias(args) and not _explicit_model_name(args):
        model_alias = _read_guided_model_alias()
        if model_alias is None:
            return (EXTERNAL_READONLY_ASK_GUIDED_CANCELLED,)
        if model_alias not in {"deepseek", "gemma4"}:
            return (EXTERNAL_READONLY_ASK_GUIDED_INPUT_REQUIRED,)
        args.model_alias = model_alias

    source_url = _normalized_optional_text(getattr(args, "source_url", None))
    if source_url:
        if not _guided_confirm("允许本次外部只读抓取该 URL？"):
            return (EXTERNAL_READONLY_ASK_GUIDED_EXTERNAL_FETCH_DECLINED,)
        _apply_guided_external_readonly_fetch_confirmation(args)

    if not _guided_confirm("允许本次受控大模型回答？"):
        return (EXTERNAL_READONLY_ASK_GUIDED_LIVE_LLM_DECLINED,)
    _apply_guided_live_llm_confirmation(args)

    if _guided_local_ollama_selected(args):
        _apply_guided_ollama_confirmation(args)
        return ()

    if _guided_external_provider_selected(args):
        if not _guided_confirm("允许本次外部模型 provider 调用？"):
            return (EXTERNAL_READONLY_ASK_GUIDED_EXTERNAL_PROVIDER_DECLINED,)
        _apply_guided_external_provider_confirmation(args)
        if (
            not os.getenv(DEEPSEEK_API_KEY_ENV)
            and not getattr(args, "prompt_provider_key", False)
            and not getattr(args, "use_stored_provider_key", False)
        ):
            key_mode = _read_guided_provider_key_mode()
            if key_mode is None:
                return (EXTERNAL_READONLY_ASK_GUIDED_CANCELLED,)
            if key_mode == "stored":
                args.use_stored_provider_key = True
            elif key_mode == "prompt":
                args.prompt_provider_key = True
            else:
                return (EXTERNAL_READONLY_ASK_GUIDED_INPUT_REQUIRED,)
    return ()


def _guided_prompt_available() -> bool:
    if os.getenv("CI"):
        return False
    return sys.stdin.isatty() and sys.stderr.isatty()


def _guided_follow_up_prompt_available() -> bool:
    if os.getenv("CI"):
        return False
    return sys.stdin.isatty() and sys.stderr.isatty()


def _read_guided_source() -> str | None:
    return _read_guided_line("请输入 URL 或 evidence path: ")


def _read_guided_question() -> str | None:
    return _read_guided_line("请输入问题: ")


def _read_guided_follow_up_question() -> str | None:
    return _read_guided_line("请输入追问问题: ")


def _read_guided_follow_up_decision() -> tuple[str, str | None]:
    choice = _read_guided_line(
        "继续围绕同一证据追问；直接输入追问问题，或输入 no 结束: "
    )
    if choice is None:
        return ("cancel", None)
    normalized = " ".join(str(choice or "").strip().lower().split())
    if not normalized:
        return ("continue", None)
    if normalized in {"y", "yes", "true", "1", "同意", "确认", "允许", "继续"}:
        return ("continue", None)
    if normalized in {"n", "no", "false", "0", "不同意", "取消", "否", "不", "不用"}:
        return ("decline", None)
    question = _normalize_guided_question_input(choice)
    if question:
        return ("question", question)
    return ("decline", None)


def _read_guided_model_alias() -> str | None:
    print("请选择模型：1) deepseek  2) gemma4", file=sys.stderr)
    choice = _read_guided_line("请输入 1、2、deepseek 或 gemma4: ")
    normalized = _normalize_guided_choice_input(
        choice,
        labels=("model", "model alias", "模型", "选择模型"),
    )
    if normalized in {"1", "deepseek"}:
        return "deepseek"
    if normalized in {"2", "gemma4"}:
        return "gemma4"
    if not normalized:
        return None
    return normalized


def _read_guided_provider_key_mode() -> str | None:
    print("请选择 DeepSeek key 使用方式：1) 使用已保存  2) 输入 key  3) 取消", file=sys.stderr)
    choice = _read_guided_line("请输入 1、2 或 3: ")
    normalized = _normalize_guided_choice_input(
        choice,
        labels=("key", "key mode", "provider key", "deepseek key", "方式", "key 方式"),
    )
    if normalized in {"1", "stored", "saved", "use-stored", "使用已保存"}:
        return "stored"
    if normalized in {"2", "prompt", "input", "输入", "输入key", "输入 key"}:
        return "prompt"
    if normalized in {"3", "cancel", "取消"}:
        return None
    return normalized or None


def _guided_confirm(prompt: str) -> bool:
    choice = _read_guided_line(f"{prompt} 输入 yes/no: ")
    normalized = " ".join(str(choice or "").strip().lower().split())
    return normalized in {"y", "yes", "true", "1", "同意", "确认", "允许"}


def _read_guided_line(prompt: str) -> str | None:
    print(prompt, end="", file=sys.stderr, flush=True)
    try:
        raw_value = sys.stdin.readline()
    except KeyboardInterrupt:
        print("", file=sys.stderr)
        return None
    if raw_value == "":
        return None
    return raw_value.strip()


def _strip_guided_field_label(value: str, labels: tuple[str, ...]) -> str:
    text = str(value or "").strip()
    lowered = text.lower()
    for label in labels:
        normalized_label = label.lower()
        for separator in (":", "："):
            prefix = f"{normalized_label}{separator}"
            if lowered.startswith(prefix):
                return text[len(prefix) :].strip()
    return text


def _normalize_guided_source_input(value: str | None) -> str:
    text = str(value or "").strip()
    match = re.search(r"https?://\S+", text)
    if match:
        return match.group(0).rstrip(".,;，；。)")
    return _strip_guided_field_label(
        text,
        (
            "url/evidence",
            "url",
            "source url",
            "source",
            "evidence path",
            "evidence",
            "来源",
            "地址",
            "路径",
        ),
    )


def _normalize_guided_question_input(value: str | None) -> str:
    return _strip_guided_field_label(
        str(value or ""),
        ("question", "q", "问题", "提问"),
    )


def _normalize_guided_choice_input(
    value: str | None,
    *,
    labels: tuple[str, ...],
) -> str:
    stripped = _strip_guided_field_label(str(value or ""), labels)
    return " ".join(stripped.strip().lower().split())


def _apply_guided_external_readonly_fetch_confirmation(args: argparse.Namespace) -> None:
    args.confirm_external_readonly_fetch = REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION
    args.operator_approved = True
    args.network_gate_open = True
    args.allow_runtime_fetch = True
    args.use_live_transport = True
    args.approval_ref = args.approval_ref or "approval://external-readonly-ask/guided"
    args.runtime_fetch_approval_ref = (
        args.runtime_fetch_approval_ref
        or "approval://external-readonly-ask/guided-runtime-fetch"
    )
    args.audit_ref = args.audit_ref or "audit://external-readonly-ask/guided"


def _apply_guided_live_llm_confirmation(args: argparse.Namespace) -> None:
    args.request_live_llm = True
    args.allow_live_llm = True
    args.live_llm_approval_ref = (
        args.live_llm_approval_ref
        or "approval://external-readonly-ask/guided-live-llm"
    )


def _apply_guided_ollama_confirmation(args: argparse.Namespace) -> None:
    args.request_ollama = True
    args.allow_ollama = True


def _apply_guided_external_provider_confirmation(args: argparse.Namespace) -> None:
    args.operator_approved = True
    args.network_gate_open = True
    args.audit_ref = args.audit_ref or "audit://external-readonly-ask/guided"


def _guided_local_ollama_selected(args: argparse.Namespace) -> bool:
    alias = _model_alias(args)
    if alias == "gemma4":
        return True
    if alias == "deepseek":
        return False
    return not _selected_external_provider(args)


def _guided_external_provider_selected(args: argparse.Namespace) -> bool:
    alias = _model_alias(args)
    if alias == "deepseek":
        return True
    if alias == "gemma4":
        return False
    return _selected_external_provider(args)


def _collect_provider_key(
    args: argparse.Namespace,
    *,
    provider_credential_store_factory: (
        ExternalReadonlyAskProviderCredentialStoreFactory | None
    ),
) -> Any:
    return resolve_evidence_summary_answer_provider_key_setup(
        EvidenceSummaryAnswerProviderKeySetupInput(
            provider_selected=_deepseek_provider_selected(args),
            environment_key_present=bool(os.getenv(DEEPSEEK_API_KEY_ENV)),
            use_stored_provider_key=bool(
                getattr(args, "use_stored_provider_key", False)
            ),
            prompt_provider_key=bool(getattr(args, "prompt_provider_key", False)),
            json_output=bool(args.format == "json" or args.json),
            prompt_available=_provider_key_prompt_available(),
        ),
        prompt_handlers=EvidenceSummaryAnswerProviderKeyPromptHandlers(
            read_secret=_read_provider_key_secret,
            read_persistence_choice=_read_provider_key_persistence_choice,
        ),
        credential_store_factory=provider_credential_store_factory,
        provider_key_required_reason=DEEPSEEK_PROVIDER_KEY_REQUIRED,
        prompt_unavailable_for_json_reason=(
            PROVIDER_KEY_PROMPT_UNAVAILABLE_FOR_JSON_OUTPUT
        ),
        prompt_requires_terminal_reason=(
            PROVIDER_KEY_PROMPT_REQUIRES_INTERACTIVE_TERMINAL
        ),
        input_required_reason=PROVIDER_KEY_INPUT_REQUIRED,
        prompt_cancelled_reason=PROVIDER_KEY_PROMPT_CANCELLED,
        stored_not_found_reason=PROVIDER_KEY_STORED_CREDENTIAL_NOT_FOUND,
        stored_load_failed_reason=PROVIDER_KEY_STORED_CREDENTIAL_LOAD_FAILED,
        persistent_save_failed_reason=PROVIDER_KEY_PERSISTENT_SAVE_FAILED,
    )


def _deepseek_provider_selected(args: argparse.Namespace) -> bool:
    return _model_selection(args).backend_provider == "deepseek"


def _provider_key_prompt_available() -> bool:
    if os.getenv("CI"):
        return False
    return sys.stdin.isatty() and sys.stderr.isatty()


def _read_provider_key_secret() -> str | None:
    try:
        return getpass.getpass("请输入 DeepSeek API key: ", stream=sys.stderr)
    except (EOFError, KeyboardInterrupt):
        return None


def _read_provider_key_persistence_choice() -> str:
    print(
        "请选择 DeepSeek key 使用方式：1) 仅本次使用  2) 长期保存  3) 取消",
        file=sys.stderr,
    )
    print("请输入 1、2 或 3：", end="", file=sys.stderr, flush=True)
    try:
        raw_choice = sys.stdin.readline()
    except KeyboardInterrupt:
        return "cancel"
    normalized = _normalize_guided_choice_input(
        raw_choice,
        labels=("key", "key mode", "provider key", "deepseek key", "方式", "key 方式"),
    )
    if normalized in {"1", "once", "one-time", "本次", "仅本次", "仅本次使用"}:
        return "once"
    if normalized in {"2", "store", "save", "persist", "长期", "长期保存"}:
        return "store"
    return "cancel"


def _output_with_follow_up_turns(
    initial_output: dict[str, Any],
    *,
    follow_up_questions: tuple[str, ...],
    session_state: EvidenceSummaryAnswerAskInteractionState,
    request_id: str,
    guided_follow_up: bool = False,
) -> dict[str, Any]:
    turns = [_turn_summary(initial_output, turn_index=1)]
    current_seed = session_state.follow_up_seed
    if initial_output.get("status") != "success" or current_seed is None:
        initial_output["turn_count"] = len(turns)
        initial_output["turns"] = turns
        initial_output["follow_up_requested"] = bool(follow_up_questions)
        initial_output["follow_up_blocking_reasons"] = (
            ["source_turn_not_success_or_seed_missing"]
            if follow_up_questions
            else []
        )
        return initial_output

    current_state = session_state
    final_output = initial_output
    planned_questions = list(follow_up_questions)
    follow_up_index = 0
    guided_prompted = False
    follow_up_declined = False
    follow_up_cancelled = False
    while planned_questions or guided_follow_up:
        if planned_questions:
            follow_up_question = planned_questions.pop(0)
        else:
            guided_prompted = True
            _print_guided_follow_up_turn_preview(final_output)
            try:
                decision, inline_question = _read_guided_follow_up_decision()
            except (EOFError, KeyboardInterrupt):
                follow_up_cancelled = True
                break
            if decision == "cancel":
                follow_up_cancelled = True
                break
            if decision == "decline":
                follow_up_declined = True
                break
            raw_question = inline_question
            if raw_question is None:
                try:
                    raw_question = _read_guided_follow_up_question()
                except (EOFError, KeyboardInterrupt):
                    follow_up_cancelled = True
                    break
                if raw_question is None:
                    follow_up_cancelled = True
                    break
            follow_up_question = _normalize_guided_question_input(raw_question)
            if not follow_up_question:
                warnings = list(final_output.get("warnings") or [])
                warnings.append(
                    EXTERNAL_READONLY_ASK_GUIDED_FOLLOW_UP_QUESTION_REQUIRED
                )
                final_output["warnings"] = warnings
                final_output["follow_up_blocking_reasons"] = [
                    EXTERNAL_READONLY_ASK_GUIDED_FOLLOW_UP_QUESTION_REQUIRED
                ]
                continue
        follow_up_index += 1
        action_result = run_evidence_summary_answer_ask_follow_up_entry(
            current_state,
            follow_up_question,
            previous_output=final_output,
            turns=tuple(turns),
            request_id=request_id,
            follow_up_index=follow_up_index,
        )
        final_output = action_result.output
        if action_result.next_state is not None:
            current_state = action_result.next_state
        current_seed = current_state.follow_up_seed
        turns.append(_turn_summary(final_output, turn_index=follow_up_index + 1))
        if final_output.get("status") != "success" or current_seed is None:
            break

    final_output["initial_request_id"] = initial_output.get("request_id")
    final_output["turn_count"] = len(turns)
    final_output["turns"] = turns
    final_output["follow_up_requested"] = (
        bool(follow_up_questions)
        or follow_up_index > 0
        or (guided_prompted and not follow_up_declined)
    )
    final_output["guided_follow_up_prompted"] = guided_prompted
    final_output["follow_up_declined"] = follow_up_declined
    final_output["follow_up_cancelled"] = follow_up_cancelled
    final_output.setdefault("follow_up_blocking_reasons", [])
    return final_output


def _print_guided_follow_up_turn_preview(output: Mapping[str, Any]) -> None:
    answer = _optional_string(output.get("answer")) or _optional_string(
        output.get("answer_preview")
    )
    if answer:
        print("", file=sys.stderr)
        print("本轮答案:", file=sys.stderr)
        print(answer, file=sys.stderr)
    print(
        "提示：追问仅在当前进程内围绕同一受治理证据继续；"
        "不启用长期 Memory 或持久会话。",
        file=sys.stderr,
    )


def _turn_summary(output: Mapping[str, Any], *, turn_index: int) -> dict[str, Any]:
    return {
        "turn_index": turn_index,
        "request_id": output.get("request_id"),
        "status": output.get("status"),
        "follow_up": output.get("follow_up") is True,
        "follow_up_turn_index": output.get("follow_up_turn_index"),
        "question_preview": output.get("question_preview"),
        "answer": output.get("answer"),
        "evidence_refs": output.get("evidence_refs") or [],
        "additional_refs": output.get("additional_refs") or [],
    }


def _emit_external_readonly_ask_output(
    args: argparse.Namespace,
    output: Mapping[str, Any],
    *,
    exit_code: int,
) -> int:
    if external_readonly_fetch_output_boundary_violated(output):
        print(
            f"{EXTERNAL_READONLY_ASK_COMMAND} output boundary violation",
            file=sys.stderr,
        )
        return EXIT_OUTPUT_BOUNDARY_FAILURE

    if args.format == "json" or args.json:
        print(json.dumps(dict(output), ensure_ascii=False, sort_keys=True))
    else:
        print(_text_output(output))
    return exit_code


def _text_output(output: Mapping[str, Any]) -> str:
    lines = [
        str(output["product"]),
        f"command: {output['command']}",
        f"status: {output['status']}",
        f"request_id: {output['request_id']}",
        f"answer_run_ref: {output.get('answer_run_ref') or 'unavailable'}",
        f"answer_trace_ref: {output.get('answer_trace_ref') or 'unavailable'}",
        f"answer_artifact_ref: {output.get('answer_artifact_ref') or 'unavailable'}",
        "observability_summary_ref: "
        f"{output.get('observability_summary_ref') or 'unavailable'}",
        f"trace_inspect_ref: {output.get('trace_inspect_ref') or 'unavailable'}",
        f"evidence_ref_count: {output['evidence_ref_count']}",
        f"additional_ref_count: {output['additional_ref_count']}",
        f"readonly_refs_status: {output['readonly_refs_status']}",
        f"llm_call_attempted: {str(output['llm_call_attempted']).lower()}",
        f"llm_runtime_call_performed: {str(output['llm_runtime_call_performed']).lower()}",
    ]
    if output.get("turn_count"):
        lines.append(f"turn_count: {output['turn_count']}")
    if output.get("answer_run_status"):
        lines.append(f"answer_run_status: {output.get('answer_run_status')}")
    if output.get("answer_run_unavailable_reason"):
        lines.append(
            "answer_run_unavailable_reason: "
            f"{output.get('answer_run_unavailable_reason')}"
        )
    if output.get("answer_trace_status"):
        lines.append(f"answer_trace_status: {output.get('answer_trace_status')}")
    if output.get("answer_trace_unavailable_reason"):
        lines.append(
            "answer_trace_unavailable_reason: "
            f"{output.get('answer_trace_unavailable_reason')}"
        )
    if output.get("answer_artifact_status"):
        lines.append(
            f"answer_artifact_status: {output.get('answer_artifact_status')}"
        )
    if output.get("answer_artifact_unavailable_reason"):
        lines.append(
            "answer_artifact_unavailable_reason: "
            f"{output.get('answer_artifact_unavailable_reason')}"
        )
    if output.get("observability_summary_status"):
        lines.append(
            "observability_summary_status: "
            f"{output.get('observability_summary_status')}"
        )
    if output.get("observability_summary_unavailable_reason"):
        lines.append(
            "observability_summary_unavailable_reason: "
            f"{output.get('observability_summary_unavailable_reason')}"
        )
    if output.get("trace_inspect_status"):
        lines.append(f"trace_inspect_status: {output.get('trace_inspect_status')}")
    if output.get("trace_inspect_unavailable_reason"):
        lines.append(
            "trace_inspect_unavailable_reason: "
            f"{output.get('trace_inspect_unavailable_reason')}"
        )
    trace_inspect_summary = _mapping(output.get("trace_inspect_summary"))
    if trace_inspect_summary:
        reason = trace_inspect_summary.get("inspect_reason")
        if reason:
            lines.append(f"trace_inspect_reason: {reason}")
        explanation = trace_inspect_summary.get("user_explanation")
        if explanation:
            lines.append(f"trace_inspect_explanation: {explanation}")
    safe_observability_summary = _mapping(output.get("safe_observability_summary"))
    observability_explanation_printed = False
    if safe_observability_summary:
        reason = safe_observability_summary.get("reason")
        if reason:
            lines.append(f"observability_reason: {reason}")
        explanation = safe_observability_summary.get("user_explanation")
        if explanation:
            lines.append(f"observability_explanation: {explanation}")
            observability_explanation_printed = True
    if output.get("observability_explanation") and not observability_explanation_printed:
        lines.append(
            f"observability_explanation: {output.get('observability_explanation')}"
        )
    if output.get("answer_scoped_transformation"):
        lines.append("answer_scoped_transformation: true")
        lines.append(
            "answer_scope: answer_scoped; temporary_only; "
            "durable_session=false; memory_enabled=false"
        )
    if output.get("guided_session_operation_summary"):
        lines.append("guided_session_operation_summary: true")
        lines.append(
            "summary_scope: current_process_only; "
            "durable_session=false; memory_enabled=false"
        )
    if output.get("follow_up"):
        lines.append(f"follow_up_turn_index: {output.get('follow_up_turn_index')}")
    if (
        output.get("follow_up_available")
        or output.get("follow_up")
        or output.get("turn_count")
        or output.get("guided_follow_up_prompted")
    ):
        lines.append(
            "follow_up_scope: temporary_only; "
            "durable_session=false; memory_enabled=false"
        )
    if output.get("guided_follow_up_prompted"):
        lines.append(
            "guided_follow_up_prompted: "
            f"{str(output.get('guided_follow_up_prompted')).lower()}"
        )
    if output.get("follow_up_declined"):
        lines.append("follow_up_declined: true")
    if output.get("follow_up_cancelled"):
        lines.append("follow_up_cancelled: true")
    if output.get("follow_up_available"):
        seed_ref = _mapping(output.get("follow_up_seed")).get("seed_ref")
        suffix = f" ({seed_ref})" if seed_ref else ""
        lines.append(f"follow_up_available: true{suffix}")
    blocking = output.get("blocking_reasons") or []
    warnings = output.get("warnings") or []
    if blocking:
        lines.append("blocking_reasons: " + ", ".join(map(str, blocking)))
    failure_explanation = output.get("failure_explanation")
    if failure_explanation:
        lines.append("failure_explanation: " + str(failure_explanation))
    recovery_hints = _list_value(output.get("recovery_hints"))
    if recovery_hints:
        lines.append("recovery_hints:")
        lines.extend(f"- {hint}" for hint in recovery_hints)
    evidence_refs = _list_value(output.get("evidence_refs"))
    if evidence_refs:
        lines.append("evidence_refs:")
        lines.extend(_text_ref_lines(evidence_refs))
    additional_refs = _list_value(output.get("additional_refs"))
    if additional_refs:
        lines.append("additional_refs:")
        lines.extend(_text_ref_lines(additional_refs))
    if warnings:
        lines.append("warnings: " + ", ".join(map(str, warnings)))
    answer = output.get("answer")
    if answer:
        lines.append("answer:")
        lines.append(str(answer))
    turns = _list_value(output.get("turns"))
    if turns:
        lines.append("turns:")
        for turn in turns:
            mapping = _mapping(turn)
            lines.append(
                "- "
                f"{mapping.get('turn_index')}: "
                f"{mapping.get('status')} "
                f"{mapping.get('question_preview')}"
            )
    return "\n".join(lines)


def _exit_code_from_output(output: Mapping[str, Any]) -> int:
    return _exit_code_from_status(output.get("status"))


def _exit_code_from_status(status: Any) -> int:
    if status == "success":
        return EXIT_OK
    if status in {"blocked", "insufficient_evidence"}:
        return EXIT_BLOCKING
    return EXIT_RUNTIME_FAILURE


def _natural_language_confirmation_satisfied(args: argparse.Namespace) -> bool:
    return (
        str(args.confirm_external_readonly_fetch or "").strip()
        == REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION
    )


def _model_name(args: argparse.Namespace) -> str:
    return _model_selection(args).model_name


def _ensure_model_selection(args: argparse.Namespace) -> tuple[str, ...]:
    selection = resolve_evidence_summary_answer_ask_model_selection_from_channel_options(
        args,
        alias_conflict_reason=EXTERNAL_READONLY_ASK_MODEL_ALIAS_CONFLICT,
        alias_unknown_reason_prefix=EXTERNAL_READONLY_ASK_MODEL_ALIAS_UNKNOWN,
    )
    setattr(args, "_external_readonly_ask_model_selection", selection)
    apply_evidence_summary_answer_ask_model_selection_to_channel_options(
        args,
        selection,
    )
    return tuple(selection.blocking_reasons)


def _model_selection(args: argparse.Namespace) -> Any:
    selection = getattr(args, "_external_readonly_ask_model_selection", None)
    if selection is None:
        _ensure_model_selection(args)
        selection = getattr(args, "_external_readonly_ask_model_selection")
    return selection


def _explicit_model_name(args: argparse.Namespace) -> str | None:
    model_name = getattr(args, "model_name", None)
    return model_name.strip() if isinstance(model_name, str) and model_name.strip() else None


def _model_alias(args: argparse.Namespace) -> str | None:
    alias = getattr(args, "model_alias", None)
    return alias.strip() if isinstance(alias, str) and alias.strip() else None


def _selected_external_provider(args: argparse.Namespace) -> bool:
    return bool(_model_selection(args).external_provider_selected)


def _external_provider_gate_blocking_reasons(
    args: argparse.Namespace,
) -> tuple[str, ...]:
    if not _selected_external_provider(args):
        return ()
    reasons: list[str] = []
    if not bool(getattr(args, "network_gate_open", False)):
        reasons.append("external_llm_network_gate_open_required")
    if not bool(getattr(args, "operator_approved", False)):
        reasons.append("external_llm_operator_approved_required")
    if not getattr(args, "audit_ref", None):
        reasons.append("external_llm_audit_ref_required")
    return tuple(reasons)


def _normalized_question(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _normalized_follow_up_questions(values: Any) -> tuple[str, ...]:
    questions = []
    for value in _list_value(values):
        question = _normalized_question(value)
        if question:
            questions.append(question)
    return tuple(questions)


def _normalized_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _preview(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip()


def _local_ollama_api_base(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "http" and parsed.hostname in {
        "127.0.0.1",
        "localhost",
        "::1",
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text_ref_lines(value: list[Any]) -> list[str]:
    lines: list[str] = []
    for item in value:
        mapping = _mapping(item)
        ref = mapping.get("ref")
        if not ref:
            continue
        kind = mapping.get("kind") or "unknown"
        purpose = mapping.get("purpose")
        suffix = f" ({purpose})" if purpose else ""
        lines.append(f"- {kind}: {ref}{suffix}")
    return lines


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _string_tuple(value: Any) -> tuple[str, ...]:
    return tuple(str(item) for item in _list_value(value))


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


__all__ = [
    "EXTERNAL_READONLY_ASK_COMMAND",
    "EXTERNAL_READONLY_ASK_INTERACTION_MODE",
    "EXTERNAL_READONLY_ASK_REQUEST_ID",
    "ExternalReadonlyAskFetchExecutor",
    "ExternalReadonlyAskLlmInvocationServiceFactory",
    "build_external_readonly_ask_cli_output",
    "build_external_readonly_ask_follow_up_cli_output",
    "external_readonly_ask_command",
    "run_external_readonly_ask_follow_up_channel",
    "run_external_readonly_ask_initial_channel",
]
