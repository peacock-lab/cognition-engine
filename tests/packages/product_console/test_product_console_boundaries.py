from __future__ import annotations

import ast
import json
import tomllib
from pathlib import Path
from types import SimpleNamespace

import product_console
from product_application_assembly.evidence_summary_answer_provider_key_setup import (
    EvidenceSummaryAnswerProviderKeyPromptHandlers,
)
from product_console import (
    build_product_console_home_payload,
    render_product_console_home,
    run_product_console,
)
from product_console.console import render_product_console_help


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "packages" / "product_console"
SOURCE_ROOT = PACKAGE_ROOT / "src" / "product_console"
PYPROJECT_PATH = PACKAGE_ROOT / "pyproject.toml"


def test_product_console_public_surface_is_minimal() -> None:
    assert product_console.__all__ == (
        "PRODUCT_CONSOLE_PACKAGE",
        "PRODUCT_CONSOLE_STATUS",
        "build_product_console_home_payload",
        "render_product_console_home",
        "run_product_console",
    )
    assert product_console.PRODUCT_CONSOLE_PACKAGE == "product_console"
    assert product_console.PRODUCT_CONSOLE_STATUS == "candidate"


def test_product_console_pyproject_declares_distribution_and_boundary() -> None:
    project = _pyproject()["project"]

    assert project["name"] == "cognition-system-product-console"
    assert project["version"] == "0.8.2"
    assert project["dependencies"] == [
        "cognition-system-product-application-assembly==0.8.2",
    ]
    assert "scripts" not in project


def test_product_console_source_uses_only_allowed_product_display_dependencies() -> None:
    allowed_prefixes = (
        "__future__",
        "collections.abc",
        "getpass",
        "json",
        "os",
        "product_application_assembly",
        "product_console",
        "sys",
        "typing",
        "warnings",
    )

    for source_path in SOURCE_ROOT.rglob("*.py"):
        for imported_module in _absolute_imports(source_path):
            assert any(
                imported_module == prefix or imported_module.startswith(f"{prefix}.")
                for prefix in allowed_prefixes
            ), (
                source_path,
                imported_module,
            )


def test_product_console_source_has_no_execution_or_hidden_cli_bridge() -> None:
    forbidden_markers = (
        "cognition_cli",
        "build_external_readonly_ask_cli_output",
        "ProductGatewayResponse",
        "product_gateway",
        "observability_hub",
        "build_evidence_summary_answer_trace",
        "build_evidence_summary_answer_artifact",
        "build_evidence_summary_answer_trace_inspect",
        "RuntimeLiveLlmConfigView",
        "ModelRouteFacts",
        "MacOSKeychain",
        "LlmGovernancePrecondition",
        "config/",
        "read_text(",
        "open(",
        "requests",
        "httpx",
        "completion" + "(",
    )

    for source_path in SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        for marker in forbidden_markers:
            assert marker not in source, (source_path, marker)


def test_product_console_renders_candidate_home_without_running_product_flow() -> None:
    payload = build_product_console_home_payload()
    text = render_product_console_home()
    captured: list[str] = []

    exit_code = run_product_console(["--json"], output_writer=captured.append)
    json_payload = json.loads(captured[0])

    assert exit_code == 0
    assert payload["command"] == "cognition-console"
    assert payload["display"]["runtime_backed"] is False
    assert payload["display"]["products"][0]["answer_run"]["status"] == "not_started"
    assert "Cognition System / 认知系统产品控制台" in text
    assert "可复查资料问答包" in text
    assert "cognition-console ask --guided" in text
    assert "不会联网、不会调用模型、不会读取或保存模型服务密钥" in text
    assert json_payload["display"]["public_schema"] is False


def test_product_console_default_home_is_user_facing_not_engineering_dump() -> None:
    text = render_product_console_home()

    assert "当前可用产品" in text
    assert "安全边界" in text
    assert "下一步" in text
    for engineering_marker in (
        "display_model_ref",
        "display_model_status",
        "runtime_backed",
        "public_schema",
        "product_id",
        "available_as_existing_cli_product_flow",
        "handoff_only",
        "candidate_display_only",
        "TUI",
        "ADK Task",
        "Workflow runtime",
    ):
        assert engineering_marker not in text


def test_product_console_json_keeps_machine_readable_display_facts() -> None:
    captured: list[str] = []

    exit_code = run_product_console(["--json"], output_writer=captured.append)
    payload = json.loads(captured[0])

    assert exit_code == 0
    assert payload["display"]["display_model_ref"]
    assert payload["display"]["runtime_backed"] is False
    assert payload["display"]["products"][0]["product_id"] == (
        "reviewable-evidence-answer-pack"
    )


