# Cognition Engine

`cognition-engine` is a Google ADK-based cognition engine and middleware skeleton. It organizes context, invocation, events, runtime, sessions, workflow results, artifacts, and governance records into testable Python modules.

Current version:

```text
v0.4.0
```

`v0.4.0` is a core-skeleton formalization release. It does not claim a finished product onboarding flow, a full telemetry stack, a configuration or contract center, or a complete agent governance platform.

## What Is Included

The v0.4.0 skeleton is aligned around these source modules:

- `cognition_engine.artifacts`: ADK FileArtifactService binding skeleton.
- `cognition_engine.invocation`: ADK Invocation semantic binding skeleton.
- `cognition_engine.events`: ADK Event / Trace field binding skeleton.
- `cognition_engine.runtime`: runtime and runner adapter skeleton.
- `cognition_engine.sessions`: session binding skeleton.
- `cognition_engine.workflows`: workflow result and workflow binding skeleton.
- `cognition_engine.control_plane`: governance records and bundle skeleton.

The control-plane layer currently covers:

- Context Record
- Run Record
- Event Trace
- Artifact Manifest
- Control Plane Bundle

These records make one cognition run easier to inspect and package. They are still skeleton-level governance records, not a finished observability or governance console.

## Install

This project uses `uv` as the preferred dependency, test, and build entry:

```bash
git clone <repo-url>
cd cognition-engine
uv sync --extra test --extra release
```

Check the CLI:

```bash
uv run python -m cognition_engine.cli --help
```

A standard editable Python install can still be used when `uv` is unavailable, but it is not the default path for this repository:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test,release]"
```

## CLI Entries

Current public CLI entries focus on minimal workflow execution and public-facing generated summaries:

```bash
uv run ce brief --insight insight-adk-runner-centrality --json
uv run ce decision-pack --insight insight-adk-runner-centrality --json
uv run ce workflow --insight insight-adk-runner-centrality --json
uv run python -m cognition_engine.workflow --insight insight-adk-runner-centrality --json
```

`python -m cognition_engine.workflow` remains a compatibility entry. The newer skeleton code lives under `workflows`, `runtime`, `sessions`, `events`, `invocation`, `artifacts`, and `control_plane`.

Real workflow runs may create files under `outputs/`. Clean generated outputs before release checks or public repository synchronization.

## Verification

Focused tests:

```bash
uv run python -m pytest \
  tests/unit/test_workflow_loop.py \
  tests/unit/test_control_plane_bundle.py \
  tests/unit/test_adk_file_artifact_binding.py \
  tests/unit/test_adk_workflow_adapter.py \
  tests/unit/test_invocation_context.py \
  tests/unit/test_events_event_trace.py \
  tests/unit/test_runtime_runner.py \
  tests/unit/test_sessions_session.py \
  tests/unit/test_workflows_workflow.py \
  -q
```

Build dry-run:

```bash
rm -rf dist build *.egg-info
uv run python -m build --sdist --wheel
```

The built wheel and sdist should be versioned `0.4.0` and must not include private task chains, generated outputs, local virtual environments, cache folders, or internal project-governance documents.

## Release Status

The v0.4.0 materials are in release-preparation repair:

- Package metadata target: `0.4.0`
- Git tag: pending final release decision
- GitHub Release: pending final release decision
- PyPI: pending final release decision
- Public repository sync: pending public-boundary evidence

Release draft materials are stored under:

```text
docs/项目/认知引擎 v0.4.0 版本建设项目/release/
```

## Boundaries

v0.4.0 does not claim:

- a complete productized user-consumption loop;
- full telemetry or tracing integration;
- a finished configuration center, contract center, or policy center;
- a complete agent governance platform;
- completed GitHub Release, PyPI upload, or public repository synchronization.

Its purpose is to make the ADK-aligned runtime skeleton testable, buildable, and ready for the next release decision.
