from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_CONTEXTS_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "config_contexts" / "src" / "config_contexts"
)


def test_config_contexts_source_does_not_import_adk_adapter_or_google_adk() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+(?:adk_adapter|google\.adk)\b",
        re.MULTILINE,
    )

    for source_path in CONFIG_CONTEXTS_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path
