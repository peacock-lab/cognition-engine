# sessions

## Module Position

`sessions/` owns lightweight helpers for ADK sessions and cognition-engine context projection.

## ADK Correspondence

This module aligns with ADK sessions and `InMemorySessionService`.

## Files

- `session.py`: session service creation, session/context id derivation, and Context Record session projection helpers.

## Not Responsible For

- ADK Runner/App construction.
- Invocation binding.
- Event Trace projection.
- ArtifactService binding.
- Business workflow step implementation.
- A top-level `context/` module.

## adk_workflow_adapter.py and control_plane Consumption

`adk_workflow_adapter.py` uses this module to create sessions and derive `context_id`. `control_plane/` uses it to assemble session/context bindings.
