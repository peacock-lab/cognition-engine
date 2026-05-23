from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from behavior_contracts import external_readonly_archive, external_readonly_evidence
from behavior_contracts.external_readonly_archive import (
    build_external_readonly_fetch_evidence_archive,
    external_readonly_fetch_output_boundary_violated,
    sanitize_external_readonly_fetch_output,
)
from behavior_contracts.external_readonly_evidence import (
    EXTERNAL_READONLY_EVIDENCE_OBSERVATION_REF_PREFIX,
    EXTERNAL_READONLY_EVIDENCE_READ_CONTEXT_INVALID_STATUS_REASON,
    EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_PAYLOAD_TYPE,
    EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_VERSION,
    ExternalReadonlyEvidenceReadonlyPublicRefs,
    build_external_readonly_evidence_read_context,
    build_external_readonly_evidence_readonly_facts,
    build_external_readonly_evidence_readonly_public_refs,
    build_external_readonly_evidence_readonly_public_refs_from_read_context,
    external_readonly_evidence_read_context_status_dict,
    external_readonly_evidence_readonly_public_refs_status_dict,
    read_external_readonly_evidence_summary,
    validate_external_readonly_evidence_readonly_public_refs,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
BEHAVIOR_CONTRACTS_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "behavior_contracts" / "src" / "behavior_contracts"
)
EXTERNAL_READONLY_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "external_readonly" / "src" / "external_readonly"
)
RUNTIME_EXTERNAL_READONLY_SOURCE_ROOT = (
    REPO_ROOT
    / "packages"
    / "runtime_container"
    / "src"
    / "runtime_container"
    / "external_readonly"
)
TASK_WORKFLOWS_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "operation_flows" / "src" / "cognition_operation_flows"
)
_EVIDENCE_OUTPUT_PATH = "outputs/external-readonly/cli-fetch/example.json"
_EVIDENCE_REF = "evidence://external-readonly/cli-fetch/example.json"


def test_behavior_contracts_exports_external_readonly_evidence_contracts() -> None:
    assert external_readonly_archive.build_external_readonly_fetch_evidence_archive is (
        build_external_readonly_fetch_evidence_archive
    )
    assert external_readonly_evidence.read_external_readonly_evidence_summary is (
        read_external_readonly_evidence_summary
    )


