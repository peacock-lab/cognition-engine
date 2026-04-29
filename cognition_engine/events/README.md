# events

## Module Position

`events/` owns ADK Event normalization and Event Trace projection helpers.

## ADK Correspondence

This module aligns with `google.adk.events.event.Event` and its native event fields.

## Files

- `event.py`: converts ADK Events into JSON-friendly dictionaries.
- `event_trace.py`: projects normalized ADK Events into Event Trace records, coverage, and status summaries.

## Not Responsible For

- ADK Runner execution.
- Invocation context binding.
- Business step event creation.
- Telemetry, tracing, metrics, or span exporters.

## control_plane Consumption

`control_plane/` consumes `build_event_trace_governance()` to assemble Event Trace, Run Record, and Context Record event summaries.
