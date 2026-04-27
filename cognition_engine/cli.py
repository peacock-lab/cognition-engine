"""Formal CLI entrypoint for Cognition Engine."""

from __future__ import annotations

import argparse
from typing import List, Optional, Sequence

from cognition_engine.bootstrap import run_init_flow
from cognition_engine.daily_flow import run_daily_workflow
from cognition_engine.decision_pack import run_decision_pack_loop
from cognition_engine.product_brief import run_product_brief_loop
from cognition_engine.runner import run_python_module
from cognition_engine.workflow import run_workflow_loop


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ce",
        description="认知引擎正式 CLI 主入口。",
    )
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="初始化与引导入口。")
    init_parser.add_argument("--setup", action="store_true", help="执行初始数据迁移与校验。")
    init_parser.add_argument("--generate", action="store_true", help="生成初始产出。")
    init_parser.add_argument("--status", action="store_true", help="显示项目状态。")
    init_parser.add_argument("--all", action="store_true", help="执行完整初始化。")

    subparsers.add_parser("daily", help="运行日常 workflow。")
    subparsers.add_parser("status", help="查看项目状态。")
    subparsers.add_parser("check", help="检查当前环境。")
    brief_parser = subparsers.add_parser("brief", help="生成首个正式产品化闭环的产品简报。")
    brief_parser.add_argument("--insight", help="洞察 ID。当前只接受单个 insight_id。")
    brief_parser.add_argument("--json", action="store_true", help="输出 JSON 结果。")
    decision_pack_parser = subparsers.add_parser("decision-pack", help="生成第二个正式产品化闭环的决策包。")
    decision_pack_parser.add_argument("--insight", help="洞察 ID。当前只接受单个 insight_id。")
    decision_pack_parser.add_argument("--json", action="store_true", help="输出 JSON 结果。")
    workflow_parser = subparsers.add_parser("workflow", help="执行 insight-to-decision workflow。")
    workflow_parser.add_argument("--insight", help="洞察 ID。当前只接受单个 insight_id。")
    workflow_parser.add_argument("--json", action="store_true", help="输出 JSON 结果。")
    subparsers.add_parser("generate", help="生成产出。")
    subparsers.add_parser("migrate", help="执行迁移/提取类任务。")

    return parser


def dispatch(namespace: argparse.Namespace, extra_args: Sequence[str]) -> int:
    if namespace.command == "init":
        return run_init_flow(
            setup=namespace.setup,
            generate=namespace.generate,
            status=namespace.status,
            all_steps=namespace.all,
        )
    if namespace.command == "daily":
        return run_daily_workflow()
    if namespace.command == "status":
        return run_python_module(
            "dashboard.metrics.show_metrics",
            list(extra_args),
            "查看项目状态",
        )
    if namespace.command == "check":
        return run_python_module(
            "tools.check_environment",
            list(extra_args),
            "检查环境",
        )
    if namespace.command == "brief":
        return run_product_brief_loop(
            namespace.insight,
            json_only=namespace.json,
            extra_args=extra_args,
        )
    if namespace.command == "decision-pack":
        return run_decision_pack_loop(
            namespace.insight,
            json_only=namespace.json,
            extra_args=extra_args,
        )
    if namespace.command == "workflow":
        return run_workflow_loop(
            namespace.insight,
            json_only=namespace.json,
            extra_args=extra_args,
        )
    if namespace.command == "generate":
        return run_python_module(
            "engine.transformer.generate_outputs",
            list(extra_args),
            "生成产出",
        )
    if namespace.command == "migrate":
        return run_python_module(
            "engine.analyzer.extract_architecture_patterns",
            list(extra_args),
            "迁移内容",
        )
    return 0


def main(args: Optional[List[str]] = None) -> None:
    parser = build_parser()
    namespace, extra_args = parser.parse_known_args(args=args)
    if namespace.command is None:
        parser.print_help()
        raise SystemExit(0)
    raise SystemExit(dispatch(namespace, extra_args))


if __name__ == "__main__":
    main()
