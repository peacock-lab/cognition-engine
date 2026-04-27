#!/usr/bin/env python3
"""Formal CLI decision-pack minimal loop tests."""

import json
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cognition_engine import cli, decision_pack  # noqa: E402
from engine.transformer import generate_outputs  # noqa: E402


def install_sample_data(tmp_path: Path) -> None:
    (tmp_path / "data" / "insights" / "adk-2.0.0a3").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "frameworks" / "adk-2.0.0a3").mkdir(parents=True, exist_ok=True)

    insight = {
        "id": "insight-adk-runner-centrality",
        "framework_id": "adk-2.0.0a3",
        "title": "Runner 是请求总控与主要收口器",
        "description": "最小决策包测试样本。",
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


def test_build_decision_pack_result_creates_output_and_metadata(tmp_path: Path) -> None:
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
            "description": "最小决策包测试样本。",
            "confidence": 0.97,
            "impact": {
                "architectural": "high",
                "migration": "high",
                "product": "medium",
            },
            "evidence": [
                {
                    "type": "documentation_reference",
                    "source_file": "core_runtime_map",
                    "source_section": "6. 单次请求运行主链",
                    "quote": "Runner 承担请求协调与主要收口。",
                }
            ],
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
        result = decision_pack.build_decision_pack_result("insight-adk-runner-centrality")
    finally:
        generate_outputs.NEW_PROJECT_PATH = original_project_path
        generate_outputs.load_insight = original_load_insight
        generate_outputs.load_framework = original_load_framework

    metadata_path = tmp_path / result["metadata_file"]
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert result["status"] == "success"
    assert result["command"] == "ce decision-pack --insight insight-adk-runner-centrality"
    assert result["command_name"] == "ce decision-pack"
    assert result["usage"] == "ce decision-pack --insight <insight_id>"
    assert result["contract_version"] == "ce-decision-pack-result/v1"
    assert result["output_type"] == "decision-pack"
    assert result["insight_id"] == "insight-adk-runner-centrality"
    assert result["framework_id"] == "adk-2.0.0a3"
    assert result["output_directory"] == "outputs/decision-packs"
    assert result["metadata_id"] == metadata["id"]
    assert "待决问题" in result["decision_summary"]
    assert "技术判断推进为可执行" in result["decision_question"]
    assert "轻量推进" in result["recommended_option"]
    assert result["next_action"].startswith("1. ")
    assert result["validation"]["output_file_exists"] is True
    assert result["validation"]["metadata_file_exists"] is True
    assert (tmp_path / result["output_file"]).exists()
    assert metadata_path.exists()
    assert metadata["type"] == "decision-pack"


def test_run_decision_pack_loop_returns_json_error_when_insight_missing(
    capsys,
    tmp_path: Path,
) -> None:
    original_project_path = generate_outputs.NEW_PROJECT_PATH
    generate_outputs.NEW_PROJECT_PATH = tmp_path
    install_sample_data(tmp_path)

    try:
        exit_code = decision_pack.run_decision_pack_loop(None, json_only=True)
    finally:
        generate_outputs.NEW_PROJECT_PATH = original_project_path

    result = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert result["status"] == "error"
    assert result["error_code"] == "missing_insight"
    assert result["usage"] == "ce decision-pack --insight <insight_id>"
    assert "insight-adk-runner-centrality" in result["available_insight_ids"]


def test_run_decision_pack_loop_returns_json_error_when_insight_not_found(
    capsys,
    tmp_path: Path,
) -> None:
    original_project_path = generate_outputs.NEW_PROJECT_PATH
    generate_outputs.NEW_PROJECT_PATH = tmp_path
    install_sample_data(tmp_path)

    try:
        exit_code = decision_pack.run_decision_pack_loop(
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


def test_run_decision_pack_loop_rejects_unexpected_args(
    capsys,
    tmp_path: Path,
) -> None:
    original_project_path = generate_outputs.NEW_PROJECT_PATH
    generate_outputs.NEW_PROJECT_PATH = tmp_path
    install_sample_data(tmp_path)

    try:
        exit_code = decision_pack.run_decision_pack_loop(
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


def test_build_decision_pack_result_supports_real_runner_sample(tmp_path: Path) -> None:
    original_project_path = generate_outputs.NEW_PROJECT_PATH
    generate_outputs.NEW_PROJECT_PATH = tmp_path
    install_real_repo_data(tmp_path, "insight-adk-runner-centrality")

    try:
        result = decision_pack.build_decision_pack_result("insight-adk-runner-centrality")
    finally:
        generate_outputs.NEW_PROJECT_PATH = original_project_path

    output_path = tmp_path / result["output_file"]
    output_text = output_path.read_text(encoding="utf-8")

    assert result["status"] == "success"
    assert result["insight_id"] == "insight-adk-runner-centrality"
    assert "Runner 是请求总控与主要收口器" in result["insight_title"]
    assert "## 决策问题" in output_text
    assert "## 推荐方案" in output_text
    assert "## 下一步行动" in output_text


def test_cli_registers_decision_pack_subcommand() -> None:
    parser = cli.build_parser()

    namespace, extra_args = parser.parse_known_args(
        ["decision-pack", "--insight", "insight-adk-runner-centrality", "--json"]
    )

    assert namespace.command == "decision-pack"
    assert namespace.insight == "insight-adk-runner-centrality"
    assert namespace.json is True
    assert extra_args == []

DECISION_PACK_FIXTURE_ROOT = project_root / "tests" / "fixtures" / "decision-packs"


def normalize_decision_pack_result_for_fixture(result: dict) -> dict:
    normalized = dict(result)
    normalized["generated_at"] = "<generated_at>"
    normalized["metadata_id"] = "<metadata_id>"
    normalized["metadata_file"] = "<metadata_file>"
    normalized["output_file"] = "<output_file>"
    normalized["validation"] = {
        "metadata_file_exists": True,
        "output_file_exists": True,
    }
    return normalized


def normalize_decision_pack_metadata_for_fixture(metadata: dict) -> dict:
    normalized = dict(metadata)
    normalized["id"] = "<metadata_id>"
    normalized["generated_at"] = "<generated_at>"
    normalized["file_path"] = "<output_file>"
    return normalized


def load_json_fixture(relative_path: str) -> dict:
    fixture_path = DECISION_PACK_FIXTURE_ROOT / relative_path
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_decision_pack_json_result_matches_stable_fixture(tmp_path: Path) -> None:
    original_project_path = generate_outputs.NEW_PROJECT_PATH
    generate_outputs.NEW_PROJECT_PATH = tmp_path
    install_real_repo_data(tmp_path, "insight-adk-runner-centrality")

    try:
        result = decision_pack.build_decision_pack_result("insight-adk-runner-centrality")
    finally:
        generate_outputs.NEW_PROJECT_PATH = original_project_path

    expected = load_json_fixture("json/runner-centrality-result.json")

    assert normalize_decision_pack_result_for_fixture(result) == expected
    assert expected["generated_at"] == "<generated_at>"
    assert expected["metadata_id"] == "<metadata_id>"
    assert expected["metadata_file"] == "<metadata_file>"
    assert expected["output_file"] == "<output_file>"


def test_decision_pack_metadata_matches_stable_fixture(tmp_path: Path) -> None:
    original_project_path = generate_outputs.NEW_PROJECT_PATH
    generate_outputs.NEW_PROJECT_PATH = tmp_path
    install_real_repo_data(tmp_path, "insight-adk-runner-centrality")

    try:
        result = decision_pack.build_decision_pack_result("insight-adk-runner-centrality")
    finally:
        generate_outputs.NEW_PROJECT_PATH = original_project_path

    metadata_path = tmp_path / result["metadata_file"]
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    expected = load_json_fixture("metadata/runner-centrality-metadata.json")

    assert normalize_decision_pack_metadata_for_fixture(metadata) == expected
    assert expected["generated_at"] == "<generated_at>"
    assert expected["id"] == "<metadata_id>"
    assert expected["file_path"] == "<output_file>"

