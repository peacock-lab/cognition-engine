"""Legacy wrappers that forward old root scripts to the formal CLI shell."""

from __future__ import annotations

import argparse

from cognition_engine.bootstrap import run_init_flow
from cognition_engine.daily_flow import run_daily_workflow


def legacy_start_main() -> int:
    parser = argparse.ArgumentParser(
        description="认知引擎旧启动脚本兼容入口（推荐改用 `ce init`）。"
    )
    parser.add_argument("--setup", action="store_true", help="初始设置（数据迁移+验证）")
    parser.add_argument("--generate", action="store_true", help="生成初始产出")
    parser.add_argument("--dashboard", action="store_true", help="显示仪表盘")
    parser.add_argument("--daily", action="store_true", help="运行每日工作流")
    parser.add_argument("--all", action="store_true", help="执行完整初始化")
    args = parser.parse_args()

    if args.daily and not any([args.setup, args.generate, args.dashboard, args.all]):
        return run_daily_workflow()

    return run_init_flow(
        setup=args.setup,
        generate=args.generate,
        status=args.dashboard,
        all_steps=args.all,
    )


def legacy_daily_main() -> int:
    return run_daily_workflow()

