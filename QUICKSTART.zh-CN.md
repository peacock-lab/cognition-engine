# 快速开始

[English](QUICKSTART.md) | 简体中文 · [返回](README.zh-CN.md)

当前发布候选版本：`v0.8.1`

## 1. 安装

```bash
python -m pip install --upgrade pip
python -m pip install "cognition-system==0.8.1"
```

或使用 uv：

```bash
uv pip install "cognition-system==0.8.1"
```

需要 Python `3.14`。

## 2. 验证

```bash
cognition --help
cognition-console --help
cognition-console ask --help
```

## 3. 体验资料问答

```bash
cognition-console ask --guided
```

示例输入：

```text
请输入 URL 或 evidence path: https://example.com
请输入问题: 这份资料主要说明了什么？
请选择模型：1) deepseek  2) gemma4
请输入 1、2、deepseek 或 gemma4: 2
允许本次外部只读抓取该 URL？ 输入 yes/no: y
允许本次受控大模型回答？ 输入 yes/no: y
```

## 4. 继续追问

成功回答后，可以围绕同一份资料继续追问：

```text
它适合用于什么场景？
```

资料不足时，系统会直接说明限制。

兼容 / 技术入口仍然保留：

```bash
cognition external-readonly ask --guided
```

## 5. 配置

需要创建用户配置目录时运行：

```bash
cognition config init --config-root ./config
```
