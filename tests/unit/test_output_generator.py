#!/usr/bin/env python3
"""Output 生成器测试。"""

import json
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cognition_engine.rendering import generate_outputs  # noqa: E402

REAL_INSIGHT_IDS = [
    "insight-adk-runner-centrality",
    "insight-adk-event-system",
]


def sample_framework() -> dict:
    return {
        "id": "adk-2.0.0a3",
        "name": "Google Agent Development Kit",
        "version": "2.0.0a3",
        "metadata": {
            "analysis_depth": "deep_audit_completed",
        },
    }


def sample_insight() -> dict:
    return {
        "id": "insight-adk-state-context-boundary",
        "framework_id": "adk-2.0.0a3",
        "title": "状态在 Session、InvocationContext、Context 间分层寄宿",
        "description": "状态边界通过多层上下文协同承载。",
        "confidence": 0.95,
        "impact": {
            "architectural": "high",
            "migration": "high",
            "product": "high",
        },
        "evidence": [
            {
                "type": "documentation_reference",
                "source_file": "core_runtime_map",
                "source_section": "7. 上下文与状态寄宿关系",
                "quote": "Session.state 是长期状态宿主。",
            }
        ],
        "connections": [],
        "tags": ["state", "context"],
        "category": "state_management",
    }


def test_generate_article_renders_non_code_evidence() -> None:
    article = generate_outputs.generate_article_from_insight(
        sample_insight(),
        sample_framework(),
    )

    assert "证据来源: documentation_reference" in article
    assert "章节 `7. 上下文与状态寄宿关系`" in article
    assert "Session.state 是长期状态宿主。" in article


def test_generate_product_brief_renders_formal_entry_core_fields() -> None:
    brief = generate_outputs.generate_product_brief(
        sample_insight(),
        sample_framework(),
    )

    assert "# 产品简报: 状态在 Session、InvocationContext、Context 间分层寄宿" in brief
    assert "## 一页结论" in brief
    assert "## 证据与可信度" in brief
    assert "Session.state 是长期状态宿主。" in brief
    assert "把长期状态、调用控制面和节点局部视图拆清" in brief
    assert "*洞察来源: insight-adk-state-context-boundary*" in brief
    assert "*置信度: 95%*" in brief


def test_generate_product_brief_stays_stable_for_real_runner_and_event_samples() -> None:
    framework = generate_outputs.load_framework("adk-2.0.0a3")

    assert framework is not None

    for insight_id in REAL_INSIGHT_IDS:
        insight = generate_outputs.load_insight(insight_id)

        assert insight is not None

        brief = generate_outputs.generate_product_brief(insight, framework)

        assert "## 一页结论" in brief
        assert "## 适用场景" in brief
        assert "## 目标使用者" in brief
        assert "## 用户问题" in brief
        assert "## 产品主张" in brief
        assert "## 上线边界" in brief
        assert "## 证据与可信度" in brief
        assert "## 相关洞察" in brief
        assert "## 下一步行动" in brief

    runner_brief = generate_outputs.generate_product_brief(
        generate_outputs.load_insight("insight-adk-runner-centrality"),
        framework,
    )
    event_brief = generate_outputs.generate_product_brief(
        generate_outputs.load_insight("insight-adk-event-system"),
        framework,
    )

    assert "Runner 负责获取或创建 session" in runner_brief
    assert "状态在 Session、InvocationContext、Context 间分层寄宿" in runner_brief
    assert "调用链" in event_brief
    assert "event creation -> event dispatch -> actions execution -> state update" in event_brief
    assert "当前未声明直接相关洞察。" in event_brief


def test_save_output_creates_distinct_metadata_records(tmp_path: Path) -> None:
    original_project_path = generate_outputs.NEW_PROJECT_PATH
    generate_outputs.NEW_PROJECT_PATH = tmp_path
    try:
        first = generate_outputs.save_output(
            "# A\n",
            "articles",
            "insight-a",
            "framework-a",
        )
        second = generate_outputs.save_output(
            "# B\n",
            "product-briefs",
            "insight-a",
            "framework-a",
        )
    finally:
        generate_outputs.NEW_PROJECT_PATH = original_project_path

    metadata_files = sorted((tmp_path / "outputs" / ".metadata").glob("*.json"))

    assert first.exists()
    assert second.exists()
    assert len(metadata_files) == 2
    assert metadata_files[0].name != metadata_files[1].name


def test_save_output_record_allows_stable_metadata_type(tmp_path: Path) -> None:
    original_project_path = generate_outputs.NEW_PROJECT_PATH
    generate_outputs.NEW_PROJECT_PATH = tmp_path
    try:
        saved = generate_outputs.save_output_record(
            "# Product Brief\n",
            "product-briefs",
            "insight-a",
            "framework-a",
            metadata_type="product-brief",
        )
    finally:
        generate_outputs.NEW_PROJECT_PATH = original_project_path

    metadata = json.loads(saved["metadata_file"].read_text(encoding="utf-8"))

    assert metadata["type"] == "product-brief"
    assert metadata["file_path"].startswith("outputs/product-briefs/")

