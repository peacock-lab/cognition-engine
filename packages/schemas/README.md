# schemas

## 目录定位

`schemas/` 是认知引擎的数据契约包，属于 `contract_core` 背后的公共契约支撑面之一。

它与 `behavior_contracts/`、`config_contexts/` 平行：

```text
behavior_contracts = 行为契约
schemas = 数据契约
config_contexts = 配置上下文契约
```

本包负责定义跨模块传输所需的公共数据结构、字段边界、校验规则与序列化语义，用于约束 runtime、composition、observability、adapter、workflow 等模块之间传递的数据形状。

本包回答的问题是：

**模块之间传递的数据长什么样、哪些字段有效、哪些字段必填、如何校验、如何序列化，以及如何防止裸 dict 在模块边界扩散。**

本包不是行为契约层，也不是配置上下文契约层，更不是实现层。

```text
behavior_contracts = 行为能力接口与边界
schemas = 公共数据结构与序列化边界
config_contexts = 配置上下文契约与 Config View
```

## 职责边界

本包负责：

1. 定义跨模块公共数据模型。
2. 定义跨模块 DTO、事件对象、结果对象、引用对象与错误对象。
3. 定义字段类型、默认值、枚举范围与结构校验规则。
4. 定义 JSON 序列化与反序列化边界。
5. 为 behavior_contracts、config_contexts、runtime、composition、observability、adapter、workflow 等模块提供稳定数据契约。
6. 作为 `contract_core` 公共契约支撑面的一部分，被上层通过契约窗口理解和复用。

本包不负责：

1. 不负责行为能力接口定义。
2. 不负责配置事实来源。
3. 不负责配置装配。
4. 不负责配置消费上下文契约。
5. 不负责业务执行逻辑。
6. 不负责 IO、存储、外部 SDK 调用。
7. 不负责系统装配。
8. 不作为 observability_hub 内部候选模型的替代层。

## 与其他层的关系

### 与 contract_core 的关系

- `contract_core/` 是公共契约入口。
- `schemas/` 是 `contract_core` 背后的正式契约支撑面之一。
- 后续对外表达时，应把 `schemas/` 归入公共契约支撑面，而不是归入历史遗留、独立主入口或实现侧能力目录。

### 与 behavior_contracts 的关系

- `behavior_contracts/` 负责行为能力契约。
- `schemas/` 负责跨模块数据契约。
- 二者同属公共契约支撑面，分别回答“能做什么”和“传递什么数据”。
- 行为契约需要引用数据对象时，应以明确业务接口方式引用 `schemas/` 中已经稳定的数据模型，不得自造重复数据结构。

### 与 config_contexts 的关系

- `config_contexts/` 负责配置上下文契约与 Config View。
- `schemas/` 负责普通跨模块业务数据、运行数据、事件数据、结果数据与引用数据。
- 配置上下文对象默认归属 `config_contexts/`，不应混入普通业务数据契约。

### 与 config_assembly 的关系

- `config_assembly/` 负责从 `config/` 配置事实装配标准配置载荷。
- `schemas/` 不读取 `config/`，不执行配置装配。
- 如需定义配置载荷的通用数据形状，应由 `config_assembly` 与 `config_contexts` 明确边界后再判断是否沉淀到 `schemas/`。

### 与 observability_hub 的关系

- `observability_hub/` 当前负责从 `RuntimeResult` 构建内部候选观察记录。
- `EvidenceBundle` 当前仍是 `observability_hub` 内部候选模型，不是 `schemas/` 当前公共契约。
- 如果后续 `EvidenceBundle`、`RunRecord`、`EventTrace`、`ArtifactManifest` 等对象被多个模块稳定消费，再评估是否上升为 `schemas/` 公共数据契约。

## 硬性规则

1. 跨模块传输不得依赖未声明结构的裸 dict。
2. 进入公共模块边界的数据，应优先使用 `schemas/` 中定义的数据模型。
3. `schemas/` 不得依赖任何实现包。
4. `schemas/` 不得读取配置文件、环境变量或外部系统。
5. `schemas/` 不得承接业务执行逻辑。
6. 新增公共数据模型时，必须说明其消费方、生产方与稳定性边界。
7. 修改公共数据模型时，必须同步评估 behavior_contracts、config_contexts、contract_core、runtime、composition、observability 与相关 adapter 的影响。
8. 模块内部候选模型不得因为名称相似而直接搬入 `schemas/`；必须先通过真实链路与跨模块消费验证。

## 当前适合承接的内容

本包当前适合承接已经稳定的公共数据契约，例如：

- WorkflowInput
- WorkflowResult
- RuntimeInput
- RuntimeResult
- RuntimeEvent
- ArtifactDelta
- InvocationRef
- ErrorRecord
- SourceRef

以下内容当前不应直接作为已稳定公共契约宣传：

- EvidenceBundle
- RunRecord
- EventTrace
- ArtifactManifest
- InvocationBindingRecord
- 旧控制面记录组合相关对象

这些对象如需进入公共契约层，应在后续经过真实链路验证、跨模块消费确认和公共契约上升评估。

## 发布面口径

在 v0.5.0 单一发布面表达中，`schemas/` 应归入：

```text
v0.5.0 正式支撑面 / 公共契约支撑面
```

不应归入：

```text
历史遗留资产
独立主入口
实现层
observability 内部候选模型层
```

## 一句话收口

`schemas/` 是认知引擎的公共数据契约包，用于在 Python 环境中补齐类似 Rust struct / enum 所承载的数据边界能力，使跨模块数据传输依赖稳定公共模型，而不是裸 dict 与隐式字段约定。