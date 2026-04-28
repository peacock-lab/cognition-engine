"""Independent model-enhancement artifact loop."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from cognition_engine.rendering import generate_outputs

from cognition_engine.modeling import (
    DEFAULT_PROVIDER,
    STATUS_ERROR,
    ModelRequest,
    ModelResponse,
    ModelRuntime,
)

COMMAND_NAME = "python -m cognition_engine.model_enhancement"
COMMAND_USAGE = f"{COMMAND_NAME} --insight <insight_id>"
CONTRACT_VERSION = "ce-model-enhancement-result/v1"
OUTPUT_TYPE = "model-enhancement"
OUTPUT_SLUG = "model-enhancements"
USER_ERROR_EXIT_CODE = 2
DEFAULT_TIMEOUT_SECONDS = 30.0


class ModelEnhancementError(ValueError):
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


def _display_path(path: Path) -> str:
    project_root = Path(generate_outputs.NEW_PROJECT_PATH)
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def list_available_insight_ids() -> list[str]:
    insights_root = Path(generate_outputs.NEW_PROJECT_PATH) / "data" / "insights"
    if not insights_root.exists():
        return []

    insight_ids = {path.stem for path in insights_root.glob("*/*.json")}
    return sorted(insight_ids)


def validate_model_enhancement_request(
    insight_id: Optional[str],
    *,
    extra_args: Optional[Sequence[str]] = None,
) -> str:
    extra_args = list(extra_args or [])
    normalized_insight_id = (insight_id or "").strip()

    if not normalized_insight_id:
        raise ModelEnhancementError(
            "missing_insight",
            "必须通过 --insight 提供单个 insight_id。",
            insight_id=None,
            extra={"available_insight_ids": list_available_insight_ids()},
        )

    if extra_args:
        raise ModelEnhancementError(
            "unexpected_args",
            "model-enhancement 入口只接受单个 --insight 参数，不接受额外位置参数或未识别参数。",
            insight_id=normalized_insight_id,
            extra={"unexpected_args": extra_args},
        )

    if any(char.isspace() for char in normalized_insight_id) or "," in normalized_insight_id:
        raise ModelEnhancementError(
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
            "error_code": error_code,
            "error_message": error_message,
            "validation": {
                "output_file_exists": False,
                "metadata_file_exists": False,
            },
        }
    )
    if extra:
        result.update(extra)
    return result


def build_model_enhancement_result(
    insight_id: str,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    runtime: Optional[ModelRuntime] = None,
) -> Dict[str, Any]:
    normalized_insight_id = validate_model_enhancement_request(insight_id)

    insight = generate_outputs.load_insight(normalized_insight_id)
    if not insight:
        raise ModelEnhancementError(
            "insight_not_found",
            f"未找到洞察: {normalized_insight_id}",
            insight_id=normalized_insight_id,
            extra={"available_insight_ids": list_available_insight_ids()},
        )

    framework = generate_outputs.load_framework(insight["framework_id"])
    if not framework:
        raise ModelEnhancementError(
            "framework_not_found",
            f"未找到框架: {insight['framework_id']}",
            insight_id=normalized_insight_id,
        )

    selected_provider = provider or os.environ.get("CE_MODEL_PROVIDER", DEFAULT_PROVIDER)
    request = _build_model_request(
        insight,
        framework,
        provider=selected_provider,
        model=model or os.environ.get("CE_MODEL_NAME") or "mock",
    )
    model_runtime = runtime or ModelRuntime()
    model_response = _run_model(model_runtime, request)
    content = build_model_enhancement_markdown(insight, framework, model_response)
    saved = generate_outputs.save_output_record(
        content,
        OUTPUT_SLUG,
        normalized_insight_id,
        insight["framework_id"],
        metadata_type=OUTPUT_TYPE,
    )

    output_file = saved["output_file"]
    metadata_file = saved["metadata_file"]
    metadata = saved["metadata"]

    result = _build_result_base(normalized_insight_id)
    result.update(
        {
            "status": "success",
            "insight_title": insight["title"],
            "framework_id": insight["framework_id"],
            "framework_name": framework["name"],
            "output_directory": f"outputs/{OUTPUT_SLUG}",
            "output_file": _display_path(output_file),
            "metadata_file": _display_path(metadata_file),
            "metadata_id": metadata["id"],
            "provider": model_response.provider,
            "model": model_response.model,
            "model_status": model_response.status,
            "fallback_used": model_response.fallback_used,
            "error_code": model_response.error_code,
            "error_message": model_response.error_message,
            "generated_at": metadata["generated_at"],
            "validation": {
                "output_file_exists": output_file.exists(),
                "metadata_file_exists": metadata_file.exists(),
            },
        }
    )
    return result


def build_model_enhancement_markdown(
    insight: Dict[str, Any],
    framework: Dict[str, Any],
    model_response: ModelResponse,
) -> str:
    model_output = model_response.output_text.strip()
    if not model_output:
        model_output = "模型未返回可用增强内容；请查看下方调用状态与错误信息。"

    return f"""# 模型增强: {insight["title"]}

## 基线洞察
- 洞察 ID: `{insight["id"]}`
- 框架: {framework["name"]} (`{insight["framework_id"]}`)
- 摘要: {insight.get("description", "当前洞察未提供摘要。")}

## 模型增强内容
{model_output}

