"""Shared init/bootstrap flow for the formal CLI shell."""

from __future__ import annotations

import json
from typing import Optional

from cognition_engine.paths import PROJECT_ROOT
from cognition_engine.runner import current_python_command, run_python_module


def print_section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def find_first_insight_id() -> Optional[str]:
    insights_dir = PROJECT_ROOT / "data" / "insights"
    if not insights_dir.exists():
        return None

    for insight_file in insights_dir.rglob("*.json"):
        try:
            payload = json.loads(insight_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        insight_id = payload.get("id")
        if isinstance(insight_id, str) and insight_id.strip():
            return insight_id
    return None


def setup_initial_data() -> bool:
    print_section("设置初始数据")
    statuses = [
        run_python_module(
            "engine.analyzer.extract_adk_insights",
            [],
            "迁移 ADK 数据",
        ),
        run_python_module(
            "engine.analyzer.validate_data",
            [],
            "验证数据完整性",
        ),
    ]
    return all(code == 0 for code in statuses)


def generate_initial_outputs() -> bool:
    print_section("生成初始产出")
    insight_id = find_first_insight_id()
    if not insight_id:
        print("⚠ 未找到可用洞察，请先执行数据迁移。")
        return False

    statuses = [
        run_python_module(
            "engine.transformer.generate_outputs",
            ["--insight", insight_id, "--type", "article"],
            f"从洞察 {insight_id} 生成文章",
        ),
        run_python_module(
            "engine.transformer.generate_outputs",
            ["--insight", insight_id, "--type", "product-brief"],
            f"从洞察 {insight_id} 生成产品简报",
        ),
    ]
    return all(code == 0 for code in statuses)


def show_dashboard() -> bool:
    print_section("项目仪表盘")
    status = run_python_module(
        "dashboard.metrics.show_metrics",
        [],
        "显示项目状态",
    )
    return status == 0


def show_next_steps() -> None:
    print_section("下一步建议")
    print("1. 运行数据迁移：")
    print("   ce init --setup")
    print("2. 验证当前状态：")
    print("   ce status --json")
    print("3. 触发首个真实产品化最小闭环：")
    print("   ce brief --insight insight-adk-runner-centrality")
    print("4. 如需使用底层通用生成器，再调用：")
    print(
        "   "
        f"{current_python_command()} -m engine.transformer.generate_outputs "
        "--insight insight-adk-runner-centrality --type both"
    )


def run_init_flow(
    *,
    setup: bool,
    generate: bool,
    status: bool,
    all_steps: bool,
    show_followup: bool = True,
) -> int:
    selected = setup or generate or status or all_steps
    if not selected:
        all_steps = True

    print("认知引擎初始化入口")
    print("=" * 60)

    success = True
    if setup or all_steps:
        success = setup_initial_data() and success
    if generate or all_steps:
        success = generate_initial_outputs() and success
    if status or all_steps:
        success = show_dashboard() and success

    if (all_steps or setup or generate or status) and show_followup:
        show_next_steps()

    if success:
        print("\n🎉 初始化完成!")
        return 0

    print("\n⚠ 初始化过程中出现错误，请检查上方输出。")
    return 1
