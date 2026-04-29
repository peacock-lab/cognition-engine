#!/usr/bin/env python3
"""对象 / 契约层样例契约测试。"""

import pytest
import json
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class TestDataModels:
    """测试当前正式文档支持的样例对象契约。"""
    
    def test_framework_metadata_structure(self):
        """框架元数据应符合当前正式对象契约。"""
        framework_metadata = {
            "id": "adk-2.0.0a3",
            "name": "Google Agent Development Kit",
            "version": "2.0.0a3",
            "type": "agent_framework",
            "repository": "/Users/peacock/projects/_study/google-adk",
            "status": "under_analysis",
            "metadata": {
                "language": "python",
                "architecture_style": "runner_workflow",
                "entry_point": "adk.runner.run",
                "created_at": "2026-04-15T12:00:00Z",
                "updated_at": "2026-04-15T12:00:00Z"
            }
        }

        required_fields = ["id", "name", "version", "type", "repository", "status"]
        for field in required_fields:
            assert field in framework_metadata, f"缺少必需字段: {field}"

        assert isinstance(framework_metadata["id"], str)
        assert isinstance(framework_metadata["name"], str)
        assert isinstance(framework_metadata["version"], str)
        assert isinstance(framework_metadata["metadata"], dict)

        assert "-" in framework_metadata["id"], "ID应包含框架名和版本"

    def test_insight_data_structure(self):
        """洞察对象应保留正式文档中的核心字段。"""
        insight_data = {
            "id": "insight-adk-runner-centrality",
            "framework_id": "adk-2.0.0a3",
            "type": "architectural_pattern",
            "category": "core_coordination",
            "title": "Runner作为中央协调器的架构模式",
            "description": "ADK以Runner为核心，协调工具调用、状态管理和事件处理",
            "evidence": [
                {
                    "type": "source_code",
                    "location": "adk/runner/runner.py",
                    "description": "Runner类定义，包含工具调用和状态管理"
                },
                {
                    "type": "call_chain",
                    "description": "请求处理流程：Request → Runner → Tools → Response"
                }
            ],
            "confidence": 0.9,
            "impact": {
                "architectural": "high",
                "migration": "high",
                "product": "medium"
            },
            "tags": ["architecture", "core_pattern", "coordination"],
            "connections": [],
            "created_at": "2026-04-15T12:00:00Z",
            "updated_at": "2026-04-15T12:00:00Z"
        }

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
            assert field in insight_data, f"缺少必需字段: {field}"

        assert isinstance(insight_data["evidence"], list)
        assert len(insight_data["evidence"]) > 0

        for evidence in insight_data["evidence"]:
            assert "type" in evidence
            assert "description" in evidence

        assert 0 <= insight_data["confidence"] <= 1

        assert isinstance(insight_data["impact"], dict)
        assert isinstance(insight_data["tags"], list)
        assert isinstance(insight_data["connections"], list)

    def test_executed_validation_data_structure(self):
        """已执行 validation 应使用 result / method 收口，而不是旧 status 枚举。"""
        validation_data = {
            "id": "validation-adk-runner-minimal",
            "framework_id": "adk-2.0.0a3",
            "insight_id": "insight-adk-runner-centrality",
            "type": "minimal_sample",
            "method": "code_execution",
            "description": "最小 Runner 运行验证",
            "execution_command": "python validation_samples/adk_runner_minimal.py",
            "expected_output": "Runner 初始化成功并完成最小调用。",
            "actual_output": "Runner 初始化成功并完成最小调用。",
            "result": "success",
            "run_timestamp": "2026-04-15T12:00:00Z",
            "environment": {
                "python_version": "3.14.3",
                "os": "macOS",
                "adk_version": "2.0.0a3"
            }
        }

        required_fields = [
            "id",
            "framework_id",
            "type",
            "method",
            "description",
            "result",
        ]
        for field in required_fields:
            assert field in validation_data, f"缺少必需字段: {field}"

        assert validation_data["result"] in ["pending", "success", "failed"]
        assert validation_data["method"] == "code_execution"
        assert "status" not in validation_data

    def test_validation_candidate_structure(self):
        """候选 validation 应体现 candidate 身份，而不是伪装成已执行记录。"""
        candidate_data = {
            "id": "validation-candidate-github-issue-google-adk-python-4901",
            "framework_id": "adk-2.0.0a3",
            "type": "minimal_sample_candidate",
            "method": "community_signal_analysis",
            "title": "Validation Candidate: mcp hang",
            "description": "验证 MCP transport 在 403 场景下是否会 hang。",
            "execution_command": "python validation_samples/adk-2.0.0a3/foo/repro_case.py",
            "expected_output": "原始错误应在限定时延内透传给调用方。",
            "actual_output": "最小复现脚手架已生成，待补充真实复现逻辑并执行；当前尚无实际运行证据。",
            "result": "pending",
            "status": "candidate",
            "source_connection_id": "connection-github-issue-google-adk-python-4901",
            "source_thread_url": "https://github.com/google/adk-python/issues/4901",
            "candidate_score": 0.96,
            "signal_summary": {
                "problem_hits": ["hang"],
                "repro_hits": ["callback"],
                "component_hits": ["mcp"],
            },
            "suggested_checks": ["原始异常是否在限定时延内透传到调用方"],
            "scaffold_status": "ready",
            "scaffold_files": [
                "validation_samples/adk-2.0.0a3/foo/repro_case.py",
                "validation_samples/adk-2.0.0a3/foo/README.md",
                "validation_samples/adk-2.0.0a3/foo/context.json",
            ],
        }

        assert candidate_data["result"] == "pending"
        assert candidate_data["status"] == "candidate"
        assert candidate_data["method"] == "community_signal_analysis"
        assert candidate_data["source_connection_id"].startswith("connection-")
        assert candidate_data["scaffold_status"] == "ready"
        assert len(candidate_data["scaffold_files"]) == 3

    def test_connection_data_structure(self):
        """connection 对象应保持当前文档定义的最小稳定字段。"""
        connection_data = {
            "id": "connection-github-issue-google-adk-python-4901",
            "framework_id": "adk-2.0.0a3",
            "type": "github_issue_thread",
            "source": "https://github.com/google/adk-python/issues/4901",
            "title": "GitHub Issue #4901: MCP hang",
            "content_summary": "MCP server returns 403 and caller hangs.",
            "relevance": 0.71,
            "connections": [],
            "status": "ingested",
            "timestamp": "2026-04-15T17:20:35.621900Z",
        }

        required_fields = [
            "id",
            "framework_id",
            "type",
            "source",
            "title",
            "content_summary",
            "relevance",
            "connections",
            "status",
            "timestamp",
        ]
        for field in required_fields:
            assert field in connection_data, f"缺少必需字段: {field}"

        assert isinstance(connection_data["relevance"], (int, float))
        assert isinstance(connection_data["connections"], list)

