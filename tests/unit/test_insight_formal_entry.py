#!/usr/bin/env python3
"""Insight formal-entry helper tests."""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.insight_formal_entry import (  # noqa: E402
    build_insight_formal_entry_record,
    inspect_insight_formal_entry,
)


def sample_insight() -> dict:
    return {
        "id": "insight-demo",
        "framework_id": "adk-2.0.0a3",
        "type": "architectural_pattern",
        "category": "core_coordination",
        "title": "Demo insight",
        "description": "Demo description",
        "confidence": 0.9,
        "impact": {
            "architectural": "high",
            "migration": "medium",
            "product": "low",
        },
        "tags": ["demo"],
        "evidence": [
            {
                "type": "documentation_reference",
                "source_file": "core_runtime_map",
                "source_section": "6. 主链",
                "quote": "extra quote should remain in detail layer",
            }
        ],
        "connections": [
            {
                "insight_id": "insight-other",
                "type": "depends_on",
                "strength": 0.8,
                "description": "demo relation",
                "notes": "extra notes should remain in detail layer",
            }
        ],
        "extracted_from": ["anchor_evidence_package"],
    }


def test_build_insight_formal_entry_record_keeps_root_direct_layout() -> None:
    normalized = build_insight_formal_entry_record(sample_insight())

    assert list(normalized.keys())[:11] == [
        "id",
        "framework_id",
        "type",
        "category",
        "title",
        "description",
        "confidence",
        "impact",
        "tags",
        "evidence",
        "connections",
    ]
    assert list(normalized["evidence"][0].keys())[:3] == [
        "type",
        "source_file",
        "source_section",
    ]
    assert normalized["evidence"][0]["quote"] == "extra quote should remain in detail layer"
    assert list(normalized["connections"][0].keys())[:4] == [
        "insight_id",
        "type",
        "strength",
        "description",
    ]
    assert normalized["connections"][0]["notes"] == "extra notes should remain in detail layer"


def test_inspect_insight_formal_entry_reports_missing_minimal_fields() -> None:
    broken = sample_insight()
    del broken["evidence"][0]["source_section"]

    checks = inspect_insight_formal_entry(broken)

    assert checks["has_evidence"] is True
    assert checks["evidence_formal_fields_complete"] is False


def test_build_insight_formal_entry_record_rejects_missing_formal_fields() -> None:
    broken = sample_insight()
    del broken["connections"][0]["description"]

    try:
        build_insight_formal_entry_record(broken)
    except ValueError as exc:
        assert "connections_formal_fields_complete" in str(exc)
    else:
        raise AssertionError("expected ValueError for incomplete connection formal-entry fields")
