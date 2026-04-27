"""Daily workflow support for the formal CLI shell."""

from __future__ import annotations

import json
import random
from datetime import datetime
from typing import List, Optional

from cognition_engine.paths import PROJECT_ROOT
from cognition_engine.runner import run_python_code, run_python_module


def pick_random_insight_id() -> Optional[str]:
    insight_ids: List[str] = []
    for insight_file in (PROJECT_ROOT / "data" / "insights").rglob("*.json"):
        try:
            payload = json.loads(insight_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        insight_id = payload.get("id")
        if isinstance(insight_id, str) and insight_id.strip():
            insight_ids.append(insight_id)
    return random.choice(insight_ids) if insight_ids else None


def run_daily_workflow() -> int:
    print("=" * 60)
    print(f"认知引擎每日工作流 - {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 60)

    success = True

    print("\n数据检查")
    success = (
        run_python_module(
            "engine.analyzer.validate_data",
            [],
            "验证数据完整性",
        )
        == 0
        and success
    )

    print("\n产出生成")
    selected_insight = pick_random_insight_id()
    if selected_insight:
        success = (
            run_python_module(
                "engine.transformer.generate_outputs",
                ["--insight", selected_insight, "--type", "both"],
                f"从 {selected_insight} 生成产出",
            )
            == 0
            and success
        )
    else:
        print("⚠ 未找到可用洞察，跳过产出生成。")
        success = False

    print("\n状态更新")
    success = (
        run_python_module(
            "dashboard.metrics.show_metrics",
            ["--save-report"],
            "更新仪表盘",
        )
        == 0
        and success
    )

    print("\n快速状态检查")
    success = (
        run_python_code(
            (
                "import json, subprocess, sys; "
                "cmd=[sys.executable,'-m','dashboard.metrics.show_metrics','--json']; "
                "result=subprocess.run(cmd,capture_output=True,text=True,check=False); "
                "data=json.loads(result.stdout); "
                "print('健康度: ' + str(round(data['health_score'], 1)) + '%'); "
                "print('今日产出: 建议手动复核生成结果'); "
                "sys.exit(result.returncode)"
            ),
            "读取 JSON 指标摘要",
        )
        == 0
        and success
    )

    print("\n" + "=" * 60)
    print("每日工作流完成!" if success else "每日工作流完成，但存在失败步骤。")
    print("=" * 60)
    return 0 if success else 1
