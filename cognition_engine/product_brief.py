"""Formal minimal productized loop: generate one product brief from one insight."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from cognition_engine.rendering import generate_outputs

COMMAND_NAME = "ce brief"
COMMAND_USAGE = "ce brief --insight <insight_id>"
CONTRACT_VERSION = "ce-brief-result/v1"
CLOSURE_ID = "formal_cli_product_brief_minimal_loop"
OUTPUT_TYPE = "product-brief"
OUTPUT_SLUG = "product-briefs"
USER_ERROR_EXIT_CODE = 2


class ProductBriefCliError(ValueError):
    """Structured user-facing error for the ce brief loop."""

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


def _build_result_base(insight_id: Optional[str]) -> Dict[str, Any]:
    return {
        "command": COMMAND_NAME if insight_id is None else f"{COMMAND_NAME} --insight {insight_id}",
        "command_name": COMMAND_NAME,
        "usage": COMMAND_USAGE,
        "contract_version": CONTRACT_VERSION,
        "closure_id": CLOSURE_ID,
        "output_type": OUTPUT_TYPE,
        "insight_id": insight_id,
    }


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
        }
    )
    if extra:
        result.update(extra)
    return result


def validate_brief_request(
    insight_id: Optional[str],
    *,
    extra_args: Optional[Sequence[str]] = None,
) -> str:
    extra_args = list(extra_args or [])
    normalized_insight_id = (insight_id or "").strip()

    if not normalized_insight_id:
        raise ProductBriefCliError(
            "missing_insight",
            "必须通过 --insight 提供单个 insight_id。",
            insight_id=None,
            extra={"available_insight_ids": list_available_insight_ids()},
        )

    if extra_args:
        raise ProductBriefCliError(
            "unexpected_args",
            "ce brief 只接受单个 --insight 参数，不接受额外位置参数或未识别参数。",
            insight_id=normalized_insight_id,
            extra={"unexpected_args": extra_args},
        )

    if any(char.isspace() for char in normalized_insight_id) or "," in normalized_insight_id:
        raise ProductBriefCliError(
            "invalid_insight_id",
            "insight_id 必须是单个 ID，不能包含空白字符或逗号分隔列表。",
            insight_id=normalized_insight_id,
        )

    return normalized_insight_id


def build_product_brief_result(insight_id: str) -> Dict[str, Any]:
    """Generate one product brief and return a machine-readable result record."""
    normalized_insight_id = validate_brief_request(insight_id)

    insight = generate_outputs.load_insight(normalized_insight_id)
    if not insight:
        raise ProductBriefCliError(
            "insight_not_found",
            f"未找到洞察: {normalized_insight_id}",
            insight_id=normalized_insight_id,
            extra={"available_insight_ids": list_available_insight_ids()},
        )

    framework = generate_outputs.load_framework(insight["framework_id"])
    if not framework:
        raise ProductBriefCliError(
            "framework_not_found",
            f"未找到框架: {insight['framework_id']}",
            insight_id=normalized_insight_id,
        )

    brief_context = generate_outputs.build_product_brief_context(insight, framework)
    content = generate_outputs.generate_product_brief(insight, framework)
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
            "output_title": metadata["title"],
            "brief_summary": brief_context["executive_summary"],
            "primary_use_case": brief_context["primary_use_case"],
            "recommended_action": brief_context["recommended_action"],
            "generated_at": metadata["generated_at"],
            "validation": {
                "output_file_exists": output_file.exists(),
                "metadata_file_exists": metadata_file.exists(),
            },
        }
    )
    return result


def print_product_brief_result(result: Dict[str, Any], *, json_only: bool = False) -> None:
    if json_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("=" * 60)
    print("正式 CLI 最小产品化闭环：产品简报生成")
    print("=" * 60)
    print(f"洞察 ID: {result['insight_id']}")
    print(f"洞察标题: {result['insight_title']}")
    print(f"框架: {result['framework_name']} ({result['framework_id']})")
    print(f"输出类型: {result['output_type']}")
    print(f"输出目录: {result['output_directory']}")
    print(f"产出文件: {result['output_file']}")
    print(f"元数据文件: {result['metadata_file']}")
    print(f"元数据 ID: {result['metadata_id']}")
    print(f"简报摘要: {result['brief_summary']}")
    print(f"主要适用场景: {result['primary_use_case']}")
    print(f"建议下一步: {result['recommended_action']}")
    print("验证结果:")
    print(f"  - output_file_exists = {result['validation']['output_file_exists']}")
    print(f"  - metadata_file_exists = {result['validation']['metadata_file_exists']}")
    print("=" * 60)


def print_product_brief_error(result: Dict[str, Any], *, json_only: bool = False) -> None:
    if json_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"错误[{result['error_code']}]: {result['error_message']}")
    print(f"用法: {result['usage']}")
    if result.get("available_insight_ids"):
        print("可用 insight_id:")
        for insight_id in result["available_insight_ids"]:
            print(f"  - {insight_id}")
    if result.get("unexpected_args"):
        print("未识别参数:")
        for arg in result["unexpected_args"]:
            print(f"  - {arg}")


def run_product_brief_loop(
    insight_id: Optional[str],
    *,
    json_only: bool = False,
    extra_args: Optional[Sequence[str]] = None,
) -> int:
    try:
        validated_insight_id = validate_brief_request(insight_id, extra_args=extra_args)
        result = build_product_brief_result(validated_insight_id)
    except ProductBriefCliError as exc:
        error_result = build_error_result(
            exc.error_code,
            exc.error_message,
            insight_id=exc.insight_id,
            extra=exc.extra,
        )
        print_product_brief_error(error_result, json_only=json_only)
        return exc.exit_code
    except Exception as exc:  # pragma: no cover - defensive catch for unexpected runtime errors
        error_result = build_error_result(
            "internal_error",
            f"生成 product-brief 时发生未预期错误: {exc}",
            insight_id=(insight_id or "").strip() or None,
        )
        print_product_brief_error(error_result, json_only=json_only)
        return 1

    print_product_brief_result(result, json_only=json_only)
    return 0