def test_product_console_help_is_chinese_productized_help() -> None:
    captured: list[str] = []

    exit_code = run_product_console(["--help"], output_writer=captured.append)
    help_text = captured[0]

    assert exit_code == 0
    assert help_text == render_product_console_help()
    assert "用法：cognition-console [--json] [--help]" in help_text
    assert "认知系统产品控制台" in help_text
    assert "cognition-console ask --guided" in help_text
    assert "不联网、不调用模型、不读取或保存模型服务密钥" in help_text
    assert "Render the Cognition System product console candidate" not in help_text


def test_product_console_ask_guided_calls_product_entry_service() -> None:
    answers = iter(
        (
            "https://example.com",
            "这份资料主要说明什么？",
            "2",
            "y",
            "y",
        )
    )
    captured_output: list[str] = []
    captured_requests = []

    def input_reader(_prompt: str) -> str:
        return next(answers)

    def ask_runner(request):
        captured_requests.append(request)
        return SimpleNamespace(
            exit_code=0,
            output={
                "command": "cognition external-readonly ask",
                "status": "success",
                "answer_run_ref": "evidence-summary-answer-run://run-test",
                "answer_trace_ref": "evidence-summary-answer-trace://trace-test",
                "answer_artifact_ref": (
                    "evidence-summary-answer-artifact://artifact-test"
                ),
                "observability_summary_ref": (
                    "evidence-summary-answer-observability-summary://summary-test"
                ),
                "trace_inspect_ref": (
                    "evidence-summary-answer-trace-inspect://inspect-test"
                ),
                "answer": "这是一个示例域名。",
            },
        )

    exit_code = run_product_console(
        ["ask", "--guided"],
        input_reader=input_reader,
        output_writer=captured_output.append,
        ask_runner=ask_runner,
    )

    assert exit_code == 0
    assert len(captured_requests) == 1
    request = captured_requests[0]
    assert request.source_url == "https://example.com"
    assert request.evidence_paths == ()
    assert request.question == "这份资料主要说明什么？"
    assert request.model_alias == "gemma4"
    assert request.input_channel == "product_console"
    assert request.confirm_external_readonly_fetch == "同意外部只读抓取"
    assert request.allow_live_llm is True
    assert "answer_run_ref: evidence-summary-answer-run://run-test" in (
        captured_output[0]
    )
    assert "details: 使用 --json 查看 trace / artifact / observability / inspect 详情。" in (
        captured_output[0]
    )
    assert "answer_trace_ref:" not in captured_output[0]
    assert "answer_artifact_ref:" not in captured_output[0]
    assert "observability_summary_ref:" not in captured_output[0]
    assert "trace_inspect_ref:" not in captured_output[0]
    assert "command: cognition-console ask" in captured_output[0]
    assert "command: cognition external-readonly ask" not in captured_output[0]
    assert "answer:\n这是一个示例域名。" in captured_output[0]


def test_product_console_ask_guided_json_keeps_review_detail_refs() -> None:
    answers = iter(
        (
            "https://example.com",
            "这份资料主要说明什么？",
            "2",
            "y",
            "y",
        )
    )
    captured_output: list[str] = []

    def input_reader(_prompt: str) -> str:
        return next(answers)

    follow_up_called = False

    def ask_runner(_request):
        return SimpleNamespace(
            exit_code=0,
            output={
                "request_id": "external-readonly-ask-request://product-console/ask",
                "command": "cognition external-readonly ask",
                "status": "success",
                "answer_run_ref": "evidence-summary-answer-run://run-test",
                "answer_trace_ref": "evidence-summary-answer-trace://trace-test",
                "answer_artifact_ref": (
                    "evidence-summary-answer-artifact://artifact-test"
                ),
                "observability_summary_ref": (
                    "evidence-summary-answer-observability-summary://summary-test"
                ),
                "trace_inspect_ref": (
                    "evidence-summary-answer-trace-inspect://inspect-test"
                ),
                "answer": "这是一个示例域名。",
                "follow_up_available": True,
            },
            next_state=object(),
        )

    def follow_up_runner(*_args, **_kwargs):
        nonlocal follow_up_called
        follow_up_called = True
        return SimpleNamespace(exit_code=0, output={"status": "success"})

    exit_code = run_product_console(
        ["ask", "--guided", "--json"],
        input_reader=input_reader,
        output_writer=captured_output.append,
        ask_runner=ask_runner,
        ask_follow_up_runner=follow_up_runner,
    )
    payload = json.loads(captured_output[0])

    assert exit_code == 0
    assert len(captured_output) == 1
    assert follow_up_called is False
    assert payload["command"] == "cognition-console ask"
    assert payload["review"]["answer_run_ref"] == (
        "evidence-summary-answer-run://run-test"
    )
    assert payload["review"]["answer_trace_ref"] == (
        "evidence-summary-answer-trace://trace-test"
    )
    assert payload["review"]["answer_artifact_ref"] == (
        "evidence-summary-answer-artifact://artifact-test"
    )
    assert payload["review"]["observability_summary_ref"] == (
        "evidence-summary-answer-observability-summary://summary-test"
    )
    assert payload["review"]["trace_inspect_ref"] == (
        "evidence-summary-answer-trace-inspect://inspect-test"
    )


