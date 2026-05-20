from __future__ import annotations

import re
from pathlib import Path

from behavior_contracts.external_readonly_governed_summary_facts import (
    validate_external_readonly_governed_summary_facts_guards,
)
from contract_core import external_readonly_governed_summary_facts
from schemas.external_readonly_governed_summary_facts import (
    ExternalReadonlyGovernedSummaryFactsSchema,
    validate_external_readonly_governed_summary_facts,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_CORE_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "contract_core" / "src" / "contract_core"
)


def test_contract_core_reexports_governed_summary_facts_contracts() -> None:
    assert (
        external_readonly_governed_summary_facts.ExternalReadonlyGovernedSummaryFactsSchema
        is ExternalReadonlyGovernedSummaryFactsSchema
    )
    assert (
        external_readonly_governed_summary_facts.validate_external_readonly_governed_summary_facts
        is validate_external_readonly_governed_summary_facts
    )
    assert (
        external_readonly_governed_summary_facts
        .validate_external_readonly_governed_summary_facts_guards
        is validate_external_readonly_governed_summary_facts_guards
    )


def test_contract_core_governed_summary_facts_facade_is_thin() -> None:
    source = (
        CONTRACT_CORE_SOURCE_ROOT / "external_readonly_governed_summary_facts.py"
    ).read_text(encoding="utf-8")
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:external_readonly|cognition_task_workflows|cognition_cli|"
        r"product_gateway|runtime_container|google\.adk|litellm|"
        r"urllib\.request|requests|httpx)\b",
        re.MULTILINE,
    )

    assert (
        "from schemas.external_readonly_governed_summary_facts import"
        in source
    )
    assert (
        "from behavior_contracts.external_readonly_governed_summary_facts import"
        in source
    )
    assert "dataclass" not in source
    assert "def " not in source
    assert "read_text" not in source
    assert "write_text" not in source
    assert "mkdir" not in source
    assert forbidden_imports.search(source) is None
