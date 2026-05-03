# observability_hub

## 目录定位

`observability_hub` 是认知引擎四层架构中的观察事实 intake 入口。

它当前不是公共契约提供者，而是消费标准运行事实、在模块内部构建候选观察记录的入口层。

## 第一批范围

第一批只做：

```text
RuntimeResult
-> build_evidence_bundle(...)
-> EvidenceBundle
```

也就是：

1. 消费 `RuntimeResult` 等公共运行事实。
2. 内部构建 `EvidenceBundle` 候选观察记录。
3. 为后续治理、审查、版本判断提供最小事实入口。

## 当前职责

`observability_hub` 当前负责：

1. 作为 observability-hub 的最低物理入口。
2. 接收标准 `RuntimeResult` / `WorkflowResult` / `RuntimeEvent` 事实。
3. 构建 `EvidenceBundle`、`RunRecord`、`EventTrace`、`ArtifactManifest`、`InvocationBindingRecord` 等内部模型。
4. 对缺失事实采用 `warnings` 与 `metadata` 保守承接。

## 当前不做

`observability_hub` 当前明确不做：

1. 不创建 `packages/evidence/`。
2. 不迁移旧 `cognition_engine/control_plane/builder.py`。
3. 不消费 `google.adk` 原生对象。
4. 不依赖 `adk_adapter`。
5. 不做 dashboard、metrics、trace storage。
6. 不做持久化。
7. 不修改 `packages/schemas/`。

## 架构边界

公共契约层是模块间交互的唯一稳定窗口。

因此 `observability_hub` 必须保持：

1. 只消费标准运行事实，而不是外部 SDK 原生对象。
2. 不直接依赖 `adk_adapter` 实现。
3. 不直接依赖 `google.adk`。
4. 不反向驱动 `schemas` 为当前内部模型让步。

模块内部模型可以存在，但不能被其他模块直接依赖。

一旦 `EvidenceBundle` 或其他内部模型被两个以上模块稳定消费，必须评估是否上升为公共契约。

## EvidenceBundle 口径

`EvidenceBundle` 当前仍是 `observability_hub` 内部候选观察记录。

它当前不是：

1. 不是全局公共契约。
2. 不是最终完整 evidence 系统。
3. 不是持久化记录系统。
4. 不是后台看板数据模型。

当前口径必须保持保守：

1. 不夸大 artifact 真实链路能力。
2. 不夸大 timing 字段完整度。
3. 不把 metadata 中的候选事实误写为稳定公共契约。

## 当前真实状态

截至 `v0.5.0` 当前阶段，以下事实已经成立：

1. `observability_hub` 已作为最低 intake 入口落地。
2. 当前可以消费 `RuntimeResult` 并构建 `EvidenceBundle`。
3. 四层最小闭环已通过测试复验成立。

当前四层最小闭环中，`observability_hub` 的位置为：

```text
contract_core
-> runtime_container
-> adk_adapter
-> ADK Workflow / Runner
-> RuntimeResult
-> observability_hub.build_evidence_bundle(...)
-> EvidenceBundle
```

## 当前限制

虽然最小闭环已经成立，但仍需明确：

1. `ArtifactManifest` 当前可以存在，但真实 artifact 链路证据仍不足，不能宣称完整。
2. `EvidenceBundle` 当前是内部候选观察记录，不应宣称为全局公共契约。
3. 当前成立的是最小闭环，不等于完整产品化 observability 系统。

## 当前阶段说明

`observability_hub` 当前口径应统一为：

```text
观察事实 intake 入口
= 消费 RuntimeResult 等公共运行事实
= 内部构建 EvidenceBundle 候选观察记录
= 暂不作为公共契约提供者
```
