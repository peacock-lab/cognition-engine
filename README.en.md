# Cognition Engine

`cognition-engine` is a lightweight cognition product loop built on top of Google ADK.

The main project entry is Chinese-first. This file provides a concise English summary for the current public `main` branch.

Chinese main entry:

```text
README.md
```

Quickstart:

```text
QUICKSTART.md
```

Current public version:

```text
v0.3.0
```

`v0.3.0` is positioned as a stable ADK foundation adoption and local real-model workflow release for Cognition Engine.

This README only describes the latest public state of the current `main` branch. Historical versions are preserved through `CHANGELOG.md`, `docs/releases/`, GitHub Releases, and Git tags.

---

## 1. v0.3.0 boundary

`v0.3.0` has stabilized:

1. the ADK-backed workflow main path;
2. pure installed-mode execution through `CE_DATA_DIR`;
3. fine-grained insight directory override through `CE_INSIGHTS_DIR`;
4. explicit real provider entry into the workflow main path;
5. the default `mock` provider;
6. the `google-adk>=2.0.0b1,<2.1` dependency path;
7. the minimal `adk-2.0.0b1` framework metadata entry;
8. retained historical `adk-2.0.0a3` smoke / fixture / regression data assets;
9. the `ce workflow` result chain: product brief, decision pack, and model enhancement;
10. output and metadata traceability.

`v0.3.0` does not claim:

1. a public provider interface;
2. a public `--model-provider` CLI option;
3. a real provider as the default provider;
4. complete Eval capability;
5. complete Observability capability;
6. a formal configuration center;
7. systematic completion of the Runner, Observability, and Context lines.

The Runner, Observability, and Context lines are deferred to later versions.

---

## 2. Installation

Clone the public repository:

```bash
git clone git@github.com:peacock-lab/cognition-engine.git
cd cognition-engine
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the project:

```bash
python -m pip install -U pip
python -m pip install -e .
```

Confirm that the CLI is available:

```bash
ce --help
python -m cognition_engine.cli --help
```

---

## 3. Minimal workflow usage

`v0.3.0` recommends running with an external data root:

```bash
CE_DATA_DIR="$PWD/data" ce workflow --insight insight-adk-runner-centrality --json
```

You can also explicitly override the insight data directory:

```bash
CE_DATA_DIR="$PWD/data" \
CE_INSIGHTS_DIR="$PWD/data/insights" \
ce workflow --insight insight-adk-runner-centrality --json
```

Current main entry:

```bash
ce workflow --insight insight-adk-runner-centrality
ce workflow --insight insight-adk-runner-centrality --json
```

`ce workflow` generates:

```text
product brief
→ decision pack
→ model enhancement
→ workflow-level result
→ metadata
```

---

## 4. Provider boundary

The current default provider is:

```text
mock
```

A real provider can be explicitly enabled through environment variables:

```bash
CE_MODEL_PROVIDER=adk_litellm_ollama \
CE_DATA_DIR="$PWD/data" \
ce workflow --insight insight-adk-runner-centrality --json
```

Current public boundary:

1. a real provider can explicitly enter the workflow main path;
2. the `--model-provider` CLI option is not public yet;
3. the real provider is not the default provider;
4. public provider capability remains a later-version decision.

---

## 5. Google ADK dependency

`cognition-engine` currently uses Google ADK 2.0.0b1+ as its controlled agent-framework dependency.

The dependency is declared in `pyproject.toml`:

```toml
google-adk>=2.0.0b1,<2.1
```

Users normally do not need to install Google ADK manually. Python packaging will read `pyproject.toml` and install the declared dependencies when installing this project.

This project does not vendor or copy Google ADK source code. It builds a productized cognition loop on top of the ADK dependency.

---

## 6. Current public capabilities

The current public capability surface includes:

1. the `ce` CLI entry;
2. the `python -m cognition_engine.cli` package entry;
3. the `ce workflow` main workflow entry;
4. the `CE_DATA_DIR` external data root;
5. the `CE_INSIGHTS_DIR` insight directory override;
6. the default mock provider;
7. explicit real provider enablement through environment variables;
8. product brief / decision pack / model enhancement combined results;
9. Markdown outputs;
10. metadata traceability;
11. minimal public data assets and examples.

---

## 7. Not included yet

This version does not include:

1. a public provider interface;
2. a public `--model-provider` CLI option;
3. complete Eval capability;
4. complete Observability capability;
5. a formal configuration center;
6. GUI / Web / channel support;
7. complete multi-agent orchestration;
8. a complete mature platform;
9. systematic governance interfaces for the Runner, Observability, and Context lines.

---

## 8. Data asset boundary

The current formal dependency path is:

```text
google-adk>=2.0.0b1,<2.1
```

Current data asset boundary:

1. `data/frameworks/adk-2.0.0b1/metadata.json` is the minimal b1 framework metadata entry;
2. `data/frameworks/adk-2.0.0a3/metadata.json` is retained as a historical data asset;
3. historical samples under `data/insights/adk-2.0.0a3/` are used for smoke / fixtures / regression validation;
4. a3 samples are not renamed into b1 samples;
5. b1 insight samples are outside the completion boundary of this version.

---

## 9. Public repository structure

The current public release surface focuses on the minimal usable product path:

```text
cognition-engine/
├── cognition_engine/
├── data/
│   ├── frameworks/
│   └── insights/
├── docs/
│   └── releases/
├── examples/
├── outputs/
├── tests/
├── pyproject.toml
├── README.md
├── README.en.md
├── QUICKSTART.md
├── CHANGELOG.md
└── LICENSE
```

Internal task chains, governance process files, private evidence records, local caches, build artifacts, and uncleaned runtime outputs are not part of the public release surface.

---

## 10. Output contracts

For the public output structure, see:

```text
outputs/OUTPUT_CONTRACTS.md
```

Current core result contracts include:

```text
ce-brief-result/v1
ce-decision-pack-result/v1
ce-insight-to-decision-workflow-result/v1
```

---

## 11. Tests

Install test dependencies:

```bash
python -m pip install -e ".[test]"
```

Run the current public unit tests:

```bash
python -m pytest tests/unit -q
```

---

## 12. Version history

This README describes the latest public state of the `main` branch.

Historical versions are preserved through:

1. `CHANGELOG.md`;
2. `docs/releases/`;
3. GitHub Releases;
4. corresponding Git tags.

The current version release note is available at:

```text
docs/releases/v0.3.0-release-note.md
```

---

## License

Apache License 2.0
