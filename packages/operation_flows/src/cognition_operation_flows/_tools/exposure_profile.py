"""Candidate-only task workflow tool exposure profile mapping helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cognition_operation_flows._tools.reference_reader import (
    DEFAULT_REFERENCE_READER_ALLOWED_SUFFIXES,
    REFERENCE_READER_SOURCE_REF,
    REFERENCE_READER_TOOL_NAME,
    REFERENCE_READER_TOOLSET_KIND,
    REFERENCE_READER_TOOLSET_NAME,
    TwfReferenceReaderPolicyCandidate,
    build_default_reference_reader_policy,
    build_reference_reader_operation_facts,
)
from cognition_operation_flows._tools.toolset_admission import (
    TwfToolOperationFactsCandidate,
    TwfToolsetInventoryCandidate,
    build_twf_toolset_inventory,
    evaluate_twf_toolset_admission,
)


TWF_TOOL_EXPOSURE_CONTROL_STAGES = (
    "default_policy",
    "profile_config_mapping",
    "session_narrowing",
    "entrypoint_narrowing",
    "toolset_admission",
    "risk_review",
    "exposure_summary",
)
TWF_TOOL_EXPOSURE_CONFIG_PRECEDENCE = (
    "entrypoint_explicit_args",
    "session_args",
    "profile_config",
    "default_values",
)
DEFAULT_TWF_TOOL_EXPOSURE_PROFILE = "readonly_reference"
MANAGED_TOOL_EXPOSURE_PARAMETERS = frozenset(
    {
        "approval_ref",
        "audit_ref",
        "discovery_credential_ref",
        "execution_credential_ref",
        "live_gate",
        "output_budget",
        "raw_config",
        "risk_level",
        "sanitized_evidence_ref",
    }
)
RISK_LEVEL_ORDER = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "unknown": 4,
    "blocked": 5,
}


@dataclass(frozen=True)
class TwfToolsetExposurePolicyCandidate:
    """Candidate mapping for one toolset exposure policy."""

    toolset_name: str
    toolset_kind: str
    source_ref: str | None
    governance_allowlist_tool_names: tuple[str, ...]
    requested_tool_names: tuple[str, ...]
    effective_tool_names: tuple[str, ...]
    readonly_only: bool = True
    max_risk_level: str = "low"
    dynamic_toolset: bool = True
    discovery_credential_ref: str | None = None
    execution_credential_ref: str | None = None
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfToolExposureProfileCandidate:
    """Candidate profile/config mapping for task workflow tool exposure."""

    profile_name: str
    source_ref: str | None
    config_precedence: tuple[str, ...]
    toolsets: tuple[TwfToolsetExposurePolicyCandidate, ...]
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    status: str = "candidate"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfToolExposureResolutionCandidate:
    """Resolved candidate exposure after admission and risk review."""

    profile: TwfToolExposureProfileCandidate
    inventories: tuple[TwfToolsetInventoryCandidate, ...]
    exposed_tool_names: tuple[str, ...]
    blocked_tool_names: tuple[str, ...]
    reference_reader_policy: TwfReferenceReaderPolicyCandidate | None = None
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    status: str = "candidate"
    metadata: dict[str, Any] = field(default_factory=dict)


def resolve_twf_tool_exposure_profile(
    *,
    profile_name: str = DEFAULT_TWF_TOOL_EXPOSURE_PROFILE,
    profile_config: Mapping[str, Any] | None = None,
    repo_root: str | Path | None = None,
    session_args: Mapping[str, Any] | None = None,
    entrypoint_explicit_args: Mapping[str, Any] | None = None,
    operation_facts_by_toolset: Mapping[
        str, Sequence[TwfToolOperationFactsCandidate]
    ]
    | None = None,
) -> TwfToolExposureResolutionCandidate:
    """Resolve profile/config tool exposure without loading or executing tools."""

    repo_path = Path(repo_root or Path.cwd()).expanduser().resolve()
    profile_config = profile_config or _default_tool_exposure_config(repo_path)
    session_args = session_args or {}
    entrypoint_explicit_args = entrypoint_explicit_args or {}
    operation_facts_by_toolset = operation_facts_by_toolset or {}
    blocking: list[str] = []
    warnings: list[str] = []

    selected_profile_name = _first_text(
        entrypoint_explicit_args.get("profile_name"),
        session_args.get("profile_name"),
        profile_name,
        DEFAULT_TWF_TOOL_EXPOSURE_PROFILE,
    )
    blocking.extend(
        _managed_override_reasons("session_args", session_args)
        + _managed_override_reasons("entrypoint_explicit_args", entrypoint_explicit_args)
    )
    profile_mapping = _profile_mapping(profile_config, selected_profile_name)
    if profile_mapping is None:
        blocking.append("tool_exposure_profile_missing")
        profile_mapping = _profile_mapping(
            _default_tool_exposure_config(repo_path),
            DEFAULT_TWF_TOOL_EXPOSURE_PROFILE,
        )
        warnings.append("default_tool_exposure_profile_used")

    source_ref = _optional_text(profile_mapping.get("source_ref"))
    profile_toolsets = _toolset_mappings(profile_mapping.get("toolsets"))
    if not profile_toolsets:
        blocking.append("tool_exposure_profile_toolsets_missing")

    session_selection = _selection_by_toolset(session_args)
    entrypoint_selection = _selection_by_toolset(entrypoint_explicit_args)
    toolset_policies: list[TwfToolsetExposurePolicyCandidate] = []
    inventories: list[TwfToolsetInventoryCandidate] = []
    exposed_tool_names: list[str] = []
    blocked_tool_names: list[str] = []
    reference_reader_policy: TwfReferenceReaderPolicyCandidate | None = None

    for raw_toolset in profile_toolsets:
        policy = _build_toolset_policy(
            raw_toolset,
            session_selection=session_selection,
            entrypoint_selection=entrypoint_selection,
        )
        toolset_policies.append(policy)
        blocking.extend(policy.blocking_reasons)
        warnings.extend(policy.warnings)
        admission = evaluate_twf_toolset_admission(
            toolset_name=policy.toolset_name,
            toolset_kind=policy.toolset_kind,
            source_ref=policy.source_ref,
            tool_filter=policy.effective_tool_names,
            allowlist_tool_names=policy.governance_allowlist_tool_names,
            discovery_credential_ref=policy.discovery_credential_ref,
            execution_credential_ref=policy.execution_credential_ref,
            dynamic_toolset=policy.dynamic_toolset,
            raw_config=raw_toolset.get("raw_config")
            if isinstance(raw_toolset.get("raw_config"), Mapping)
            else {},
        )
        blocking.extend(admission.blocking_reasons)
        warnings.extend(admission.warnings)
        operations = tuple(operation_facts_by_toolset.get(policy.toolset_name, ()))
        if (
            policy.toolset_name == REFERENCE_READER_TOOLSET_NAME
            and not operations
        ):
            operations = (build_reference_reader_operation_facts(),)
        if policy.effective_tool_names and not operations:
            blocking.append(f"operation_facts_missing:{policy.toolset_name}")
        inventory = build_twf_toolset_inventory(admission, operations)
        inventories.append(inventory)
        effective_tool_names = set(policy.effective_tool_names)
        for tool in inventory.tools:
            if not tool.selected or tool.tool_name not in effective_tool_names:
                continue
            risk_allowed = _risk_at_or_below(
                tool.risk_review.risk_level,
                policy.max_risk_level,
            )
            if tool.exposed and risk_allowed:
                exposed_tool_names.append(tool.tool_name)
            else:
                blocked_tool_names.append(tool.tool_name)
                if tool.exposed and not risk_allowed:
                    warnings.append(
                        f"selected_tool_exceeds_profile_max_risk:{tool.tool_name}"
                    )
        if REFERENCE_READER_TOOL_NAME in policy.effective_tool_names:
            reference_reader_policy = _build_reference_reader_policy_from_toolset(
                raw_toolset,
                repo_root=repo_path,
            )
            if not _policy_roots_under_repo(reference_reader_policy, repo_path):
                blocking.append("reference_reader_allowed_roots_outside_repo")

    profile = TwfToolExposureProfileCandidate(
        profile_name=selected_profile_name,
        source_ref=source_ref,
        config_precedence=TWF_TOOL_EXPOSURE_CONFIG_PRECEDENCE,
        toolsets=tuple(toolset_policies),
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        status="resolved" if not blocking else "blocked",
        metadata={
            "candidate_only": True,
            "stages": list(TWF_TOOL_EXPOSURE_CONTROL_STAGES),
            "repo_root": str(repo_path),
            "session_selection_present": bool(session_selection),
            "entrypoint_selection_present": bool(entrypoint_selection),
            "does_not_load_toolsets": True,
            "does_not_execute_tools": True,
            "does_not_read_config_files": True,
        },
    )
    return TwfToolExposureResolutionCandidate(
        profile=profile,
        inventories=tuple(inventories),
        exposed_tool_names=tuple(_ordered_unique(exposed_tool_names)),
        blocked_tool_names=tuple(_ordered_unique(blocked_tool_names)),
        reference_reader_policy=reference_reader_policy,
        blocking_reasons=profile.blocking_reasons,
        warnings=profile.warnings,
        status=profile.status,
        metadata={
            "candidate_only": True,
            "config_precedence": list(TWF_TOOL_EXPOSURE_CONFIG_PRECEDENCE),
            "toolset_count": len(toolset_policies),
            "inventory_count": len(inventories),
            "exposed_count": len(_ordered_unique(exposed_tool_names)),
            "blocked_count": len(_ordered_unique(blocked_tool_names)),
        },
    )


def twf_tool_exposure_profile_status_dict(
    resolution: TwfToolExposureResolutionCandidate,
) -> dict[str, Any]:
    """Return a sanitized status dict for result packages and evidence."""

    reference_policy = resolution.reference_reader_policy
    return {
        "profile": {
            "name": resolution.profile.profile_name,
            "source_ref": resolution.profile.source_ref,
            "status": resolution.status,
            "blocking_reasons": list(resolution.blocking_reasons),
            "warnings": list(resolution.warnings),
            "config_precedence": list(resolution.profile.config_precedence),
        },
        "selection": {
            "exposed_tool_names": list(resolution.exposed_tool_names),
            "blocked_tool_names": list(resolution.blocked_tool_names),
        },
        "toolsets": [
            {
                "toolset_name": policy.toolset_name,
                "toolset_kind": policy.toolset_kind,
                "source_ref": policy.source_ref,
                "governance_allowlist_tool_names": list(
                    policy.governance_allowlist_tool_names
                ),
                "requested_tool_names": list(policy.requested_tool_names),
                "effective_tool_names": list(policy.effective_tool_names),
                "readonly_only": policy.readonly_only,
                "max_risk_level": policy.max_risk_level,
                "blocking_reasons": list(policy.blocking_reasons),
                "warnings": list(policy.warnings),
            }
            for policy in resolution.profile.toolsets
        ],
        "reference_reader_policy": (
            {
                "allowed_roots": list(reference_policy.allowed_roots),
                "allowed_files": list(reference_policy.allowed_files),
                "allowed_suffixes": list(reference_policy.allowed_suffixes),
                "max_bytes": reference_policy.max_bytes,
                "max_chars": reference_policy.max_chars,
                "max_excerpt_lines": reference_policy.max_excerpt_lines,
            }
            if reference_policy is not None
            else None
        ),
        "metadata": dict(resolution.metadata),
    }


def _default_tool_exposure_config(repo_root: Path) -> dict[str, Any]:
    return {
        "profiles": {
            DEFAULT_TWF_TOOL_EXPOSURE_PROFILE: {
                "source_ref": "default://twf-tool-exposure/readonly-reference",
                "toolsets": [
                    {
                        "toolset_name": REFERENCE_READER_TOOLSET_NAME,
                        "toolset_kind": REFERENCE_READER_TOOLSET_KIND,
                        "source_ref": REFERENCE_READER_SOURCE_REF,
                        "allowlist_tool_names": (REFERENCE_READER_TOOL_NAME,),
                        "tool_filter": (REFERENCE_READER_TOOL_NAME,),
                        "readonly_only": True,
                        "max_risk_level": "low",
                        "dynamic_toolset": True,
                        "discovery_credential_ref": "credential://not-required",
                        "execution_credential_ref": "credential://not-required",
                        "reference_reader": {
                            "allowed_roots": (str(repo_root),),
                            "allowed_suffixes": DEFAULT_REFERENCE_READER_ALLOWED_SUFFIXES,
                            "max_bytes": 32768,
                            "max_chars": 6000,
                            "max_excerpt_lines": 80,
                        },
                    }
                ],
            }
        }
    }


def _profile_mapping(
    profile_config: Mapping[str, Any],
    profile_name: str,
) -> Mapping[str, Any] | None:
    profiles = profile_config.get("profiles")
    if not isinstance(profiles, Mapping):
        return None
    profile = profiles.get(profile_name)
    return profile if isinstance(profile, Mapping) else None


def _toolset_mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Mapping):
        return tuple(
            item
            for item in value.values()
            if isinstance(item, Mapping)
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _build_toolset_policy(
    raw_toolset: Mapping[str, Any],
    *,
    session_selection: Mapping[str, tuple[str, ...]],
    entrypoint_selection: Mapping[str, tuple[str, ...]],
) -> TwfToolsetExposurePolicyCandidate:
    toolset_name = _first_text(raw_toolset.get("toolset_name"), "unknown_toolset")
    toolset_kind = _first_text(raw_toolset.get("toolset_kind"), "toolset")
    allowlist = tuple(
        _ordered_unique(
            _sequence_texts(
                raw_toolset.get("allowlist_tool_names")
                or raw_toolset.get("allowed_tool_names")
                or raw_toolset.get("allowed_tools")
                or raw_toolset.get("tool_filter")
            )
        )
    )
    requested = tuple(_ordered_unique(_sequence_texts(raw_toolset.get("tool_filter"))))
    if not requested:
        requested = allowlist
    blocking: list[str] = []
    warnings: list[str] = []
    if not allowlist:
        blocking.append(f"toolset_governance_allowlist_missing:{toolset_name}")
    requested, session_blocking = _apply_selection_narrowing(
        requested,
        allowlist,
        session_selection.get(toolset_name) or session_selection.get("*"),
        source="session_args",
    )
    blocking.extend(session_blocking)
    requested, entrypoint_blocking = _apply_selection_narrowing(
        requested,
        allowlist,
        entrypoint_selection.get(toolset_name) or entrypoint_selection.get("*"),
        source="entrypoint_explicit_args",
    )
    blocking.extend(entrypoint_blocking)
    max_risk_level = _first_text(raw_toolset.get("max_risk_level"), "low").lower()
    if max_risk_level not in RISK_LEVEL_ORDER:
        warnings.append(f"toolset_max_risk_level_unrecognized:{toolset_name}")
        max_risk_level = "low"
    return TwfToolsetExposurePolicyCandidate(
        toolset_name=toolset_name,
        toolset_kind=toolset_kind,
        source_ref=_optional_text(raw_toolset.get("source_ref")),
        governance_allowlist_tool_names=allowlist,
        requested_tool_names=tuple(_ordered_unique(requested)),
        effective_tool_names=tuple(_ordered_unique(requested)),
        readonly_only=bool(raw_toolset.get("readonly_only", True)),
        max_risk_level=max_risk_level,
        dynamic_toolset=bool(raw_toolset.get("dynamic_toolset", True)),
        discovery_credential_ref=_optional_text(
            raw_toolset.get("discovery_credential_ref")
        ),
        execution_credential_ref=_optional_text(
            raw_toolset.get("execution_credential_ref")
        ),
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "candidate_only": True,
            "selection_policy": "session_and_entrypoint_can_only_narrow_governance_allowlist",
        },
    )


def _selection_by_toolset(args: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    selected = _sequence_texts(args.get("selected_tool_names"))
    selections = args.get("toolset_selections")
    by_toolset: dict[str, tuple[str, ...]] = {}
    if selected:
        by_toolset["*"] = tuple(_ordered_unique(selected))
    if isinstance(selections, Mapping):
        for toolset_name, tool_names in selections.items():
            by_toolset[str(toolset_name)] = tuple(
                _ordered_unique(_sequence_texts(tool_names))
            )
    return by_toolset


def _apply_selection_narrowing(
    requested: tuple[str, ...],
    allowlist: tuple[str, ...],
    selection: tuple[str, ...] | None,
    *,
    source: str,
) -> tuple[tuple[str, ...], list[str]]:
    if not selection:
        return requested, []
    allowset = set(allowlist)
    invalid = tuple(tool for tool in selection if tool not in allowset)
    blocking = [
        f"{source}_selection_outside_governance_allowlist:{tool}"
        for tool in invalid
    ]
    narrowed = tuple(tool for tool in requested if tool in set(selection))
    return narrowed, blocking


def _build_reference_reader_policy_from_toolset(
    raw_toolset: Mapping[str, Any],
    *,
    repo_root: Path,
) -> TwfReferenceReaderPolicyCandidate:
    config = raw_toolset.get("reference_reader")
    if not isinstance(config, Mapping):
        config = {}
    roots = _sequence_texts(config.get("allowed_roots")) or (str(repo_root),)
    files = _sequence_texts(config.get("allowed_files"))
    resolved_roots = tuple(_resolve_root(root, repo_root) for root in roots)
    resolved_files = tuple(_resolve_root(file, repo_root) for file in files)
    return build_default_reference_reader_policy(
        allowed_roots=resolved_roots,
        allowed_files=resolved_files,
        allowed_suffixes=(
            _sequence_texts(config.get("allowed_suffixes"))
            or DEFAULT_REFERENCE_READER_ALLOWED_SUFFIXES
        ),
        max_bytes=_positive_int(config.get("max_bytes"), 32768),
        max_chars=_positive_int(config.get("max_chars"), 6000),
        max_excerpt_lines=_positive_int(config.get("max_excerpt_lines"), 80),
    )


def _resolve_root(value: str, repo_root: Path) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    return str(path.resolve())


def _policy_roots_under_repo(
    policy: TwfReferenceReaderPolicyCandidate,
    repo_root: Path,
) -> bool:
    return all(
        Path(root).resolve() == repo_root
        or repo_root in Path(root).resolve().parents
        for root in policy.allowed_roots
    ) and all(
        Path(file).resolve() == repo_root
        or repo_root in Path(file).resolve().parents
        for file in policy.allowed_files
    )


def _managed_override_reasons(source: str, args: Mapping[str, Any]) -> list[str]:
    return [
        f"{source}_overrides_managed_tool_exposure_parameter:{key}"
        for key in sorted(args)
        if key in MANAGED_TOOL_EXPOSURE_PARAMETERS
    ]


def _risk_at_or_below(risk_level: str, max_risk_level: str) -> bool:
    return RISK_LEVEL_ORDER.get(risk_level, RISK_LEVEL_ORDER["unknown"]) <= (
        RISK_LEVEL_ORDER.get(max_risk_level, RISK_LEVEL_ORDER["low"])
    )


def _first_text(*values: Any) -> str:
    for value in values:
        text = _optional_text(value)
        if text:
            return text
    return ""


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _sequence_texts(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, Sequence):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def _positive_int(value: Any, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
