"""Service-level adapter for Google ADK ArtifactService."""

from __future__ import annotations

from typing import Any

from adk_adapter.async_utils import run_sync


class AdkArtifactServiceAdapter:
    """Thin adapter around an ADK BaseArtifactService implementation."""

    def __init__(
        self,
        service: Any | None = None,
        *,
        app_name: str = "cognition_engine_adk_adapter",
        user_id: str = "cognition-engine-adk-user",
        session_id: str | None = None,
    ) -> None:
        if service is None:
            from google.adk.artifacts import InMemoryArtifactService

            service = InMemoryArtifactService()
        self._service = service
        self.app_name = app_name
        self.user_id = user_id
        self.session_id = session_id

    @property
    def adk_service(self) -> Any:
        """Return the wrapped ADK service for Runner injection."""

        return self._service

    async def save_artifact(
        self,
        *,
        filename: str,
        artifact: Any,
        session_id: str | None = None,
        custom_metadata: dict[str, Any] | None = None,
    ) -> int:
        """Save an artifact through ADK ArtifactService."""

        return await self._service.save_artifact(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=session_id if session_id is not None else self.session_id,
            filename=filename,
            artifact=artifact,
            custom_metadata=custom_metadata,
        )

    def save_artifact_sync(
        self,
        *,
        filename: str,
        artifact: Any,
        session_id: str | None = None,
        custom_metadata: dict[str, Any] | None = None,
    ) -> int:
        """Sync wrapper for save_artifact."""

        return run_sync(
            self.save_artifact(
                filename=filename,
                artifact=artifact,
                session_id=session_id,
                custom_metadata=custom_metadata,
            )
        )

    async def load_artifact(
        self,
        *,
        filename: str,
        session_id: str | None = None,
        version: int | None = None,
    ) -> Any | None:
        """Load an artifact through ADK ArtifactService."""

        return await self._service.load_artifact(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=session_id if session_id is not None else self.session_id,
            filename=filename,
            version=version,
        )

    def load_artifact_sync(
        self,
        *,
        filename: str,
        session_id: str | None = None,
        version: int | None = None,
    ) -> Any | None:
        """Sync wrapper for load_artifact."""

        return run_sync(
            self.load_artifact(filename=filename, session_id=session_id, version=version)
        )

    async def list_artifact_keys(self, *, session_id: str | None = None) -> list[str]:
        """List artifact keys through ADK ArtifactService."""

        return await self._service.list_artifact_keys(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=session_id if session_id is not None else self.session_id,
        )

    def list_artifact_keys_sync(self, *, session_id: str | None = None) -> list[str]:
        """Sync wrapper for list_artifact_keys."""

        return run_sync(self.list_artifact_keys(session_id=session_id))

    async def list_versions(
        self,
        *,
        filename: str,
        session_id: str | None = None,
    ) -> list[int]:
        """List artifact versions through ADK ArtifactService."""

        return await self._service.list_versions(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=session_id if session_id is not None else self.session_id,
            filename=filename,
        )

    def list_versions_sync(
        self,
        *,
        filename: str,
        session_id: str | None = None,
    ) -> list[int]:
        """Sync wrapper for list_versions."""

        return run_sync(self.list_versions(filename=filename, session_id=session_id))

    async def list_artifact_versions(
        self,
        *,
        filename: str,
        session_id: str | None = None,
    ) -> list[Any]:
        """List artifact version records through ADK ArtifactService."""

        return await self._service.list_artifact_versions(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=session_id if session_id is not None else self.session_id,
            filename=filename,
        )

    async def get_artifact_version(
        self,
        *,
        filename: str,
        session_id: str | None = None,
        version: int | None = None,
    ) -> Any | None:
        """Return one ADK artifact version record."""

        return await self._service.get_artifact_version(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=session_id if session_id is not None else self.session_id,
            filename=filename,
            version=version,
        )

    async def delete_artifact(
        self,
        *,
        filename: str,
        session_id: str | None = None,
    ) -> None:
        """Delete an artifact through ADK ArtifactService."""

        await self._service.delete_artifact(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=session_id if session_id is not None else self.session_id,
            filename=filename,
        )

    def metadata(self) -> dict[str, Any]:
        """Return adapter metadata without leaking ADK objects."""

        return {
            "adapter": "adk_adapter.artifact_service",
            "adk_service_type": type(self._service).__name__,
            "app_name": self.app_name,
            "user_id": self.user_id,
            "session_id": self.session_id,
        }
