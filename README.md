# Cognition System

English | [简体中文](README.zh-CN.md)

Current release candidate: `v0.8.2`

Cognition System is a cognitive capability system for governed AI collaboration. It combines language models, tool ecosystems, runtime capabilities, and governance rules to help users understand sources, handle tasks, and deliver traceable results within explicit approval and reviewable boundaries.

The first verifiable product is the Reviewable Source QA Pack, exposed through the Cognition System product console. With your approval, the system reads a URL or evidence path, answers based on that material, and returns a reviewable answer run.

## What It Can Do Today

Ask a question about a URL or governed evidence input:

```bash
cognition-console ask --guided
```

Guided mode asks for:

1. The material to read.
2. Your question.
3. A local or online model path.
4. Approval to read the external source for this run.
5. Approval to call a model for this run.

The answer shows its evidence context where possible. If the material is too short or insufficient, the system says so instead of inventing unsupported content.

The technical compatibility entry remains available:

```bash
cognition external-readonly ask --guided
```

## Install

```bash
python -m pip install --upgrade pip
python -m pip install "cognition-system==0.8.2"
```

Or with uv:

```bash
uv pip install "cognition-system==0.8.2"
```

Python `3.14` is required.

## Quick Trial

```bash
cognition-console ask --guided
```

Example:

```text
请输入 URL 或 evidence path: https://example.com
请输入问题: 这份资料主要说明了什么？
请选择模型：1) deepseek  2) gemma4
请输入 1、2、deepseek 或 gemma4: 2
允许本次外部只读抓取该 URL？ 输入 yes/no: y
允许本次受控大模型回答？ 输入 yes/no: y
```

Model choices:

1. `gemma4`: local Ollama / Gemma4.
2. `deepseek`: online DeepSeek V4 Flash.

## Safety Boundaries

By default, the system does not:

1. Access the network silently.
2. Call a model silently.
3. Read or save provider keys silently.
4. Expose raw web pages, raw model responses, tracebacks, or provider keys in answers.
5. Present current follow-up context as long-term memory.

## Useful Commands

```bash
cognition-console --help
cognition-console ask --help
cognition-console ask --guided
cognition --help
cognition external-readonly ask --help
cognition config init --config-root ./config
```

## Documentation

- Quick start: [QUICKSTART.md](QUICKSTART.md)
- Chinese quick start: [QUICKSTART.zh-CN.md](QUICKSTART.zh-CN.md)
- Version history: [CHANGELOG.md](CHANGELOG.md)
- Source repository: https://github.com/peacock-lab/cognition-engine
