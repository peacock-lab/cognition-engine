from __future__ import annotations

import json
from pathlib import Path

from composition import (
    ExternalReadonlyEvidenceReadonlyProductBundle,
    build_external_readonly_evidence_readonly_product_bundle,
)
from contract_core.external_readonly_evidence import (
    ExternalReadonlyEvidenceReadContext,
    ExternalReadonlyEvidenceReadonlyPublicRefs,
    ExternalReadonlyEvidenceSummary,
    external_readonly_evidence_read_context_status_dict,
    validate_external_readonly_evidence_readonly_public_refs,
)
from observability_hub import ExternalReadonlyEvidenceObservationCandidate


REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSITION_SOURCE_ROOT = REPO_ROOT / "packages" / "composition" / "src" / "composition"


def test_builds_readonly_bundle_from_read_context_dataclass() -> None:
    bundle = build_external_readonly_evidence_readonly_product_bundle(
        ExternalReadonlyEvidenceReadContext(
            status="ready",
            reference_review_ready=True,
            summaries=(_ready_summary(),),
            evidence_output_paths=(_EVIDENCE_OUTPUT_PATH,),
            evidence_refs=(_EVIDENCE_REF,),
            source_urls=("https://example.com/reference",),
        ),
        metadata={"test_case": "dataclass"},
    )

    assert isinstance(bundle, ExternalReadonlyEvidenceReadonlyProductBundle)
    assert len(bundle.observation_candidates) == 1
    assert isinstance(
        bundle.observation_candidates[0],
        ExternalReadonlyEvidenceObservationCandidate,
    )
    assert bundle.observation_candidates[0].status == "ready"
    assert bundle.observation_candidates[0].evidence_ref == _EVIDENCE_REF
    assert bundle.observation_candidates[0].source == (
        "observability_hub.external_readonly_evidence"
    )
    assert bundle.metadata["test_case"] == "dataclass"
    assert "config_context" not in bundle.metadata


def test_public_refs_are_compact_and_keep_layered_refs_distinct() -> None:
    bundle = build_external_readonly_evidence_readonly_product_bundle(
        ExternalReadonlyEvidenceReadContext(
            status="ready",
            reference_review_ready=True,
            summaries=(_ready_summary(),),
        )
    )

    refs = bundle.to_public_refs()
    contract = bundle.to_public_contract()
    facts = refs["external_readonly_evidence_readonly_facts"]

    assert isinstance(contract, ExternalReadonlyEvidenceReadonlyPublicRefs)
    validate_external_readonly_evidence_readonly_public_refs(contract)
    assert refs["payload_type"] == (
        "external_readonly_evidence_readonly_public_refs"
    )
    assert refs["payload_version"] == (
        "external_readonly_evidence_readonly_public_refs_v1"
    )
    assert refs["external_readonly_evidence_observation_refs"][0].startswith(
        "external-readonly-evidence-observation://"
        "external-readonly-evidence-observation-"
    )
    assert refs["external_readonly_evidence_refs"] == [_EVIDENCE_REF]
    assert facts["observation_candidate_ids"][0].startswith(
        "external-readonly-evidence-observation-"
    )
    assert facts["evidence_refs"] == [_EVIDENCE_REF]
    assert facts["evidence_output_paths"] == [_EVIDENCE_OUTPUT_PATH]
    assert facts["source_urls"] == ["https://example.com/reference"]
    assert facts["status"] == "ready"
    assert facts["reference_review_ready"] is True
    assert facts["allowed_for_model_context"] is True
    assert facts["candidate_count"] == 1
    assert facts["readonly"] is True
    assert facts["candidate_only"] is True
    assert facts["does_not_read_files"] is True
    assert facts["does_not_write_files"] is True
    assert facts["does_not_call_network"] is True
    assert facts["does_not_call_model"] is True
    assert facts["does_not_call_runtime"] is True
    assert "sanitized_excerpt_preview" not in facts


