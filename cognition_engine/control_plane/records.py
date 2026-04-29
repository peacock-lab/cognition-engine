"""Control-plane record constants and small record helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from cognition_engine.sessions import shared_run_identity

BUNDLE_TYPE = "control_plane_bundle"
BUNDLE_VERSION = "ce-control-plane-bundle/v1"

CONTEXT_RECORD_TYPE = "context_record"
CONTEXT_RECORD_VERSION = "ce-context-record/v1"

RUN_RECORD_TYPE = "run_record"
RUN_RECORD_VERSION = "ce-run-record/v1"

EVENT_TRACE_TYPE = "event_trace"
EVENT_TRACE_VERSION = "ce-event-trace/v1"

ARTIFACT_MANIFEST_TYPE = "artifact_manifest"
ARTIFACT_MANIFEST_VERSION = "ce-artifact-manifest/v1"


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
