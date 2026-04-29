#!/usr/bin/env python3
"""本地项目连接器测试。"""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from connectors.import_local_project import build_connection_record, collect_project_stats


def test_collect_project_stats_detects_manifests_and_extensions(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("requests\n", encoding="utf-8")

    stats = collect_project_stats(tmp_path)

    assert stats["total_files"] == 3
    assert "requirements.txt" in stats["manifest_files"]
    assert any(item["extension"] == "py" for item in stats["dominant_extensions"])
    assert any(item["name"] == "src" for item in stats["top_level_directories"])


def test_build_connection_record_for_non_git_project(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    stats = collect_project_stats(tmp_path)
    git_context = {
        "is_git_repo": False,
        "repo_root": str(tmp_path),
        "current_branch": None,
        "is_dirty": False,
        "remotes": [],
        "recent_commits": [],
    }

    record = build_connection_record(
        project_path=tmp_path,
        project_stats=stats,
        git_context=git_context,
        framework_id="cross-framework",
        channel="local_project_snapshot",
        tags=["workspace", "project"],
    )

    assert record["type"] == "local_project"
    assert record["framework_id"] == "cross-framework"
    assert record["metadata"]["project"]["is_git_repo"] is False
    assert record["metadata"]["stats"]["manifest_count"] == 1
    assert len(record["project_snapshot"]["manifest_files"]) == 1


def test_build_connection_record_for_git_project_context(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name":"demo"}\n', encoding="utf-8")
    stats = collect_project_stats(tmp_path)
    git_context = {
        "is_git_repo": True,
        "repo_root": str(tmp_path),
        "current_branch": "main",
        "is_dirty": True,
        "remotes": [{"name": "origin", "urls": ["git@github.com:demo/repo.git"]}],
        "recent_commits": [
            {
                "sha": "abcdef123456",
                "summary": "Initial commit",
                "author": "tester",
                "committed_at": "2026-04-16T00:00:00Z",
            }
        ],
    }

    record = build_connection_record(
        project_path=tmp_path,
        project_stats=stats,
        git_context=git_context,
        framework_id="demo-framework",
        channel="local_project_snapshot",
        tags=["git", "repo"],
    )

    assert record["title"] == f"本地项目快照: {tmp_path.name}"
    assert record["metadata"]["project"]["current_branch"] == "main"
    assert record["metadata"]["project"]["is_dirty"] is True
    assert record["metadata"]["stats"]["recent_commits_collected"] == 1
    assert record["project_snapshot"]["git"]["remotes"][0]["name"] == "origin"
    assert "Initial commit" in record["content_summary"]
