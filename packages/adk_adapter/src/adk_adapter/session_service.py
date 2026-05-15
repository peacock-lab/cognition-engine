"""Service-level adapter for Google ADK SessionService."""

from __future__ import annotations

from typing import Any

from adk_adapter.async_utils import run_sync


class AdkSessionServiceAdapter:
    """Thin adapter around an ADK BaseSessionService implementation."""

    def __init__(
        self,
        service: Any | None = None,
        *,
        app_name: str = "cognition_engine_adk_adapter",
        user_id: str = "cognition-engine-adk-user",
    ) -> None:
        if service is None:
            from google.adk.sessions import InMemorySessionService

            service = InMemorySessionService()
        self._service = service
        self.app_name = app_name
        self.user_id = user_id

    @property
    def adk_service(self) -> Any:
        """Return the wrapped ADK service for Runner injection."""

        return self._service

    async def create_session(
        self,
        *,
        state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Any:
        """Create an ADK session."""

        return await self._service.create_session(
            app_name=self.app_name,
            user_id=self.user_id,
            state=state,
            session_id=session_id,
        )

    def create_session_sync(
        self,
        *,
        state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Any:
        """Sync wrapper for create_session."""

        return run_sync(self.create_session(state=state, session_id=session_id))

    async def get_session(
        self,
        *,
        session_id: str,
        config: Any | None = None,
    ) -> Any | None:
        """Load an ADK session."""

        return await self._service.get_session(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=session_id,
            config=config,
        )

    def get_session_sync(self, *, session_id: str, config: Any | None = None) -> Any | None:
        """Sync wrapper for get_session."""

        return run_sync(self.get_session(session_id=session_id, config=config))

    async def list_sessions(self) -> Any:
        """List ADK sessions."""

        return await self._service.list_sessions(app_name=self.app_name, user_id=self.user_id)

    def list_sessions_sync(self) -> Any:
        """Sync wrapper for list_sessions."""

        return run_sync(self.list_sessions())

    async def delete_session(self, *, session_id: str) -> None:
        """Delete an ADK session."""

        await self._service.delete_session(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=session_id,
        )

    async def append_event(self, *, session: Any, event: Any) -> Any:
        """Append an ADK event to an ADK session."""

        return await self._service.append_event(session, event)

    def append_event_sync(self, *, session: Any, event: Any) -> Any:
        """Sync wrapper for append_event."""

        return run_sync(self.append_event(session=session, event=event))

    def metadata(self) -> dict[str, Any]:
        """Return adapter metadata without leaking ADK objects."""

        return {
            "adapter": "adk_adapter.session_service",
            "adk_service_type": type(self._service).__name__,
            "app_name": self.app_name,
            "user_id": self.user_id,
        }
