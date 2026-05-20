# Quick Start

[简体中文](QUICKSTART.zh-CN.md) | English · [Back](README.md)

当前公开版本 `v0.8.0`

This guide covers the public local install and CLI smoke path for the Cognition System `v0.8.0` release candidate.

## 1. Install

```bash
python -m pip install --upgrade pip
python -m pip install "cognition-system==0.8.0"
```

Or with uv:

```bash
uv pip install "cognition-system==0.8.0"
```

## 2. Verify

```bash
python -c "import importlib.metadata as m; print(m.version('cognition-system'))"
python -c "import importlib.metadata as m; print('cognition-system', m.version('cognition-system'), 'import ok')"
cognition --help
cognition external-readonly ask --help
```

Expected smoke text:

```text
cognition-system 0.8.0 import ok
```

## 3. Initialize Configuration

```bash
cognition config init --config-root ./config
```

The installed default configuration baseline comes from the packaged `config_assembly/default_config/` resources. The repository-level `config/` directory is not published as a package.

## 4. Guided External-Readonly Ask

For an interactive trial:

```bash
cognition external-readonly ask --guided
```

The guide asks for source type, question, model alias, explicit approvals, and credential handling. It does not silently open network access, live model calls, audit gates, or stored credentials.

Model aliases:

1. `deepseek`: online DeepSeek V4 Flash path for low-hardware users.
2. `gemma4`: local Ollama / Gemma4 path for local-model users.

## 5. Automation

Automation and JSON-output paths should pass explicit arguments. Guided mode with JSON output should fail closed:

```bash
cognition external-readonly ask --guided --json
```

## 6. Safety Boundaries

The public CLI should not expose raw HTML, raw provider response, response headers, tracebacks, provider keys, or unrestricted model names. Network access, live model calls, runtime fetch, operator approval, and audit refs remain explicit choices.

## 7. Useful Commands

```bash
cognition --json
cognition config init --config-root ./config
cognition external-readonly ask --help
cognition external-readonly ask --guided
```

Runtime outputs belong in a local ignored `outputs/` directory and are not part of the public release surface.
