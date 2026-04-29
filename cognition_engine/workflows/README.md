# workflows

## Module Position

`workflows/` owns cognition-engine workflow orchestration.

## ADK Correspondence

This module aligns with the ADK `google.adk.workflow` capability domain.

## Files

- `workflow.py`: workflow request validation, result assembly, output attachment, markdown rendering, and loop helpers.

## Not Responsible For

- ADK Runner/App construction.
- ADK session service creation.
- Invocation binding internals.
- ADK Event normalization or Event Trace projection.
- ArtifactService binding internals.
- Control-plane record internals.

## Top-Level Consumption

Top-level `cognition_engine/workflow.py` re-exports this module for compatibility and keeps `python -m cognition_engine.workflow` available.
