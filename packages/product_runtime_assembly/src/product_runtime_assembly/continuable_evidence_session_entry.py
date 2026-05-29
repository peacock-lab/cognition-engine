"""Product-console session handlers backed by the local session store."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

from config_contexts.runtime import ContinuableEvidenceSessionStoragePolicyConfigView

from product_runtime_assembly.continuable_evidence_session_state_root import (
    ContinuableEvidenceSessionStateRootResolution,
    resolve_continuable_evidence_session_state_root,
)
from product_runtime_assembly.continuable_evidence_session_store import (
    ContinuableEvidenceSessionLocalStoreRecord,
    delete_continuable_evidence_session_record,
    expire_continuable_evidence_session_records,
    list_continuable_evidence_session_index_entries,
    load_continuable_evidence_session_record_manifest,
    resolve_continuable_evidence_session_store_paths,
    save_continuable_evidence_session_record,
)
from schemas.continuable_evidence_session import (
    ContinuableEvidenceSessionArtifactIndexSchema,
    ContinuableEvidenceSessionDeletePolicySchema,
    ContinuableEvidenceSessionExpirationPolicySchema,
    ContinuableEvidenceSessionExportPolicySchema,
    ContinuableEvidenceSessionIndexEntrySchema,
    ContinuableEvidenceSessionLocalStateRootPolicySchema,
    ContinuableEvidenceSessionRecordManifestSchema,
    ContinuableEvidenceSessionResumePolicySchema,
    ContinuableEvidenceSessionRuntimeVisibleSummarySchema,
    ContinuableEvidenceSessionSchema,
    ContinuableEvidenceSessionSeedSchema,
    ContinuableEvidenceSessionStoragePolicySchema,
    ContinuableEvidenceSessionSummarySchema,
    ContinuableEvidenceSessionTrajectorySchema,
    ContinuableEvidenceSessionTurnSchema,
)


STORAGE_POLICY_REF = "policy://continuable-evidence-session/storage/default-v1"
STATE_ROOT_POLICY_REF = "policy://continuable-evidence-session/state-root/default-v1"
RETENTION_POLICY_REF = "policy://continuable-evidence-session/retention/default-v1"
DELETE_POLICY_REF = "policy://continuable-evidence-session/delete/default-v1"
EXPORT_POLICY_REF = "policy://continuable-evidence-session/export/default-v1"
RESUME_POLICY_REF = "policy://continuable-evidence-session/resume/default-v1"


def build_product_console_session_save_handler(
    *,
    now_factory: Callable[[], datetime] | None = None,
    storage_config: ContinuableEvidenceSessionStoragePolicyConfigView | None = None,
    state_root_resolver: (
        Callable[[Mapping[str, Any]], ContinuableEvidenceSessionStateRootResolution]
        | None
    ) = None,
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    """Build a product-console save handler backed by the local session store."""

    def _handle(request: Mapping[str, Any]) -> Mapping[str, Any]:
        state_root_result = _resolve_request_state_root(
            request,
            storage_config=storage_config,
            state_root_resolver=state_root_resolver,
        )
        if state_root_result.get("status") != "ready":
            return state_root_result
        state_root = state_root_result["state_root"]
        now = _utc_now(now_factory)
        record_result = _build_store_record(request, now=now)
        if record_result.get("status") != "ready":
            return record_result
        record = record_result["record"]
        result = save_continuable_evidence_session_record(
            state_root=state_root,
            record=record,
        )
        return {
            "status": "success",
            "action": "save",
            "session_id": result.session_id,
            "continuable_evidence_session_ref": (
                result.index_entry.continuable_evidence_session_ref
            ),
            "state_root": state_root,
            "state_root_source": state_root_result["state_root_source"],
            "message": "已保存 refs 与安全摘要，可用于后续查看和恢复提示。",
            "written_relative_paths": result.written_relative_paths,
        }

    return _handle


def build_product_console_session_action_handler(
    *,
    now_factory: Callable[[], datetime] | None = None,
    storage_config: ContinuableEvidenceSessionStoragePolicyConfigView | None = None,
    state_root_resolver: (
        Callable[[Mapping[str, Any]], ContinuableEvidenceSessionStateRootResolution]
        | None
    ) = None,
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    """Build product-console session list/delete/expire/preview handler."""

    def _handle(request: Mapping[str, Any]) -> Mapping[str, Any]:
        action = _required_text(request.get("action"), "action")
        state_root_result = _resolve_request_state_root(
            request,
            storage_config=storage_config,
            state_root_resolver=state_root_resolver,
        )
        if state_root_result.get("status") != "ready":
            return state_root_result
        state_root = state_root_result["state_root"]
        state_root_source = state_root_result["state_root_source"]
        if action == "list":
            entries = list_continuable_evidence_session_index_entries(
                state_root=state_root
            )
            return {
                "status": "success",
                "action": "list",
                "state_root": state_root,
                "state_root_source": state_root_source,
                "entries": [_index_entry_dict(entry) for entry in entries],
            }
        if action == "delete":
            session_id = _required_text(request.get("session_id"), "session_id")
            if request.get("confirmed") is not True:
                return {
                    "status": "confirmation_required",
                    "action": "delete",
                    "session_id": session_id,
                    "state_root": state_root,
                    "state_root_source": state_root_source,
                    "recovery_hints": ("如确认删除，请追加 --yes。",),
                }
            result = delete_continuable_evidence_session_record(
                state_root=state_root,
                session_id=session_id,
                delete_policy=ContinuableEvidenceSessionDeletePolicySchema(
                    delete_policy_ref=DELETE_POLICY_REF,
                ),
                deleted_at=_iso_z(_utc_now(now_factory)),
            )
            return {
                "status": "success",
                "action": "delete",
                "session_id": result.session_id,
                "deleted": result.deleted,
                "remaining_index_count": result.remaining_index_count,
                "state_root": state_root,
                "state_root_source": state_root_source,
            }
        if action == "expire":
            now_text = _required_text(request.get("now"), "now")
            result = expire_continuable_evidence_session_records(
                state_root=state_root,
                expiration_policy=ContinuableEvidenceSessionExpirationPolicySchema(
                    retention_policy_ref=RETENTION_POLICY_REF,
                ),
                now=now_text,
            )
            return {
                "status": "success",
                "action": "expire",
                "state_root": state_root,
                "state_root_source": state_root_source,
                "expired_session_ids": result.expired_session_ids,
                "entries": [_index_entry_dict(entry) for entry in result.index_entries],
            }
        if action == "resume-preview":
            session_id = _required_text(request.get("session_id"), "session_id")
            entries = list_continuable_evidence_session_index_entries(
                state_root=state_root
            )
            matching_entry = next(
                (entry for entry in entries if entry.session_id == session_id),
                None,
            )
            try:
                loaded = load_continuable_evidence_session_record_manifest(
                    state_root=state_root,
                    session_id=session_id,
                )
            except FileNotFoundError:
                reason = (
                    "session_record_unavailable"
                    if matching_entry is not None
                    else "session_not_found"
                )
                return {
                    "status": "unavailable",
                    "action": "resume-preview",
                    "reason": reason,
                    "session_id": session_id,
                    "state_root": state_root,
                    "state_root_source": state_root_source,
                    "recovery_hints": (
                        "未找到该会话的本地保存记录；不会重新读取资料、调用模型或重放 Workflow。",
                    ),
                }
            preview = {
                "session_id": loaded.session_id,
                "record_status": loaded.manifest.record_status,
                "updated_at": loaded.manifest.updated_at,
                "expires_at": loaded.manifest.expires_at,
                "requires_external_readonly_authorization": True,
                "requires_model_authorization": True,
                "runtime_summary": _load_runtime_visible_summary_preview(
                    state_root=state_root,
                    session_id=loaded.session_id,
                ),
            }
            if matching_entry is not None:
                preview.update(
                    {
                        "session_status": matching_entry.session_status,
                        "latest_resume_summary_preview": (
                            matching_entry.latest_resume_summary_preview
                        ),
                        "source_scope_summary": matching_entry.source_scope_summary,
                    }
                )
            return {
                "status": "success",
                "action": "resume-preview",
                "session_id": session_id,
                "state_root": state_root,
                "state_root_source": state_root_source,
                "resume_preview": preview,
                "recovery_hints": (
                    "当前只展示恢复提示；不会重新读取资料或调用模型。",
                ),
            }
        return {
            "status": "unavailable",
            "action": action,
            "reason": "unsupported_session_action",
            "recovery_hints": (
                "支持的 action: list, delete, expire, resume-preview。",
            ),
        }

    return _handle


def _resolve_request_state_root(
    request: Mapping[str, Any],
    *,
    storage_config: ContinuableEvidenceSessionStoragePolicyConfigView | None,
    state_root_resolver: (
        Callable[[Mapping[str, Any]], ContinuableEvidenceSessionStateRootResolution]
        | None
    ),
) -> dict[str, Any]:
    try:
        resolution = (
            state_root_resolver(request)
            if state_root_resolver is not None
            else resolve_continuable_evidence_session_state_root(
                explicit_state_root=_optional_text(request.get("state_root")),
                prompt_selected_state_root=_optional_text(
                    request.get("prompt_selected_state_root")
                ),
                config_view=storage_config,
            )
        )
    except Exception as exc:
        return {
            "status": "unavailable",
            "reason": "state_root_unavailable",
            "message": str(exc),
            "recovery_hints": (
                "请提供 --state-root，或检查默认本地状态目录配置。",
            ),
        }
    return {
        "status": "ready",
        "state_root": resolution.state_root,
        "state_root_source": resolution.state_root_source,
    }


def _build_store_record(
    request: Mapping[str, Any],
    *,
    now: datetime,
) -> dict[str, Any]:
    output = _mapping(request.get("output"))
    turns = tuple(_mapping(item) for item in _sequence(request.get("turns")))
    if not turns:
        return _unavailable("session_save_requires_turns")
    answer_run_ref = _first_ref("answer_run_ref", output, *turns)
    if not answer_run_ref:
        return _unavailable("session_save_requires_answer_run_ref")
    evidence_refs = _ref_summaries("evidence_refs", output, *turns)
    if not evidence_refs:
        return _unavailable("session_save_requires_evidence_refs")
    digest_refs = _digest_refs(output, *turns)
    if not digest_refs:
        return _unavailable("session_save_requires_digest_refs")

    session_id = f"product-console-ask-{_digest(answer_run_ref)[:16]}"
    session_ref = f"continuable-evidence-session://{session_id}"
    seed_ref = f"continuable-evidence-session-seed://{session_id}"
    summary_ref = f"continuable-evidence-session-summary://{session_id}/latest"
    artifact_index_ref = (
        f"continuable-evidence-session-artifact-index://{session_id}"
    )
    trajectory_ref = f"continuable-evidence-session-trajectory://{session_id}"
    manifest_ref = (
        f"policy://continuable-evidence-session/record-manifest/{session_id}"
    )
    created_at = _iso_z(now)
    expires_at = _iso_z(now + timedelta(days=30))
    turn_models = tuple(
        _turn_model(turn, session_ref=session_ref, session_id=session_id, now=created_at)
        for turn in turns
    )
    latest_preview = _preview(
        output.get("answer_preview")
        or turns[-1].get("answer_preview")
        or "已保存的资料问答会话，可查看恢复提示。"
    )
    question_preview = _preview(
        output.get("question_preview")
        or turns[0].get("question_preview")
        or "资料问答会话"
    )
    answer_trace_ref = _first_ref("answer_trace_ref", output, *turns)
    answer_artifact_ref = _first_ref("answer_artifact_ref", output, *turns)
    observability_summary_ref = _first_ref("observability_summary_ref", output, *turns)
    trace_inspect_ref = _first_ref("trace_inspect_ref", output, *turns)
    runtime_visible_summary = _runtime_visible_summary_model(
        output,
        *turns,
        session_ref=session_ref,
        summary_ref=summary_ref,
    )
    runtime_visible_summary_file_names = (
        ("summaries/runtime-visible.json",)
        if runtime_visible_summary is not None
        else ()
    )

    record = ContinuableEvidenceSessionLocalStoreRecord(
        storage_policy=ContinuableEvidenceSessionStoragePolicySchema(
            storage_policy_ref=STORAGE_POLICY_REF,
            continuable_evidence_session_ref=session_ref,
            local_state_root_policy_ref=STATE_ROOT_POLICY_REF,
            retention_policy_ref=RETENTION_POLICY_REF,
            delete_policy_ref=DELETE_POLICY_REF,
            export_policy_ref=EXPORT_POLICY_REF,
        ),
        local_state_root_policy=ContinuableEvidenceSessionLocalStateRootPolicySchema(
            local_state_root_policy_ref=STATE_ROOT_POLICY_REF,
        ),
        manifest=ContinuableEvidenceSessionRecordManifestSchema(
            record_manifest_ref=manifest_ref,
            continuable_evidence_session_ref=session_ref,
            record_status="resumable",
            logical_file_names=(
                "manifest.json",
                "session.json",
                "seed.json",
                "resume-policy.json",
                "artifact-index.json",
                "trajectory.json",
                "summaries/latest.json",
                *runtime_visible_summary_file_names,
                *(
                    f"turns/{turn.turn_index:04d}-{turn.turn_kind}.json"
                    for turn in turn_models
                ),
            ),
            storage_policy_ref=STORAGE_POLICY_REF,
            local_state_root_policy_ref=STATE_ROOT_POLICY_REF,
            retention_policy_ref=RETENTION_POLICY_REF,
            delete_policy_ref=DELETE_POLICY_REF,
            export_policy_ref=EXPORT_POLICY_REF,
            created_at=created_at,
            updated_at=created_at,
            expires_at=expires_at,
        ),
        index_entry=ContinuableEvidenceSessionIndexEntrySchema(
            session_id=session_id,
            continuable_evidence_session_ref=session_ref,
            session_status="resumable",
            created_at=created_at,
            updated_at=created_at,
            expires_at=expires_at,
            source_scope_summary=f"已保存资料问答：{question_preview}",
            latest_resume_summary_preview=latest_preview,
            turn_count=len(turn_models),
            evidence_ref_count=len(evidence_refs),
            digest_ref_count=len(digest_refs),
            resumable=True,
        ),
        session=ContinuableEvidenceSessionSchema(
            session_id=session_id,
            continuable_evidence_session_ref=session_ref,
            session_status="resumable",
            source_answer_run_ref=answer_run_ref,
            latest_answer_run_ref=answer_run_ref,
            session_seed_ref=seed_ref,
            session_summary_ref=summary_ref,
            session_artifact_index_ref=artifact_index_ref,
            session_trajectory_ref=trajectory_ref,
            turn_count=len(turn_models),
            evidence_ref_count=len(evidence_refs),
            digest_ref_count=len(digest_refs),
            created_at=created_at,
            updated_at=created_at,
            expires_at=expires_at,
            resumable=True,
        ),
        seed=ContinuableEvidenceSessionSeedSchema(
            seed_id=f"{session_id}-seed",
            session_seed_ref=seed_ref,
            continuable_evidence_session_ref=session_ref,
            source_request_id=str(
                output.get("request_id") or turns[0].get("request_id") or session_id
            ),
            source_answer_run_ref=answer_run_ref,
            source_answer_status=str(output.get("status") or "success"),
            evidence_refs=evidence_refs,
            digest_refs=digest_refs,
            answer_artifact_ref=answer_artifact_ref,
            trace_inspect_ref=trace_inspect_ref,
            observability_summary_ref=observability_summary_ref,
            resume_summary_ref=summary_ref,
            seed_source="initial_answer_run",
        ),
        resume_policy=ContinuableEvidenceSessionResumePolicySchema(
            policy_ref=RESUME_POLICY_REF,
            continuable_evidence_session_ref=session_ref,
            resume_allowed=True,
            resume_status="requires_confirmation",
            retention_policy_ref=RETENTION_POLICY_REF,
            export_allowed=True,
        ),
        artifact_index=ContinuableEvidenceSessionArtifactIndexSchema(
            session_artifact_index_ref=artifact_index_ref,
            continuable_evidence_session_ref=session_ref,
            answer_run_refs=(answer_run_ref,),
            answer_artifact_refs=(answer_artifact_ref,) if answer_artifact_ref else (),
            trace_inspect_refs=(trace_inspect_ref,) if trace_inspect_ref else (),
            observability_summary_refs=(
                (observability_summary_ref,) if observability_summary_ref else ()
            ),
        ),
        trajectory=ContinuableEvidenceSessionTrajectorySchema(
            session_trajectory_ref=trajectory_ref,
            continuable_evidence_session_ref=session_ref,
            user_visible_turns=tuple(
                {
                    "turn_kind": turn.turn_kind,
                    "turn_status": turn.turn_status,
                    "turn_index": turn.turn_index,
                }
                for turn in turn_models
            ),
            developer_review_refs=tuple(
                ref for ref in (trace_inspect_ref,) if ref is not None
            ),
            evidence_grounded_turn_count=sum(
                1 for turn in turn_models if turn.turn_kind != "answer_transformation"
            ),
            answer_transformation_turn_count=sum(
                1 for turn in turn_models if turn.turn_kind == "answer_transformation"
            ),
            latest_resume_summary_ref=summary_ref,
        ),
        latest_summary=ContinuableEvidenceSessionSummarySchema(
            session_summary_ref=summary_ref,
            continuable_evidence_session_ref=session_ref,
            summary_kind="resume",
            summary_text=(
                f"已保存一段可继续资料问答会话。最近摘要：{latest_preview}"
            ),
            source_refs=(answer_run_ref, digest_refs[0]),
            evidence_scope_summary=f"资料范围摘要：{question_preview}",
            last_user_intent_summary=question_preview,
            answer_state_boundary="evidence_follow_up",
        ),
        turns=turn_models,
        delete_policy=ContinuableEvidenceSessionDeletePolicySchema(
            delete_policy_ref=DELETE_POLICY_REF,
        ),
        expiration_policy=ContinuableEvidenceSessionExpirationPolicySchema(
            retention_policy_ref=RETENTION_POLICY_REF,
        ),
        export_policy=ContinuableEvidenceSessionExportPolicySchema(
            export_policy_ref=EXPORT_POLICY_REF,
        ),
        runtime_visible_summary=runtime_visible_summary,
    )
    return {"status": "ready", "record": record}


def _turn_model(
    turn: Mapping[str, Any],
    *,
    session_ref: str,
    session_id: str,
    now: str,
) -> ContinuableEvidenceSessionTurnSchema:
    index = int(turn.get("turn_index") or 1)
    answer_scoped = turn.get("answer_scoped_transformation") is True
    turn_kind = (
        "initial_question"
        if index == 1
        else ("answer_transformation" if answer_scoped else "evidence_follow_up")
    )
    return ContinuableEvidenceSessionTurnSchema(
        turn_id=f"{session_id}-turn-{index}",
        session_turn_ref=f"continuable-evidence-session-turn://{session_id}/{index}",
        continuable_evidence_session_ref=session_ref,
        turn_index=index,
        turn_kind=turn_kind,
        turn_status="success" if turn.get("status") == "success" else "unavailable",
        input_summary=_preview(turn.get("question_preview") or "资料问答"),
        output_summary=_preview(turn.get("answer_preview") or "已生成安全摘要"),
        answer_run_ref=_optional_ref(turn.get("answer_run_ref")),
        answer_artifact_ref=_optional_ref(turn.get("answer_artifact_ref")),
        trace_inspect_ref=_optional_ref(turn.get("trace_inspect_ref")),
        observability_summary_ref=_optional_ref(turn.get("observability_summary_ref")),
        requires_reauthorization=turn_kind == "evidence_follow_up",
        created_at=now,
    )


def _runtime_visible_summary_model(
    output: Mapping[str, Any],
    *turns: Mapping[str, Any],
    session_ref: str,
    summary_ref: str,
) -> ContinuableEvidenceSessionRuntimeVisibleSummarySchema | None:
    source = _runtime_visible_summary_payload(output, *turns)
    artifact_index = _runtime_artifact_index(source)
    if not source or not artifact_index:
        return None
    availability_hint = _mapping(source.get("runtime_availability_hint"))
    evaluation_summary = _mapping(source.get("runtime_evaluation_summary"))
    return ContinuableEvidenceSessionRuntimeVisibleSummarySchema(
        runtime_visible_summary_ref=f"{summary_ref}/runtime-visible",
        continuable_evidence_session_ref=session_ref,
        runtime_binding_ref=_optional_ref(source.get("runtime_binding_ref")),
        runtime_binding_status=str(
            availability_hint.get("runtime_binding_status")
            or source.get("runtime_binding_status")
            or "unavailable"
        ),
        runtime_availability_hint=str(
            availability_hint.get("hint")
            or source.get("runtime_availability_hint_text")
            or "已保存 runtime 用户可见摘要；用户 runtime 路径尚未打开。"
        ),
        trajectory_summary=_mapping(source.get("runtime_trajectory_summary")),
        artifact_index=artifact_index,
        evaluation_summary_ref=_optional_ref(
            evaluation_summary.get("evaluation_summary_ref")
            or source.get("evaluation_summary_ref")
        ),
        evaluation_status=str(
            evaluation_summary.get("evaluation_status")
            or source.get("evaluation_status")
            or "not_evaluated"
        ),
        next_actions=(
            "查看恢复预览时只展示安全摘要；不会自动恢复回答或调用模型。",
        ),
        warnings=(
            "runtime summary 是安全摘要，不表示 ADK runtime 已进入用户执行路径。",
        ),
    )


def _runtime_visible_summary_payload(
    *items: Mapping[str, Any],
) -> Mapping[str, Any]:
    for item in items:
        direct = _mapping(item.get("runtime_visible_summary"))
        if direct:
            return direct
    return {}


def _runtime_artifact_index(source: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in _sequence(source.get("runtime_artifact_index")):
        ref = _ref_value(item)
        if not ref or ref in seen:
            continue
        item_mapping = _mapping(item)
        refs.append(
            {
                "ref": ref,
                "kind": str(item_mapping.get("kind") or "runtime_artifact_ref"),
                "purpose": str(
                    item_mapping.get("purpose")
                    or "runtime_visible_summary_artifact_index"
                ),
            }
        )
        seen.add(ref)
    return tuple(refs)


def _load_runtime_visible_summary_preview(
    *,
    state_root: str,
    session_id: str,
) -> dict[str, Any]:
    session_id = _safe_session_id(session_id)
    paths = resolve_continuable_evidence_session_store_paths(state_root)
    path = paths.sessions_dir / session_id / "summaries" / "runtime-visible.json"
    if not path.exists():
        return {
            "has_runtime_visible_summary": False,
            "boundary_hints": (
                "当前会话尚未保存 runtime 用户可见摘要。",
                "恢复预览不会重新读取资料、调用模型或重放 Workflow。",
            ),
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = ContinuableEvidenceSessionRuntimeVisibleSummarySchema.model_validate(
        payload
    )
    return {
        "has_runtime_visible_summary": True,
        "runtime_visible_summary_ref": summary.runtime_visible_summary_ref,
        "runtime_binding_status": summary.runtime_binding_status,
        "runtime_availability_hint": summary.runtime_availability_hint,
        "artifact_refs": tuple(item.ref for item in summary.artifact_index),
        "evaluation_summary_ref": summary.evaluation_summary_ref,
        "evaluation_status": summary.evaluation_status,
        "user_product_runtime_path_enabled": False,
        "auto_resume_answer_enabled": False,
        "workflow_replay_enabled": False,
        "boundary_hints": (
            "runtime summary 是安全摘要，不表示 ADK runtime 已进入用户执行路径。",
            "恢复预览不会自动恢复回答、调用模型或重放 Workflow。",
        ),
    }


def _ref_summaries(
    field_name: str,
    *items: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        for ref_item in _sequence(item.get(field_name)):
            ref_value = _ref_value(ref_item)
            if ref_value and ref_value not in seen:
                refs.append({"ref": ref_value, "kind": field_name})
                seen.add(ref_value)
    return tuple(refs)


def _digest_refs(*items: Mapping[str, Any]) -> tuple[str, ...]:
    refs: list[str] = []
    seen: set[str] = set()
    for item in items:
        for field_name in ("additional_refs", "digest_refs"):
            for ref_item in _sequence(item.get(field_name)):
                ref_value = _ref_value(ref_item)
                if (
                    ref_value
                    and ref_value.startswith("governed-evidence-digest://")
                    and ref_value not in seen
                ):
                    refs.append(ref_value)
                    seen.add(ref_value)
    return tuple(refs)


def _first_ref(field_name: str, *items: Mapping[str, Any]) -> str | None:
    for item in items:
        value = _optional_ref(item.get(field_name))
        if value:
            return value
    return None


def _ref_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _optional_ref(value.get("ref"))
    return None


def _optional_ref(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _safe_session_id(value: str) -> str:
    text = _required_text(value, "session_id")
    if "/" in text or "\\" in text or text in {".", ".."} or ".." in text:
        raise ValueError("session_id must be a safe local directory name.")
    return text


def _index_entry_dict(entry: ContinuableEvidenceSessionIndexEntrySchema) -> dict[str, Any]:
    return entry.model_dump(mode="json", exclude_none=True)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> tuple[Any, ...]:
    return tuple(value) if isinstance(value, list | tuple) else ()


def _required_text(value: Any, field_name: str) -> str:
    text = _optional_text(value)
    if text is None:
        raise ValueError(f"{field_name} is required.")
    return text


def _optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _preview(value: Any, *, limit: int = 220) -> str:
    text = str(value or "").replace("\n", " ").strip()
    return (text or "已保存的资料问答会话")[:limit]


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _utc_now(now_factory: Callable[[], datetime] | None) -> datetime:
    value = now_factory() if now_factory else datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso_z(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _unavailable(reason: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "reason": reason,
        "recovery_hints": (
            "本轮输出缺少保存所需的安全 refs，未写入 session store。",
        ),
    }


__all__ = (
    "build_product_console_session_action_handler",
    "build_product_console_session_save_handler",
)
