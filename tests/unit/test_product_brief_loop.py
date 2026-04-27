#!/usr/bin/env python3
"""Formal CLI product brief minimal loop tests."""

import json
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cognition_engine import product_brief  # noqa: E402
from engine.transformer import generate_outputs  # noqa: E402


def install_sample_data(tmp_path: Path) -> None:
    (tmp_path / "data" / "insights" / "adk-2.0.0a3").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "frameworks" / "adk-2.0.0a3").mkdir(parents=True, exist_ok=True)

    insight = {
        "id": "insight-adk-runner-centrality",
        "framework_id": "adk-2.0.0a3",
        "title": "Runner 是请求总控与主要收口器",
        "description": "最小闭环测试样本。",
        "confidence": 0.97,
        "impact": {
            "architectural": "high",
            "migration": "high",
            "product": "medium",
        },
        "evidence": [],
        "connections": [],
        "tags": ["runner"],
        "category": "core_coordination",
    }
    framework = {
        "id": "adk-2.0.0a3",
        "name": "Google Agent Development Kit",
        "version": "2.0.0a3",
        "metadata": {
            "analysis_depth": "deep_audit_completed",
        },
        "source_documents": [],
        "input_channels": [],
        "timestamps": {
            "first_analyzed": "2026-04-15T00:00:00",
            "last_updated": "2026-04-24T00:00:00",
        },
    }

    (tmp_path / "data" / "insights" / "adk-2.0.0a3" / "insight-adk-runner-centrality.json").write_text(
        json.dumps(insight, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (tmp_path / "data" / "frameworks" / "adk-2.0.0a3" / "metadata.json").write_text(
        json.dumps(framework, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def install_real_repo_data(tmp_path: Path, *insight_ids: str) -> None:
    insights_dir = tmp_path / "data" / "insights" / "adk-2.0.0a3"
    frameworks_dir = tmp_path / "data" / "frameworks" / "adk-2.0.0a3"
    insights_dir.mkdir(parents=True, exist_ok=True)
    frameworks_dir.mkdir(parents=True, exist_ok=True)

    source_framework = project_root / "data" / "frameworks" / "adk-2.0.0a3" / "metadata.json"
    frameworks_dir.joinpath("metadata.json").write_text(
        source_framework.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    for insight_id in insight_ids:
        source_insight = project_root / "data" / "insights" / "adk-2.0.0a3" / f"{insight_id}.json"
        insights_dir.joinpath(f"{insight_id}.json").write_text(
            source_insight.read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def test_build_product_brief_result_creates_output_and_metadata(tmp_path: Path) -> None:
    original_project_path = generate_outputs.NEW_PROJECT_PATH
    original_load_insight = generate_outputs.load_insight
    original_load_framework = generate_outputs.load_framework
    generate_outputs.NEW_PROJECT_PATH = tmp_path
    install_sample_data(tmp_path)

    try:
        generate_outputs.load_insight = lambda insight_id: {
            "id": insight_id,
            "framework_id": "adk-2.0.0a3",
            "title": "Runner 是请求总控与主要收口器",
            "description": "最小闭环测试样本。",
            "confidence": 0.97,
            "impact": {
                "architectural": "high",
                "migration": "high",
                "product": "medium",
            },
            "evidence": [],
            "connections": [],
            "tags": ["runner"],
            "category": "core_coordination",
        }
        generate_outputs.load_framework = lambda framework_id: {
            "id": framework_id,
            "name": "Google Agent Development Kit",
            "version": "2.0.0a3",
            "metadata": {"analysis_depth": "deep_audit_completed"},
        }
        result = product_brief.build_product_brief_result("insight-adk-runner-centrality")
    finally:
        generate_outputs.NEW_PROJECT_PATH = original_project_path
        generate_outputs.load_insight = original_load_insight
        generate_outputs.load_framework = original_load_framework

    metadata_path = tmp_path / result["metadata_file"]
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert result["status"] == "success"
    assert result["contract_version"] == "ce-brief-result/v1"
    assert result["output_type"] == "product-brief"
    assert result["insight_id"] == "insight-adk-runner-centrality"
    assert "产品化能力表达" in result["brief_summary"]
    assert "运行总控层" in result["primary_use_case"]
    assert "Runner 主链职责" in result["recommended_action"]
    assert result["validation"]["output_file_exists"] is True
    assert result["validation"]["metadata_file_exists"] is True
    assert (tmp_path / result["output_file"]).exists()
    assert metadata_path.exists()
    assert metadata["type"] == "product-brief"


def test_run_product_brief_loop_returns_json_error_when_insight_missing(
    capsys,
    tmp_path: Path,
) -> None:
    original_project_path = generate_outputs.NEW_PROJECT_PATH
    generate_outputs.NEW_PROJECT_PATH = tmp_path
    install_sample_data(tmp_path)

    try:
        exit_code = product_brief.run_product_brief_loop(None, json_only=True)
    finally:
        generate_outputs.NEW_PROJECT_PATH = original_project_path

    result = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert result["status"] == "error"
    assert result["error_code"] == "missing_insight"
    assert result["usage"] == "ce brief --insight <insight_id>"
    assert "insight-adk-runner-centrality" in result["available_insight_ids"]


def test_run_product_brief_loop_returns_json_error_when_insight_not_found(
    capsys,
    tmp_path: Path,
) -> None:
    original_project_path = generate_outputs.NEW_PROJECT_PATH
    generate_outputs.NEW_PROJECT_PATH = tmp_path
    install_sample_data(tmp_path)

    try:
        exit_code = product_brief.run_product_brief_loop(
            "insight-does-not-exist",
            json_only=True,
        )
    finally:
        generate_outputs.NEW_PROJECT_PATH = original_project_path

    result = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert result["status"] == "error"
    assert result["error_code"] == "insight_not_found"
    assert result["insight_id"] == "insight-does-not-exist"
    assert "insight-adk-runner-centrality" in result["available_insight_ids"]


def test_run_product_brief_loop_rejects_unexpected_args(
    capsys,
    tmp_path: Path,
) -> None:
    original_project_path = generate_outputs.NEW_PROJECT_PATH
    generate_outputs.NEW_PROJECT_PATH = tmp_path
    install_sample_data(tmp_path)

    try:
        exit_code = product_brief.run_product_brief_loop(
            "insight-adk-runner-centrality",
            json_only=True,
            extra_args=["extra-insight"],
        )
    finally:
        generate_outputs.NEW_PROJECT_PATH = original_project_path

    result = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert result["status"] == "error"
    assert result["error_code"] == "unexpected_args"
    assert result["unexpected_args"] == ["extra-insight"]


def test_build_product_brief_result_supports_real_event_system_sample(tmp_path: Path) -> None:
    original_project_path = generate_outputs.NEW_PROJECT_PATH
    generate_outputs.NEW_PROJECT_PATH = tmp_path
    install_real_repo_data(tmp_path, "insight-adk-event-system")

    try:
        result = product_brief.build_product_brief_result("insight-adk-event-system")
    finally:
        generate_outputs.NEW_PROJECT_PATH = original_project_path

    output_path = tmp_path / result["output_file"]
    output_text = output_path.read_text(encoding="utf-8")

    assert result["status"] == "success"
    assert result["insight_id"] == "insight-adk-event-system"
    assert "标准化的事件收口链。" in result["brief_summary"]
    assert "统一可解释的事件收口链" in result["primary_use_case"]
    assert "最小字段集合" in result["recommended_action"]
    assert "## 证据与可信度" in output_text
    assert "调用链" in output_text
    assert "当前未声明直接相关洞察。" in output_text

FIXTURE_ROOT = project_root / "tests" / "fixtures" / "product-briefs"

REQUIRED_PRODUCT_BRIEF_HEADINGS = [
    "# 产品简报:",
    "## 一页结论",
    "## 适用场景",
    "## 目标使用者",
    "## 用户问题",
    "## 产品主张",
    "## 上线边界",
    "## 证据与可信度",
    "## 相关洞察",
    "## 下一步行动",
]

FORBIDDEN_LEGACY_TEMPLATE_TERMS = [
    "MVP",
    "收入影响",
    "NPS",
    "市场规模",
    "资源需求",
    "立即行动",
]


def load_product_brief_fixture(name: str) -> str:
    return (FIXTURE_ROOT / name).read_text(encoding="utf-8")


def assert_product_brief_heading_order(markdown_text: str) -> None:
    positions = [markdown_text.index(heading) for heading in REQUIRED_PRODUCT_BRIEF_HEADINGS]
    assert positions == sorted(positions)


def extract_section(markdown_text: str, heading: str) -> str:
    start = markdown_text.index(heading) + len(heading)
    next_heading = markdown_text.find("\n## ", start)
    if next_heading == -1:
        return markdown_text[start:].strip()
    return markdown_text[start:next_heading].strip()


def assert_product_brief_quality_contract(markdown_text: str) -> None:
    one_page_summary = extract_section(markdown_text, "## 一页结论")
    assert "**推荐落点**" in one_page_summary
    assert "**主要适用场景**" in one_page_summary
    assert "**影响判断**" in one_page_summary

    launch_boundary = extract_section(markdown_text, "## 上线边界")
    assert launch_boundary

    evidence = extract_section(markdown_text, "## 证据与可信度")
    assert "**框架**" in evidence
    assert "**洞察来源**" in evidence
    assert "**置信度**" in evidence
    assert "**证据摘要**" in evidence

    next_actions = extract_section(markdown_text, "## 下一步行动")
    numbered_actions = [
        line for line in next_actions.splitlines()
        if line.startswith(("1. ", "2. ", "3. "))
    ]
    assert len(numbered_actions) >= 3


def assert_product_brief_markdown_contract(markdown_text: str) -> None:
    for heading in REQUIRED_PRODUCT_BRIEF_HEADINGS:
        assert heading in markdown_text

    assert_product_brief_heading_order(markdown_text)
    assert_product_brief_quality_contract(markdown_text)

    for forbidden_term in FORBIDDEN_LEGACY_TEMPLATE_TERMS:
        assert forbidden_term not in markdown_text

    assert "*生成时间:" in markdown_text
    assert "*洞察来源:" in markdown_text
    assert "*置信度:" in markdown_text


def test_product_brief_markdown_fixtures_follow_current_structure_contract() -> None:
    fixture_names = [
        "runner-centrality.md",
        "event-system.md",
    ]

    for fixture_name in fixture_names:
        markdown_text = load_product_brief_fixture(fixture_name)
        assert_product_brief_markdown_contract(markdown_text)


def test_product_brief_fixture_directory_documents_boundary() -> None:
    readme_text = load_product_brief_fixture("README.md")

    assert "Markdown 回归测试基线目录" in readme_text
    assert "examples/product-briefs/" in readme_text
    assert "outputs/product-briefs/" in readme_text
    assert "outputs/.metadata/" in readme_text
    assert "metadata fixture" in readme_text

