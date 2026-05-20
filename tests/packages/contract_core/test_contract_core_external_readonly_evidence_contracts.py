from __future__ import annotations

import re
from pathlib import Path

from behavior_contracts.external_readonly_archive import (
    build_external_readonly_fetch_evidence_archive,
)
from behavior_contracts.external_readonly_evidence import (
    build_external_readonly_evidence_readonly_public_refs,
    build_external_readonly_evidence_readonly_public_refs_from_read_context,
    read_external_readonly_evidence_summary,
)
from contract_core import external_readonly_archive, external_readonly_evidence


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_CORE_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "contract_core" / "src" / "contract_core"
)


def test_contract_core_reexports_external_readonly_evidence_contracts() -> None:
    assert external_readonly_archive.build_external_readonly_fetch_evidence_archive is (
        build_external_readonly_fetch_evidence_archive
    )
    assert external_readonly_evidence.read_external_readonly_evidence_summary is (
        read_external_readonly_evidence_summary
    )
    assert (
        external_readonly_evidence.build_external_readonly_evidence_readonly_public_refs
        is build_external_readonly_evidence_readonly_public_refs
    )
    assert (
        external_readonly_evidence.build_external_readonly_evidence_readonly_public_refs_from_read_context
        is build_external_readonly_evidence_readonly_public_refs_from_read_context
    )


def test_contract_core_external_readonly_facades_are_thin() -> None:
    evidence_source = (
        CONTRACT_CORE_SOURCE_ROOT / "external_readonly_evidence.py"
    ).read_text(encoding="utf-8")
    archive_source = (
        CONTRACT_CORE_SOURCE_ROOT / "external_readonly_archive.py"
    ).read_text(encoding="utf-8")
    serialized = evidence_source + archive_source
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:external_readonly|cognition_task_workflows|cognition_cli|"
        r"product_gateway|runtime_container|google\.adk|litellm|"
        r"urllib\.request|requests|httpx)\b",
        re.MULTILINE,
    )

    assert "from behavior_contracts.external_readonly_evidence import" in evidence_source
    assert "from behavior_contracts.external_readonly_archive import" in archive_source
    assert "dataclass" not in serialized
    assert "def " not in serialized
    assert "read_text" not in serialized
    assert "write_text" not in serialized
    assert "mkdir" not in serialized
    assert forbidden_imports.search(serialized) is None
