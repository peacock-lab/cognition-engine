from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.run_adk_single_agent_structured_output_evidence_trace import (  # noqa: E402
    CAPABILITY_ID,
    DEFAULT_MATRIX_CELL_ID,
    ENTRY_ID,
    FORMAL_ENTRY_REFERENCE,
    MATRIX_SCOPE_IDS,
    OUTPUTS_DIR,
    build_formal_entry_links,
    build_matrix_overview,
    build_selected_trace,
    build_success_payload,
    resolve_output_path,
)


def test_resolve_output_path_defaults_to_structured_output_directory() -> None:
    output_path = resolve_output_path(None)

    assert output_path.parent == OUTPUTS_DIR
    assert output_path.name.startswith(f"{ENTRY_ID}-")
    assert output_path.suffix == ".json"


def test_build_selected_trace_for_m02_contains_formal_links() -> None:
    selected_trace = build_selected_trace(DEFAULT_MATRIX_CELL_ID)

    assert selected_trace["matrix_cell_id"] == "M-02"
    assert selected_trace["task_id"] == "023"
    assert selected_trace["all_assets_exist"] is True
    assert [asset["asset_type"] for asset in selected_trace["assets"]] == [
        "task_package",
        "result_package",
        "probe",
        "test",
        "report",
    ]
    assert [link["capability_id"] for link in selected_trace["formal_entry_links"]] == [
        "CA-02",
        "CA-03",
    ]


def test_build_matrix_overview_covers_all_cells() -> None:
    overview = build_matrix_overview()

    assert len(overview) == len(MATRIX_SCOPE_IDS)
    assert [record["matrix_cell_id"] for record in overview] == MATRIX_SCOPE_IDS
    assert all(record["all_assets_exist"] is True for record in overview)


def test_build_success_payload_marks_evidence_trace_as_established() -> None:
    output_path = project_root / "outputs" / "structured_output" / "formal-evidence-trace.json"
    trace_result = {
        "selected_trace": build_selected_trace(DEFAULT_MATRIX_CELL_ID),
        "matrix_overview": build_matrix_overview(),
        "related_formal_assets": [],
    }

    payload = build_success_payload(
        started_at="2026-04-17T05:00:00Z",
        completed_at="2026-04-17T05:00:01Z",
        duration_seconds=1.23456,
        selected_matrix_cell_id=DEFAULT_MATRIX_CELL_ID,
        output_path=output_path,
        trace_result=trace_result,
    )

    assert payload["result"] == "success"
    assert payload["capability_id"] == CAPABILITY_ID
    assert payload["matrix_cell_id"] == DEFAULT_MATRIX_CELL_ID
    assert payload["matrix_scope_ids"] == MATRIX_SCOPE_IDS
    assert payload["formal_evidence_trace_established"] is True
    assert payload["selected_trace_assets_complete"] is True
    assert payload["matrix_trace_total_count"] == 12
    assert payload["matrix_trace_coverage_count"] == 12
    assert payload["formal_entry_reference"] == FORMAL_ENTRY_REFERENCE
    assert payload["output_file"] == "outputs/structured_output/formal-evidence-trace.json"
    assert payload["duration_seconds"] == 1.2346
    assert "CA-04" in payload["boundary_judgement"]


def test_build_formal_entry_links_for_non_formalized_cells_is_empty() -> None:
    assert build_formal_entry_links("M-03") == []
