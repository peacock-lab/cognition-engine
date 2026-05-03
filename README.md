# Cognition Engine

`cognition-engine` 当前处于 `v0.5.0` 新基线发布准备阶段。

`v0.5.0` 已完成根聚合包发布结构修补：根包 `cognition-engine` 已切换为 `0.5.0` 聚合包，依赖自营核心包、代理适配包和依赖型支撑包；但最终公仓发布、Git tag、GitHub Release 与 PyPI 发布动作尚未执行。

## 当前状态

当前仓库的真实状态可以概括为：

```text
1. v0.5.0 新主线已经转向 packages/* workspace 多包结构；
2. v0.5.0 采用“根包统一入口 + 自营核心包 + 代理适配包 + 依赖型支撑包”的第二层早期分发模块化方案；
3. 根包 cognition-engine 已切换为 0.5.0 聚合包；
4. 安装 cognition-engine 可自动解析并安装 10 个 v0.5.0 子包；
5. 四层主入口已经成立；
6. 正式支撑面已经收敛为依赖型发布边界；
7. 旧 cognition_engine/、ce 与旧 workflow 不进入 v0.5.0 正式发布面；
8. packages/* 构建、隔离安装与严格 import smoke 已通过；
9. 当前尚未执行最终 Git tag、公仓同步、GitHub Release 或 PyPI 发布。
```

## v0.5.0 发布结构

`v0.5.0` 发布结构分为四类：

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

对应源码入口如下：

- `packages/contract_core/`：公共契约层，自营核心包
- `packages/runtime_container/`：运行时治理容器，自营核心包
- `packages/adk_adapter/`：ADK 能力适配实现层，代理 / 生态适配包
- `packages/observability_hub/`：观测平台与事实 intake，自营核心包

## 正式支撑面

当前已锁定的依赖型支撑包源码面为：

```text
packages/behavior_contracts/
packages/schemas/
packages/config_contexts/
packages/config_assembly/
config/
packages/runtime/
packages/composition/
```

这些目录属于 `v0.5.0` 主线的依赖型支撑层。它们作为正式 PyPI distribution 存在，并随根包或核心包安装时自动解析安装；但它们不作为普通用户优先手动安装对象，也不作为产品叙事主入口。

## 旧兼容面

以下对象当前仍保留，但都应按“旧兼容面”理解：

```text
cognition_engine/ = 旧单包源码面 / 历史过渡资产，不进入 v0.5.0 根聚合包 wheel
ce = 旧兼容 CLI 入口，不作为 v0.5.0 正式 console script
cognition_engine/workflow.py = 旧 workflow 兼容入口，不作为 v0.5.0 新主线入口
cognition_engine/workflows/ = 旧 workflow 兼容面，不作为 v0.5.0 新主线入口
pyproject.toml = v0.5.0 根聚合包元数据，已不再打包旧 cognition_engine/
```

因此：

- 不应再把 `cognition_engine/` 写成当前正式主线或根包发布内容
- 不应把 `ce` 写成 `v0.5.0` 正式 CLI 入口
- 不应把 `workflow.py / workflows/` 写成 `runtime_container` 或 `composition` 的直接替代入口

## 当前已成立的最小闭环

当前已经成立并被复验的最小闭环为：

```text
contract_core
-> runtime_container
-> adk_adapter
-> ADK Workflow / Runner
-> RuntimeResult
-> observability_hub.build_evidence_bundle(...)
-> EvidenceBundle
```

这说明：

- 四层主线已经具备最小闭环成立依据
- `RuntimeResult -> EvidenceBundle` 的最小取证链路已经成立
- 当前成立的是“最小闭环”，不是完整产品化系统

## 本地开发起步

当前推荐使用 `uv` 管理本地依赖与测试：

```bash
git clone <repo-url>
cd cognition-engine
uv sync --extra test --extra release
```

`v0.5.0` 发布完成后的推荐安装入口将是：

```bash
pip install cognition-engine
```

安装根包后，pip 会自动解析安装自营核心包、代理适配包和依赖型支撑包。普通用户不需要手动安装支撑包。

如需在源码仓库内确认旧兼容 CLI 仍可被调用，可运行：

```bash
uv run python -m cognition_engine.cli --help
```

注意：

- 上述命令只用于本地开发与兼容验证
- 不应把它理解为 `v0.5.0` 正式发布入口
- 当前 README 只说明发布准备口径，最终 PyPI 发布动作尚未执行

## 推荐验证路径

当前更推荐优先验证 `v0.5.0` 四层主线，而不是先从旧单包入口理解系统。

推荐验证对象：

```text
tests/packages/*
```

其中可直接运行的代表性验证命令为：

```bash
uv run pytest tests/packages -q --import-mode=importlib
```

说明：

- 这组测试覆盖当前 packages/* 新基线测试面
- `tests/packages` 重名收集冲突已修复，全量收集与全量测试已通过

## 构建与安装验证状态

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

## 旧兼容入口示例

以下命令可以继续用于旧兼容验证，但它们不是 `v0.5.0` 新主线入口：

```bash
uv run ce workflow --insight insight-adk-runner-centrality --json
uv run ce brief --insight insight-adk-runner-centrality --json
uv run ce decision-pack --insight insight-adk-runner-centrality --json
uv run python -m cognition_engine.workflow --insight insight-adk-runner-centrality --json
```

这些命令可能在 `outputs/` 下生成运行产物。

如果仅做本地冒烟验证、兼容验证或取证，请在验证后按需清理输出，避免把运行副产物带入后续构建、比对或同步流程。

## 当前不做什么

当前阶段明确不宣称以下事项已经完成：

- 不宣称最终 PyPI 发布动作已经执行
- 不宣称 Git tag 已完成
- 不宣称公仓同步已完成
- 不宣称 GitHub Release 已完成
- 不宣称 `ce` 是 `v0.5.0` 正式 CLI 入口
- 不宣称 `workflow.py / workflows/` 是 `runtime_container` 的替代入口
- 不宣称第三层独立运行时或第四层分布式生态已经成立

## 后续收口方向

当前阶段后续仍需继续处理：

- 修订 `QUICKSTART.md / CHANGELOG.md`，同步最新根聚合包与多 distribution 发布口径
- 完成公仓同步清单最终裁定
- 完成 PyPI 发布前最终验证
- 执行公仓同步、Git tag、GitHub Release 与 PyPI 发布前最终判断
- 发布后复验根包安装、子包依赖解析、README 展示与 release 记录
