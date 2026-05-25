"""In-chat governed reference path controls."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Literal

from cognition_cli.chat.controls import _chat_plan_control_kwargs
from contract_core.external_readonly_evidence import (
    read_external_readonly_evidence_summary,
    validate_external_readonly_evidence_path,
)
from contract_core.product_gateway_cli import (
    PRODUCT_GATEWAY_CLI_REFERENCE_READER_FORBIDDEN_PATH_MARKERS,
    PRODUCT_GATEWAY_CLI_REFERENCE_READER_FORBIDDEN_SEGMENTS,
    PRODUCT_GATEWAY_CLI_REFERENCE_READER_TOOL_NAME,
)
from product_gateway.cli_surface import resolve_cli_operation_flow_tool_exposure_profile


REFERENCE_PATH_HINT = (
    "我还没有收到可读取的具体文件路径。你可以直接发送 `.md`、`.txt`、"
    "`.json`、`.yaml`、`.yml` 或 `.toml` 文件路径；当前版本不做目录扫描。"
)
REFERENCE_CONFIRMATION_WARNING = (
    "这会把该文件加入本轮受控资料，并使用 local_reference_reader 只读读取。"
)
EXTERNAL_READONLY_EVIDENCE_CONFIRMATION_WARNING = (
    "这会把该 evidence-output 加入本轮外部只读证据摘要；"
    "reference-review 只读取已归档 JSON，不会联网、不会上传、不会展示 raw response；"
    "受控问答与追问将通过 external-readonly ask 治理链路执行。"
)

_REFERENCE_FILE_PATH_RE = re.compile(
    r"/(?:Users|Volumes|private|tmp|var|home)/.+?"
    r"\.(?:md|txt|json|yaml|yml|toml)(?=$|\s|[，。；：,;:!！?？）)])",
    re.IGNORECASE | re.DOTALL,
)
_LOCAL_PATH_RE = re.compile(
    r"/(?:Users|Volumes|private|tmp|var|home)/[^\s，。；：,;:!！?？）)]+",
    re.IGNORECASE,
)
_EXTERNAL_READONLY_EVIDENCE_PATH_RE = re.compile(
    r"(?:(?:/(?:Users|Volumes|private|tmp|var|home)/[^\s，。；：,;:!！?？）)]*/)?"
    r"outputs/external-readonly/[^\s，。；：,;:!！?？）)]+\.json)"
    r"(?=$|\s|[，。；：,;:!！?？）)])",
    re.IGNORECASE,
)

_CONFIRM_WORDS = {
    "同意",
    "确认",
    "可以",
    "好的",
    "好",
    "是",
    "是的",
    "继续",
    "执行",
    "读取",
    "ok",
    "yes",
    "y",
}
_CANCEL_WORDS = {
    "取消",
    "不同意",
    "不要",
    "否",
    "不用",
    "算了",
    "停止",
    "no",
    "n",
}


@dataclass(frozen=True)
class PendingReferencePathAdd:
    requested_path: str
    resolved_path: str
    original_user_text: str
    task_text: str
    reference_kind: Literal["local_reference", "external_readonly_evidence"] = (
        "local_reference"
    )


@dataclass(frozen=True)
class ReferencePathValidation:
    requested_path: str
    resolved_path: str | None
    allowed: bool
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReferencePathInteraction:
    action: Literal["none", "pending", "confirmed", "cancelled", "blocked", "waiting"]
    assistant_text: str | None = None
    pending: PendingReferencePathAdd | None = None
    execute_user_text: str | None = None
    warning_code: str | None = None


def build_reference_interaction(
    args: argparse.Namespace,
    user_text: str,
    pending: PendingReferencePathAdd | None,
) -> ReferencePathInteraction:
    """Return the in-chat reference path interaction for one user turn."""

    if pending is not None:
        return _pending_reference_interaction(user_text, pending)

    requested_evidence_path = extract_first_external_readonly_evidence_path(user_text)
    if requested_evidence_path is not None:
        validation = validate_external_readonly_evidence_path_for_chat(
            args,
            requested_evidence_path,
        )
        if not validation.allowed:
            return ReferencePathInteraction(
                action="blocked",
                assistant_text=_blocked_external_readonly_evidence_text(validation),
                warning_code="external_readonly_evidence_path_blocked",
            )
        if validation.resolved_path is None:
            return ReferencePathInteraction(
                action="blocked",
                assistant_text=_blocked_external_readonly_evidence_text(validation),
                warning_code="external_readonly_evidence_path_blocked",
            )
        pending_add = PendingReferencePathAdd(
            requested_path=requested_evidence_path,
            resolved_path=validation.resolved_path,
            original_user_text=user_text,
            task_text=_task_text_without_control_path(
                user_text,
                requested_evidence_path,
                replacement="这份外部只读证据摘要",
            ),
            reference_kind="external_readonly_evidence",
        )
        return ReferencePathInteraction(
            action="pending",
            assistant_text=_pending_external_readonly_evidence_text(pending_add),
            pending=pending_add,
            warning_code="external_readonly_evidence_path_confirmation_required",
        )

    requested_path = extract_first_reference_file_path(user_text)
    if requested_path is None:
        local_path = extract_first_local_path(user_text)
        if local_path is not None:
            validation = validate_reference_path_for_chat(args, local_path)
            return ReferencePathInteraction(
                action="blocked",
                assistant_text=_blocked_reference_text(validation),
                warning_code="reference_path_blocked",
            )
        if "--reference-path" in user_text:
            return ReferencePathInteraction(
                action="blocked",
                assistant_text=REFERENCE_PATH_HINT,
                warning_code="reference_path_missing",
            )
        return ReferencePathInteraction(action="none")

    validation = validate_reference_path_for_chat(args, requested_path)
    if not validation.allowed:
        return ReferencePathInteraction(
            action="blocked",
            assistant_text=_blocked_reference_text(validation),
            warning_code="reference_path_blocked",
        )

    resolved_path = validation.resolved_path
    if resolved_path is None:
        return ReferencePathInteraction(
            action="blocked",
            assistant_text=_blocked_reference_text(validation),
            warning_code="reference_path_blocked",
        )
    pending_add = PendingReferencePathAdd(
        requested_path=requested_path,
        resolved_path=resolved_path,
        original_user_text=user_text,
        task_text=_task_text_without_control_path(
            user_text,
            requested_path,
            replacement="这份资料",
        ),
    )
    return ReferencePathInteraction(
        action="pending",
        assistant_text=_pending_reference_text(pending_add),
        pending=pending_add,
        warning_code="reference_path_confirmation_required",
    )


def apply_confirmed_reference_path(
    args: argparse.Namespace,
    pending: PendingReferencePathAdd,
) -> None:
    if pending.reference_kind == "external_readonly_evidence":
        paths = list(getattr(args, "external_readonly_evidence_paths", ()) or ())
        if pending.resolved_path not in paths:
            paths.append(pending.resolved_path)
        args.external_readonly_evidence_paths = paths
        return
    paths = list(getattr(args, "reference_paths", ()) or ())
    if pending.resolved_path not in paths:
        paths.append(pending.resolved_path)
    args.reference_paths = paths


def reference_list_text(args: argparse.Namespace) -> str:
    paths = tuple(getattr(args, "reference_paths", ()) or ())
    evidence_paths = tuple(
        getattr(args, "external_readonly_evidence_paths", ()) or ()
    )
    if not paths and not evidence_paths:
        return "当前会话还没有加入受控资料文件或外部只读证据。"
    lines = ["当前会话受控资料文件："]
    if paths:
        lines.extend(f"{index}. {path}" for index, path in enumerate(paths, start=1))
    else:
        lines.append("- 本地资料文件：无")
    if evidence_paths:
        lines.append("当前会话外部只读 evidence-output：")
        lines.extend(
            f"{index}. {path}" for index, path in enumerate(evidence_paths, start=1)
        )
    return "\n".join(lines)


def clear_reference_paths(args: argparse.Namespace) -> None:
    args.reference_paths = []
    args.external_readonly_evidence_paths = []


def extract_first_reference_file_path(user_text: str) -> str | None:
    match = _REFERENCE_FILE_PATH_RE.search(user_text)
    if match is None:
        return None
    return match.group(0).strip()


def extract_first_external_readonly_evidence_path(user_text: str) -> str | None:
    match = _EXTERNAL_READONLY_EVIDENCE_PATH_RE.search(user_text)
    if match is None:
        return None
    return match.group(0).strip()


def extract_first_local_path(user_text: str) -> str | None:
    match = _LOCAL_PATH_RE.search(user_text)
    if match is None:
        return None
    return match.group(0).strip()


def validate_reference_path_for_chat(
    args: argparse.Namespace,
    requested_path: str,
) -> ReferencePathValidation:
    try:
        controls = _chat_plan_control_kwargs(args)
        repo_root = Path(str(controls["reference_repo_root"])).expanduser().resolve()
        exposure = resolve_cli_operation_flow_tool_exposure_profile(
            profile_name=str(controls["reference_profile_name"]),
            profile_config=controls["reference_profile_config"],
            repo_root=repo_root,
            entrypoint_explicit_args=controls["reference_entrypoint_explicit_args"],
        )
    except Exception:
        return ReferencePathValidation(
            requested_path=requested_path,
            resolved_path=None,
            allowed=False,
            blocking_reasons=("reference_reader_config_unavailable",),
        )
    blocking = list(exposure.blocking_reasons)
    warnings = list(exposure.warnings)
    if exposure.status != "resolved":
        blocking.append("reference_tool_exposure_profile_blocked")
    if PRODUCT_GATEWAY_CLI_REFERENCE_READER_TOOL_NAME not in exposure.exposed_tool_names:
        blocking.append("reference_reader_not_exposed")
    if exposure.reference_reader_policy is None:
        blocking.append("reference_reader_policy_missing")
    if "://" in requested_path:
        blocking.append("reference_url_scheme_not_allowed")
    path = Path(requested_path).expanduser()
    if ".." in path.parts:
        blocking.append("reference_path_traversal_not_allowed")

    resolved_path: Path | None = None
    policy = exposure.reference_reader_policy
    if not blocking and policy is not None:
        resolved_path = path.resolve()
        if _has_forbidden_segment(resolved_path):
            blocking.append("reference_forbidden_segment")
        if _has_forbidden_path_marker(resolved_path):
            blocking.append("reference_forbidden_path_marker")
        if _normalize_suffix(resolved_path.suffix) not in set(policy.allowed_suffixes):
            blocking.append("reference_suffix_not_allowed")
        if not _is_allowed_reference_path(
            resolved_path,
            policy.allowed_roots,
            policy.allowed_files,
        ):
            blocking.append("reference_outside_allowed_roots")
        if not resolved_path.exists():
            blocking.append("reference_not_found")
        elif resolved_path.is_dir():
            blocking.append("reference_directory_not_supported")
        elif not resolved_path.is_file():
            blocking.append("reference_not_file")

    return ReferencePathValidation(
        requested_path=requested_path,
        resolved_path=str(resolved_path) if resolved_path is not None else None,
        allowed=not blocking,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
    )


def validate_external_readonly_evidence_path_for_chat(
    args: argparse.Namespace,
    requested_path: str,
) -> ReferencePathValidation:
    try:
        controls = _chat_plan_control_kwargs(args)
        repo_root = Path(str(controls["reference_repo_root"])).expanduser().resolve()
    except Exception:
        return ReferencePathValidation(
            requested_path=requested_path,
            resolved_path=None,
            allowed=False,
            blocking_reasons=("external_readonly_evidence_config_unavailable",),
        )
    blocking: list[str] = []
    if "://" in requested_path:
        blocking.append("external_readonly_evidence_url_scheme_not_allowed")
    relative_path = _external_readonly_evidence_relative_path(
        requested_path,
        repo_root=repo_root,
    )
    if relative_path is None:
        blocking.append("external_readonly_evidence_path_outside_repo")
        return ReferencePathValidation(
            requested_path=requested_path,
            resolved_path=None,
            allowed=False,
            blocking_reasons=tuple(_ordered_unique(blocking)),
        )
    path_issue = validate_external_readonly_evidence_path(
        evidence_path=relative_path,
        repo_root=repo_root,
    )
    if path_issue:
        blocking.append(path_issue)
    summary = None
    if not blocking:
        summary = read_external_readonly_evidence_summary(
            relative_path,
            repo_root=repo_root,
        )
        blocking.extend(summary.blocking_reasons)
    return ReferencePathValidation(
        requested_path=requested_path,
        resolved_path=relative_path,
        allowed=not blocking,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(summary.warnings if summary is not None else ()),
    )


def _pending_reference_interaction(
    user_text: str,
    pending: PendingReferencePathAdd,
) -> ReferencePathInteraction:
    normalized = "".join(user_text.strip().lower().split())
    if normalized in _CONFIRM_WORDS:
        return ReferencePathInteraction(
            action="confirmed",
            pending=None,
            execute_user_text=pending.task_text,
        )
    if normalized in _CANCEL_WORDS:
        return ReferencePathInteraction(
            action="cancelled",
            assistant_text="已取消读取该文件，本轮不会加入受控资料。",
            warning_code="reference_path_confirmation_cancelled",
        )
    return ReferencePathInteraction(
        action="waiting",
        assistant_text=(
            "我正在等待你确认是否读取这个文件。请回复“同意”继续，"
            "或回复“取消”放弃。"
        ),
        pending=pending,
        warning_code="reference_path_confirmation_waiting",
    )


def _task_text_without_control_path(
    user_text: str,
    path: str,
    *,
    replacement: str,
) -> str:
    text = user_text.replace(path, replacement, 1)
    normalized = " ".join(text.strip().split())
    return normalized or "请审查并总结这份资料"


def _pending_reference_text(pending: PendingReferencePathAdd) -> str:
    return "\n".join(
        [
            "我识别到一个本地资料文件，并已完成受控读取前检查。",
            f"- 文件：{pending.resolved_path}",
            f"- {REFERENCE_CONFIRMATION_WARNING}",
            "请回复“同意”继续读取并执行你的请求，或回复“取消”放弃。",
        ]
    )


def _pending_external_readonly_evidence_text(
    pending: PendingReferencePathAdd,
) -> str:
    return "\n".join(
        [
            "我识别到一个外部只读 evidence-output，并已完成受控读取前检查。",
            f"- 文件：{pending.resolved_path}",
            f"- {EXTERNAL_READONLY_EVIDENCE_CONFIRMATION_WARNING}",
            "请回复“同意”继续读取并执行你的请求，或回复“取消”放弃。",
        ]
    )


def _blocked_reference_text(validation: ReferencePathValidation) -> str:
    reasons = "、".join(validation.blocking_reasons) or "unknown"
    if "reference_directory_not_supported" in validation.blocking_reasons:
        suggestion = (
            "当前版本不做目录扫描或文件发现。请提供目录内某个具体资料文件；"
            "如需按目录查找文件，应单独启用目录索引只读工具。"
        )
    elif (
        "reference_forbidden_path_marker" in validation.blocking_reasons
        or "reference_forbidden_segment" in validation.blocking_reasons
    ):
        suggestion = (
            "该路径命中敏感路径边界。请不要提供密钥、凭据、token 或私有配置文件；"
            "如需审查配置，请提供已脱敏的公开资料文件。"
        )
    else:
        allowed_files_hint = ""
        if validation.resolved_path is not None:
            allowed_files_hint = "，或明确白名单内的项目元信息文件"
        suggestion = (
            "你可以改为提供 allowed roots 内的具体 .md / .txt / .json / .yaml / .yml / .toml 文件"
            f"{allowed_files_hint}。"
        )
    return (
        "这个文件路径暂时不能读取。"
        f"\n- 路径：{validation.requested_path}"
        f"\n- 原因：{reasons}"
        f"\n{suggestion}"
    )


def _blocked_external_readonly_evidence_text(
    validation: ReferencePathValidation,
) -> str:
    reasons = "、".join(validation.blocking_reasons) or "unknown"
    return (
        "这个外部只读 evidence-output 暂时不能读取。"
        f"\n- 路径：{validation.requested_path}"
        f"\n- 原因：{reasons}"
        "\n你可以改为提供 outputs/external-readonly/ 下已归档的 .json evidence-output；"
        "本路径只做本地只读摘要消费，不会触发联网。"
    )


def _external_readonly_evidence_relative_path(
    requested_path: str,
    *,
    repo_root: Path,
) -> str | None:
    raw_path = Path(requested_path).expanduser()
    if raw_path.is_absolute():
        resolved = raw_path.resolve()
        try:
            return str(resolved.relative_to(repo_root))
        except ValueError:
            return None
    return str(raw_path)


def _is_allowed_reference_path(
    path: Path,
    allowed_roots: tuple[str, ...],
    allowed_files: tuple[str, ...] = (),
) -> bool:
    return _is_under_allowed_root(path, allowed_roots) or _is_allowed_file(
        path,
        allowed_files,
    )


def _is_under_allowed_root(path: Path, allowed_roots: tuple[str, ...]) -> bool:
    for root in allowed_roots:
        root_path = Path(root).expanduser().resolve()
        if path == root_path or root_path in path.parents:
            return True
    return False


def _is_allowed_file(path: Path, allowed_files: tuple[str, ...]) -> bool:
    resolved = path.expanduser().resolve()
    return any(
        resolved == Path(allowed_file).expanduser().resolve()
        for allowed_file in allowed_files
    )


def _has_forbidden_segment(path: Path) -> bool:
    forbidden = {
        segment.lower()
        for segment in PRODUCT_GATEWAY_CLI_REFERENCE_READER_FORBIDDEN_SEGMENTS
    }
    return any(part.lower() in forbidden for part in path.parts)


def _has_forbidden_path_marker(path: Path) -> bool:
    path_text = str(path).lower()
    return any(
        marker.lower() in path_text
        for marker in PRODUCT_GATEWAY_CLI_REFERENCE_READER_FORBIDDEN_PATH_MARKERS
    )


def _normalize_suffix(suffix: str) -> str:
    normalized = suffix.strip().lower()
    return normalized if normalized.startswith(".") else f".{normalized}"


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
