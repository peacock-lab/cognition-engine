# Quickstart

This quickstart uses the v0.4.0 public release-preparation surface of `cognition-engine`.

## 1. Install With uv

```bash
git clone <repo-url>
cd cognition-engine
uv sync --extra test --extra release
```

Check the CLI:

```bash
uv run python -m cognition_engine.cli --help
```

## 2. Run A Minimal Workflow

The compatibility workflow module can be invoked directly:

```bash
uv run python -m cognition_engine.workflow --insight insight-adk-runner-centrality --json
```

Equivalent CLI entry:

```bash
uv run ce workflow --insight insight-adk-runner-centrality --json
```

Other current CLI entries:

```bash
uv run ce brief --insight insight-adk-runner-centrality --json
uv run ce decision-pack --insight insight-adk-runner-centrality --json
```

Real workflow runs may create files under `outputs/`. When using these commands for release checks or local smoke verification, clean generated outputs afterward so build artifacts do not accidentally capture runtime files.

## 3. Run Focused Tests

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

## 4. Optional Build Dry-Run

```bash
rm -rf dist build *.egg-info
uv run python -m build --sdist --wheel
```

After the build, verify that the generated wheel and sdist are versioned `0.4.0` and do not include generated outputs, private task packages, local environments, cache folders, or internal project-governance documents.

## 5. Scope

v0.4.0 exposes a Google ADK-aligned cognition engine skeleton:

- `artifacts`
- `invocation`
- `events`
- `runtime`
- `sessions`
- `workflows`
- `control_plane`

It does not claim a completed productized platform, full telemetry/tracing integration, configuration center, contract center, GitHub Release, PyPI upload, or public repository synchronization.
