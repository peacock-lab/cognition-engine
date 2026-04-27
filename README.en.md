# Cognition Engine

`cognition-engine` is a lightweight cognition product loop built on top of Google ADK.

The main project entry is now Chinese-first. This file provides a concise English summary.

Chinese main entry:

```text
README.md
```

Quickstart:

```text
QUICKSTART.md
```

---

## Current release

Current version:

```text
v0.1.2
```

`v0.1.2` is a lightweight patch release after the `v0.1.0` product baseline. It adds the second formal CLI product loop, `ce decision-pack`, and completes the related public documentation, examples, output contracts, regression fixtures, and minimal runtime baseline.

It clarifies:

1. the Google ADK dependency relationship
2. the installation path
3. the formal CLI entry points
4. the first product loop boundary

`ce decision-pack` is now part of the public `v0.1.2` release as the second formal CLI product loop.

---

## Google ADK dependency

`cognition-engine` currently uses Google ADK 2.0.0b1+ as its controlled agent-framework dependency.

The dependency is declared in `pyproject.toml`:

```toml
google-adk>=2.0.0b1,<2.1
```

Users normally do not need to install Google ADK manually.

When installing this project with:

```bash
python -m pip install -e .
```

Python packaging will read `pyproject.toml` and install the declared dependencies, including `google-adk`.

This project does not vendor or copy Google ADK source code. It builds a productized cognition loop on top of the ADK dependency.

---

## Installation

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

Install the project in editable mode:

```bash
python -m pip install -U pip
python -m pip install -e .
```

Confirm that the CLI is available:

```bash
python -m cognition_engine.cli --help
ce --help
```

---

## Formal CLI entries

The current formal entries are:

```bash
ce
python -m cognition_engine.cli
```

Recommended first commands:

```bash
python -m cognition_engine.cli --help
ce status --json
ce brief --insight insight-adk-runner-centrality
ce brief --insight insight-adk-runner-centrality --json
ce decision-pack --insight insight-adk-runner-centrality
ce decision-pack --insight insight-adk-runner-centrality --json
```

The current public product paths are:

```text
ce brief
ce decision-pack
```

Stable product brief examples are available under:

```text
examples/product-briefs/
```

These examples are for reading and demonstration. They are not runtime metadata or test baselines.

Stable decision-pack examples are available under:

```text
examples/decision-packs/
```

The current sample is:

```text
examples/decision-packs/runner-centrality.md
```

This sample is generated from the formal `ce decision-pack` entry. It is for reading and demonstration, not runtime metadata or a test baseline.

---

## First product loop

The first formal product loop is:

```bash
ce brief --insight insight-adk-runner-centrality
```

It performs the following actions:

1. reads a structured insight
2. generates a product brief
3. writes a Markdown output under `outputs/product-briefs/`
4. writes metadata under `outputs/.metadata/`

JSON output is available with:

```bash
ce brief --insight insight-adk-runner-centrality --json
```

The JSON result follows the current `ce-brief-result/v1` contract.

---

## Decision-pack capability

The current project also supports decision-pack generation:

```bash
ce decision-pack --insight insight-adk-runner-centrality
```

It performs the following actions:

1. reads a structured insight
2. generates a decision pack
3. writes a Markdown output under `outputs/decision-packs/`
4. writes metadata under `outputs/.metadata/`

JSON output is available with:

```bash
ce decision-pack --insight insight-adk-runner-centrality --json
```

The JSON result follows the current `ce-decision-pack-result/v1` contract.

`ce decision-pack` is part of the public `v0.1.2` release as the second formal CLI product loop.

---

## Current scope

This release supports:

1. formal package entry through `pyproject.toml`
2. formal CLI entry through `ce`
3. package entry through `python -m cognition_engine.cli`
4. the first product loop through `ce brief`
5. decision-pack generation through `ce decision-pack`
6. Markdown product-brief output
7. Markdown decision-pack output
8. metadata trace output
9. minimal unit coverage for product brief and decision pack
10. stable product brief examples
11. stable decision-pack examples

---

## Not included yet

This release does not claim:

1. Docker support
2. GUI / Web / channel support
3. full multi-agent orchestration
4. advanced evaluation workflows
5. all output types reaching the same maturity level
6. a complete mature platform

---

## Useful documents

Recommended reading:

```text
README.md
QUICKSTART.md
examples/product-briefs/README.md
examples/decision-packs/README.md
outputs/OUTPUT_CONTRACTS.md
VALIDATION_MODEL.md
VALIDATION_STATE_FLOW.md
```

---

## License

Apache License 2.0
