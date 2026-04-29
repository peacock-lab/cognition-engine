from __future__ import annotations

import asyncio
from pathlib import Path

from google.adk.artifacts.file_artifact_service import FileArtifactService

from cognition_engine.adk_workflow_adapter import APP_NAME, USER_ID
from cognition_engine.artifacts.adk_file_artifact_binding import (
    ADK_FILE_ARTIFACT_SERVICE_NAME,
    bind_adk_file_artifacts,
)
from cognition_engine.rendering import generate_outputs


def with_project_path(tmp_path: Path):
    class ProjectPathContext:
        def __enter__(self):
            self.original_project_path = generate_outputs.NEW_PROJECT_PATH
            generate_outputs.NEW_PROJECT_PATH = tmp_path
            return self

        def __exit__(self, exc_type, exc, tb):
            generate_outputs.NEW_PROJECT_PATH = self.original_project_path

    return ProjectPathContext()


def test_bind_adk_file_artifacts_saves_text_artifact_and_updates_ref(
    tmp_path: Path,
) -> None:
    workflow_result = sample_workflow_result(tmp_path)
    root_dir = tmp_path / "outputs" / ".adk-artifacts"

    with with_project_path(tmp_path):
        bind_adk_file_artifacts(workflow_result, root_dir=root_dir)

    artifact_ref = workflow_result["artifact_refs"][0]
    assert artifact_ref["adk_artifact_service"] == ADK_FILE_ARTIFACT_SERVICE_NAME
    assert artifact_ref["adk_artifact_key"].endswith(".md")
    assert artifact_ref["adk_artifact_version"] == 0
    assert artifact_ref["adk_artifact_uri"].startswith("adk-file-artifact://")
    assert artifact_ref["adk_artifact_bound"] is True
    assert artifact_ref["adk_artifact_error"] is None
    assert workflow_result["validation"]["adk_file_artifacts_bound"] is True

    service = FileArtifactService(root_dir=root_dir)

    async def load_saved_text() -> str:
        loaded = await service.load_artifact(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=workflow_result["session_id"],
            filename=artifact_ref["adk_artifact_key"],
            version=artifact_ref["adk_artifact_version"],
        )
        return loaded.text

    assert asyncio.run(load_saved_text()) == "# Product brief\n\nhello\n"


def test_bind_adk_file_artifacts_writes_custom_metadata(tmp_path: Path) -> None:
    workflow_result = sample_workflow_result(tmp_path)

    with with_project_path(tmp_path):
        bind_adk_file_artifacts(
            workflow_result,
            root_dir=tmp_path / "outputs" / ".adk-artifacts",
        )

    metadata = workflow_result["artifact_refs"][0]["adk_artifact_metadata"]
    assert metadata["execution_id"] == "ce-adk-workflow-sample"
    assert metadata["session_id"] == "adk-session-sample"
    assert metadata["context_id"] == "adk-session:adk-session-sample"
    assert metadata["invocation_id"] == "ce-adk-invocation-sample"
    assert metadata["artifact_id"] == "ce-adk-workflow-sample:product_brief:output"
    assert metadata["step_name"] == "product_brief"
    assert metadata["output_type"] == "product-brief"
    assert metadata["metadata_id"] == "output-product"
    assert metadata["source_path"] == "outputs/product-briefs/sample.md"


def test_bind_adk_file_artifacts_records_failure_without_raising(
    tmp_path: Path,
) -> None:
    workflow_result = sample_workflow_result(tmp_path)

    class FailingService:
        async def save_artifact(self, **kwargs):
            raise RuntimeError("artifact backend unavailable")

    with with_project_path(tmp_path):
        bind_adk_file_artifacts(
            workflow_result,
            root_dir=tmp_path / "outputs" / ".adk-artifacts",
            service_factory=lambda root_dir: FailingService(),
        )

    artifact_ref = workflow_result["artifact_refs"][0]
    assert artifact_ref["adk_artifact_service"] == ADK_FILE_ARTIFACT_SERVICE_NAME
    assert artifact_ref["adk_artifact_bound"] is False
    assert artifact_ref["adk_artifact_version"] is None
    assert artifact_ref["adk_artifact_uri"] is None
    assert artifact_ref["adk_artifact_error"] == {
        "error_type": "RuntimeError",
        "error_message": "artifact backend unavailable",
    }
    assert workflow_result["validation"]["adk_file_artifacts_bound"] is False
    assert workflow_result["validation"]["adk_file_artifact_binding_errors"] is True


def sample_workflow_result(tmp_path: Path) -> dict:
    output_file = tmp_path / "outputs" / "product-briefs" / "sample.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("# Product brief\n\nhello\n", encoding="utf-8")

    return {
        "execution_id": "ce-adk-workflow-sample",
        "session_id": "adk-session-sample",
        "context_id": "adk-session:adk-session-sample",
        "invocation_id": "ce-adk-invocation-sample",
        "output_type": "insight-to-decision-workflow",
        "step_results": [
            {
                "name": "product_brief",
                "output_type": "product-brief",
            }
        ],
        "artifact_refs": [
            {
                "artifact_id": "ce-adk-workflow-sample:product_brief:output",
                "step_name": "product_brief",
                "kind": "business_output",
                "mapping_status": "business_artifact_mapping",
                "path": "outputs/product-briefs/sample.md",
                "metadata_file": "outputs/.metadata/product.json",
                "metadata_id": "output-product",
            }
        ],
        "validation": {},
    }
