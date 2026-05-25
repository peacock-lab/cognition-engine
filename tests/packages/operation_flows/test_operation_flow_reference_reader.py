from __future__ import annotations

from cognition_operation_flows._tools.reference_reader import (
    REFERENCE_READER_TOOL_NAME,
    OperationFlowReferenceReadRequestCandidate,
    build_default_reference_reader_policy,
    operation_flow_reference_read_status_dict,
    read_operation_flow_reference,
)


def test_reference_reader_reads_local_markdown_with_low_risk(tmp_path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    reference = docs_dir / "guide.md"
    reference.write_text("# Guide\nhello reference\n", encoding="utf-8")
    policy = build_default_reference_reader_policy(allowed_roots=(tmp_path,))

    result = read_operation_flow_reference(
        OperationFlowReferenceReadRequestCandidate(
            reference="docs/guide.md",
            policy=policy,
            task_run_id="run-334",
        )
    )
    status = operation_flow_reference_read_status_dict(result)

    assert result.allowed is True
    assert result.status == "succeeded"
    assert result.resolved_path == str(reference.resolve())
    assert result.reference_digest is not None
    assert len(result.reference_digest) == 64
    assert result.evidence_ref is not None
    assert result.evidence_ref.startswith("evidence://reference-reader/")
    assert result.risk_review is not None
    assert result.risk_review.risk_level == "low"
    assert result.risk_review.allowed_for_readonly is True
    assert result.risk_review.confirmation_required is False
    assert result.toolset_inventory is not None
    assert result.toolset_inventory.exposed_tool_names == (REFERENCE_READER_TOOL_NAME,)
    assert "1: # Guide" in result.content_excerpt
    assert status["tool"]["readonly_operation"] is True
    assert status["metadata"]["does_not_write_files"] is True
    assert status["metadata"]["does_not_access_network"] is True


def test_reference_reader_accepts_repo_relative_path_under_named_allowed_root(
    tmp_path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    reference = docs_dir / "guide.md"
    reference.write_text("# Guide\nrepo relative reference\n", encoding="utf-8")
    policy = build_default_reference_reader_policy(allowed_roots=(docs_dir,))

    result = read_operation_flow_reference(
        OperationFlowReferenceReadRequestCandidate(reference="docs/guide.md", policy=policy)
    )

    assert result.allowed is True
    assert result.status == "succeeded"
    assert result.resolved_path == str(reference.resolve())
    assert "repo relative reference" in result.content_excerpt


def test_reference_reader_blocks_absolute_path_outside_allowed_root(tmp_path) -> None:
    allowed_root = tmp_path / "allowed"
    outside_root = tmp_path / "outside"
    allowed_root.mkdir()
    outside_root.mkdir()
    outside = outside_root / "note.md"
    outside.write_text("outside", encoding="utf-8")
    policy = build_default_reference_reader_policy(allowed_roots=(allowed_root,))

    result = read_operation_flow_reference(
        OperationFlowReferenceReadRequestCandidate(reference=str(outside), policy=policy)
    )

    assert result.allowed is False
    assert result.status == "blocked"
    assert "reference_outside_allowed_roots" in result.blocking_reasons
    assert result.content_excerpt == ""


def test_reference_reader_reads_explicit_allowed_file_outside_allowed_roots(
    tmp_path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    project_file = tmp_path / "pyproject.toml"
    project_file.write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    policy = build_default_reference_reader_policy(
        allowed_roots=(docs_dir,),
        allowed_files=(project_file,),
    )

    result = read_operation_flow_reference(
        OperationFlowReferenceReadRequestCandidate(reference=str(project_file), policy=policy)
    )

    assert result.allowed is True
    assert result.status == "succeeded"
    assert result.resolved_path == str(project_file.resolve())
    assert "[project]" in result.content_excerpt
    assert result.metadata["allowed_files"] == [str(project_file.resolve())]


def test_reference_reader_blocks_parent_traversal(tmp_path) -> None:
    policy = build_default_reference_reader_policy(allowed_roots=(tmp_path,))

    result = read_operation_flow_reference(
        OperationFlowReferenceReadRequestCandidate(reference="../outside.md", policy=policy)
    )

    assert result.allowed is False
    assert "reference_path_traversal_not_allowed" in result.blocking_reasons


def test_reference_reader_blocks_forbidden_suffix_and_segment(tmp_path) -> None:
    script = tmp_path / "script.py"
    script.write_text("print('nope')", encoding="utf-8")
    blocked_dir = tmp_path / "node_modules"
    blocked_dir.mkdir()
    blocked_doc = blocked_dir / "readme.md"
    blocked_doc.write_text("blocked", encoding="utf-8")
    policy = build_default_reference_reader_policy(allowed_roots=(tmp_path,))

    suffix_result = read_operation_flow_reference(
        OperationFlowReferenceReadRequestCandidate(reference="script.py", policy=policy)
    )
    segment_result = read_operation_flow_reference(
        OperationFlowReferenceReadRequestCandidate(reference="node_modules/readme.md", policy=policy)
    )

    assert suffix_result.allowed is False
    assert "reference_suffix_not_allowed" in suffix_result.blocking_reasons
    assert segment_result.allowed is False
    assert "reference_forbidden_segment" in segment_result.blocking_reasons


def test_reference_reader_blocks_forbidden_path_marker(tmp_path) -> None:
    secret_file = tmp_path / ".env.example.md"
    secret_file.write_text("EXAMPLE=1", encoding="utf-8")
    policy = build_default_reference_reader_policy(allowed_roots=(tmp_path,))

    result = read_operation_flow_reference(
        OperationFlowReferenceReadRequestCandidate(reference=".env.example.md", policy=policy)
    )

    assert result.allowed is False
    assert "reference_forbidden_path_marker" in result.blocking_reasons


def test_reference_reader_redacts_sensitive_lines_from_excerpt(tmp_path) -> None:
    reference = tmp_path / "notes.md"
    reference.write_text(
        "safe line\napi_key: should-not-leak\nanother safe line\n",
        encoding="utf-8",
    )
    policy = build_default_reference_reader_policy(allowed_roots=(tmp_path,))

    result = read_operation_flow_reference(
        OperationFlowReferenceReadRequestCandidate(reference="notes.md", policy=policy)
    )
    status = operation_flow_reference_read_status_dict(result)

    assert result.allowed is True
    assert result.redacted_line_count == 1
    assert "reference_sensitive_lines_redacted" in result.warnings
    assert "should-not-leak" not in result.content_excerpt
    assert "[redacted sensitive reference line]" in result.content_excerpt
    assert "should-not-leak" not in status["read"]["content_excerpt"]


def test_reference_reader_applies_bounded_output_budgets(tmp_path) -> None:
    reference = tmp_path / "long.md"
    reference.write_text("0123456789\n" * 20, encoding="utf-8")
    policy = build_default_reference_reader_policy(
        allowed_roots=(tmp_path,),
        max_bytes=40,
        max_chars=18,
        max_excerpt_lines=2,
    )

    result = read_operation_flow_reference(
        OperationFlowReferenceReadRequestCandidate(reference="long.md", policy=policy)
    )

    assert result.allowed is True
    assert result.truncated is True
    assert "reference_bytes_truncated" in result.warnings
    assert "reference_excerpt_truncated" in result.warnings
    assert result.char_count <= 18
