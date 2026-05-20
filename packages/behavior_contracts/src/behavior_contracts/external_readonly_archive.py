"""Pure archive helpers for external-readonly CLI evidence outputs."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any


EXTERNAL_READONLY_FETCH_ARCHIVE_CONTROLLED_ROOT = (
    "outputs/external-readonly/cli-fetch"
)
EXTERNAL_READONLY_FETCH_ARCHIVE_REF_PREFIX = (
    "evidence://external-readonly/cli-fetch/"
)
EXTERNAL_READONLY_FETCH_ARCHIVE_FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        "authorization",
        "content",
        "cookie",
        "credential",
        "credentials",
        "full_page_content",
        "html",
        "message",
        "messages",
        "password",
        "payload",
        "private_key",
        "provider_payload",
        "provider_response",
        "raw",
        "raw_body",
        "raw_html",
        "raw_network_response",
        "raw_payload",
        "raw_provider_payload",
        "raw_provider_response",
        "raw_request_payload",
        "raw_response",
        "response",
        "response_body",
        "response_headers",
        "response_text",
        "secret",
        "service_account_json",
        "session",
        "token",
    }
)


def build_external_readonly_fetch_evidence_archive(
    output: Mapping[str, Any],
    *,
    root: Path,
    evidence_output: str,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Build a sanitized archive payload without writing it to disk."""

    payload = sanitize_external_readonly_fetch_output(output)
    issue = validate_external_readonly_fetch_evidence_output_path(
        root=root,
        evidence_output=evidence_output,
        overwrite=overwrite,
    )
    if issue:
        return external_readonly_fetch_evidence_output_blocked_payload(
            payload,
            evidence_output=evidence_output,
            issue=issue,
        )

    relative_path = Path(evidence_output)
    return {
        **payload,
        "evidence_written": True,
        "evidence_output_path": relative_path.as_posix(),
        "evidence_ref": external_readonly_fetch_evidence_ref_for_output(
            relative_path
        ),
    }


def validate_external_readonly_fetch_evidence_output_path(
    *,
    root: Path,
    evidence_output: str,
    overwrite: bool = False,
) -> str | None:
    """Return a blocking reason if the evidence output path is not controlled."""

    path = Path(evidence_output)
    if path.is_absolute():
        return "evidence_output_path_must_be_relative"
    if path.suffix != ".json":
        return "evidence_output_path_must_be_json"
    if any(part in {"", ".", ".."} for part in path.parts):
        return "evidence_output_path_unsafe"
    if not path.as_posix().startswith(
        f"{EXTERNAL_READONLY_FETCH_ARCHIVE_CONTROLLED_ROOT}/"
    ):
        return "evidence_output_path_outside_controlled_root"

    root_resolved = root.resolve()
    target = (root / path).resolve()
    controlled_root = (
        root / EXTERNAL_READONLY_FETCH_ARCHIVE_CONTROLLED_ROOT
    ).resolve()
    try:
        target.relative_to(controlled_root)
        target.relative_to(root_resolved)
    except ValueError:
        return "evidence_output_path_unsafe"
    if target.exists() and not overwrite:
        return "evidence_output_exists"
    return None


def sanitize_external_readonly_fetch_output(
    output: Mapping[str, Any],
) -> dict[str, Any]:
    """Drop forbidden raw payload keys from a CLI evidence output mapping."""

    return {
        str(key): _sanitize_value(value)
        for key, value in output.items()
        if str(key) not in EXTERNAL_READONLY_FETCH_ARCHIVE_FORBIDDEN_OUTPUT_KEYS
    }


def external_readonly_fetch_output_boundary_violated(value: Any) -> bool:
    """Return true when a mapping still contains raw forbidden output keys."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in EXTERNAL_READONLY_FETCH_ARCHIVE_FORBIDDEN_OUTPUT_KEYS:
                return True
            if external_readonly_fetch_output_boundary_violated(item):
                return True
    elif isinstance(value, list | tuple):
        return any(
            external_readonly_fetch_output_boundary_violated(item)
            for item in value
        )
    return False


def external_readonly_fetch_evidence_output_blocked_payload(
    payload: Mapping[str, Any],
    *,
    evidence_output: str,
    issue: str,
) -> dict[str, Any]:
    """Build a sanitized blocked archive payload for an unsafe output path."""

    blocking = list(payload.get("blocking_reasons") or [])
    if issue not in blocking:
        blocking.append(issue)
    return {
        **dict(payload),
        "status": "blocked",
        "success": False,
        "failure_type": "external_readonly_evidence_output_blocked",
        "blocking_reasons": blocking,
        "evidence_written": False,
        "evidence_output_path": evidence_output,
        "evidence_ref": None,
    }


def external_readonly_fetch_evidence_ref_for_output(path: Path) -> str:
    """Return the controlled evidence ref for a CLI fetch archive path."""

    relative = path.as_posix().removeprefix(
        f"{EXTERNAL_READONLY_FETCH_ARCHIVE_CONTROLLED_ROOT}/"
    )
    return f"{EXTERNAL_READONLY_FETCH_ARCHIVE_REF_PREFIX}{relative}"


def preview_external_readonly_text(value: str, *, limit: int = 500) -> str:
    """Return a compact sanitized text preview."""

    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _sanitize_value(item)
            for key, item in value.items()
            if str(key) not in EXTERNAL_READONLY_FETCH_ARCHIVE_FORBIDDEN_OUTPUT_KEYS
        }
    if isinstance(value, list | tuple):
        return [_sanitize_value(item) for item in value]
    return value
