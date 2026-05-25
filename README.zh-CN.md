# Cognition System / 认知系统

[English](README.md) | 简体中文

当前发布候选版本：`v0.8.1`

Cognition System 是一个面向受治理 AI 协作的认知能力系统：它把大模型、工具生态、运行能力和治理规则组合起来，在明确授权和可复查边界内帮助用户理解资料、处理任务并交付可追踪结果。

当前第一批可直接体验的产品能力是“可复查资料问答包”，推荐通过“认知系统产品控制台”使用。系统会在用户授权下读取 URL 或 evidence path，基于资料回答问题，并返回可复查的问答运行引用。

## 当前能做什么

你可以让系统读取一个 URL 或 evidence path，然后基于这份资料回答问题。

```bash
cognition-console ask --guided
```

系统会逐步询问：

1. 要读取的资料。
2. 你想问的问题。
3. 使用本地模型还是线上模型。
4. 是否允许本次读取外部资料。
5. 是否允许本次调用模型回答。

回答会尽量说明答案依据、证据引用和受限原因。资料不足时，系统会提示无法展开，而不是编造内容。

兼容 / 技术入口仍然保留：

```bash
cognition external-readonly ask --guided
```

## 安装

```bash
python -m pip install --upgrade pip
python -m pip install "cognition-system==0.8.1"
```

或使用 uv：

```bash
uv pip install "cognition-system==0.8.1"
```

需要 Python `3.14`。

## 快速体验

```bash
cognition-console ask --guided
```

示例：

```text
请输入 URL 或 evidence path: https://example.com
请输入问题: 这份资料主要说明了什么？
请选择模型：1) deepseek  2) gemma4
请输入 1、2、deepseek 或 gemma4: 2
允许本次外部只读抓取该 URL？ 输入 yes/no: y
允许本次受控大模型回答？ 输入 yes/no: y
```

模型选择：

1. `gemma4`：本地 Ollama / Gemma4。
2. `deepseek`：线上 DeepSeek V4 Flash。

## 安全边界

系统默认不会：

1. 静默联网。
2. 静默调用模型。
3. 静默读取或保存 provider key。
4. 在回答中暴露原始网页、原始模型响应、traceback 或 provider key。
5. 把当前追问冒充长期记忆。

## 常用命令

```bash
cognition-console --help
cognition-console ask --help
cognition-console ask --guided
cognition --help
cognition external-readonly ask --help
cognition config init --config-root ./config
```

## 文档

- 快速开始：[QUICKSTART.zh-CN.md](QUICKSTART.zh-CN.md)
- English quick start：[QUICKSTART.md](QUICKSTART.md)
- 版本历史：[CHANGELOG.md](CHANGELOG.md)
- 源码仓库：https://github.com/peacock-lab/cognition-engine
