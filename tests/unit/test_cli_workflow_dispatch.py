from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cognition_engine import cli
from engine.transformer import generate_outputs


project_root = Path(__file__).parent.parent.parent


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


def with_project_path(tmp_path: Path):
    class ProjectPathContext:
        def __enter__(self):
            self.original_project_path = generate_outputs.NEW_PROJECT_PATH
            generate_outputs.NEW_PROJECT_PATH = tmp_path
            return self

        def __exit__(self, exc_type, exc, tb):
            generate_outputs.NEW_PROJECT_PATH = self.original_project_path

    return ProjectPathContext()


def test_cli_registers_workflow_subcommand() -> None:
    parser = cli.build_parser()

    namespace, extra_args = parser.parse_known_args(
        ["workflow", "--insight", "insight-adk-runner-centrality", "--json"]
    )

    assert namespace.command == "workflow"
    assert namespace.insight == "insight-adk-runner-centrality"
    assert namespace.json is True
    assert not hasattr(namespace, "model_provider")
    assert extra_args == []


def test_ce_workflow_json_dispatches_to_workflow_loop(
    capsys,
    tmp_path: Path,
) -> None:
    install_real_repo_data(tmp_path, "insight-adk-runner-centrality")
    parser = cli.build_parser()
    namespace, extra_args = parser.parse_known_args(
        ["workflow", "--insight", "insight-adk-runner-centrality", "--json"]
    )

    with with_project_path(tmp_path):
        exit_code = cli.dispatch(namespace, extra_args)

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["workflow_name"] == "insight-to-decision workflow"
    assert payload["model_enhancement"]["output_type"] == "model-enhancement"
    assert payload["validation"]["model_enhancement_output_file_exists"] is True


def test_ce_workflow_missing_insight_returns_structured_error(
    capsys,
    tmp_path: Path,
) -> None:
    install_real_repo_data(tmp_path, "insight-adk-runner-centrality")
    parser = cli.build_parser()
    namespace, extra_args = parser.parse_known_args(["workflow", "--json"])

    with with_project_path(tmp_path):
        exit_code = cli.dispatch(namespace, extra_args)

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["status"] == "error"
    assert payload["error_code"] == "missing_insight"
    assert "insight-adk-runner-centrality" in payload["available_insight_ids"]


def test_ce_workflow_rejects_unrecognized_extra_args(
    capsys,
    tmp_path: Path,
) -> None:
    install_real_repo_data(tmp_path, "insight-adk-runner-centrality")
    parser = cli.build_parser()
    namespace, extra_args = parser.parse_known_args(
        ["workflow", "--insight", "insight-adk-runner-centrality", "--json", "extra"]
    )

    with with_project_path(tmp_path):
        exit_code = cli.dispatch(namespace, extra_args)

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["status"] == "error"
    assert payload["error_code"] == "unexpected_args"
    assert payload["unexpected_args"] == ["extra"]


def test_ce_workflow_does_not_expose_model_provider_option() -> None:
    parser = cli.build_parser()

    namespace, extra_args = parser.parse_known_args(
        [
            "workflow",
            "--insight",
            "insight-adk-runner-centrality",
            "--model-provider",
            "adk_litellm_ollama",
        ]
    )

    assert namespace.command == "workflow"
    assert not hasattr(namespace, "model_provider")
    assert extra_args == ["--model-provider", "adk_litellm_ollama"]


def test_ce_workflow_defaults_to_mock_provider(tmp_path: Path) -> None:
    install_real_repo_data(tmp_path, "insight-adk-runner-centrality")
    parser = cli.build_parser()
    namespace, extra_args = parser.parse_known_args(
        ["workflow", "--insight", "insight-adk-runner-centrality", "--json"]
    )

    with with_project_path(tmp_path):
        exit_code = cli.dispatch(namespace, extra_args)

    assert exit_code == 0
    output_files = list((tmp_path / "outputs" / "model-enhancements").glob("*.md"))
    assert len(output_files) == 1
    assert "provider: `mock`" in output_files[0].read_text(encoding="utf-8")


def test_existing_brief_and_decision_pack_dispatch_remain_registered() -> None:
    parser = cli.build_parser()

    brief_namespace, brief_extra = parser.parse_known_args(
        ["brief", "--insight", "insight-adk-runner-centrality", "--json"]
    )
    decision_namespace, decision_extra = parser.parse_known_args(
        ["decision-pack", "--insight", "insight-adk-runner-centrality", "--json"]
    )

    assert brief_namespace.command == "brief"
    assert brief_namespace.insight == "insight-adk-runner-centrality"
    assert brief_namespace.json is True
    assert brief_extra == []
    assert decision_namespace.command == "decision-pack"
    assert decision_namespace.insight == "insight-adk-runner-centrality"
    assert decision_namespace.json is True
    assert decision_extra == []


def test_module_cli_workflow_outputs_json(tmp_path: Path) -> None:
    install_real_repo_data(tmp_path, "insight-adk-runner-centrality")
    script = (
        "import json, sys; "
        "from pathlib import Path; "
        "from engine.transformer import generate_outputs; "
        "generate_outputs.NEW_PROJECT_PATH = Path(sys.argv[1]); "
        "from cognition_engine.cli import main; "
        "main(['workflow', '--insight', 'insight-adk-runner-centrality', '--json'])"
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
    assert payload["workflow_name"] == "insight-to-decision workflow"
