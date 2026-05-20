# Cognition System

English | [简体中文](README.zh-CN.md)

Cognition System is a Python 3.14 multi-package release candidate for governed external-readonly question answering, controlled CLI workflows, configuration assembly, runtime orchestration, evidence observation, and product gateway experiments.

当前公开版本：`v0.8.0`

The `v0.8.0` line publishes the `cognition-system` aggregate package plus 18 `cognition-system-*` subpackages. This candidate is prepared for local public-repository validation; it is not a completed PyPI release.

## Install

```bash
python -m pip install --upgrade pip
python -m pip install "cognition-system==0.8.0"
```

If you use uv:

```bash
uv pip install "cognition-system==0.8.0"
```

## Verify

```bash
python -c "import importlib.metadata as m; print(m.version('cognition-system'))"
python -c "import importlib.metadata as m; print('cognition-system', m.version('cognition-system'), 'import ok')"
cognition --help
```

Expected smoke text:

```text
cognition-system 0.8.0 import ok
```

## CLI

The public console command is:

```bash
cognition
```

The primary product trial entry point is:

```bash
cognition external-readonly ask --guided
```

Guided mode asks for an external-readonly source, a question, a model alias, explicit network and model-call approvals, and credential handling when an external provider is selected.

Supported model aliases:

1. `deepseek`: online DeepSeek V4 Flash path for low-hardware users.
2. `gemma4`: local Ollama / Gemma4 path for local-model users.

Automation, CI, and JSON-output workflows should pass explicit options instead of `--guided`. The guarded behavior is intentional: `cognition external-readonly ask --guided --json` should fail closed.

## Configuration

The repository-level `config/` directory is not published as a package and is not copied into the public release surface. Installed default configuration resources are packaged by `cognition-system-config-assembly` under `config_assembly/default_config/`.

Create a user-owned configuration directory when needed:

```bash
cognition config init --config-root ./config
```

## Package Areas

The `v0.8.0` candidate includes 19 distributions:

1. `cognition-system`
2. `cognition-system-schemas`
3. `cognition-system-behavior-contracts`
4. `cognition-system-config-assembly`
5. `cognition-system-config-contexts`
6. `cognition-system-runtime`
7. `cognition-system-contract-core`
8. `cognition-system-adk-adapter`
9. `cognition-system-observability-hub`
10. `cognition-system-cognition-agent`
11. `cognition-system-cognition-governance`
12. `cognition-system-composition`
13. `cognition-system-external-readonly`
14. `cognition-system-runtime-container`
15. `cognition-system-task-workflows`
16. `cognition-system-product-gateway`
17. `cognition-system-product-runtime-assembly`
18. `cognition-system-product-application-assembly`
19. `cognition-system-cli`

## Safety Boundaries

The CLI keeps these boundaries:

1. No silent network access.
2. No silent live model call.
3. No silent provider-key read or save.
4. No raw HTML, raw provider response, response headers, traceback, or provider key in product output.
5. No arbitrary model name; only configured aliases are accepted.
6. No PyPI upload, Git tag, GitHub Release, or remote push is part of this candidate validation.

Runtime outputs belong in a local ignored `outputs/` directory and are not part of the public release surface.

## Documentation

- Quick start: [QUICKSTART.md](QUICKSTART.md)
- Chinese quick start: [QUICKSTART.zh-CN.md](QUICKSTART.zh-CN.md)
- Version history: [CHANGELOG.md](CHANGELOG.md)
- Source repository: https://github.com/peacock-lab/cognition-engine
