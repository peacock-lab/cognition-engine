"""Parallel binding between workflow output files and ADK FileArtifactService."""

from __future__ import annotations

import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from google.genai import types

from cognition_engine.adk_workflow_adapter import APP_NAME, USER_ID
from cognition_engine.rendering import generate_outputs


ADK_FILE_ARTIFACT_SERVICE_NAME = "FileArtifactService"
ADK_ARTIFACT_ROOT = Path("outputs") / ".adk-artifacts"
ADK_ARTIFACT_URI_SCHEME = "adk-file-artifact"

ServiceFactory = Callable[[Path], Any]


def bind_adk_file_artifacts(
    workflow_result: Dict[str, Any],
    *,
    root_dir: Optional[Path] = None,
    service_factory: Optional[ServiceFactory] = None,
) -> Dict[str, Any]:
    """Save workflow artifacts to ADK FileArtifactService and update artifact refs.

    Binding is deliberately best-effort: failures are recorded on each artifact ref
    and never raised into the workflow run.
    """

    artifact_refs = workflow_result.get("artifact_refs") or []
    if not artifact_refs:
        return workflow_result

    artifact_root = root_dir or default_adk_artifact_root()
    try:
        service = _build_service(artifact_root, service_factory)
    except Exception as exc:  # noqa: BLE001 - binding must not break workflow
        for artifact_ref in artifact_refs:
            _record_binding_failure(
                workflow_result,
                artifact_ref,
                artifact_root=artifact_root,
                exc=exc,
            )
        _update_validation(workflow_result)
        return workflow_result

    for artifact_ref in artifact_refs:
        _bind_single_artifact_ref(
            workflow_result,
            artifact_ref,
            service=service,
            artifact_root=artifact_root,
        )

    _update_validation(workflow_result)
    return workflow_result


def default_adk_artifact_root() -> Path:
    return generate_outputs.NEW_PROJECT_PATH / ADK_ARTIFACT_ROOT


def _build_service(root_dir: Path, service_factory: Optional[ServiceFactory]) -> Any:
    root_dir.mkdir(parents=True, exist_ok=True)
    if service_factory:
        return service_factory(root_dir)

    from google.adk.artifacts.file_artifact_service import FileArtifactService

    return FileArtifactService(root_dir=root_dir)


def _bind_single_artifact_ref(
    workflow_result: Dict[str, Any],
    artifact_ref: Dict[str, Any],
    *,
    service: Any,
    artifact_root: Path,
) -> None:
    artifact_ref["adk_artifact_service"] = ADK_FILE_ARTIFACT_SERVICE_NAME
    artifact_ref["adk_artifact_root"] = _display_project_path(artifact_root)

    try:
        source_path = _resolve_source_path(artifact_ref.get("path"))
        if not source_path or not source_path.exists():
            raise FileNotFoundError(f"artifact source file not found: {artifact_ref.get('path')}")

        artifact_key = _artifact_key(artifact_ref)
        content = source_path.read_text(encoding="utf-8")
        custom_metadata = _custom_metadata(workflow_result, artifact_ref, source_path)
        version = _run_coroutine(
            service.save_artifact(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=workflow_result.get("session_id"),
                filename=artifact_key,
                artifact=types.Part.from_text(text=content),
                custom_metadata=custom_metadata,
            )
        )

        artifact_ref.update(
            {
                "adk_artifact_key": artifact_key,
                "adk_artifact_version": version,
                "adk_artifact_uri": _artifact_uri(
                    session_id=workflow_result.get("session_id"),
                    artifact_key=artifact_key,
                    version=version,
                ),
                "adk_artifact_bound": True,
                "adk_artifact_error": None,
                "adk_artifact_metadata": custom_metadata,
            }
        )
    except Exception as exc:  # noqa: BLE001 - best-effort governance binding
        _record_binding_failure(
            workflow_result,
            artifact_ref,
            artifact_root=artifact_root,
            exc=exc,
        )