class TestDataIntegrity:
    """测试样例契约共用的对象级约束与目录完整性。"""
    
    def test_json_serialization(self):
        """JSON 序列化应保持对象内容不变。"""
        test_data = {
            "id": "test-json",
            "name": "测试数据",
            "nested": {
                "value": 123,
                "list": [1, 2, 3]
            }
        }
        
        json_str = json.dumps(test_data, ensure_ascii=False)
        loaded_data = json.loads(json_str)

        assert loaded_data == test_data
        assert loaded_data["id"] == "test-json"
        assert loaded_data["nested"]["value"] == 123

    def test_file_path_consistency(self):
        """当前数据主对象目录应真实存在。"""
        data_dir = project_root / "data"
        expected_subdirs = ["frameworks", "insights", "validations", "connections"]

        for subdir in expected_subdirs:
            subdir_path = data_dir / subdir
            assert subdir_path.exists(), f"数据子目录不存在: {subdir}"
            assert subdir_path.is_dir(), f"不是目录: {subdir}"

class TestDataValidation:
    """测试样例契约共用的正式规则。"""
    
    def test_id_uniqueness_pattern(self):
        """当前对象 ID 应符合现有命名模式。"""
        test_cases = [
            ("adk-2.0.0a3", True),  # 有效：框架-版本
            ("insight-adk-runner-centrality", True),  # 有效：类型-框架-描述
            ("validation-adk-runner-minimal", True),  # 有效：类型-框架-描述
            ("validation-candidate-github-issue-google-adk-python-4901", True),
            ("connection-github-issue-google-adk-python-4901", True),
            ("invalid_id", False),  # 无效：缺少分隔符
            ("adk", False),  # 无效：太短
            ("", False),  # 无效：空
        ]

        for test_id, should_be_valid in test_cases:
            if should_be_valid:
                assert "-" in test_id, f"有效ID应包含分隔符: {test_id}"
                assert len(test_id) >= 5, f"有效ID应足够长: {test_id}"
            else:
                pass

    def test_validation_result_contract(self):
        """validation 正式结果应遵循当前状态文档，而不是旧枚举。"""
        valid_results = ["pending", "success", "failed"]
        invalid_results = ["failure", "partial", "reproduced"]

        for result in valid_results:
            assert result in ["pending", "success", "failed"]

        for result in invalid_results:
            assert result not in valid_results

    def test_timestamp_format(self):
        """时间戳应接受当前文档中的 ISO 8601 形式。"""
        valid_timestamps = [
            "2026-04-15T12:00:00Z",
            "2026-04-15T12:00:00+00:00",
            "2026-04-15T12:00:00.123Z",
        ]

        for timestamp in valid_timestamps:
            try:
                parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                assert parsed.year == 2026
                assert parsed.month == 4
                assert parsed.day == 15
            except ValueError:
                pytest.fail(f"无效的时间戳格式: {timestamp}")

if __name__ == "__main__":
    # 直接运行测试
    print("运行数据模型测试...")
    print("=" * 60)
    
    test_classes = [TestDataModels, TestDataIntegrity, TestDataValidation]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                total_tests += 1
                try:
                    method = getattr(instance, method_name)
                    method()
                    passed_tests += 1
                    print(f"✅ {method_name} 通过")
                except AssertionError as e:
                    print(f"❌ {method_name} 失败: {e}")
                except Exception as e:
                    print(f"❌ {method_name} 错误: {e}")
    
    print("=" * 60)
    print(f"测试完成: {passed_tests}/{total_tests} 通过")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过!")
        sys.exit(0)
    else:
        print("⚠️  部分测试失败")
        sys.exit(1)
