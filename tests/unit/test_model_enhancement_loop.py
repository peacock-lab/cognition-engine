from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cognition_engine import model_enhancement
from cognition_engine.modeling import ModelResponse
from cognition_engine.rendering import generate_outputs


project_root = Path(__file__).parent.parent.parent


def install_sample_data(tmp_path: Path) -> None:
    insights_dir = tmp_path / "data" / "insights" / "adk-2.0.0a3"
    frameworks_dir = tmp_path / "data" / "frameworks" / "adk-2.0.0a3"
    insights_dir.mkdir(parents=True, exist_ok=True)
    frameworks_dir.mkdir(parents=True, exist_ok=True)

    insight = {
        "id": "insight-adk-runner-centrality",
        "framework_id": "adk-2.0.0a3",
        "type": "architectural_insight",
        "title": "Runner 是请求总控与主要收口器",
        "description": "最小模型增强测试样本。",
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
    framework = {
        "id": "adk-2.0.0a3",
        "name": "Google Agent Development Kit",
        "version": "2.0.0a3",
        "type": "framework_metadata",
        "repository": "google/adk-python",
        "status": "analyzed",
        "metadata": {
            "language": "python",
            "architecture_style": "agent_runtime",
            "primary_entry_points": ["Runner"],
            "core_modules": ["google.adk.runners"],
            "analysis_depth": "deep_audit_completed",
            "source_documents": [
                {
                    "source_id": "core_runtime_map",
                    "title": "Core Runtime Map",
                    "kind": "analysis",
                    "path": "docs/core_runtime_map.md",
                }
            ],
            "input_channels": ["local_fixture"],
        },
        "timestamps": {
            "first_analyzed": "2026-04-15T00:00:00",
            "last_updated": "2026-04-24T00:00:00",
        },
    }

    insights_dir.joinpath("insight-adk-runner-centrality.json").write_text(
        json.dumps(insight, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    frameworks_dir.joinpath("metadata.json").write_text(
        json.dumps(framework, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def with_project_path(tmp_path: Path):
    class ProjectPathContext:
        def __enter__(self):
            self.original_project_path = generate_outputs.NEW_PROJECT_PATH
            generate_outputs.NEW_PROJECT_PATH = tmp_path
            return self

        def __exit__(self, exc_type, exc, tb):
            generate_outputs.NEW_PROJECT_PATH = self.original_project_path

    return ProjectPathContext()


def test_run_model_enhancement_loop_returns_json_error_when_insight_missing(
    capsys,
    tmp_path: Path,
) -> None:
    install_sample_data(tmp_path)

    with with_project_path(tmp_path):
        exit_code = model_enhancement.run_model_enhancement_loop(None, json_only=True)

    result = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert result["status"] == "error"
    assert result["contract_version"] == "ce-model-enhancement-result/v1"
    assert result["error_code"] == "missing_insight"
    assert "insight-adk-runner-centrality" in result["available_insight_ids"]
    assert result["validation"]["output_file_exists"] is False


def test_run_model_enhancement_loop_returns_json_error_when_insight_not_found(
    capsys,
    tmp_path: Path,
) -> None:
    install_sample_data(tmp_path)

    with with_project_path(tmp_path):
        exit_code = model_enhancement.run_model_enhancement_loop(
            "insight-does-not-exist",
            json_only=True,
        )

    result = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert result["status"] == "error"
    assert result["error_code"] == "insight_not_found"
    assert result["insight_id"] == "insight-does-not-exist"


def test_mock_provider_creates_model_enhancement_output_and_metadata(
    tmp_path: Path,
) -> None:
    install_sample_data(tmp_path)

    with with_project_path(tmp_path):
        result = model_enhancement.build_model_enhancement_result(
            "insight-adk-runner-centrality",
        )

    output_path = tmp_path / result["output_file"]
    metadata_path = tmp_path / result["metadata_file"]
    output_text = output_path.read_text(encoding="utf-8")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert result["status"] == "success"
    assert result["contract_version"] == "ce-model-enhancement-result/v1"
    assert result["output_type"] == "model-enhancement"
    assert result["output_directory"] == "outputs/model-enhancements"
    assert result["provider"] == "mock"
    assert result["model_status"] == "success"
    assert result["fallback_used"] is False
    assert result["validation"]["output_file_exists"] is True
    assert result["validation"]["metadata_file_exists"] is True
    assert metadata["type"] == "model-enhancement"
    assert "Runner 是请求总控与主要收口器" in output_text
    assert "Google Agent Development Kit" in output_text
    assert "最小模型增强测试样本。" in output_text
    assert "provider: `mock`" in output_text


def test_model_enhancement_does_not_create_product_brief_or_decision_pack_outputs(
    tmp_path: Path,
) -> None:
    install_sample_data(tmp_path)

    with with_project_path(tmp_path):
        model_enhancement.build_model_enhancement_result(
            "insight-adk-runner-centrality",
        )

    assert not (tmp_path / "outputs" / "product-briefs").exists()
    assert not (tmp_path / "outputs" / "decision-packs").exists()


def test_provider_error_is_recorded_in_traceable_output(tmp_path: Path) -> None:
    install_sample_data(tmp_path)

    with with_project_path(tmp_path):
        result = model_enhancement.build_model_enhancement_result(
            "insight-adk-runner-centrality",
            provider="not_supported",
        )

    output_text = (tmp_path / result["output_file"]).read_text(encoding="utf-8")

    assert result["status"] == "success"
    assert result["provider"] == "not_supported"
    assert result["model_status"] == "error"
    assert result["error_code"] == "unsupported_provider"
    assert result["validation"]["output_file_exists"] is True
    assert "模型未返回可用增强内容" in output_text
    assert "unsupported_provider" in output_text


def test_module_entry_outputs_json_with_mock_provider(tmp_path: Path) -> None:
    install_sample_data(tmp_path)
    script = (
        "import json, sys; "
        "from pathlib import Path; "
        "from cognition_engine.rendering import generate_outputs; "
        "generate_outputs.NEW_PROJECT_PATH = Path(sys.argv[1]); "
        "from cognition_engine.model_enhancement import main; "
        "raise SystemExit(main(['--insight', 'insight-adk-runner-centrality', '--json']))"
    )

    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    payload = json.loads(result.stdout)

    assert payload["status"] == "success"
    assert payload["output_type"] == "model-enhancement"
    assert payload["provider"] == "mock"


def test_model_request_timeout_uses_timeout_environment(
    monkeypatch,
    tmp_path: Path,
) -> None:
    class CapturingRuntime:
        def __init__(self) -> None:
            self.timeout_seconds = None

        def run(self, request):  # noqa: ANN001, ANN201
            self.timeout_seconds = request.timeout_seconds
            return ModelResponse(
                status="success",
                output_text="captured",
                model=request.model,
                provider=request.provider,
                latency_ms=0.0,
                raw_summary={},
            )

    install_sample_data(tmp_path)
    runtime = CapturingRuntime()
    monkeypatch.setenv("CE_MODEL_TIMEOUT_SECONDS", "180")

    with with_project_path(tmp_path):
        result = model_enhancement.build_model_enhancement_result(
            "insight-adk-runner-centrality",
            provider="adk_litellm_ollama",
            runtime=runtime,
        )

    assert result["status"] == "success"
    assert result["provider"] == "adk_litellm_ollama"
    assert runtime.timeout_seconds == 180.0


def test_model_request_timeout_defaults_to_30_seconds(
    monkeypatch,
    tmp_path: Path,
) -> None:
    class CapturingRuntime:
        def __init__(self) -> None:
            self.timeout_seconds = None

        def run(self, request):  # noqa: ANN001, ANN201
            self.timeout_seconds = request.timeout_seconds
            return ModelResponse(
                status="success",
                output_text="captured",
                model=request.model,
                provider=request.provider,
                latency_ms=0.0,
                raw_summary={},
            )

    install_sample_data(tmp_path)
    runtime = CapturingRuntime()
    monkeypatch.delenv("CE_MODEL_TIMEOUT_SECONDS", raising=False)

    with with_project_path(tmp_path):
        model_enhancement.build_model_enhancement_result(
            "insight-adk-runner-centrality",
            runtime=runtime,
        )

    assert runtime.timeout_seconds == 30.0


def test_invalid_timeout_environment_falls_back_to_default(
    monkeypatch,
    tmp_path: Path,
) -> None:
    class CapturingRuntime:
        def __init__(self) -> None:
            self.timeout_seconds = None

        def run(self, request):  # noqa: ANN001, ANN201
            self.timeout_seconds = request.timeout_seconds
            return ModelResponse(
                status="success",
                output_text="captured",
                model=request.model,
                provider=request.provider,
                latency_ms=0.0,
                raw_summary={},
            )

    install_sample_data(tmp_path)
    runtime = CapturingRuntime()
    monkeypatch.setenv("CE_MODEL_TIMEOUT_SECONDS", "not-a-number")

    with with_project_path(tmp_path):
        result = model_enhancement.build_model_enhancement_result(
            "insight-adk-runner-centrality",
            runtime=runtime,
        )

    assert result["status"] == "success"
    assert runtime.timeout_seconds == 30.0