def _record_binding_failure(
    workflow_result: Dict[str, Any],
    artifact_ref: Dict[str, Any],
    *,
    artifact_root: Path,
    exc: Exception,
) -> None:
    artifact_ref.update(
        {
            "adk_artifact_service": ADK_FILE_ARTIFACT_SERVICE_NAME,
            "adk_artifact_root": _display_project_path(artifact_root),
            "adk_artifact_key": artifact_ref.get("adk_artifact_key")
            or _artifact_key(artifact_ref),
            "adk_artifact_version": None,
            "adk_artifact_uri": None,
            "adk_artifact_bound": False,
            "adk_artifact_error": {
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
            "adk_artifact_metadata": _custom_metadata(
                workflow_result,
                artifact_ref,
                _resolve_source_path(artifact_ref.get("path")),
            ),
        }
    )


def _resolve_source_path(path_value: Any) -> Optional[Path]:
    if not path_value:
        return None

    path = Path(str(path_value))
    if path.is_absolute():
        return path
    return generate_outputs.NEW_PROJECT_PATH / path


def _artifact_key(artifact_ref: Dict[str, Any]) -> str:
    step_name = str(artifact_ref.get("step_name") or "artifact")
    kind = str(artifact_ref.get("kind") or "output")
    path_value = str(artifact_ref.get("path") or artifact_ref.get("artifact_id") or "artifact")
    suffix = Path(path_value).suffix or ".txt"
    stem = Path(path_value).stem or "artifact"
    raw_key = f"{step_name}-{kind}-{stem}{suffix}"
    return re.sub(r"[^A-Za-z0-9._-]+", "-", raw_key).strip("-") or "artifact.txt"


def _custom_metadata(
    workflow_result: Dict[str, Any],
    artifact_ref: Dict[str, Any],
    source_path: Optional[Path],
) -> Dict[str, Any]:
    return {
        "execution_id": workflow_result.get("execution_id"),
        "session_id": workflow_result.get("session_id"),
        "context_id": workflow_result.get("context_id"),
        "invocation_id": workflow_result.get("invocation_id"),
        "artifact_id": artifact_ref.get("artifact_id"),
        "step_name": artifact_ref.get("step_name"),
        "kind": artifact_ref.get("kind"),
        "output_type": _output_type(workflow_result, artifact_ref),
        "metadata_id": artifact_ref.get("metadata_id"),
        "metadata_file": artifact_ref.get("metadata_file"),
        "mapping_status": artifact_ref.get("mapping_status"),
        "source_path": artifact_ref.get("path"),
        "source_file_exists": bool(source_path and source_path.exists()),
    }


def _output_type(
    workflow_result: Dict[str, Any],
    artifact_ref: Dict[str, Any],
) -> Optional[str]:
    step_name = artifact_ref.get("step_name")
    if step_name == "workflow":
        return workflow_result.get("output_type")

    for step_result in workflow_result.get("step_results", []):
        if step_result.get("name") == step_name:
            return step_result.get("output_type")
    return None


def _artifact_uri(
    *,
    session_id: Optional[str],
    artifact_key: str,
    version: int,
) -> str:
    session_segment = session_id or "global"
    return (
        f"{ADK_ARTIFACT_URI_SCHEME}://{APP_NAME}/{USER_ID}/sessions/"
        f"{session_segment}/artifacts/{artifact_key}/versions/{version}"
    )


def _display_project_path(path: Path) -> str:
    try:
        return str(path.relative_to(generate_outputs.NEW_PROJECT_PATH))
    except ValueError:
        return str(path)


def _update_validation(workflow_result: Dict[str, Any]) -> None:
    artifact_refs = workflow_result.get("artifact_refs") or []
    validation = workflow_result.setdefault("validation", {})
    validation["adk_file_artifacts_bound"] = all(
        bool(ref.get("adk_artifact_bound")) for ref in artifact_refs
    ) if artifact_refs else False
    validation["adk_file_artifact_binding_attempted"] = bool(artifact_refs)
    validation["adk_file_artifact_binding_errors"] = any(
        bool(ref.get("adk_artifact_error")) for ref in artifact_refs
    )


def _run_coroutine(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()
