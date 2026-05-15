# Quickstart

[Back to README](README.md) | English | [简体中文](QUICKSTART.zh-CN.md)

This guide shows the minimum local path for Cognition System `v0.7.0`.

## 1. Install

```bash
python -m pip install --upgrade pip
python -m pip install "cognition-system==0.7.0"
```

Or with uv:

```bash
uv pip install "cognition-system==0.7.0"
```

## 2. Verify the Package

```bash
python -c "import importlib.metadata as m; print(m.version('cognition-system'))"
cognition --help
```

Expected result: the installed version is `0.7.0`, and the `cognition` command prints its help text.

## 3. Initialize Configuration

```bash
cognition config init --config-root ./config
```

This creates a local configuration directory from packaged defaults.

## 4. Run a Preflight Check

```bash
cognition run \
  --preflight-only \
  --operator-approved \
  --approval-ref approval://local \
  --audit-ref audit://local \
  --sanitized-evidence-ref evidence://local \
  --governance-summary-output-ref artifact://local \
  --json
```

## 5. Try a Local Chat Shell

```bash
cognition chat \
  --chat-session-id local-demo \
  --operator-approved \
  --approval-ref approval://local \
  --audit-ref audit://local \
  --sanitized-evidence-ref evidence://local \
  --governance-summary-output-ref artifact://local
```

Inside the chat shell, use:

```text
/status
/status --json
/help
/exit
```

## Notes

`v0.7.0` is a new public baseline under `cognition-system` package names. Earlier experimental package names are not compatibility targets for this line.
