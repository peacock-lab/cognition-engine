# Cognition System / 认知系统

[English](README.md) | 简体中文

Cognition System 是面向受治理 AI 任务工作流的 Python 3.14 多包基线，覆盖受控 CLI 执行、配置组装、运行时编排、证据观测和面向产品入口的候选能力。

当前公开版本：`v0.7.0`

`v0.7.0` 是 `cognition-system` 分发包族的公开 PyPI 新基线。

## 安装

```bash
python -m pip install --upgrade pip
python -m pip install "cognition-system==0.7.0"
```

如果使用 uv：

```bash
uv pip install "cognition-system==0.7.0"
```

## 验证

```bash
python -c "import importlib.metadata as m; print(m.version('cognition-system'))"
cognition --help
```

## 初始化配置

Cognition System 内置默认配置资源。运行本地工作流前，可以先创建用户侧配置目录：

```bash
cognition config init --config-root ./config
```

## CLI

公开控制台命令保持为：

```bash
cognition
```

常用入口：

```bash
cognition --json
cognition config init --config-root ./config
cognition run \
  --preflight-only \
  --operator-approved \
  --approval-ref approval://local \
  --audit-ref audit://local \
  --sanitized-evidence-ref evidence://local \
  --governance-summary-output-ref artifact://local \
  --json
cognition chat \
  --chat-session-id local-demo \
  --operator-approved \
  --approval-ref approval://local \
  --audit-ref audit://local \
  --sanitized-evidence-ref evidence://local \
  --governance-summary-output-ref artifact://local
```

## 包结构

`v0.7.0` 基线发布以下包：

1. `cognition-system`
2. `cognition-system-cli`
3. `cognition-system-runtime-container`
4. `cognition-system-runtime`
5. `cognition-system-composition`
6. `cognition-system-adk-adapter`
7. `cognition-system-contract-core`
8. `cognition-system-schemas`
9. `cognition-system-behavior-contracts`
10. `cognition-system-config-assembly`
11. `cognition-system-config-contexts`
12. `cognition-system-observability-hub`
13. `cognition-system-cognition-agent`
14. `cognition-system-product-gateway`

## 当前范围

本版本建立公开包结构和 CLI 新基线，包含受控任务工作流外壳、配置初始化、状态和证据摘要、只读资料审查路径，以及 Memory 和 Skills 的 candidate-only 投影辅助能力。

本版本不声明生产级托管服务、完整可视化控制台、自动工具执行，也不开放不受限制的 Memory runtime 或 Skills runtime。

## 文档

- 快速开始：[QUICKSTART.zh-CN.md](QUICKSTART.zh-CN.md)
- 英文快速开始：[QUICKSTART.md](QUICKSTART.md)
- 版本历史：[CHANGELOG.md](CHANGELOG.md)
- 源码仓库：https://github.com/peacock-lab/cognition-engine
