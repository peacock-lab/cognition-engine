# 快速开始

[English](QUICKSTART.md) | 简体中文 · [返回](README.zh-CN.md)

当前公开版本 `v0.8.0`

本文档说明 Cognition System `v0.8.0` 发布候选的公开本地安装与 CLI smoke 路径。

## 1. 安装

```bash
python -m pip install --upgrade pip
python -m pip install "cognition-system==0.8.0"
```

或使用 uv：

```bash
uv pip install "cognition-system==0.8.0"
```

## 2. 验证

```bash
python -c "import importlib.metadata as m; print(m.version('cognition-system'))"
python -c "import importlib.metadata as m; print('cognition-system', m.version('cognition-system'), 'import ok')"
cognition --help
cognition external-readonly ask --help
```

预期 smoke 文本：

```text
cognition-system 0.8.0 import ok
```

## 3. 初始化配置

```bash
cognition config init --config-root ./config
```

安装态默认配置基线来自包内 `config_assembly/default_config/` 资源。仓库级 `config/` 目录不是独立发布包。

## 4. 引导式外部只读问答

交互式试用：

```bash
cognition external-readonly ask --guided
```

引导模式会询问资料来源、问题、模型别名、显式授权和凭据处理方式。它不会静默打开网络访问、live model 调用、审计 gate 或已保存凭据。

模型别名：

1. `deepseek`：适合低硬件用户的线上 DeepSeek V4 Flash 路径。
2. `gemma4`：适合本地模型用户的 Ollama / Gemma4 路径。

## 5. 自动化

自动化和 JSON 输出路径应显式传入参数。带 JSON 输出的 guided mode 应 fail closed：

```bash
cognition external-readonly ask --guided --json
```

## 6. 安全边界

公开 CLI 不应暴露 raw HTML、raw provider response、response headers、traceback、provider key 或不受限制的模型名。网络访问、live model 调用、runtime fetch、operator approval 和 audit ref 都保持显式选择。

## 7. 常用命令

```bash
cognition --json
cognition config init --config-root ./config
cognition external-readonly ask --help
cognition external-readonly ask --guided
```

运行产物应留在本地忽略的 `outputs/` 目录中，不属于公开发布面。
