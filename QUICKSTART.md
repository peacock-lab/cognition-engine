# Quick Start

[简体中文](QUICKSTART.zh-CN.md) | English · [Back](README.md)

Current version: `v0.8.0`

## 1. Install

```bash
python -m pip install --upgrade pip
python -m pip install "cognition-system==0.8.0"
```

Or with uv:

```bash
uv pip install "cognition-system==0.8.0"
```

Python `3.14` is required.

## 2. Verify

```bash
cognition --help
cognition external-readonly ask --help
```

## 3. Try Source QA

```bash
cognition external-readonly ask --guided
```

Example inputs:

```text
请输入 URL 或 evidence path: https://example.com
请输入问题: 这份资料主要说明了什么？
请选择模型：1) deepseek  2) gemma4
请输入 1、2、deepseek 或 gemma4: 2
允许本次外部只读抓取该 URL？ 输入 yes/no: y
允许本次受控大模型回答？ 输入 yes/no: y
```

## 4. Follow Up

After a successful answer, continue around the same source:

```text
它适合用于什么场景？
```

If the source is insufficient, the system explains the limitation.

## 5. Configuration

Create a user configuration directory when needed:

```bash
cognition config init --config-root ./config
```
