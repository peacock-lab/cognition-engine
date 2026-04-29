# Cognition Engine

`cognition-engine` 是一个基于 Google ADK 的认知引擎 / 中间件骨架。它把认知工作流中的上下文、调用、事件、运行、会话、产物与治理记录拆成可测试、可组合的源码帽子，为后续更完整的 agent runtime 与治理能力提供稳定内核。

当前版本：

```text
v0.4.0
```

`v0.4.0` 是核心骨架转正阶段性发布。它不是完整产品化平台发布，也不是遥测、配置中心、契约中心或全量 agent governance platform 的完成声明。

## v0.4.0 重点

本版本将核心运行时骨架整理为 ADK 对齐的模块结构：

- `cognition_engine.artifacts`: ADK FileArtifactService 绑定骨架。
- `cognition_engine.invocation`: ADK Invocation 原生语义绑定骨架。
- `cognition_engine.events`: ADK Event / Trace 字段绑定骨架。
- `cognition_engine.runtime`: Runtime / Runner 适配骨架。
- `cognition_engine.sessions`: Session 绑定骨架。
- `cognition_engine.workflows`: Workflow 结果与流程绑定骨架。
- `cognition_engine.control_plane`: control-plane 治理记录与 bundle 骨架。

`control_plane` 当前可生成并组合以下记录：

- Context Record
- Run Record
- Event Trace
- Artifact Manifest
- Control Plane Bundle

这些记录用于把一次认知运行的关键上下文、运行结果、事件轨迹与产物索引收束为可检查的数据结构。它们仍处在骨架建设阶段，不等同于完整观测平台或正式治理控制台。

## 安装

项目优先使用 `uv` 管理依赖、测试与构建：

```bash
git clone <repo-url>
cd cognition-engine
uv sync --extra test --extra release
```

确认 CLI 可用：

```bash
uv run python -m cognition_engine.cli --help
```

如果本机暂时不能使用 `uv`，可以退回到标准 Python editable 安装；但这不是本项目当前推荐路径：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test,release]"
```

## CLI 入口

当前公开入口聚焦在最小可运行的认知工作流与说明面生成：

```bash
uv run ce brief --insight insight-adk-runner-centrality --json
uv run ce decision-pack --insight insight-adk-runner-centrality --json
uv run ce workflow --insight insight-adk-runner-centrality --json
uv run python -m cognition_engine.workflow --insight insight-adk-runner-centrality --json
```

`python -m cognition_engine.workflow` 是现有兼容入口；新骨架能力主要沉淀在 `cognition_engine.workflows`、`runtime`、`sessions`、`events`、`invocation`、`artifacts` 与 `control_plane` 下。

真实 workflow 运行会在 `outputs/` 下生成运行产物与元数据。发布验证或本地 smoke 后，请按需要清理相关输出，避免把运行产物带入构建或公仓同步。

## 验证

推荐先运行聚焦单测：

```bash
uv run python -m pytest \
  tests/unit/test_workflow_loop.py \
  tests/unit/test_control_plane_bundle.py \
  tests/unit/test_adk_file_artifact_binding.py \
  tests/unit/test_adk_workflow_adapter.py \
  tests/unit/test_invocation_context.py \
  tests/unit/test_events_event_trace.py \
  tests/unit/test_runtime_runner.py \
  tests/unit/test_sessions_session.py \
  tests/unit/test_workflows_workflow.py \
  -q
```

发布前构建 dry-run：

```bash
rm -rf dist build *.egg-info
uv run python -m build --sdist --wheel
```

构建后应确认 wheel / sdist 版本为 `0.4.0`，且不包含 `outputs/`、`tasks/`、`docs/项目/`、`docs/推进资产库/`、`.adk-artifacts`、`__pycache__` 或 `.venv`。

## 发布状态

本仓库中的 `v0.4.0` 材料处于发布准备修补状态：

- 包元数据目标版本：`0.4.0`
- Git tag：待发布决策后补充
- GitHub Release：待发布决策后补充
- PyPI：待发布决策后补充
- 公仓同步：待公仓边界取证后执行

发布草稿材料位于：

```text
docs/项目/认知引擎 v0.4.0 版本建设项目/release/
```

## 当前边界

`v0.4.0` 不声明以下能力已经完成：

- 产品化用户接入闭环完成；
- telemetry / tracing 全栈正式集成完成；
- 配置中心、契约中心或策略中心完成；
- 完整 agent governance platform 完成；
- GitHub Release、PyPI 上传或公仓同步已经执行。

它的价值在于把 ADK 对齐的核心运行时骨架整理到可测试、可构建、可继续演进的状态。
