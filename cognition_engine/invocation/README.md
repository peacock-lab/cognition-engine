# invocation

## Module Position

`invocation/` owns the cognition-engine projection of ADK invocation context semantics.

## ADK Correspondence

This module aligns with `google.adk.agents.invocation_context` and ADK Event `invocation_id` fields.

## Files

- `invocation_context.py`: ADK invocation binding plugin and invocation binding summary helpers.

## Not Responsible For

- ADK Runner or Workflow execution.
- Business workflow steps.
- Event Trace record construction.
- Artifact Manifest or FileArtifactService binding.

## control_plane Consumption

`control_plane/` consumes `build_invocation_binding_summary()` to display project invocation and ADK Event invocation binding status.