def test_external_readonly_contract_reads_archived_evidence_without_network(
    tmp_path: Path,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/example.json"
    target = tmp_path / evidence_path
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(_valid_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )

    summary = read_external_readonly_evidence_summary(
        evidence_path,
        repo_root=tmp_path,
    )
    context = build_external_readonly_evidence_read_context(
        (evidence_path,),
        repo_root=tmp_path,
    )
    status = external_readonly_evidence_read_context_status_dict(context)

    assert summary.status == "ready"
    assert summary.reference_review_ready is True
    assert summary.evidence_ref == (
        "evidence://external-readonly/cli-fetch/example.json"
    )
    assert context.status == "ready"
    assert status["metadata"]["does_not_access_network"] is True
    assert status["metadata"]["does_not_write_files"] is True
    assert status["summaries"][0]["sanitized_excerpt_preview"] == _excerpt()


def test_external_readonly_readonly_public_refs_contract_is_sanitized() -> None:
    facts = build_external_readonly_evidence_readonly_facts(
        observation_candidate_ids=("observation-1", "observation-1"),
        evidence_output_paths=(_EVIDENCE_OUTPUT_PATH,),
        evidence_refs=(_EVIDENCE_REF,),
        source_urls=("https://example.com/reference",),
        status="ready",
        reference_review_ready=True,
        allowed_for_model_context=True,
        candidate_count=1,
        blocking_reasons=(),
        warnings=("reference-review-ready",),
        metadata_keys=(
            "config_context",
            "source",
            "sanitized_excerpt_preview",
            "response_headers",
        ),
        raw_boundary_flags={
            "raw_response_included": False,
            "raw_html_included": False,
            "response_headers_included": False,
        },
        metadata={
            "source": "unit-test",
            "config_context": {"token": "must-not-leak"},
            "object_module": "runtime_container.secret",
            "safe_nested": {"not": "included"},
        },
    )
    public_refs = build_external_readonly_evidence_readonly_public_refs(
        external_readonly_evidence_observation_refs=(
            f"{EXTERNAL_READONLY_EVIDENCE_OBSERVATION_REF_PREFIX}observation-1",
        ),
        external_readonly_evidence_refs=(_EVIDENCE_REF,),
        facts=facts,
        metadata={
            "source": "unit-test",
            "authorization": "must-not-leak",
            "object_module": "observability_hub.internal",
        },
    )
    status = external_readonly_evidence_readonly_public_refs_status_dict(
        public_refs
    )
    serialized = json.dumps(status, ensure_ascii=False, sort_keys=True)

    assert isinstance(public_refs, ExternalReadonlyEvidenceReadonlyPublicRefs)
    assert status["payload_type"] == (
        EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_PAYLOAD_TYPE
    )
    assert status["payload_version"] == (
        EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_VERSION
    )
    assert status["external_readonly_evidence_refs"] == [_EVIDENCE_REF]
    assert status["external_readonly_evidence_readonly_facts"][
        "observation_candidate_ids"
    ] == ["observation-1"]
    assert status["external_readonly_evidence_readonly_facts"][
        "metadata_keys"
    ] == ["config_context", "source"]
    assert status["external_readonly_evidence_readonly_facts"][
        "metadata"
    ] == {"source": "unit-test"}
    assert status["metadata"] == {"source": "unit-test"}
    assert "must-not-leak" not in serialized
    assert "sanitized_excerpt_preview" not in serialized
    assert "response_headers" not in status[
        "external_readonly_evidence_readonly_facts"
    ]["metadata_keys"]
    assert "runtime_container.secret" not in serialized
    assert "observability_hub.internal" not in serialized


def test_read_context_to_readonly_public_refs_preserves_twf_refs_semantics() -> None:
    public_refs = build_external_readonly_evidence_readonly_public_refs_from_read_context(
        {
            "status": "ready",
            "reference_review_ready": True,
            "evidence_output_paths": (_EVIDENCE_OUTPUT_PATH,),
            "evidence_refs": (_EVIDENCE_REF,),
            "source_urls": ("https://example.com/reference",),
            "warnings": ("reference_review_ready",),
            "summaries": (
                {
                    "sanitized_excerpt_preview": "config-secret excerpt",
                    "raw_response": "raw-response-secret-value",
                    "raw_response_included": True,
                    "raw_html_included": False,
                    "response_headers_included": True,
                },
                {
                    "sanitized_excerpt_preview": "second secret excerpt",
                    "raw_response_included": False,
                    "raw_html_included": False,
                    "response_headers_included": False,
                },
            ),
            "metadata": {
                "source": "unit-test",
                "config_context": {"token": "config-secret-value"},
                "raw_payload": "raw-response-secret-value",
            },
        },
        metadata={"source": "unit-test"},
    )
    status = external_readonly_evidence_readonly_public_refs_status_dict(
        public_refs
    )
    facts = status["external_readonly_evidence_readonly_facts"]
    serialized = json.dumps(status, ensure_ascii=False, sort_keys=True)

    assert status["external_readonly_evidence_observation_refs"] == []
    assert status["external_readonly_evidence_refs"] == [_EVIDENCE_REF]
    assert facts["status"] == "ready"
    assert facts["reference_review_ready"] is True
    assert facts["allowed_for_model_context"] is True
    assert facts["candidate_count"] == 2
    assert facts["warnings"] == ["reference_review_ready"]
    assert facts["metadata_keys"] == ["source"]
    assert facts["raw_boundary_flags"] == {
        "raw_response_included": True,
        "raw_html_included": False,
        "response_headers_included": True,
    }
    assert facts["metadata"] == {"source": "unit-test"}
    assert status["metadata"] == {"source": "unit-test"}
    assert "sanitized_excerpt_preview" not in serialized
    assert "config-secret-value" not in serialized
    assert "raw-response-secret-value" not in serialized
    assert "config_context" not in serialized


def test_read_context_to_readonly_public_refs_handles_status_edges() -> None:
    cases = (
        ("blocked", False, "blocked", False, 1),
        ("mixed", False, "mixed", False, 1),
        ("empty", True, "empty", False, 0),
    )

    for raw_status, ready, expected_status, allowed, expected_count in cases:
        public_refs = (
            build_external_readonly_evidence_readonly_public_refs_from_read_context(
                {
                    "status": raw_status,
                    "reference_review_ready": ready,
                    "evidence_output_paths": (_EVIDENCE_OUTPUT_PATH,),
                    "evidence_refs": (_EVIDENCE_REF,),
                    "source_urls": ("https://example.com/reference",),
                    "summaries": (
                        {
                            "raw_response_included": False,
                            "raw_html_included": False,
                            "response_headers_included": False,
                        },
                    ),
                    "blocking_reasons": ("evidence_file_missing",),
                }
            )
        )
        status = external_readonly_evidence_readonly_public_refs_status_dict(
            public_refs
        )
        facts = status["external_readonly_evidence_readonly_facts"]

        assert facts["status"] == expected_status
        assert facts["allowed_for_model_context"] is allowed
        assert facts["candidate_count"] == expected_count
        assert status["external_readonly_evidence_observation_refs"] == []
        if expected_status == "empty":
            assert status["external_readonly_evidence_refs"] == []
            assert facts["evidence_output_paths"] == []
            assert facts["source_urls"] == []
        else:
            assert status["external_readonly_evidence_refs"] == [_EVIDENCE_REF]


def test_read_context_to_readonly_public_refs_blocks_invalid_status() -> None:
    public_refs = build_external_readonly_evidence_readonly_public_refs_from_read_context(
        {
            "status": "unexpected",
            "reference_review_ready": True,
            "evidence_output_paths": (_EVIDENCE_OUTPUT_PATH,),
            "evidence_refs": (_EVIDENCE_REF,),
            "source_urls": ("https://example.com/reference",),
            "blocking_reasons": ("already_blocked",),
        }
    )
    status = external_readonly_evidence_readonly_public_refs_status_dict(
        public_refs
    )
    facts = status["external_readonly_evidence_readonly_facts"]

    assert facts["status"] == "blocked"
    assert facts["allowed_for_model_context"] is False
    assert facts["candidate_count"] == 1
    assert facts["blocking_reasons"] == [
        "already_blocked",
        EXTERNAL_READONLY_EVIDENCE_READ_CONTEXT_INVALID_STATUS_REASON,
    ]
    assert status["external_readonly_evidence_refs"] == [_EVIDENCE_REF]
    assert status["external_readonly_evidence_observation_refs"] == []


def test_external_readonly_readonly_public_refs_validate_rejects_bad_refs() -> None:
    facts = build_external_readonly_evidence_readonly_facts(
        observation_candidate_ids=("observation-1",),
        evidence_output_paths=(_EVIDENCE_OUTPUT_PATH,),
        evidence_refs=(_EVIDENCE_REF,),
        source_urls=("https://example.com/reference",),
        status="ready",
        reference_review_ready=True,
        allowed_for_model_context=True,
        candidate_count=1,
    )
    public_refs = build_external_readonly_evidence_readonly_public_refs(
        external_readonly_evidence_observation_refs=(
            f"{EXTERNAL_READONLY_EVIDENCE_OBSERVATION_REF_PREFIX}observation-1",
        ),
        external_readonly_evidence_refs=(_EVIDENCE_REF,),
        facts=facts,
    )
    status = external_readonly_evidence_readonly_public_refs_status_dict(
        public_refs
    )
    status["external_readonly_evidence_refs"] = ["file://raw.json"]

    try:
        validate_external_readonly_evidence_readonly_public_refs(status)
    except ValueError as exc:
        assert "external_readonly_evidence_refs" in str(exc)
    else:
        raise AssertionError("bad evidence refs must be rejected")


def test_external_readonly_archive_contract_builds_sanitized_payload_without_writing(
    tmp_path: Path,
) -> None:
    evidence_output = "outputs/external-readonly/cli-fetch/archive.json"
    output = {
        "status": "success",
        "success": True,
        "blocking_reasons": [],
        "runtime": {
            "sanitized_excerpt_preview": "safe text",
            "response_headers": {"set-cookie": "must not leak"},
        },
        "raw_response": "<html>raw</html>",
    }

    archived = build_external_readonly_fetch_evidence_archive(
        output,
        root=tmp_path,
        evidence_output=evidence_output,
    )
    target = tmp_path / evidence_output

    assert archived["status"] == "success"
    assert archived["evidence_written"] is True
    assert archived["evidence_output_path"] == evidence_output
    assert archived["evidence_ref"] == (
        "evidence://external-readonly/cli-fetch/archive.json"
    )
    assert "raw_response" not in archived
    assert "response_headers" not in archived["runtime"]
    assert target.exists() is False
    assert external_readonly_fetch_output_boundary_violated(archived) is False


def test_external_readonly_archive_contract_blocks_unsafe_path_without_writing(
    tmp_path: Path,
) -> None:
    archived = build_external_readonly_fetch_evidence_archive(
        {"status": "success", "success": True, "blocking_reasons": []},
        root=tmp_path,
        evidence_output="outputs/external-readonly/../leak.json",
    )

    assert archived["status"] == "blocked"
    assert archived["evidence_written"] is False
    assert "evidence_output_path_unsafe" in archived["blocking_reasons"]
    assert not (tmp_path / "outputs" / "leak.json").exists()


def test_external_readonly_summary_archive_have_no_compatibility_facades() -> None:
    assert not (
        RUNTIME_EXTERNAL_READONLY_SOURCE_ROOT / "evidence_summary.py"
    ).exists()
    assert not (
        RUNTIME_EXTERNAL_READONLY_SOURCE_ROOT / "evidence_archive.py"
    ).exists()
    assert not (
        TASK_WORKFLOWS_SOURCE_ROOT / "twf_external_readonly_evidence_summary.py"
    ).exists()
    assert not (EXTERNAL_READONLY_SOURCE_ROOT / "evidence_summary.py").exists()
    assert not (EXTERNAL_READONLY_SOURCE_ROOT / "evidence_archive.py").exists()


def test_external_readonly_summary_archive_contracts_keep_contract_boundary() -> None:
    summary_source = (
        BEHAVIOR_CONTRACTS_SOURCE_ROOT / "external_readonly_evidence.py"
    ).read_text(encoding="utf-8")
    archive_source = (
        BEHAVIOR_CONTRACTS_SOURCE_ROOT / "external_readonly_archive.py"
    ).read_text(encoding="utf-8")
    serialized = summary_source + archive_source
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:external_readonly|cognition_operation_flows|cognition_cli|"
        r"composition|observability_hub|product_gateway|runtime_container|"
        r"google\.adk|litellm|"
        r"urllib\.request|requests|httpx)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(serialized) is None
    assert "write_text" not in archive_source
    assert "mkdir" not in archive_source
    assert "does_not_access_network" in summary_source


def test_external_readonly_archive_contract_sanitizer_rejects_raw_keys() -> None:
    sanitized = sanitize_external_readonly_fetch_output(
        {
            "runtime": {
                "sanitized_excerpt_preview": "safe text",
                "response_headers": {"set-cookie": "must not leak"},
            },
            "raw_provider_response": {"body": "raw"},
        }
    )

    assert sanitized == {"runtime": {"sanitized_excerpt_preview": "safe text"}}
    assert external_readonly_fetch_output_boundary_violated(
        {"runtime": {"response_headers": {}}}
    ) is True


def _valid_archive(evidence_path: str) -> dict[str, object]:
    return {
        "allow_runtime_fetch": True,
        "allowed_for_model_context": True,
        "blocking_reasons": [],
        "command": "cognition external-readonly fetch",
        "evidence_output_path": evidence_path,
        "evidence_ref": (
            "evidence://external-readonly/"
            f"{Path(evidence_path).relative_to('outputs/external-readonly')}"
        ),
        "evidence_written": True,
        "external_network_call_performed": True,
        "raw_html_included": False,
        "raw_response_included": False,
        "response_headers_included": False,
        "runtime": {
            "allowed_for_model_context": True,
            "blocking_reasons": [],
            "content_hash": _hash(_excerpt()),
            "external_network_call_performed": True,
            "runtime_fetch_performed": True,
            "sanitized_excerpt_preview": _excerpt(),
            "source_urls": ["https://example.com/"],
            "status": "completed",
            "total_excerpt_chars": len(_excerpt()),
            "transport_called": True,
            "warnings": [],
        },
        "runtime_fetch_performed": True,
        "source_url": "https://example.com/",
        "status": "success",
        "success": True,
        "transport_called": True,
        "uploads_content": False,
        "writes_files": False,
    }


def _excerpt() -> str:
    return "Example Domain sanitized excerpt for reference review."


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
