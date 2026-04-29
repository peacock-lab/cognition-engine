#!/usr/bin/env python3
"""对象 / 契约层真实样本契约检查。"""

import json
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def load_json(relative_path: str):
    """读取项目内的真实 JSON 样本。"""
    file_path = project_root / relative_path
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def assert_iso8601_like(value: str):
    """校验当前项目接受的 ISO 8601 时间字符串。"""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.year >= 2026


class TestRealDataContracts:
    """基于真实样本检查当前正式对象契约。"""

    def test_framework_metadata_real_sample(self):
        """framework metadata 真实样本应符合最小正式契约。"""
        data = load_json("data/frameworks/adk-2.0.0a3/metadata.json")

        required_fields = [
            "id",
            "name",
            "version",
            "type",
            "repository",
            "status",
            "metadata",
            "timestamps",
        ]
        for field in required_fields:
            assert field in data, f"framework metadata 缺少字段: {field}"

        assert data["type"] == "agent_framework"
        assert isinstance(data["metadata"], dict)
        assert isinstance(data["timestamps"], dict)
        assert "language" in data["metadata"]
        assert "architecture_style" in data["metadata"]
        assert isinstance(data["metadata"]["primary_entry_points"], list)
        assert len(data["metadata"]["primary_entry_points"]) > 0
        assert isinstance(data["metadata"]["core_modules"], list)
        assert len(data["metadata"]["core_modules"]) > 0
        assert isinstance(data["metadata"]["analysis_depth"], str)
        assert isinstance(data["metadata"]["source_documents"], list)
        assert len(data["metadata"]["source_documents"]) > 0
        for source_document in data["metadata"]["source_documents"]:
            assert "source_id" in source_document
            assert "title" in source_document
            assert "kind" in source_document
            assert "path" in source_document
        assert isinstance(data["metadata"]["input_channels"], list)
        assert len(data["metadata"]["input_channels"]) > 0
        assert all(isinstance(item, str) and item for item in data["metadata"]["input_channels"])
        assert "first_analyzed" in data["timestamps"]
        assert "last_updated" in data["timestamps"]
        assert_iso8601_like(f"{data['timestamps']['first_analyzed']}T00:00:00+00:00")
        assert_iso8601_like(f"{data['timestamps']['last_updated']}T00:00:00+00:00")

    def test_insight_real_sample(self):
        """insight 真实样本应符合最小正式契约。"""
        data = load_json(
            "data/insights/adk-2.0.0a3/insight-adk-runner-centrality.json"
        )

        required_fields = [
            "id",
            "framework_id",
            "type",
            "category",
            "title",
            "description",
            "evidence",
            "confidence",
            "impact",
            "tags",
            "connections",
        ]
        for field in required_fields:
            assert field in data, f"insight 缺少字段: {field}"

        assert isinstance(data["evidence"], list)
        assert len(data["evidence"]) > 0
        for evidence in data["evidence"]:
            assert "type" in evidence
            assert "source_file" in evidence
            assert "source_section" in evidence
        assert isinstance(data["connections"], list)
        for connection in data["connections"]:
            assert "insight_id" in connection
            assert "type" in connection
            assert "strength" in connection
            assert "description" in connection
        assert 0 <= data["confidence"] <= 1
        assert_iso8601_like(data["extraction_timestamp"])

    def test_executed_validation_real_sample(self):
        """已执行 validation 真实样本应符合已执行对象契约。"""
        data = load_json(
            "data/validations/adk-2.0.0a3/validation-adk-state-model.json"
        )

        required_fields = [
            "id",
            "framework_id",
            "insight_id",
            "type",
            "method",
            "description",
            "execution_command",
            "expected_output",
            "actual_output",
            "result",
            "run_timestamp",
        ]
        for field in required_fields:
            assert field in data, f"已执行 validation 缺少字段: {field}"

        assert data["type"] == "minimal_sample"
        assert data["method"] == "code_execution"
        assert data["result"] in ["success", "failed"]
        assert "status" not in data
        assert data["insight_id"].startswith("insight-")
        assert_iso8601_like(data["run_timestamp"])

    def test_executed_validation_with_local_rerun_sample(self):
        """本地复跑已补齐的 validation 应同时指向样本入口与证据文件。"""
        data = load_json(
            "data/validations/adk-2.0.0a3/validation-adk-state-delta-output-event.json"
        )
        evidence = load_json(
            "validation_samples/adk-2.0.0a3/validation-adk-state-delta-output-event/rerun_evidence.json"
        )

        assert data["type"] == "minimal_sample"
        assert data["result"] == "success"
        assert data["code_sample"].endswith(
            "validation-adk-state-delta-output-event/repro_case.py"
        )
        assert data["execution_command"].startswith(".venv/bin/python ")
        assert data["rerun_evidence_path"].endswith(
            "validation-adk-state-delta-output-event/rerun_evidence.json"
        )
        assert evidence["validation_id"] == data["id"]
        assert evidence["reproduced_issue"] is True
        assert evidence["child_output"] == "result"
        assert evidence["state_delta"]["key"] == "val"
        assert data["validation_execution"] == {
            "reproduced_issue": True,
            "internal_observation": {
                "observed_node_name": "n",
                "output_event_count": 1,
            },
            "context_access": {
                "state_delta": {
                    "key": "val",
                }
            },
            "runner_execution": {
                "process_returncode": 0,
                "fatal_error_type": None,
                "fatal_error_message": None,
            },
        }
        assert_iso8601_like(data["run_timestamp"])

    def test_executed_validation_failure_side_sample(self):
        """failure-side executed validation 真实样本应正式落盘最小失败摘要。"""
        data = load_json(
            "data/validations/adk-2.0.0a3/validation-github-issue-google-adk-python-4901-failure-side.json"
        )

        assert data["type"] == "minimal_sample"
        assert data["method"] == "code_execution"
        assert data["result"] == "failed"
        assert "status" not in data
        assert data["validation_execution"] == {
            "reproduced_issue": False,
            "internal_observation": {
                "observed_node_name": None,
                "output_event_count": None,
            },
            "context_access": {
                "state_delta": {},
            },
            "runner_execution": {
                "process_returncode": 1,
                "fatal_error_type": "PermissionError",
                "fatal_error_message": "[Errno 1] Operation not permitted",
            },
        }
        assert data["last_observed_payload"]["fatal_error_type"] == "PermissionError"
        assert data["last_observed_payload"]["process_returncode"] == 1
        assert_iso8601_like(data["run_timestamp"])

    def test_validation_candidate_real_sample(self):
        """validation candidate 真实样本应符合 pending candidate 契约。"""
        data = load_json(
            "data/validations/adk-2.0.0a3/validation-candidate-github-issue-google-adk-python-4901.json"
        )

        required_fields = [
            "id",
            "framework_id",
            "type",
            "method",
            "title",
            "description",
            "execution_command",
            "expected_output",
            "actual_output",
            "result",
            "status",
            "timestamp",
            "run_timestamp",
            "source_connection_id",
            "source_thread_url",
            "candidate_score",
        ]
        for field in required_fields:
            assert field in data, f"validation candidate 缺少字段: {field}"

        assert data["type"] in ["external_signal_candidate", "minimal_sample_candidate"]
        assert data["method"] == "community_signal_analysis"
        assert data["result"] == "pending"
        assert data["status"] == "candidate"
        assert data["source_connection_id"].startswith("connection-")
        assert isinstance(data.get("signal_summary"), dict)
        assert isinstance(data.get("suggested_checks"), list)
        assert_iso8601_like(data["timestamp"])
        assert_iso8601_like(data["run_timestamp"])

    def test_connection_real_sample(self):
        """connection 真实样本应符合最小正式契约。"""
        data = load_json(
            "data/connections/github/connection-github-issue-google-adk-python-4901.json"
        )

        required_fields = [
            "id",
            "framework_id",
            "type",
            "source",
            "title",
            "relevance",
            "status",
            "timestamp",
        ]
        for field in required_fields:
            assert field in data, f"connection 缺少字段: {field}"

        assert isinstance(data["relevance"], (int, float))
        assert any(
            key in data for key in ["connections", "dialogue", "content_summary", "metadata"]
        )
        assert_iso8601_like(data["timestamp"])

    def test_connection_relation_branches_real_samples(self):
        """connection 真实样本应覆盖 one-of 目标引用与条件 type 规则。"""
        github_thread = load_json(
            "data/connections/github/connection-github-issue-google-adk-python-4901.json"
        )
        source_document = load_json(
            "data/connections/framework-learning-lab/connection-source-adk-core-runtime-map.json"
        )

        relation_target_fields = ("connection_id", "validation_id", "insight_id")

        for relation in github_thread["connections"] + source_document["connections"]:
            present_targets = [field for field in relation_target_fields if field in relation]
            assert len(present_targets) == 1, f"关系项目标引用异常: {relation}"
            assert isinstance(relation["connection_strength"], (int, float))
            assert isinstance(relation["notes"], str) and relation["notes"].strip()

        github_targets = {field for relation in github_thread["connections"] for field in relation_target_fields if field in relation}
        assert github_targets == {"connection_id", "validation_id"}
        assert all("type" in relation for relation in github_thread["connections"])

        insight_relations = [relation for relation in source_document["connections"] if "insight_id" in relation]
        assert insight_relations
        assert all("type" not in relation for relation in insight_relations)