def test_builds_readonly_bundle_from_read_context_status_dict() -> None:
    context = ExternalReadonlyEvidenceReadContext(
        status="ready",
        reference_review_ready=True,
        summaries=(_ready_summary(),),
    )
    bundle = build_external_readonly_evidence_readonly_product_bundle(
        external_readonly_evidence_read_context_status_dict(context)
    )

    assert len(bundle.observation_candidates) == 1
    assert bundle.observation_candidates[0].evidence_output_path == (
        _EVIDENCE_OUTPUT_PATH
    )
    assert bundle.to_public_refs()[
        "external_readonly_evidence_readonly_facts"
    ]["status"] == "ready"


def test_mixed_status_preserves_blocking_reasons() -> None:
    bundle = build_external_readonly_evidence_readonly_product_bundle(
        ExternalReadonlyEvidenceReadContext(
            status="blocked",
            reference_review_ready=False,
            summaries=(
                _ready_summary("outputs/external-readonly/cli-fetch/one.json"),
                _blocked_summary(
                    "outputs/external-readonly/cli-fetch/missing.json"
                ),
            ),
        )
    )

    facts = bundle.to_public_refs()["external_readonly_evidence_readonly_facts"]

    assert facts["status"] == "mixed"
    assert facts["reference_review_ready"] is False
    assert facts["allowed_for_model_context"] is False
    assert facts["candidate_count"] == 2
    assert facts["blocking_reasons"] == ["evidence_file_missing"]


def test_blocked_status_is_used_when_all_candidates_are_blocked() -> None:
    bundle = build_external_readonly_evidence_readonly_product_bundle(
        ExternalReadonlyEvidenceReadContext(
            status="blocked",
            reference_review_ready=False,
            summaries=(_blocked_summary(_EVIDENCE_OUTPUT_PATH),),
        )
    )

    facts = bundle.to_public_refs()["external_readonly_evidence_readonly_facts"]

    assert facts["status"] == "blocked"
    assert facts["blocking_reasons"] == ["evidence_file_missing"]


def test_empty_read_context_returns_empty_public_refs() -> None:
    bundle = build_external_readonly_evidence_readonly_product_bundle(
        ExternalReadonlyEvidenceReadContext(
            status="empty",
            reference_review_ready=False,
        )
    )

    refs = bundle.to_public_refs()
    facts = refs["external_readonly_evidence_readonly_facts"]

    assert refs["external_readonly_evidence_observation_refs"] == []
    assert refs["external_readonly_evidence_refs"] == []
    assert facts["status"] == "empty"
    assert facts["candidate_count"] == 0
    assert facts["reference_review_ready"] is False
    assert facts["allowed_for_model_context"] is False
    assert facts["raw_boundary_flags"] == {
        "raw_response_included": False,
        "raw_html_included": False,
        "response_headers_included": False,
    }


def test_public_refs_do_not_expose_raw_payload_or_config_context_values() -> None:
    bundle = build_external_readonly_evidence_readonly_product_bundle(
        {
            "status": "blocked",
            "reference_review_ready": False,
            "summaries": [
                {
                    "evidence_output_path": _EVIDENCE_OUTPUT_PATH,
                    "status": "blocked",
                    "reference_review_ready": False,
                    "raw_response_included": True,
                    "raw_html_included": True,
                    "response_headers_included": True,
                    "blocking_reasons": ["raw_response_forbidden"],
                    "metadata": {
                        "config_context": {
                            "token": "config-context-token-value",
                        },
                        "source": "test",
                    },
                    "raw_response": "raw-response-secret-value",
                    "raw_html": "<html>raw-html-secret-value</html>",
                    "response_headers": {
                        "set-cookie": "cookie-header-value",
                    },
                }
            ],
        },
        metadata={
            "test_case": "raw-boundary",
            "config_context": {
                "token": "bundle-config-context-token-value",
            },
            "authorization": "authorization-header-value",
            "safe_nested": {"not": "included"},
        },
    )

    refs = bundle.to_public_refs()
    facts = refs["external_readonly_evidence_readonly_facts"]
    serialized = json.dumps(refs, ensure_ascii=False, sort_keys=True)

    assert facts["raw_boundary_flags"] == {
        "raw_response_included": True,
        "raw_html_included": True,
        "response_headers_included": True,
    }
    assert facts["metadata_keys"] == ["config_context", "source"]
    assert facts["metadata"]["test_case"] == "raw-boundary"
    assert "sanitized_excerpt_preview" not in serialized
    assert "config-context-token-value" not in serialized
    assert "bundle-config-context-token-value" not in serialized
    assert "authorization-header-value" not in serialized
    assert "raw-response-secret-value" not in serialized
    assert "raw-html-secret-value" not in serialized
    assert "cookie-header-value" not in serialized