def test_product_console_ask_guided_interrupts_without_traceback() -> None:
    captured_output: list[str] = []
    ask_called = False

    def input_reader(_prompt: str) -> str:
        raise KeyboardInterrupt

    def ask_runner(_request):
        nonlocal ask_called
        ask_called = True
        return SimpleNamespace(exit_code=0, output={"status": "success"})

    exit_code = run_product_console(
        ["ask", "--guided"],
        input_reader=input_reader,
        output_writer=captured_output.append,
        ask_runner=ask_runner,
    )

    assert exit_code == 130
    assert ask_called is False
    assert "status: interrupted" in captured_output[0]
    assert "product_console_input_interrupted" in captured_output[0]
    assert "traceback" not in captured_output[0].lower()


def test_product_console_ask_guided_json_interrupts_without_traceback() -> None:
    captured_output: list[str] = []

    def input_reader(_prompt: str) -> str:
        raise KeyboardInterrupt

    exit_code = run_product_console(
        ["ask", "--guided", "--json"],
        input_reader=input_reader,
        output_writer=captured_output.append,
        ask_runner=lambda _request: SimpleNamespace(
            exit_code=0,
            output={"status": "success"},
        ),
    )
    payload = json.loads(captured_output[0])

    assert exit_code == 130
    assert payload["status"] == "interrupted"
    assert payload["blocking_reasons"] == ["product_console_input_interrupted"]
    assert "traceback" not in captured_output[0].lower()


def test_product_console_ask_guided_runs_same_process_follow_up_loop() -> None:
    answers = iter(
        (
            "https://example.com",
            "这份资料主要说明什么？",
            "2",
            "y",
            "y",
            "请基于以上答案内容做个三点式摘要",
        )
    )
    captured_output: list[str] = []
    captured_follow_ups = []

    def input_reader(_prompt: str) -> str:
        return next(answers)

    initial_state = object()
    next_state = object()

    def ask_runner(_request):
        return SimpleNamespace(
            exit_code=0,
            output={
                "request_id": "external-readonly-ask-request://product-console/ask",
                "command": "cognition-console ask",
                "status": "success",
                "answer_run_ref": "evidence-summary-answer-run://run-initial",
                "answer_trace_ref": "evidence-summary-answer-trace://trace-initial",
                "answer_artifact_ref": (
                    "evidence-summary-answer-artifact://artifact-initial"
                ),
                "observability_summary_ref": (
                    "evidence-summary-answer-observability-summary://summary-initial"
                ),
                "trace_inspect_ref": (
                    "evidence-summary-answer-trace-inspect://inspect-initial"
                ),
                "answer": "这是一个示例域名。",
                "question_preview": "这份资料主要说明什么？",
                "follow_up_available": True,
            },
            next_state=initial_state,
        )

    def follow_up_runner(
        state,
        follow_up_question,
        *,
        previous_output,
        turns,
        request_id,
        follow_up_index,
    ):
        captured_follow_ups.append(
            {
                "state": state,
                "follow_up_question": follow_up_question,
                "previous_output": previous_output,
                "turns": turns,
                "request_id": request_id,
                "follow_up_index": follow_up_index,
            }
        )
        return SimpleNamespace(
            exit_code=0,
            output={
                "request_id": (
                    "external-readonly-ask-request://product-console/ask/"
                    "answer-transform-1"
                ),
                "command": "cognition-console ask",
                "status": "success",
                "answer_run_ref": None,
                "answer_run_status": "unavailable",
                "answer_run_unavailable_reason": (
                    "answer_scoped_transformation_uses_previous_answer"
                ),
                "answer_trace_ref": None,
                "answer_trace_unavailable_reason": (
                    "answer_scoped_transformation_uses_previous_answer"
                ),
                "answer_artifact_ref": None,
                "answer_artifact_unavailable_reason": (
                    "answer_scoped_transformation_uses_previous_answer"
                ),
                "observability_summary_ref": None,
                "observability_summary_unavailable_reason": (
                    "answer_scoped_transformation_uses_previous_answer"
                ),
                "trace_inspect_ref": None,
                "trace_inspect_unavailable_reason": (
                    "answer_scoped_transformation_uses_previous_answer"
                ),
                "answer": "1. 示例域名。\n2. 用于文档。\n3. 不用于实际运营。",
                "answer_scoped_transformation": True,
                "question_preview": follow_up_question,
                "follow_up_available": False,
            },
            next_state=next_state,
        )

    exit_code = run_product_console(
        ["ask", "--guided"],
        input_reader=input_reader,
        output_writer=captured_output.append,
        ask_runner=ask_runner,
        ask_follow_up_runner=follow_up_runner,
    )

    assert exit_code == 0
    assert len(captured_follow_ups) == 1
    follow_up = captured_follow_ups[0]
    assert follow_up["state"] is initial_state
    assert follow_up["follow_up_question"] == "请基于以上答案内容做个三点式摘要"
    assert follow_up["request_id"] == "external-readonly-ask-request://product-console/ask"
    assert follow_up["follow_up_index"] == 1
    assert follow_up["turns"][0]["answer"] == "这是一个示例域名。"
    assert "follow_up: 可继续围绕同一证据追问" in captured_output[0]
    assert "仅在当前进程内有效" in captured_output[1]
    assert "answer_run_ref: unavailable" not in captured_output[-1]
    assert "本轮只基于上一轮可见答案变换" in captured_output[-1]
    assert "answer:\n1. 示例域名。" in captured_output[-1]


