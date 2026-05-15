# 快速开始

[返回首页](README.zh-CN.md) | [English](QUICKSTART.md) | 简体中文

本文档说明 Cognition System `v0.7.0` 的最小本地使用路径。

## 1. 安装

```bash
python -m pip install --upgrade pip
python -m pip install "cognition-system==0.7.0"
```

或使用 uv：

```bash
uv pip install "cognition-system==0.7.0"
```

## 2. 验证安装

```bash
python -c "import importlib.metadata as m; print(m.version('cognition-system'))"
cognition --help
```

预期结果：安装版本为 `0.7.0`，并且 `cognition` 命令可以打印帮助信息。

## 3. 初始化配置

```bash
cognition config init --config-root ./config
```

该命令会基于包内默认配置创建本地配置目录。

## 4. 运行预检

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

## 5. 启动本地 Chat Shell

```bash
cognition chat \
  --chat-session-id local-demo \
  --operator-approved \
  --approval-ref approval://local \
  --audit-ref audit://local \
  --sanitized-evidence-ref evidence://local \
  --governance-summary-output-ref artifact://local
```

进入 chat shell 后，可以使用：

```text
/status
/status --json
/help
/exit
```

## 说明

`v0.7.0` 是 `cognition-system` 包名体系下的公开新基线。更早的实验性包名不是本发布线的兼容目标。
