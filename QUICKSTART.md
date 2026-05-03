# 快速开始

本文件用于说明当前仓库的本地开发、取证与 `v0.5.0` 新基线发布准备阶段的快速开始路径。

当前 `v0.5.0` 已完成根聚合包与多 distribution 发布结构修补，但最终公仓发布、Git tag、GitHub Release 与 PyPI 发布动作尚未执行。因此，本文件同时说明本地开发路径与发布完成后的推荐安装入口口径。

## 1. 先理解当前结构

当前仓库优先应按 `workspace + packages/*` 理解，而不是按旧单包发布面理解。

`v0.5.0` 采用“根包统一入口 + 自营核心包 + 代理适配包 + 依赖型支撑包”的第二层早期分发模块化方案。

当前四层源码主入口为：

```text
packages/contract_core/
packages/runtime_container/
packages/adk_adapter/
packages/observability_hub/
```

当前依赖型支撑包源码面为：

```text
packages/behavior_contracts/
packages/schemas/
packages/config_contexts/
packages/config_assembly/
config/
packages/runtime/
packages/composition/
```

对应发布结构为：

```text
根包：
cognition-engine

自营核心包：
cognition-engine-contract-core
cognition-engine-runtime-container
cognition-engine-observability-hub

代理 / 生态适配包：
cognition-engine-adk-adapter

依赖型支撑包：
cognition-engine-schemas
cognition-engine-behavior-contracts
cognition-engine-config-contexts
cognition-engine-config-assembly
cognition-engine-runtime
cognition-engine-composition
```

普通用户推荐入口是根包 `cognition-engine`；支撑包会随根包或核心包安装时自动解析安装，不作为普通用户优先手动安装对象。

以下对象当前只作为旧兼容面保留：

```text
cognition_engine/ = 旧单包源码面 / 历史过渡资产，不进入 v0.5.0 根聚合包 wheel
ce = 旧兼容 CLI 入口，不作为 v0.5.0 正式 console script
cognition_engine/workflow.py = 旧 workflow 兼容入口，不作为 v0.5.0 新主线入口
cognition_engine/workflows/ = 旧 workflow 兼容面，不作为 v0.5.0 新主线入口
```

## 2. 同步本地开发环境

当前推荐使用 `uv`：

```bash
git clone <repo-url>
cd cognition-engine
uv sync --extra test --extra release
```

`v0.5.0` 发布完成后的普通用户推荐安装入口将是：

```bash
pip install cognition-engine
```

安装根包后，pip 会自动解析安装自营核心包、代理适配包和依赖型支撑包。当前该安装入口属于发布准备口径，最终 PyPI 发布动作尚未执行。

如需确认旧兼容 CLI 仍存在，可运行：

```bash
uv run python -m cognition_engine.cli --help
```

注意：

- 这一步只用于源码仓库内的本地开发验证
- 不应把旧 `ce` 理解为 `v0.5.0` 正式 CLI 入口
- 当前 QUICKSTART 说明发布准备口径，最终 PyPI 发布动作尚未执行

## 3. 优先验证 v0.5.0 四层主线

当前推荐优先运行 `tests/packages` 全量测试：

```bash
uv run pytest tests/packages -q --import-mode=importlib
```

这组命令主要验证：

- `packages/*` 新基线测试面
- 四层源码主入口
- 依赖型支撑包基础能力
- 代理适配包接入能力

补充说明：

- `tests/packages` 重名收集冲突已修复
- 全量收集与全量测试已通过

## 4. 构建与安装验证状态

当前已经完成以下发布前验证：

```text
1. hatchling 构建后端已补齐；
2. packages/* 10 个子包全部可构建 wheel；
3. packages/* 10 个子包全部可隔离安装；
4. 根包 cognition-engine 已可构建为 0.5.0 聚合 wheel；
5. 根 wheel 不包含旧 cognition_engine/ 源码；
6. 安装 cognition-engine==0.5.0 可自动安装 10 个 v0.5.0 子包；
7. 严格 repo 外部 import smoke 已通过；
8. 旧 cognition_engine 未被根聚合包安装。
```

## 5. 旧兼容入口如何使用

如果需要做兼容验证，可使用以下旧入口：

```bash
uv run ce workflow --insight insight-adk-runner-centrality --json
uv run ce brief --insight insight-adk-runner-centrality --json
uv run ce decision-pack --insight insight-adk-runner-centrality --json
uv run python -m cognition_engine.workflow --insight insight-adk-runner-centrality --json
```

这些命令只应理解为源码仓库内的兼容验证入口：

- 旧兼容 CLI / workflow 入口
- 历史单包链路验证入口
- 过渡阶段保留入口
- 不进入 `v0.5.0` 根聚合包正式发布面

不应理解为：

- `v0.5.0` 新四层主入口
- `runtime_container` 的替代入口
- 当前正式发布安装后的默认用户入口
- `v0.5.0` 正式 console script

## 6. `outputs/` 说明

旧兼容 workflow 运行可能在 `outputs/` 下生成运行产物。

如果你只是做本地冒烟验证、兼容验证或取证，请在验证后按需清理这些输出，避免把运行副产物带入后续构建、对比或同步动作。

## 7. 当前不做什么

当前快速开始不覆盖以下动作：

- 不宣称最终 PyPI 发布动作已经执行
- 不宣称 Git tag 已完成
- 不宣称公仓同步已完成
- 不宣称 GitHub Release 已完成
- 不把旧 `ce` / `workflow` 写成当前主线入口
- 不宣称第三层独立运行时或第四层分布式生态已经成立

## 8. 当前范围判断

当前阶段说明的是：

- `v0.5.0` 新主线已经落到 `packages/*`
- `v0.5.0` 已采用根包统一入口、自营核心包、代理适配包和依赖型支撑包的第二层早期分发模块化方案
- 根包 `cognition-engine` 已切换为 `0.5.0` 聚合包
- 旧单包入口已退出 `v0.5.0` 正式发布面
- 仓库正在进入公仓同步与 PyPI 发布前最终判断

当前不说明：

- 最终公仓发布已经完成
- PyPI 发布动作已经执行
- Git tag 或 GitHub Release 已经完成
- 第三层独立运行时或第四层分布式生态已经成立
