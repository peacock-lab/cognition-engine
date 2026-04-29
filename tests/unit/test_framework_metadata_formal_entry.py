#!/usr/bin/env python3
"""Framework metadata formal-entry helper tests."""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.framework_metadata_formal_entry import (  # noqa: E402
    build_framework_metadata_formal_entry_record,
    inspect_framework_metadata_formal_entry,
)


def sample_framework_metadata() -> dict:
    return {
        "id": "adk-2.0.0a3",
        "name": "Google Agent Development Kit",
        "version": "2.0.0a3",
        "type": "agent_framework",
        "repository": "/tmp/google-adk",
        "status": "under_analysis",
        "metadata": {
            "language": "python",
            "architecture_style": "runner_workflow",
            "primary_entry_points": ["src/google/adk/runners.py"],
            "core_modules": ["agents", "workflow"],
            "analysis_depth": "deep_audit_completed",
            "source_documents": [
                {
                    "source_id": "core_runtime_map",
                    "title": "Core runtime map",
                    "kind": "long_term_doc",
                    "path": "/tmp/core-runtime-map.md",
                    "note": "extra detail should remain in detail layer",
                }
            ],
            "input_channels": ["framework_learning_lab_result_packages"],
            "source": "framework-learning-lab migration",
        },
        "timestamps": {
            "first_analyzed": "2026-04-15",
            "last_updated": "2026-04-19",
            "next_review": "2026-05-01",
        },
        "version_schema": "1.1",
    }


def test_build_framework_metadata_formal_entry_record_keeps_root_direct_layout() -> None:
    normalized = build_framework_metadata_formal_entry_record(sample_framework_metadata())

    assert list(normalized.keys())[:8] == [
        "id",
        "name",
        "version",
        "type",
        "repository",
        "status",
        "metadata",
        "timestamps",
    ]
    assert list(normalized["metadata"].keys())[:7] == [
        "language",
        "architecture_style",
        "primary_entry_points",
        "core_modules",
        "analysis_depth",
        "source_documents",
        "input_channels",
    ]
    assert list(normalized["metadata"]["source_documents"][0].keys())[:4] == [
        "source_id",
        "title",
        "kind",
        "path",
    ]
    assert normalized["metadata"]["source_documents"][0]["note"] == (
        "extra detail should remain in detail layer"
    )
    assert list(normalized["timestamps"].keys())[:2] == [
        "first_analyzed",
        "last_updated",
    ]
    assert normalized["timestamps"]["next_review"] == "2026-05-01"
    assert normalized["metadata"]["source"] == "framework-learning-lab migration"
    assert normalized["version_schema"] == "1.1"


def test_inspect_framework_metadata_formal_entry_reports_missing_minimal_fields() -> None:
    broken = sample_framework_metadata()
    del broken["metadata"]["source_documents"][0]["path"]

    checks = inspect_framework_metadata_formal_entry(broken)

    assert checks["has_source_documents"] is True
    assert checks["source_documents_formal_fields_complete"] is False


def test_build_framework_metadata_formal_entry_record_rejects_missing_formal_fields() -> None:
    broken = sample_framework_metadata()
    del broken["timestamps"]["last_updated"]

    try:
        build_framework_metadata_formal_entry_record(broken)
    except ValueError as exc:
        assert "timestamps_formal_fields_complete" in str(exc)
    else:
        raise AssertionError(
            "expected ValueError for incomplete framework metadata formal-entry fields"
        )