def test_product_console_ask_guided_no_exits_follow_up_loop() -> None:
    answers = iter(
        (
            "https://example.com",
            "这份资料主要说明什么？",
            "2",
            "y",
            "y",
            "no",
        )
    )
    follow_up_called = False

    def input_reader(_prompt: str) -> str:
        return next(answers)

    def ask_runner(_request):
        return SimpleNamespace(
            exit_code=0,
            output={
                "request_id": "external-readonly-ask-request://product-console/ask",
                "command": "cognition-console ask",
                "status": "success",
                "answer": "这是一个示例域名。",
                "follow_up_available": True,
            },
            next_state=object(),
        )

    def follow_up_runner(*_args, **_kwargs):
        nonlocal follow_up_called
        follow_up_called = True
        return SimpleNamespace(exit_code=0, output={"status": "success"})

    exit_code = run_product_console(
        ["ask", "--guided"],
        input_reader=input_reader,
        output_writer=lambda _text: None,
        ask_runner=ask_runner,
        ask_follow_up_runner=follow_up_runner,
    )

    assert exit_code == 0
    assert follow_up_called is False


def test_product_console_ask_guided_empty_follow_up_keeps_prompting() -> None:
    answers = iter(
        (
            "https://example.com",
            "这份资料主要说明什么？",
            "2",
            "y",
            "y",
            "",
            "n",
        )
    )
    captured_output: list[str] = []

    def input_reader(_prompt: str) -> str:
        return next(answers)

    def ask_runner(_request):
        return SimpleNamespace(
            exit_code=0,
            output={
                "request_id": "external-readonly-ask-request://product-console/ask",
                "command": "cognition-console ask",
                "status": "success",
                "answer": "这是一个示例域名。",
                "follow_up_available": True,
            },
            next_state=object(),
        )

    exit_code = run_product_console(
        ["ask", "--guided"],
        input_reader=input_reader,
        output_writer=captured_output.append,
        ask_runner=ask_runner,
    )

    assert exit_code == 0
    assert "请输入追问问题，或输入 no 结束。" in captured_output


def test_product_console_ask_guided_reuses_saved_deepseek_key() -> None:
    answers = iter(
        (
            "https://example.com",
            "这份资料主要说明什么？",
            "1",
            "y",
            "y",
            "y",
            "1",
        )
    )
    captured_requests = []

    def input_reader(_prompt: str) -> str:
        return next(answers)

    def ask_runner(request):
        captured_requests.append(request)
        return SimpleNamespace(exit_code=0, output={"status": "success"})

    class FakeStore:
        def load_api_key(self):
            return SimpleNamespace(
                status="success",
                backend="fake_keychain",
                secret_value="sk-from-store",
            )

    exit_code = run_product_console(
        ["ask", "--guided"],
        input_reader=input_reader,
        output_writer=lambda _text: None,
        ask_runner=ask_runner,
        provider_credential_store_factory=lambda: FakeStore(),
    )

    assert exit_code == 0
    assert captured_requests[0].model_alias == "deepseek"
    assert captured_requests[0].provider_key == "sk-from-store"
    assert captured_requests[0].provider_key_metadata["provider_key_source"] == (
        "stored_keychain"
    )
    assert captured_requests[0].channel_blocking_reasons == ()


