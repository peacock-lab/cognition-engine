# Cognition System

English | [简体中文](README.zh-CN.md)

Cognition System is a Python 3.14 multi-package baseline for governed AI task workflows, controlled CLI execution, configuration assembly, runtime orchestration, evidence observation, and public-facing gateway experiments.

Current public version: `v0.7.0`

The `v0.7.0` line is the new public PyPI baseline for the `cognition-system` distribution family.

## Install

```bash
python -m pip install --upgrade pip
python -m pip install "cognition-system==0.7.0"
```

If you use uv:

```bash
uv pip install "cognition-system==0.7.0"
```

## Verify

```bash
python -c "import importlib.metadata as m; print(m.version('cognition-system'))"
cognition --help
```

## Initialize Configuration

Cognition System includes packaged default configuration resources. Create a user-owned configuration directory before running local workflows:

```bash
cognition config init --config-root ./config
```

## CLI

The public console command remains:

```bash
cognition
```

Useful entry points:

```bash
cognition --json
cognition config init --config-root ./config
cognition run \
  --preflight-only \
  --operator-approved \
  --approval-ref approval://local \
  --audit-ref audit://local \
  --sanitized-evidence-ref evidence://local \
  --governance-summary-output-ref artifact://local \
  --json
cognition chat \
  --chat-session-id local-demo \
  --operator-approved \
  --approval-ref approval://local \
  --audit-ref audit://local \
  --sanitized-evidence-ref evidence://local \
  --governance-summary-output-ref artifact://local
```

## Package Areas

The `v0.7.0` baseline publishes these package areas:

1. `cognition-system`
2. `cognition-system-cli`
3. `cognition-system-runtime-container`
4. `cognition-system-runtime`
5. `cognition-system-composition`
6. `cognition-system-adk-adapter`
7. `cognition-system-contract-core`
8. `cognition-system-schemas`
9. `cognition-system-behavior-contracts`
10. `cognition-system-config-assembly`
11. `cognition-system-config-contexts`
12. `cognition-system-observability-hub`
13. `cognition-system-cognition-agent`
14. `cognition-system-product-gateway`

## Current Scope

This release establishes a corrected public package and CLI baseline. It includes controlled task workflow shells, configuration initialization, status and evidence summaries, read-only reference review paths, and candidate-only projection helpers for memory and skills.

This release does not claim a production hosted service, a complete visual console, automatic tool execution, or unrestricted memory and skills runtime execution.

## Documentation

- Quick start: [QUICKSTART.md](QUICKSTART.md)
- Chinese quick start: [QUICKSTART.zh-CN.md](QUICKSTART.zh-CN.md)
- Version history: [CHANGELOG.md](CHANGELOG.md)
- Source repository: https://github.com/peacock-lab/cognition-engine