## 模型调用记录
- provider: `{model_response.provider}`
- model: `{model_response.model}`
- status: `{model_response.status}`
- fallback_used: `{str(model_response.fallback_used).lower()}`
- error_code: `{model_response.error_code or ""}`
- error_message: {model_response.error_message or ""}
"""


def print_model_enhancement_result(
    result: Dict[str, Any],
    *,
    json_only: bool = False,
) -> None:
    if json_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("=" * 60)
    print("独立模型增强产物最小闭环")
    print("=" * 60)
    print(f"洞察 ID: {result['insight_id']}")
    print(f"洞察标题: {result['insight_title']}")
    print(f"框架: {result['framework_name']} ({result['framework_id']})")
    print(f"输出类型: {result['output_type']}")
    print(f"产出文件: {result['output_file']}")
    print(f"元数据文件: {result['metadata_file']}")
    print(f"provider: {result['provider']}")
    print(f"model: {result['model']}")
    print(f"model_status: {result['model_status']}")
    print(f"fallback_used: {result['fallback_used']}")
    print("=" * 60)


def print_model_enhancement_error(
    result: Dict[str, Any],
    *,
    json_only: bool = False,
) -> None:
    if json_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"错误[{result['error_code']}]: {result['error_message']}")
    print(f"用法: {result['usage']}")
    if result.get("available_insight_ids"):
        print("可用 insight_id:")
        for insight_id in result["available_insight_ids"]:
            print(f"  - {insight_id}")


def run_model_enhancement_loop(
    insight_id: Optional[str],
    *,
    json_only: bool = False,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    extra_args: Optional[Sequence[str]] = None,
) -> int:
    try:
        validated_insight_id = validate_model_enhancement_request(
            insight_id,
            extra_args=extra_args,
        )
        result = build_model_enhancement_result(
            validated_insight_id,
            provider=provider,
            model=model,
        )
    except ModelEnhancementError as exc:
        error_result = build_error_result(
            exc.error_code,
            exc.error_message,
            insight_id=exc.insight_id,
            extra=exc.extra,
        )
        print_model_enhancement_error(error_result, json_only=json_only)
        return exc.exit_code
    except Exception as exc:  # pragma: no cover - defensive catch for unexpected errors
        error_result = build_error_result(
            "internal_error",
            f"生成 model-enhancement 时发生未预期错误: {exc}",
            insight_id=(insight_id or "").strip() or None,
        )
        print_model_enhancement_error(error_result, json_only=json_only)
        return 1

    print_model_enhancement_result(result, json_only=json_only)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成独立模型增强产物")
    parser.add_argument("--insight", required=True, help="单个 insight_id")
    parser.add_argument("--provider", default=None, help="模型 provider，默认 mock")
    parser.add_argument("--model", default=None, help="模型名称")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args, extra_args = parser.parse_known_args(argv)
    return run_model_enhancement_loop(
        args.insight,
        json_only=args.json,
        provider=args.provider,
        model=args.model,
        extra_args=extra_args,
    )


def _build_result_base(insight_id: Optional[str]) -> Dict[str, Any]:
    return {
        "command": COMMAND_NAME if insight_id is None else f"{COMMAND_NAME} --insight {insight_id}",
        "command_name": COMMAND_NAME,
        "usage": COMMAND_USAGE,
        "contract_version": CONTRACT_VERSION,
        "output_type": OUTPUT_TYPE,
        "insight_id": insight_id,
    }


def _build_model_request(
    insight: Dict[str, Any],
    framework: Dict[str, Any],
    *,
    provider: str,
    model: str,
) -> ModelRequest:
    instruction = (
        "请基于给定洞察生成一个简短的模型增强判断，重点补充机会、风险和下一步建议。"
        "保持输出为普通 Markdown 段落，不要声明已经修改任何正式产品产物。"
    )
    input_text = (
        f"洞察标题: {insight['title']}\n"
        f"框架: {framework['name']}\n"
        f"基线摘要: {insight.get('description', '')}\n"
        f"置信度: {insight.get('confidence', 'unknown')}\n"
        f"标签: {', '.join(insight.get('tags', []))}"
    )
    return ModelRequest(
        purpose=OUTPUT_TYPE,
        input_text=input_text,
        instruction=instruction,
        model=model,
        provider=provider,
        temperature=0.0,
        timeout_seconds=_resolve_timeout_seconds(),
        metadata={
            "insight_id": insight["id"],
            "framework_id": insight["framework_id"],
            "output_type": OUTPUT_TYPE,
        },
    )


def _run_model(runtime: ModelRuntime, request: ModelRequest) -> ModelResponse:
    try:
        return runtime.run(request)
    except Exception as exc:  # noqa: BLE001
        return ModelResponse(
            status=STATUS_ERROR,
            output_text="",
            model=request.model,
            provider=request.provider,
            latency_ms=0.0,
            raw_summary={"purpose": request.purpose},
            error_code=type(exc).__name__,
            error_message=str(exc),
            fallback_used=False,
        )


def _resolve_timeout_seconds() -> float:
    raw_timeout = os.environ.get("CE_MODEL_TIMEOUT_SECONDS", "").strip()
    if not raw_timeout:
        return DEFAULT_TIMEOUT_SECONDS

    try:
        timeout_seconds = float(raw_timeout)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS

    if timeout_seconds <= 0:
        return DEFAULT_TIMEOUT_SECONDS
    return timeout_seconds


if __name__ == "__main__":
    raise SystemExit(main())