def test_generate_decision_pack_renders_minimal_decision_structure() -> None:
    decision_pack = generate_outputs.generate_decision_pack(
        sample_insight(),
        sample_framework(),
    )

    required_sections = [
        "# 决策包: 状态在 Session、InvocationContext、Context 间分层寄宿",
        "## 一页结论",
        "## 决策问题",
        "## 背景与证据",
        "## 可选方案",
        "## 推荐方案",
        "## 取舍理由",
        "## 风险与边界",
        "## 下一步行动",
    ]

    for section in required_sections:
        assert section in decision_pack

    assert "Session.state 是长期状态宿主。" in decision_pack
    assert "**推荐方案**" in decision_pack
    assert "建议采用轻量推进。" in decision_pack
    assert "*洞察来源: insight-adk-state-context-boundary*" in decision_pack
    assert "*置信度: 95%*" in decision_pack


def test_save_output_record_allows_decision_pack_metadata_type(tmp_path: Path) -> None:
    original_project_path = generate_outputs.NEW_PROJECT_PATH
    generate_outputs.NEW_PROJECT_PATH = tmp_path
    try:
        saved = generate_outputs.save_output_record(
            "# 决策包: Example\n",
            "decision-packs",
            "insight-a",
            "framework-a",
            metadata_type="decision-pack",
        )
    finally:
        generate_outputs.NEW_PROJECT_PATH = original_project_path

    metadata = json.loads(saved["metadata_file"].read_text(encoding="utf-8"))

    assert metadata["type"] == "decision-pack"
    assert metadata["file_path"].startswith("outputs/decision-packs/")

DECISION_PACK_FIXTURE_ROOT = project_root / "tests" / "fixtures" / "decision-packs"

REQUIRED_DECISION_PACK_HEADINGS = [
    "# 决策包:",
    "## 一页结论",
    "## 决策问题",
    "## 背景与证据",
    "## 可选方案",
    "## 推荐方案",
    "## 取舍理由",
    "## 风险与边界",
    "## 下一步行动",
]


def load_decision_pack_fixture(name: str) -> str:
    return (DECISION_PACK_FIXTURE_ROOT / name).read_text(encoding="utf-8")


def extract_decision_pack_section(markdown_text: str, heading: str) -> str:
    start = markdown_text.index(heading) + len(heading)
    next_heading = markdown_text.find("\n## ", start)
    if next_heading == -1:
        return markdown_text[start:].strip()
    return markdown_text[start:next_heading].strip()


def assert_decision_pack_heading_order(markdown_text: str) -> None:
    positions = [markdown_text.index(heading) for heading in REQUIRED_DECISION_PACK_HEADINGS]
    assert positions == sorted(positions)


def assert_decision_pack_quality_contract(markdown_text: str) -> None:
    one_page_summary = extract_decision_pack_section(markdown_text, "## 一页结论")
    assert "**待决问题**" in one_page_summary
    assert "**推荐方案**" in one_page_summary
    assert "**建议下一步**" in one_page_summary

    evidence = extract_decision_pack_section(markdown_text, "## 背景与证据")
    assert "**框架**" in evidence
    assert "**洞察来源**" in evidence
    assert "**置信度**" in evidence
    assert "**影响判断**" in evidence
    assert "**证据摘要**" in evidence

    risk_boundary = extract_decision_pack_section(markdown_text, "## 风险与边界")
    assert risk_boundary

    next_actions = extract_decision_pack_section(markdown_text, "## 下一步行动")
    numbered_actions = [
        line for line in next_actions.splitlines()
        if line.startswith(("1. ", "2. ", "3. "))
    ]
    assert len(numbered_actions) >= 3


def assert_decision_pack_markdown_contract(markdown_text: str) -> None:
    for heading in REQUIRED_DECISION_PACK_HEADINGS:
        assert heading in markdown_text

    assert_decision_pack_heading_order(markdown_text)
    assert_decision_pack_quality_contract(markdown_text)

    assert "*生成时间:" in markdown_text
    assert "*洞察来源:" in markdown_text
    assert "*置信度:" in markdown_text


def test_decision_pack_markdown_fixture_follows_current_structure_contract() -> None:
    markdown_text = load_decision_pack_fixture("runner-centrality.md")

    assert_decision_pack_markdown_contract(markdown_text)
    assert "Runner 是请求总控与主要收口器" in markdown_text
    assert "Runner 承担请求协调与主要收口" in markdown_text


def test_decision_pack_fixture_directory_documents_boundary() -> None:
    readme_text = load_decision_pack_fixture("README.md")

    assert "Markdown 回归测试基线目录" in readme_text
    assert "outputs/decision-packs/" in readme_text
    assert "outputs/.metadata/" in readme_text
    assert "metadata fixture" in readme_text
    assert "稳定展示样例" in readme_text