def test_root_public_surface_exports_external_readonly_readonly_bundle() -> None:
    assert ExternalReadonlyEvidenceReadonlyProductBundle.__name__ == (
        "ExternalReadonlyEvidenceReadonlyProductBundle"
    )
    assert callable(
        build_external_readonly_evidence_readonly_product_bundle
    )


def test_readonly_assembly_source_does_not_execute_or_import_runtime_layers() -> None:
    source = (
        COMPOSITION_SOURCE_ROOT
        / "external_readonly_evidence_readonly_assembly.py"
    ).read_text(encoding="utf-8")
    forbidden_call_markers = (
        "." + "invoke" + "(",
        "service" + "." + "invoke",
        "completion" + "(",
        "acompletion" + "(",
        "runner" + "." + "run",
        "run" + "_async",
    )
    forbidden_import_markers = (
        "from " + "runtime_container",
        "import " + "runtime_container",
        "from " + "runtime ",
        "import " + "runtime ",
        "from " + "adk_adapter",
        "import " + "adk_adapter",
        "google" + "." + "adk",
        "from " + "external_readonly",
        "import " + "external_readonly",
    )

    for forbidden in forbidden_call_markers + forbidden_import_markers:
        assert forbidden not in source


_EVIDENCE_OUTPUT_PATH = "outputs/external-readonly/cli-fetch/example.json"
_EVIDENCE_REF = "evidence://external-readonly/cli-fetch/example.json"


def _ready_summary(
    evidence_output_path: str = _EVIDENCE_OUTPUT_PATH,
) -> ExternalReadonlyEvidenceSummary:
    relative_name = evidence_output_path.rsplit("/", 1)[-1]
    return ExternalReadonlyEvidenceSummary(
        evidence_output_path=evidence_output_path,
        status="ready",
        reference_review_ready=True,
        evidence_ref=f"evidence://external-readonly/cli-fetch/{relative_name}",
        source_url="https://example.com/reference",
        runtime_status="completed",
        allowed_for_model_context=True,
        evidence_written=True,
        runtime_fetch_performed=True,
        transport_called=True,
        external_network_call_performed=True,
        raw_response_included=False,
        raw_html_included=False,
        response_headers_included=False,
        uploads_content=False,
        writes_files=False,
        content_hash="sha256-safe",
        sanitized_excerpt_preview="safe excerpt",
        total_excerpt_chars=len("safe excerpt"),
        metadata={
            "does_not_access_network": True,
            "does_not_write_files": True,
            "does_not_call_model": True,
            "config_context": {
                "token": "config-context-token-value",
            },
        },
    )


def _blocked_summary(
    evidence_output_path: str,
) -> ExternalReadonlyEvidenceSummary:
    return ExternalReadonlyEvidenceSummary(
        evidence_output_path=evidence_output_path,
        status="blocked",
        reference_review_ready=False,
        blocking_reasons=("evidence_file_missing",),
        warnings=("reference_review_unavailable",),
        metadata={"controlled_path_review": "passed"},
    )
