# runtime

## Module Position

`runtime/` owns lightweight helpers for ADK Runner/App execution boundaries.

## ADK Correspondence

This module aligns with ADK Runner, App, Workflow, and BaseNode runtime concepts.

## Files

- `runner.py`: runtime path constants, Runner/App construction, and `run_async` event collection helpers.

## Not Responsible For

- Business workflow step implementation.
- Invocation binding.
- Event normalization or Event Trace projection.
- Session/context projection details.
- ArtifactService binding.

## adk_workflow_adapter.py Consumption

`adk_workflow_adapter.py` uses this module to build the ADK Runner and collect ADK events while keeping workflow-specific step wrapping local.
