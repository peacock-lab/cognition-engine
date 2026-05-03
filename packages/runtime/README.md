# runtime

## 目录定位

`runtime/` 是认知引擎的运行组织支撑包，属于 `runtime_container` 背后的正式支撑面之一。

当前 v0.5.0 四层主入口中，运行时治理容器的主入口已经由以下物理包承担：

```text
packages/runtime_container/
```

因此，`runtime/` 不再被表述为 `runtime-container` 的物理替代入口，也不再与 `composition/` 共同充当未落地 `runtime_container` 的临时映射。

当前正确关系是：

```text
runtime_container = 运行时治理容器主入口 / facade
runtime = runtime_container 背后的运行组织支撑包
composition = runtime_container 背后的装配支撑包
```

本包负责基于公共行为契约、公共数据契约与配置上下文组织一次治理运行过程。

本包是运行组织者，不是契约定义者，不是装配根，也不是 ADK runtime 的替代实现。

本包回答的问题是：

**在 behavior_contracts、schemas、config_contexts 已经定义清楚的前提下，认知引擎如何组织一次标准治理运行流程，并产出 RuntimeResult。**

## 职责边界

本包负责：

1. 消费 `behavior_contracts` 中定义的运行相关行为契约。
2. 消费 `schemas` 中定义的 RuntimeInput、RuntimeResult、WorkflowResult、RuntimeEvent 等数据契约。
3. 消费 `config_contexts` 中定义的运行配置上下文。
4. 组织 runtime 执行过程。
5. 调用由 `composition` 或上层装配入口注入的 WorkflowRunner、InvocationTracker、EventPublisher 等能力实现。
6. 产出标准 RuntimeResult。
7. 为 `observability_hub` 提供稳定运行事实来源。
8. 作为 `runtime_container` 的正式运行组织支撑面，被上层通过运行容器入口理解和复用。

本包不负责：

1. 不定义行为契约。
2. 不定义公共数据模型。
3. 不定义配置上下文契约。
4. 不读取根目录 `config/`。
5. 不执行配置装配。
6. 不承担系统级装配根职责。
7. 不直接依赖 ADK SDK。
8. 不直接依赖具体 adapter 实现。
9. 不直接依赖 LiteLLM、Hermes、OpenClaw 等外部运行实现。
10. 不直接构建完整 evidence 系统。

## 与其他层的关系

### 与 runtime_container 的关系

- `runtime_container/` 是运行时治理容器主入口。
- `runtime/` 是 `runtime_container` 背后的运行组织支撑包。
- 后续对外表达时，应把 `runtime/` 归入运行时治理容器背后的正式支撑面，而不是把它表述为四层主入口。

### 与 composition 的关系

- `composition/` 是装配支撑包，负责把配置上下文、运行依赖与具体实现装配为可运行对象。
- `runtime/` 负责执行组织与结果聚合。
- 二者都属于 `runtime_container` 背后的正式支撑面，但职责不同。

### 与 behavior_contracts 的关系

- `behavior_contracts/` 定义行为能力契约。
- `runtime/` 消费这些契约，并通过注入的实现完成运行组织。
- `runtime/` 不应自造与公共行为契约冲突的接口。

### 与 schemas 的关系

- `schemas/` 定义 RuntimeInput、RuntimeResult、WorkflowResult、RuntimeEvent 等公共数据契约。
- `runtime/` 消费并产出这些公共数据对象。
- `runtime/` 不应通过裸 dict 扩散跨模块运行结果。

### 与 config_contexts 的关系

- `config_contexts/` 定义运行过程可消费的配置上下文契约与 Config View。
- `runtime/` 只消费被注入的配置上下文，不直接读取 `config/`，也不承担配置装配。

### 与 adk_adapter 的关系

- `adk_adapter/` 是 ADK 能力适配实现层。
- `runtime/` 不直接依赖 `adk_adapter/` 或 `google.adk`。
- 具体 ADK 能力应通过 WorkflowRunner 公共契约被装配后注入 runtime。

### 与 observability_hub 的关系

- `observability_hub/` 消费 RuntimeResult 等运行事实。
- `runtime/` 负责产出稳定 RuntimeResult，不负责构建 EvidenceBundle。
- EvidenceBundle 当前仍是 `observability_hub` 内部候选观察记录，不属于 runtime 输出契约。

## 允许依赖

```text
behavior_contracts
schemas
config_contexts
```

可通过装配关系间接协作的对象：

```text
composition
runtime_container
adapter 实现
observability_hub
```

## 禁止依赖

```text
config/
google.adk
litellm
hermes
openclaw
具体 workflow 实现包
具体 adapter 实现包
旧 cognition_engine 单包实现
```

## 标准执行链路

```text
RuntimeInput
→ RuntimeConfigContext / Config View
→ StandardRuntimeRunner / RuntimeOrchestrator
→ WorkflowRunner
→ WorkflowResult
→ RuntimeEvent
→ RuntimeResult
```

## 发布面口径

在 v0.5.0 单一发布面表达中，`runtime/` 应归入：

```text
v0.5.0 正式支撑面 / 运行组织支撑面
```

不应归入：

```text
历史遗留资产
独立主入口
ADK runtime 替代实现
早期未落地阶段的替代入口
```

四层主入口中与本包对应的入口是：

```text
packages/runtime_container/
```

## 一句话收口

`runtime/` 是 `runtime_container` 背后的运行组织支撑包，只按公共契约与配置上下文组织治理运行；它不直接读取配置事实、不绑定外部 SDK、不定义上游契约，也不替代 ADK runtime。
