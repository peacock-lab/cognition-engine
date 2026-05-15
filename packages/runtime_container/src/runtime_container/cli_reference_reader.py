"""Candidate-only local reference reader for readonly CLI tools."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any

from runtime_container.cli_toolset_admission import (
    CliToolOperationFactsCandidate,
    CliToolRiskReviewCandidate,
    CliToolsetInventoryCandidate,
    build_cli_toolset_inventory,
    evaluate_cli_toolset_admission,
    review_cli_tool_operation_risk,
)


REFERENCE_READER_TOOLSET_NAME = "local_reference_tools"
REFERENCE_READER_TOOLSET_KIND = "toolset"
REFERENCE_READER_TOOL_NAME = "local_reference_reader"
REFERENCE_READER_SOURCE_REF = "local-reference-reader://workspace"
REFERENCE_READER_CONTROL_STAGES = (
    "toolset_admission",
    "operation_facts",
    "risk_review",
    "path_resolution",
    "bounded_read",
    "redaction",
    "evidence_summary",
)
DEFAULT_REFERENCE_READER_ALLOWED_SUFFIXES = (
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
)
DEFAULT_REFERENCE_READER_FORBIDDEN_SEGMENTS = (
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
)
DEFAULT_REFERENCE_READER_FORBIDDEN_PATH_MARKERS = (
    ".env",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials",
    "id_dsa",
    "id_ed25519",
    "id_rsa",
    "private_key",
    "secrets",
    "service_account",
)
REFERENCE_READER_SENSITIVE_LINE_MARKERS = (
    "access_token",
    "api_key",
    "authorization:",
    "bearer ",
    "client_secret",
    "credential",
    "password",
    "private_key",
    "secret",
    "service_account_json",
    "-----begin ",
)


@dataclass(frozen=True)
class CliReferenceReaderPolicyCandidate:
    """Candidate policy for a local, readonly reference reader."""

    allowed_roots: tuple[str, ...]
    allowed_suffixes: tuple[str, ...] = DEFAULT_REFERENCE_READER_ALLOWED_SUFFIXES
    forbidden_segments: tuple[str, ...] = DEFAULT_REFERENCE_READER_FORBIDDEN_SEGMENTS
    forbidden_path_markers: tuple[
        str, ...
    ] = DEFAULT_REFERENCE_READER_FORBIDDEN_PATH_MARKERS
    max_bytes: int = 32768
    max_chars: int = 6000
    max_excerpt_lines: int = 80
    include_line_numbers: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliReferenceReadRequestCandidate:
    """Candidate request for reading one local reference."""

    reference: str
    policy: CliReferenceReaderPolicyCandidate
    purpose: str = "reference_reader"
    task_run_id: str | None = None
    evidence_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliReferenceReadResultCandidate:
    """Sanitized result for a bounded local reference read."""

    reference: str
    allowed: bool
    status: str
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    resolved_path: str | None = None
    reference_digest: str | None = None
    content_excerpt: str = ""
    line_count: int = 0
    char_count: int = 0
    truncated: bool = False
    redacted_line_count: int = 0
    evidence_ref: str | None = None
    operation_facts: CliToolOperationFactsCandidate | None = None
    risk_review: CliToolRiskReviewCandidate | None = None
    toolset_inventory: CliToolsetInventoryCandidate | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def build_default_reference_reader_policy(
    *,
    repo_root: str | Path | None = None,
    allowed_roots: Sequence[str | Path] | None = None,
    allowed_suffixes: Sequence[str] = DEFAULT_REFERENCE_READER_ALLOWED_SUFFIXES,
    max_bytes: int = 32768,
    max_chars: int = 6000,
    max_excerpt_lines: int = 80,
) -> CliReferenceReaderPolicyCandidate:
    """Build a default bounded local-reference policy."""

    roots = allowed_roots
    if roots is None:
        roots = (repo_root or Path.cwd(),)
    normalized_roots = tuple(
        str(Path(root).expanduser().resolve()) for root in roots if str(root).strip()
    )
    return CliReferenceReaderPolicyCandidate(
        allowed_roots=normalized_roots,
        allowed_suffixes=tuple(_normalize_suffix(suffix) for suffix in allowed_suffixes),
        max_bytes=max_bytes,
        max_chars=max_chars,
        max_excerpt_lines=max_excerpt_lines,
        metadata={
            "candidate_only": True,
            "does_not_write_files": True,
            "does_not_access_network": True,
        },
    )


def build_reference_reader_operation_facts() -> CliToolOperationFactsCandidate:
    """Return operation facts for the local reference reader."""

    return CliToolOperationFactsCandidate(
        tool_name=REFERENCE_READER_TOOL_NAME,
        toolset_name=REFERENCE_READER_TOOLSET_NAME,
        toolset_kind=REFERENCE_READER_TOOLSET_KIND,
        operation_id="readReference",
        operation="read",
        requires_auth=False,
        touches_external_system=False,
        has_request_body=False,
        metadata={
            "candidate_only": True,
            "local_filesystem_readonly": True,
            "does_not_write_files": True,
            "does_not_execute_commands": True,
            "does_not_access_network": True,
        },
    )


def build_reference_reader_toolset_inventory() -> CliToolsetInventoryCandidate:
    """Build the admission and readonly inventory for the reference reader."""

    admission = evaluate_cli_toolset_admission(
        toolset_name=REFERENCE_READER_TOOLSET_NAME,
        toolset_kind=REFERENCE_READER_TOOLSET_KIND,
        source_ref=REFERENCE_READER_SOURCE_REF,
        tool_filter=(REFERENCE_READER_TOOL_NAME,),
        allowlist_tool_names=(REFERENCE_READER_TOOL_NAME,),
        discovery_credential_ref="credential://not-required",
        execution_credential_ref="credential://not-required",
        dynamic_toolset=True,
    )
    return build_cli_toolset_inventory(
        admission,
        (build_reference_reader_operation_facts(),),
    )


def read_cli_reference(
    request: CliReferenceReadRequestCandidate,
) -> CliReferenceReadResultCandidate:
    """Read one local reference with path, size, redaction, and evidence guards."""

    operation_facts = build_reference_reader_operation_facts()
    risk_review = review_cli_tool_operation_risk(operation_facts)
    inventory = build_reference_reader_toolset_inventory()
    blocking: list[str] = []
    warnings: list[str] = []
    reference = request.reference.strip()
    resolved_path: Path | None = None
    raw_bytes = b""
    truncated = False
    excerpt = ""
    digest: str | None = None
    line_count = 0
    char_count = 0
    redacted_line_count = 0

    if not inventory.exposed_tool_names:
        blocking.append("reference_reader_tool_not_exposed")
    if not risk_review.allowed_for_readonly:
        blocking.append("reference_reader_not_allowed_for_readonly")
    if not reference:
        blocking.append("reference_missing")
    if "://" in reference:
        blocking.append("reference_url_scheme_not_allowed")
    if _has_path_traversal(reference):
        blocking.append("reference_path_traversal_not_allowed")
    if not request.policy.allowed_roots:
        blocking.append("reference_allowed_roots_missing")

    if not blocking:
        resolved_path = _resolve_reference_path(reference, request.policy.allowed_roots)
        if resolved_path is None:
            blocking.append("reference_outside_allowed_roots")
        else:
            if not resolved_path.exists():
                blocking.append("reference_not_found")
            elif not resolved_path.is_file():
                blocking.append("reference_not_file")
            elif _has_forbidden_segment(
                resolved_path, request.policy.forbidden_segments
            ):
                blocking.append("reference_forbidden_segment")
            elif _has_forbidden_path_marker(
                resolved_path, request.policy.forbidden_path_markers
            ):
                blocking.append("reference_forbidden_path_marker")
            elif _normalize_suffix(resolved_path.suffix) not in set(
                request.policy.allowed_suffixes
            ):
                blocking.append("reference_suffix_not_allowed")

    if not blocking and resolved_path is not None:
        raw_bytes, truncated = _read_bounded_bytes(
            resolved_path,
            max_bytes=request.policy.max_bytes,
        )
        if truncated:
            warnings.append("reference_bytes_truncated")
        digest = hashlib.sha256(raw_bytes).hexdigest()
        text = raw_bytes.decode("utf-8", errors="replace")
        if "\ufffd" in text:
            warnings.append("reference_decode_replacement_used")
        sanitized_text, redacted_line_count = _redact_sensitive_lines(text)
        if redacted_line_count:
            warnings.append("reference_sensitive_lines_redacted")
        excerpt, line_count, char_count, excerpt_truncated = _build_excerpt(
            sanitized_text,
            max_chars=request.policy.max_chars,
            max_lines=request.policy.max_excerpt_lines,
            include_line_numbers=request.policy.include_line_numbers,
        )
        truncated = truncated or excerpt_truncated
        if excerpt_truncated:
            warnings.append("reference_excerpt_truncated")

    status = "succeeded" if not blocking else "blocked"
    evidence_ref = (
        request.evidence_ref
        or (f"evidence://reference-reader/{digest[:16]}" if digest else None)
    )
    return CliReferenceReadResultCandidate(
        reference=reference,
        allowed=not blocking,
        status=status,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        resolved_path=str(resolved_path) if resolved_path is not None else None,
        reference_digest=digest,
        content_excerpt=excerpt,
        line_count=line_count,
        char_count=char_count,
        truncated=truncated,
        redacted_line_count=redacted_line_count,
        evidence_ref=evidence_ref,
        operation_facts=operation_facts,
        risk_review=risk_review,
        toolset_inventory=inventory,
        metadata={
            "candidate_only": True,
            "stages": list(REFERENCE_READER_CONTROL_STAGES),
            "purpose": request.purpose,
            "task_run_id": request.task_run_id,
            "does_not_write_files": True,
            "does_not_execute_commands": True,
            "does_not_access_network": True,
            "allowed_roots": list(request.policy.allowed_roots),
            "allowed_suffixes": list(request.policy.allowed_suffixes),
            "max_bytes": request.policy.max_bytes,
            "max_chars": request.policy.max_chars,
            "max_excerpt_lines": request.policy.max_excerpt_lines,
        },
    )


def cli_reference_read_status_dict(
    result: CliReferenceReadResultCandidate,
) -> dict[str, Any]:
    """Return a sanitized status dict for evidence/result packages."""

    risk_review = result.risk_review
    inventory = result.toolset_inventory
    return {
        "reference": {
            "requested": result.reference,
            "resolved_path": result.resolved_path,
            "allowed": result.allowed,
            "status": result.status,
            "blocking_reasons": list(result.blocking_reasons),
            "warnings": list(result.warnings),
        },
        "read": {
            "digest": result.reference_digest,
            "evidence_ref": result.evidence_ref,
            "line_count": result.line_count,
            "char_count": result.char_count,
            "truncated": result.truncated,
            "redacted_line_count": result.redacted_line_count,
            "content_excerpt": result.content_excerpt,
        },
        "tool": {
            "tool_name": REFERENCE_READER_TOOL_NAME,
            "toolset_name": REFERENCE_READER_TOOLSET_NAME,
            "risk_level": risk_review.risk_level if risk_review else None,
            "readonly_operation": (
                risk_review.readonly_operation if risk_review else None
            ),
            "allowed_for_readonly": (
                risk_review.allowed_for_readonly if risk_review else None
            ),
            "confirmation_required": (
                risk_review.confirmation_required if risk_review else None
            ),
            "exposed_tool_names": (
                list(inventory.exposed_tool_names) if inventory else []
            ),
        },
        "metadata": dict(result.metadata),
    }


def _resolve_reference_path(reference: str, allowed_roots: Sequence[str]) -> Path | None:
    candidate = Path(reference).expanduser()
    candidate_paths = (candidate,) if candidate.is_absolute() else ()
    if not candidate_paths:
        candidate_paths = tuple(_relative_reference_candidates(candidate, allowed_roots))
    first_allowed_path: Path | None = None
    for candidate_path in candidate_paths:
        resolved = candidate_path.resolve()
        if _is_under_allowed_root(resolved, allowed_roots):
            if resolved.exists():
                return resolved
            if first_allowed_path is None:
                first_allowed_path = resolved
    return first_allowed_path


def _relative_reference_candidates(
    candidate: Path,
    allowed_roots: Sequence[str],
) -> tuple[Path, ...]:
    paths: list[Path] = []
    for root in allowed_roots:
        root_path = Path(root).expanduser().resolve()
        paths.append(root_path / candidate)
        paths.append(root_path.parent / candidate)
    return tuple(paths)


def _is_under_allowed_root(path: Path, allowed_roots: Sequence[str]) -> bool:
    for root in allowed_roots:
        root_path = Path(root).expanduser().resolve()
        if path == root_path or root_path in path.parents:
            return True
    return False


def _read_bounded_bytes(path: Path, *, max_bytes: int) -> tuple[bytes, bool]:
    read_limit = max(0, max_bytes) + 1
    with path.open("rb") as handle:
        data = handle.read(read_limit)
    return data[:max_bytes], len(data) > max_bytes


def _build_excerpt(
    text: str,
    *,
    max_chars: int,
    max_lines: int,
    include_line_numbers: bool,
) -> tuple[str, int, int, bool]:
    lines = text.splitlines()
    rendered_lines: list[str] = []
    char_budget = max(0, max_chars)
    line_budget = max(0, max_lines)
    truncated = len(lines) > line_budget if line_budget else bool(lines)
    for index, line in enumerate(lines[:line_budget], start=1):
        rendered = f"{index}: {line}" if include_line_numbers else line
        remaining = char_budget - sum(len(item) + 1 for item in rendered_lines)
        if remaining <= 0:
            truncated = True
            break
        if len(rendered) > remaining:
            rendered_lines.append(rendered[:remaining])
            truncated = True
            break
        rendered_lines.append(rendered)
    excerpt = "\n".join(rendered_lines)
    if len(excerpt) < len(text):
        truncated = True
    return excerpt, len(lines), len(excerpt), truncated


def _redact_sensitive_lines(text: str) -> tuple[str, int]:
    redacted_count = 0
    redacted_lines: list[str] = []
    for line in text.splitlines():
        lowered = line.lower()
        if any(marker in lowered for marker in REFERENCE_READER_SENSITIVE_LINE_MARKERS):
            redacted_lines.append("[redacted sensitive reference line]")
            redacted_count += 1
        else:
            redacted_lines.append(line)
    return "\n".join(redacted_lines), redacted_count


def _has_path_traversal(reference: str) -> bool:
    return ".." in Path(reference).parts


def _has_forbidden_segment(path: Path, forbidden_segments: Sequence[str]) -> bool:
    forbidden = {segment.lower() for segment in forbidden_segments}
    return any(part.lower() in forbidden for part in path.parts)


def _has_forbidden_path_marker(path: Path, forbidden_path_markers: Sequence[str]) -> bool:
    path_text = str(path).lower()
    return any(marker.lower() in path_text for marker in forbidden_path_markers)


def _normalize_suffix(suffix: str) -> str:
    normalized = suffix.strip().lower()
    return normalized if normalized.startswith(".") else f".{normalized}"


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
