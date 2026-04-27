"""Minimal insight-to-decision workflow orchestration."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Callable, Dict, Optional, Sequence

from engine.transformer import generate_outputs

from cognition_engine.adk_workflow_adapter import (
    WorkflowStep,
    add_workflow_artifact_ref,
    run_adk_backed_workflow,
)
from cognition_engine import decision_pack, model_enhancement, product_brief

COMMAND_NAME = "python -m cognition_engine.workflow"
COMMAND_USAGE = f"{COMMAND_NAME} --insight <insight_id>"
CONTRACT_VERSION = "ce-insight-to-decision-workflow-result/v1"
WORKFLOW_NAME = "insight-to-decision workflow"
OUTPUT_TYPE = "insight-to-decision-workflow"
OUTPUT_SLUG = "workflows"
METADATA_TYPE = "workflow"
USER_ERROR_EXIT_CODE = 2

StepBuilder = Callable[[str], Dict[str, Any]]


class WorkflowError(ValueError):
    def __init__(
        self,
        error_code: str,
        error_message: str,
        *,
        insight_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        exit_code: int = USER_ERROR_EXIT_CODE,
    ) -> None:
        super().__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message
        self.insight_id = insight_id
        self.extra = extra or {}
        self.exit_code = exit_code


def list_available_insight_ids() -> list[str]:
    insights_root = generate_outputs.NEW_PROJECT_PATH / "data" / "insights"
    if not insights_root.exists():
        return []

    insight_ids = {path.stem for path in insights_root.glob("*/*.json")}
    return sorted(insight_ids)


def validate_workflow_request(
    insight_id: Optional[str],
    *,
    extra_args: Optional[Sequence[str]] = None,
) -> str:
    extra_args = list(extra_args or [])
    normalized_insight_id = (insight_id or "").strip()

    if not normalized_insight_id:
        raise WorkflowError(
            "missing_insight",
            "必须通过 --insight 提供单个 insight_id。",
            insight_id=None,
            extra={"available_insight_ids": list_available_insight_ids()},
        )

    if extra_args:
        raise WorkflowError(
            "unexpected_args",
            "workflow 入口只接受单个 --insight 参数，不接受额外位置参数或未识别参数。",
            insight_id=normalized_insight_id,
            extra={"unexpected_args": extra_args},
        )

    if any(char.isspace() for char in normalized_insight_id) or "," in normalized_insight_id:
        raise WorkflowError(
            "invalid_insight_id",
            "insight_id 必须是单个 ID，不能包含空白字符或逗号分隔列表。",
            insight_id=normalized_insight_id,
        )

    return normalized_insight_id


def build_error_result(
    error_code: str,
    error_message: str,
    *,
    insight_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    result = _build_result_base(insight_id)
    result.update(
        {
            "status": "error",
            "execution_id": None,
            "session_id": None,
            "context_id": None,
            "invocation_id": None,
            "adk_runtime": None,
            "adk_backed": False,
            "legacy_fallback_used": False,
            "steps": [],
            "step_results": [],
            "product_brief": None,
            "decision_pack": None,
            "model_enhancement": None,
            "artifact_refs": [],
            "event_summary": {
                "source": "request validation",
                "adk_event_count": 0,
                "business_event_count": 0,
                "step_events": [],
                "adk_events": [],
            },
            "validation": _empty_validation(),
            "error_code": error_code,
            "error_message": error_message,
        }
    )
    if extra:
        result.update(extra)
    return result


def build_workflow_result(
    insight_id: str,
    *,
    model_provider: Optional[str] = None,
    product_brief_builder: Optional[StepBuilder] = None,
    decision_pack_builder: Optional[StepBuilder] = None,
    model_enhancement_builder: Optional[StepBuilder] = None,
) -> Dict[str, Any]:
    normalized_insight_id = validate_workflow_request(insight_id)
    selected_model_provider = (
        model_provider
        or os.environ.get("CE_WORKFLOW_MODEL_PROVIDER")
        or os.environ.get("CE_MODEL_PROVIDER")
        or "mock"
    )

    product_builder = product_brief_builder or product_brief.build_product_brief_result
    decision_builder = decision_pack_builder or decision_pack.build_decision_pack_result
    enhancement_builder = model_enhancement_builder or (
        lambda current_insight_id: model_enhancement.build_model_enhancement_result(
            current_insight_id,
            provider=selected_model_provider,
        )
    )

    result = run_adk_backed_workflow(
        insight_id=normalized_insight_id,
        result_base=_build_result_base(normalized_insight_id),
        steps=[
            WorkflowStep("product_brief", "product-brief", product_builder),
            WorkflowStep("decision_pack", "decision-pack", decision_builder),
            WorkflowStep("model_enhancement", "model-enhancement", enhancement_builder),
        ],
    )
    if result["status"] in {"success", "partial_success"}:
        _attach_workflow_output(result)
    return result


def print_workflow_result(result: Dict[str, Any], *, json_only: bool = False) -> None:
    if json_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("=" * 60)
    print("认知工作流最小组合闭环")
    print("=" * 60)
    print(f"workflow: {result['workflow_name']}")
    print(f"insight_id: {result['insight_id']}")
    print(f"status: {result['status']}")
    for step in result["steps"]:
        print(f"- {step['name']}: {step['status']} -> {step['output_file']}")
    print("=" * 60)


def print_workflow_error(result: Dict[str, Any], *, json_only: bool = False) -> None:
    if json_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"错误[{result['error_code']}]: {result['error_message']}")
    print(f"用法: {result['usage']}")
    if result.get("available_insight_ids"):
        print("可用 insight_id:")
        for insight_id in result["available_insight_ids"]:
            print(f"  - {insight_id}")


def run_workflow_loop(
    insight_id: Optional[str],
    *,
    json_only: bool = False,
    model_provider: Optional[str] = None,
    extra_args: Optional[Sequence[str]] = None,
) -> int:
    try:
        validated_insight_id = validate_workflow_request(
            insight_id,
            extra_args=extra_args,
        )
        result = build_workflow_result(
            validated_insight_id,
            model_provider=model_provider,
        )
    except WorkflowError as exc:
        error_result = build_error_result(
            exc.error_code,
            exc.error_message,
            insight_id=exc.insight_id,
            extra=exc.extra,
        )
        print_workflow_error(error_result, json_only=json_only)
        return exc.exit_code
    except Exception as exc:  # pragma: no cover - defensive catch for unexpected errors
        error_result = build_error_result(
            "internal_error",
            f"执行 workflow 时发生未预期错误: {exc}",
            insight_id=(insight_id or "").strip() or None,
        )
        print_workflow_error(error_result, json_only=json_only)
        return 1

    print_workflow_result(result, json_only=json_only)
    return 0 if result["status"] in {"success", "partial_success"} else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="执行 insight-to-decision workflow")
    parser.add_argument("--insight", required=True, help="单个 insight_id")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args, extra_args = parser.parse_known_args(argv)
    return run_workflow_loop(
        args.insight,
        json_only=args.json,
        extra_args=extra_args,
    )


def _build_result_base(insight_id: Optional[str]) -> Dict[str, Any]:
    return {
        "command": COMMAND_NAME if insight_id is None else f"{COMMAND_NAME} --insight {insight_id}",
        "command_name": COMMAND_NAME,
        "usage": COMMAND_USAGE,
        "contract_version": CONTRACT_VERSION,
        "workflow_name": WORKFLOW_NAME,
        "output_type": OUTPUT_TYPE,
        "insight_id": insight_id,
        "output_file": None,
        "metadata_file": None,
        "metadata_id": None,
    }


def _empty_validation() -> Dict[str, bool]:
    return {
        "workflow_output_file_exists": False,
        "workflow_metadata_file_exists": False,
        "product_brief_output_file_exists": False,
        "product_brief_metadata_file_exists": False,
        "decision_pack_output_file_exists": False,
        "decision_pack_metadata_file_exists": False,
        "model_enhancement_output_file_exists": False,
        "model_enhancement_metadata_file_exists": False,
        "adk_backed_workflow": False,
        "adk_session_mapped": False,
        "adk_invocation_mapped": False,
        "adk_events_mapped": False,
        "adk_artifacts_mapped": False,
        "legacy_fallback_used": False,
    }


def _attach_workflow_output(result: Dict[str, Any]) -> None:
    content = build_workflow_markdown(result)
    framework_id = _workflow_framework_id(result)
    saved = generate_outputs.save_output_record(
        content,
        OUTPUT_SLUG,
        result["insight_id"],
        framework_id,
        metadata_type=METADATA_TYPE,
    )
    output_file = saved["output_file"]
    metadata_file = saved["metadata_file"]
    metadata = saved["metadata"]

    result["output_file"] = _display_path(output_file)
    result["metadata_file"] = _display_path(metadata_file)
    result["metadata_id"] = metadata["id"]
    result["validation"]["workflow_output_file_exists"] = output_file.exists()
    result["validation"]["workflow_metadata_file_exists"] = metadata_file.exists()
    add_workflow_artifact_ref(result)


def build_workflow_markdown(result: Dict[str, Any]) -> str:
    step_lines = "\n".join(_format_step_line(step) for step in result["steps"])
    child_lines = "\n".join(
        _format_child_reference(label, result[key])
        for label, key in (
            ("Product brief", "product_brief"),
            ("Decision pack", "decision_pack"),
            ("Model enhancement", "model_enhancement"),
        )
        if result.get(key)
    )

    return f"""# Workflow 汇总: {result["workflow_name"]}

