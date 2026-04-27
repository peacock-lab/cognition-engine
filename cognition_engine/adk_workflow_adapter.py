"""ADK-backed adapter for the insight-to-decision workflow."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from uuid import uuid4


StepBuilder = Callable[[str], Dict[str, Any]]

APP_NAME = "cognition_engine_adk_backed_workflow"
USER_ID = "cognition-engine-workflow-user"
ADK_RUNTIME_PATH = "Runner -> Workflow -> BaseNode business steps"
ADK_ARTIFACT_MAPPING_STATUS = "business_artifact_mapping"


@dataclass(frozen=True)
class WorkflowStep:
    name: str
    output_type: str
    builder: StepBuilder


def run_adk_backed_workflow(
    *,
    insight_id: str,
    result_base: Dict[str, Any],
    steps: list[WorkflowStep],
) -> Dict[str, Any]:
    adapter = AdkBackedWorkflowAdapter(insight_id=insight_id, steps=steps)
    return adapter.run(result_base)


class AdkBackedWorkflowAdapter:
    def __init__(self, *, insight_id: str, steps: list[WorkflowStep]) -> None:
        self.insight_id = insight_id
        self.steps = steps
        self.execution_id = f"ce-adk-workflow-{uuid4().hex}"
        self.invocation_id = f"ce-adk-invocation-{uuid4().hex}"
        self.session_id: Optional[str] = None
        self.context_id: Optional[str] = None
        self.step_summaries: list[Dict[str, Any]] = []
        self.child_summaries: dict[str, Optional[Dict[str, Any]]] = {
            step.name: None for step in steps
        }
        self.business_events: list[Dict[str, Any]] = []
        self.adk_events: list[Dict[str, Any]] = []
        self.halted = False

    def run(self, result_base: Dict[str, Any]) -> Dict[str, Any]:
        asyncio.run(self._run_with_adk())
        status = self._workflow_status()
        result = dict(result_base)
        result.update(
            {
                "status": status,
                "execution_id": self.execution_id,
                "session_id": self.session_id,
                "context_id": self.context_id,
                "invocation_id": self.invocation_id,
                "adk_runtime": ADK_RUNTIME_PATH,
                "adk_backed": True,
                "legacy_fallback_used": False,
                "steps": self.step_summaries,
                "step_results": list(self.step_summaries),
                "product_brief": self.child_summaries.get("product_brief"),
                "decision_pack": self.child_summaries.get("decision_pack"),
                "model_enhancement": self.child_summaries.get("model_enhancement"),
                "artifact_refs": self._build_artifact_refs(),
                "event_summary": self._build_event_summary(),
                "validation": self._build_validation(),
                "error_code": self._result_error_code(status),
                "error_message": self._result_error_message(status),
            }
        )
        return result

    async def _run_with_adk(self) -> None:
        from google.adk.agents.context import Context
        from google.adk.runners import Runner
        from google.adk.sessions.in_memory_session_service import InMemorySessionService
        from google.adk.workflow import Workflow
        from google.adk.workflow._base_node import START
        from google.adk.workflow._base_node import BaseNode
        from google.genai import types

        adapter = self

        class BusinessStepNode(BaseNode):
            async def _run_impl(self, *, ctx: Context, node_input: Any):
                del node_input
                step = adapter._step_by_name(self.name)
                if adapter.halted:
                    adapter._record_business_event(
                        step.name,
                        "skipped",
                        output_type=step.output_type,
                    )
                    yield f"{step.name}:skipped"
                    return

                adapter._record_business_event(
                    step.name,
                    "started",
                    output_type=step.output_type,
                )
                child_result = await asyncio.to_thread(adapter._execute_step, step)
                child_summary = _summarize_child_result(child_result)
                adapter.child_summaries[step.name] = child_summary
                adapter.step_summaries.append(_build_step_summary(step.name, child_summary))
                adapter._record_business_event(
                    step.name,
                    child_summary["status"],
                    output_type=child_summary["output_type"],
                    output_file=child_summary["output_file"],
                    metadata_file=child_summary["metadata_file"],
                    error_code=child_summary["error_code"],
                    error_message=child_summary["error_message"],
                )
                ctx.state[f"ce_workflow_{step.name}_status"] = child_summary["status"]
                ctx.state[f"ce_workflow_{step.name}_output_file"] = child_summary["output_file"]
                if adapter._should_halt(step.name, child_summary):
                    adapter.halted = True
                    ctx.state["ce_workflow_halted_at"] = step.name
                yield f"{step.name}:{child_summary['status']}"

        nodes = [BusinessStepNode(name=step.name) for step in self.steps]
        workflow = Workflow(
            name="ce_adk_backed_insight_to_decision_workflow",
            edges=[(START, *nodes)],
        )
        session_service = InMemorySessionService()
        runner = Runner(
            app_name=APP_NAME,
            node=workflow,
            session_service=session_service,
        )
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
        )
        self.session_id = session.id
        self.context_id = f"adk-session:{session.id}"
        message = types.Content(
            role="user",
            parts=[types.Part(text=f"ce workflow insight_id={self.insight_id}")],
        )

        events = []
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session.id,
            new_message=message,
        ):
            events.append(event)

        self.adk_events = [_serialize_adk_event(event) for event in events]

    def _step_by_name(self, step_name: str) -> WorkflowStep:
        for step in self.steps:
            if step.name == step_name:
                return step
        raise KeyError(step_name)

    def _execute_step(self, step: WorkflowStep) -> Dict[str, Any]:
        try:
            return step.builder(self.insight_id)
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "error",
                "contract_version": None,
                "output_type": step.output_type,
                "output_file": None,
                "metadata_file": None,
                "metadata_id": None,
                "error_code": getattr(exc, "error_code", type(exc).__name__),
                "error_message": getattr(exc, "error_message", str(exc)),
                "validation": {
                    "output_file_exists": False,
                    "metadata_file_exists": False,
                },
            }

    def _should_halt(self, step_name: str, child_summary: Dict[str, Any]) -> bool:
        if child_summary["status"] == "success":
            return False
        return step_name in {"product_brief", "decision_pack"}

    def _workflow_status(self) -> str:
        enhancement_summary = self.child_summaries.get("model_enhancement")
        if enhancement_summary:
            if enhancement_summary["status"] == "success":
                return "success"
            return "partial_success"

        decision_summary = self.child_summaries.get("decision_pack")
        if decision_summary and decision_summary["status"] != "success":
            return "error"

        product_summary = self.child_summaries.get("product_brief")
        if product_summary and product_summary["status"] != "success":
            return "error"

        return "error"

    def _result_error_code(self, status: str) -> Optional[str]:
        if status == "success":
            return None
        failed_summary = self._first_failed_summary()
        return failed_summary.get("error_code") if failed_summary else "workflow_failed"

    def _result_error_message(self, status: str) -> Optional[str]:
        if status == "success":
            return None
        failed_summary = self._first_failed_summary()
        return failed_summary.get("error_message") if failed_summary else "workflow failed"

    def _first_failed_summary(self) -> Optional[Dict[str, Any]]:
        for step in self.steps:
            summary = self.child_summaries.get(step.name)
            if summary and summary.get("status") != "success":
                return summary
        return None

    def _build_validation(self) -> Dict[str, bool]:
        product_summary = self.child_summaries.get("product_brief")
        decision_summary = self.child_summaries.get("decision_pack")
        enhancement_summary = self.child_summaries.get("model_enhancement")
        return {
            "workflow_output_file_exists": False,
            "workflow_metadata_file_exists": False,
            "product_brief_output_file_exists": _validation_value(
                product_summary,
                "output_file_exists",
            ),
            "product_brief_metadata_file_exists": _validation_value(
                product_summary,
                "metadata_file_exists",
            ),
            "decision_pack_output_file_exists": _validation_value(
                decision_summary,
                "output_file_exists",
            ),
            "decision_pack_metadata_file_exists": _validation_value(
                decision_summary,
                "metadata_file_exists",
            ),
            "model_enhancement_output_file_exists": _validation_value(
                enhancement_summary,
                "output_file_exists",
            ),
            "model_enhancement_metadata_file_exists": _validation_value(
                enhancement_summary,
                "metadata_file_exists",
            ),
            "adk_backed_workflow": True,
            "adk_session_mapped": bool(self.session_id),
            "adk_invocation_mapped": bool(self.invocation_id),
            "adk_events_mapped": bool(self.adk_events or self.business_events),
            "adk_artifacts_mapped": True,
            "legacy_fallback_used": False,
        }

    def _build_artifact_refs(self) -> list[Dict[str, Any]]:
        artifact_refs: list[Dict[str, Any]] = []
        for step in self.steps:
            summary = self.child_summaries.get(step.name)
            if not summary:
                continue
            artifact_refs.append(
                {
                    "artifact_id": f"{self.execution_id}:{step.name}:output",
                    "step_name": step.name,
                    "kind": "business_output",
                    "mapping_status": ADK_ARTIFACT_MAPPING_STATUS,
                    "path": summary.get("output_file"),
                    "metadata_file": summary.get("metadata_file"),
                    "metadata_id": summary.get("metadata_id"),
                }
            )
        return artifact_refs

    def _build_event_summary(self) -> Dict[str, Any]:
        return {
            "source": "ADK Runner events plus business step event mapping",
            "adk_runtime_path": ADK_RUNTIME_PATH,
            "adk_event_count": len(self.adk_events),
            "business_event_count": len(self.business_events),
            "step_events": list(self.business_events),
            "adk_events": list(self.adk_events),
        }

    def _record_business_event(
        self,
        step_name: str,
        status: str,
        *,
        output_type: Optional[str],
        output_file: Optional[str] = None,
        metadata_file: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        self.business_events.append(
            {
                "execution_id": self.execution_id,
                "session_id": self.session_id,
                "context_id": self.context_id,
                "invocation_id": self.invocation_id,
                "step_name": step_name,
                "status": status,
                "output_type": output_type,
                "output_file": output_file,
                "metadata_file": metadata_file,
                "error_code": error_code,
                "error_message": error_message,
                "timestamp": _now_utc_iso(),
            }
        )


def add_workflow_artifact_ref(result: Dict[str, Any]) -> None:
    artifact_refs = result.setdefault("artifact_refs", [])
    artifact_refs.append(
        {
            "artifact_id": f"{result['execution_id']}:workflow:output",
            "step_name": "workflow",
            "kind": "workflow_summary",
            "mapping_status": ADK_ARTIFACT_MAPPING_STATUS,
            "path": result.get("output_file"),
            "metadata_file": result.get("metadata_file"),
            "metadata_id": result.get("metadata_id"),
        }
    )


def _summarize_child_result(child_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": child_result.get("status"),
        "contract_version": child_result.get("contract_version"),
        "output_type": child_result.get("output_type"),
        "output_file": child_result.get("output_file"),
        "metadata_file": child_result.get("metadata_file"),
        "metadata_id": child_result.get("metadata_id"),
        "error_code": child_result.get("error_code"),
        "error_message": child_result.get("error_message"),
        "validation": child_result.get("validation", {}),
    }


def _build_step_summary(
    step_name: str,
    child_summary: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "name": step_name,
        "status": child_summary["status"],
        "output_type": child_summary["output_type"],
        "output_file": child_summary["output_file"],
        "metadata_file": child_summary["metadata_file"],
        "error_code": child_summary["error_code"],
        "error_message": child_summary["error_message"],
    }


def _validation_value(
    child_summary: Optional[Dict[str, Any]],
    key: str,
) -> bool:
    if not child_summary:
        return False
    validation = child_summary.get("validation", {})
    return bool(validation.get(key))


def _serialize_adk_event(event: object) -> Dict[str, Any]:
    node_info = getattr(event, "node_info", None)
    node_path = getattr(node_info, "path", None)
    return {
        "author": getattr(event, "author", None),
        "node_name": _extract_node_name(node_path),
        "node_path": node_path,
        "output": getattr(event, "output", None),
    }


def _extract_node_name(node_path: Optional[str]) -> Optional[str]:
    if not node_path:
        return None
    node_name = node_path.rsplit("/", 1)[-1]
    if "@" in node_name:
        node_name = node_name.rsplit("@", 1)[0]
    return node_name


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
