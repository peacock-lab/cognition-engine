# 变更记录

## v0.5.0 - 新基线发布准备

当前条目记录的是 `v0.5.0` 新基线发布准备事实。

`v0.5.0` 已完成根聚合包与多 distribution 发布结构修补，但最终公仓发布、Git tag、GitHub Release 与 PyPI 发布动作尚未执行。

### 新增

- `v0.5.0` 已采用第二层早期分发模块化方案：
  - 根包统一入口
  - 自营核心包
  - 代理适配包
  - 依赖型支撑包
- 根包 `cognition-engine` 已切换为 `0.5.0` 聚合包。
- 根包 `cognition-engine` 已作为普通用户推荐安装入口：
  - `pip install cognition-engine`
- 自营核心包发布边界已经明确：
  - `cognition-engine-contract-core`
  - `cognition-engine-runtime-container`
  - `cognition-engine-observability-hub`
- 代理 / 生态适配包发布边界已经明确：
  - `cognition-engine-adk-adapter`
- 依赖型支撑包发布边界已经明确：
  - `cognition-engine-schemas`
  - `cognition-engine-behavior-contracts`
  - `cognition-engine-config-contexts`
  - `cognition-engine-config-assembly`
  - `cognition-engine-runtime`
  - `cognition-engine-composition`
- 四层源码主入口已经物理落地：
  - `packages/contract_core/`
  - `packages/runtime_container/`
  - `packages/adk_adapter/`
  - `packages/observability_hub/`
- 依赖型支撑包源码面已经明确：
  - `packages/behavior_contracts/`
  - `packages/schemas/`
  - `packages/config_contexts/`
  - `packages/config_assembly/`
  - `config/`
  - `packages/runtime/`
  - `packages/composition/`

### 变更

- 根 `pyproject.toml` 已从 `0.4.0` 旧分发形态切换为 `0.5.0` 根聚合包元数据。
- 根包不再通过 package discovery 打包旧 `cognition_engine/` 源码。
- 根包不再暴露旧 `ce` console script 作为 `v0.5.0` 正式入口。
- `uv.lock` 已随根聚合包依赖结构重算。
- `README.md` 已同步为“根包统一入口 + 自营核心包 + 代理适配包 + 依赖型支撑包”的最新发布准备口径。
- `QUICKSTART.md` 已同步为本地开发、取证与发布准备并行口径。
- 旧 `cognition_engine/` 已降级为旧单包源码面 / 历史过渡资产。
- 旧 `cognition_engine/workflow.py` 与 `cognition_engine/workflows/` 不再作为 `v0.5.0` 新主线入口。

### 验证

- `tests/packages` 重名收集冲突已修复。
- `tests/packages` 全量收集与全量测试已通过。
- `hatchling` 构建后端已补齐。
- `packages/*` 10 个子包全部可构建 wheel。
- `packages/*` 10 个子包全部可隔离安装。
- 根包 `cognition-engine` 已可构建为 `0.5.0` 聚合 wheel。
- 根 wheel 不包含旧 `cognition_engine/` 源码。
- 安装 `cognition-engine==0.5.0` 可自动安装 10 个 `v0.5.0` 子包。
- 严格 repo 外部 import smoke 已通过。
- 旧 `cognition_engine` 未被根聚合包安装。

### 发布结构

`v0.5.0` 当前发布结构为：

```text
GitHub：一个公仓 cognition-engine
GitHub Release：一个 v0.5.0 Release
PyPI：多个 distribution
用户推荐入口：pip install cognition-engine
```

PyPI distribution 分类为：

```text
根包：
- cognition-engine

自营核心包：
- cognition-engine-contract-core
- cognition-engine-runtime-container
- cognition-engine-observability-hub

代理 / 生态适配包：
- cognition-engine-adk-adapter

依赖型支撑包：
- cognition-engine-schemas
- cognition-engine-behavior-contracts
- cognition-engine-config-contexts
- cognition-engine-config-assembly
- cognition-engine-runtime
- cognition-engine-composition
```

普通用户不需要手动安装支撑包。支撑包会随根包或核心包安装时自动解析安装。

### 发布状态

当前阶段明确：

- 尚未执行最终 PyPI 发布动作
- 尚未执行 Git tag
- 尚未执行公仓同步
- 尚未创建 GitHub Release
- 不把旧 `cognition_engine` 根包重新写成 `v0.5.0` 正式发布包
- 不宣称第三层独立运行时已经成立
- 不宣称第四层分布式生态已经成立

当前阶段应理解为：

```text
根聚合包发布结构已成立
多 distribution 发布对象已明确
构建与隔离安装验证已通过
正在进入公仓同步与 PyPI 发布前最终判断
```

### 后续

后续待处理事项包括：

- 完成公仓同步清单最终裁定
- 完成 PyPI 发布前最终验证
- 执行公仓同步、Git tag、GitHub Release 与 PyPI 发布前最终判断
- 发布后复验根包安装、子包依赖解析、README 展示与 release 记录

## 历史版本

仓库历史中仍保留更早阶段的私有推进记录、旧单包公开面修补记录与 `v0.4.0` 相关材料。

这些内容属于历史阶段背景，不应再被视为当前根公开文档的主叙事基线。