def test_product_console_ask_guided_uses_deepseek_environment_key_without_mode_prompt(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env")
    answers = iter(
        (
            "https://example.com",
            "这份资料主要说明什么？",
            "1",
            "y",
            "y",
            "y",
        )
    )
    captured_requests = []

    def input_reader(_prompt: str) -> str:
        return next(answers)

    def ask_runner(request):
        captured_requests.append(request)
        return SimpleNamespace(exit_code=0, output={"status": "success"})

    exit_code = run_product_console(
        ["ask", "--guided"],
        input_reader=input_reader,
        output_writer=lambda _text: None,
        ask_runner=ask_runner,
    )

    assert exit_code == 0
    assert captured_requests[0].provider_key is None
    assert captured_requests[0].provider_key_metadata["provider_key_source"] == (
        "environment"
    )
    assert captured_requests[0].channel_blocking_reasons == ()


def test_product_console_ask_guided_accepts_prompted_deepseek_key_once() -> None:
    answers = iter(
        (
            "https://example.com",
            "这份资料主要说明什么？",
            "1",
            "y",
            "y",
            "y",
            "2",
        )
    )
    captured_requests = []

    def input_reader(_prompt: str) -> str:
        return next(answers)

    def ask_runner(request):
        captured_requests.append(request)
        return SimpleNamespace(exit_code=0, output={"status": "success"})

    prompt_handlers = EvidenceSummaryAnswerProviderKeyPromptHandlers(
        read_secret=lambda: "sk-from-prompt",
        read_persistence_choice=lambda: "once",
    )

    exit_code = run_product_console(
        ["ask", "--guided"],
        input_reader=input_reader,
        output_writer=lambda _text: None,
        ask_runner=ask_runner,
        provider_key_prompt_handlers=prompt_handlers,
    )

    assert exit_code == 0
    assert captured_requests[0].model_alias == "deepseek"
    assert captured_requests[0].provider_key == "sk-from-prompt"
    assert captured_requests[0].provider_key_metadata["provider_key_source"] == (
        "prompt_once"
    )
    assert captured_requests[0].channel_blocking_reasons == ()


def test_product_console_ask_guided_blocks_deepseek_key_cancel() -> None:
    answers = iter(
        (
            "https://example.com",
            "这份资料主要说明什么？",
            "1",
            "y",
            "y",
            "y",
            "3",
        )
    )
    captured_requests = []

    def input_reader(_prompt: str) -> str:
        return next(answers)

    def ask_runner(request):
        captured_requests.append(request)
        return SimpleNamespace(exit_code=3, output={"status": "blocked"})

    exit_code = run_product_console(
        ["ask", "--guided"],
        input_reader=input_reader,
        output_writer=lambda _text: None,
        ask_runner=ask_runner,
    )

    assert exit_code == 3
    assert captured_requests[0].model_alias == "deepseek"
    assert captured_requests[0].provider_key is None
    assert captured_requests[0].channel_blocking_reasons == (
        "provider_key_prompt_cancelled",
    )


def test_product_console_ask_guided_projects_channel_blocking_reasons() -> None:
    answers = iter(
        (
            "https://example.com",
            "",
            "2",
            "n",
            "n",
        )
    )
    captured_requests = []

    def input_reader(_prompt: str) -> str:
        return next(answers)

    def ask_runner(request):
        captured_requests.append(request)
        return SimpleNamespace(exit_code=3, output={"status": "blocked"})

    exit_code = run_product_console(
        ["ask", "--guided"],
        input_reader=input_reader,
        output_writer=lambda _text: None,
        ask_runner=ask_runner,
    )

    assert exit_code == 3
    assert captured_requests[0].channel_blocking_reasons == (
        "external_readonly_ask_guided_question_required",
        "external_readonly_ask_guided_external_fetch_declined",
        "external_readonly_ask_guided_live_llm_declined",
    )


def _absolute_imports(source_path: Path) -> tuple[str, ...]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.append(node.module)
    return tuple(imports)


def _pyproject() -> dict:
    return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
