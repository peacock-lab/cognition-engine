"""ADK session helpers and Context Record projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


ADK_SESSION_SERVICE_NAME = "InMemorySessionService"


@dataclass(frozen=True)
class SessionContext:
    session: Any
    session_id: str
    context_id: str


def create_in_memory_session_service() -> Any:
    from google.adk.sessions.in_memory_session_service import InMemorySessionService

    return InMemorySessionService()


async def create_session_context(
    session_service: Any,
    *,
    app_name: str,
    user_id: str,
) -> SessionContext:
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
    )
    session_id = session.id
    return SessionContext(
        session=session,
        session_id=session_id,
        context_id=context_id_from_session_id(session_id),
    )


def context_id_from_session_id(session_id: Optional[str]) -> Optional[str]:
    if not session_id:
        return None
    return f"adk-session:{session_id}"


def shared_run_identity(workflow_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "execution_id": workflow_result.get("execution_id"),
        "session_id": workflow_result.get("session_id"),
        "context_id": workflow_result.get("context_id"),
        "invocation_id": workflow_result.get("invocation_id"),
    }


def build_adk_session_binding(session_id: Optional[str]) -> Dict[str, Any]:
    return {
        "session_service": ADK_SESSION_SERVICE_NAME if session_id else None,
        "session_id": session_id,
        "binding_status": "adk_session_mapped" if session_id else "missing_adk_session",
    }


def build_project_context_binding(
    *,
    execution_id: Optional[str],
    context_id: Optional[str],
    invocation_id: Optional[str],
) -> Dict[str, Any]:
    return {
        "execution_id": execution_id,
        "context_id": context_id,
        "invocation_id": invocation_id,
        "binding_status": (
            "project_context_id_over_adk_session"
            if context_id
            else "missing_project_context_id"
        ),
    }
