from __future__ import annotations

from engine.analyzer.generate_adk_probe_execution_evidence_index import (
    DEFAULT_FRAMEWORK_ID,
    INDEXES_DIR,
    REPORTS_DIR,
    build_index_payload,
    build_record,
    collect_records,
    infer_probe_family,
    load_json,
    resolve_output_path,
)


def test_resolve_output_path_defaults_to_framework_index_file() -> None:
    output_path = resolve_output_path(None, DEFAULT_FRAMEWORK_ID)

    assert output_path == INDEXES_DIR / DEFAULT_FRAMEWORK_ID / "index.json"


def test_infer_probe_family_supports_runtime_and_structured_output() -> None:
    assert infer_probe_family("engine/analyzer/probe_adk_runtime.py") == "runtime"
    assert (
        infer_probe_family(
            "engine/analyzer/probe_adk_single_agent_structured_output_failure.py"
        )
        == "structured output"
    )


def test_build_record_derives_record_id_and_probe_family_from_real_report() -> None:
    report_path = next(REPORTS_DIR.glob("adk-runtime-minimal-probe-*.json"))
    payload = load_json(report_path)

    record = build_record(report_path, payload)

    assert record["record_id"] == report_path.stem
    assert record["probe_family"] == "runtime"
    assert record["engine_entry"] == "engine/analyzer/probe_adk_runtime.py"
    assert record["report_file"] == f"reports/{report_path.name}"


def test_collect_records_real_data_matches_minimal_index_contract() -> None:
    records = collect_records(DEFAULT_FRAMEWORK_ID)
    payload = build_index_payload(DEFAULT_FRAMEWORK_ID, records)
    required_fields = {
        "record_id",
        "framework_id",
        "probe_id",
        "probe_family",
        "capability_surface",
        "engine_entry",
        "result",
        "started_at",
        "completed_at",
        "duration_seconds",
        "boundary_judgement",
        "report_file",
    }

    assert payload["record_count"] == len(records)
    assert len(records) >= 29
    assert all(set(record) == required_fields for record in records)
    assert all(record["report_file"].startswith("reports/") for record in records)
    assert {record["probe_family"] for record in records} >= {
        "runtime",
        "workflow",
        "agent runtime result",
        "single agent tool call",
        "artifact",
        "structured output",
    }