## 基本信息
- contract_version: `{result["contract_version"]}`
- output_type: `{result["output_type"]}`
- insight_id: `{result["insight_id"]}`
- status: `{result["status"]}`
- execution_id: `{result.get("execution_id") or ""}`
- session_id: `{result.get("session_id") or ""}`
- context_id: `{result.get("context_id") or ""}`
- invocation_id: `{result.get("invocation_id") or ""}`
- adk_runtime: `{result.get("adk_runtime") or ""}`
- error_code: `{result["error_code"] or ""}`
- error_message: {result["error_message"] or ""}

## 执行步骤摘要
{step_lines}

## 子产物引用
{child_lines}

## ADK-backed 承接映射
- adk_backed: `{str(result.get("adk_backed", False)).lower()}`
- legacy_fallback_used: `{str(result.get("legacy_fallback_used", False)).lower()}`
- event_count: `{result.get("event_summary", {}).get("adk_event_count", 0)}`
- artifact_ref_count: `{len(result.get("artifact_refs", []))}`

## 当前边界
- 本产物只汇总一次 workflow 执行关系与子产物引用。
- 本产物不复制 product brief、decision pack 或 model enhancement 全文。
- 本产物不代表版本发布声明。
"""


def _format_step_line(step: Dict[str, Any]) -> str:
    return (
        f"- `{step['name']}`: status=`{step['status']}`, "
        f"output_type=`{step['output_type']}`, "
        f"output_file=`{step['output_file'] or ''}`, "
        f"metadata_file=`{step['metadata_file'] or ''}`, "
        f"error_code=`{step['error_code'] or ''}`"
    )


def _format_child_reference(label: str, child_summary: Dict[str, Any]) -> str:
    return (
        f"- {label}: output_file=`{child_summary.get('output_file') or ''}`, "
        f"metadata_file=`{child_summary.get('metadata_file') or ''}`, "
        f"metadata_id=`{child_summary.get('metadata_id') or ''}`"
    )


def _display_path(path) -> str:
    try:
        return str(path.relative_to(generate_outputs.NEW_PROJECT_PATH))
    except ValueError:
        return str(path)


def _workflow_framework_id(result: Dict[str, Any]) -> str:
    for key in ("product_brief", "decision_pack", "model_enhancement"):
        child = result.get(key)
        if not child:
            continue
        output_file = child.get("output_file") or ""
        parts = output_file.split("/")
        if len(parts) >= 3:
            filename = parts[-1]
            prefix = f"{parts[-2]}-"
            suffix = f"-{result['insight_id']}-"
            if filename.startswith(prefix) and suffix in filename:
                return filename.removeprefix(prefix).split(suffix, 1)[0]
    return "workflow"


if __name__ == "__main__":
    raise SystemExit(main())
