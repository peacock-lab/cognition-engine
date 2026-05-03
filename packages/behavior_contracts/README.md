# behavior_contracts

## 目录定位

`behavior_contracts/` 是认知引擎的行为契约包，属于 `contract_core` 背后的公共契约支撑面之一。

它与 `schemas/`、`config_contexts/` 平行：

```text
behavior_contracts = 行为契约
schemas = 数据契约
config_contexts = 配置上下文契约
```

本包负责定义跨 package、跨模块协作所需的能力接口、行为语义、错误语义与稳定边界。

本包对应 Rust 项目经验中的 traits 层，但在 Python 中以标准行为契约包形式存在，技术实现优先使用 `typing.Protocol`、公共错误语义与必要的行为链路共享类型。

本包回答的问题是：

**系统中有哪些稳定能力、调用方应依赖什么行为边界、实现包应实现哪些能力接口，以及这些行为能力如何通过装配根绑定到具体实现。**

本包不是数据契约层，也不是配置上下文契约层，更不是实现层。

```text
behavior_contracts = 行为能力接口与边界
schemas = 公共数据结构与序列化边界
config_contexts = 配置上下文契约与 Config View
```

## 职责边界

本包负责：

1. 定义跨模块行为能力接口。
2. 定义行为调用语义。
3. 定义公共错误语义。
4. 定义依赖倒置边界。
5. 为 runtime、composition、observability、adapter、workflow 等模块提供稳定行为契约。
6. 为装配根提供能力绑定依据。
7. 作为 `contract_core` 公共契约支撑面的一部分，被上层通过契约窗口理解和复用。

本包不负责：

1. 不负责具体实现。
2. 不负责公共数据模型仓库职责。
3. 不负责配置事实来源。
4. 不负责配置装配。
5. 不负责配置上下文契约定义。
6. 不负责 IO、存储、外部 SDK 调用。
7. 不负责系统装配。
8. 不负责业务执行逻辑。

## 与其他层的关系

### 与 contract_core 的关系

- `contract_core/` 是公共契约入口。
- `behavior_contracts/` 是 `contract_core` 背后的正式契约支撑面之一。
- 后续对外表达时，应把 `behavior_contracts/` 归入公共契约支撑面，而不是归入历史遗留、独立主入口或实现侧能力目录。

### 与 schemas 的关系

- `schemas/` 负责公共数据契约。
- `behavior_contracts/` 负责行为能力契约。
- 二者同属公共契约支撑面，分别回答“传递什么数据”和“能做什么”。
- 行为契约需要引用数据对象时，应引用 `schemas/` 中已稳定的数据模型，不得自造重复数据结构。

### 与 config_contexts 的关系

- `config_contexts/` 负责配置上下文契约与 Config View。
- `behavior_contracts/` 不定义配置上下文对象。
- 行为契约可以声明实现需要某类配置能力，但不承接配置事实来源、配置装配逻辑或配置消费视图定义。

### 与 runtime / composition 的关系

- `runtime/` 消费行为契约并组织运行过程。
- `composition/` 负责把行为契约、配置上下文与具体实现装配为可运行对象。
- `behavior_contracts/` 不依赖 `runtime/` 或 `composition/`，也不承担运行组织与系统装配职责。

### 与 adapter 实现的关系

- 具体 adapter 应实现 `behavior_contracts/` 中定义的稳定行为契约。
- adapter 不应要求调用方直接依赖自身实现细节。
- 具体实现与行为契约的绑定由装配根负责。

### 与 observability_hub 的关系

- `observability_hub/` 可消费运行结果与事件事实。
- `behavior_contracts/` 不定义 EvidenceBundle、RunRecord、EventTrace 等观察记录模型。
- 如果未来需要把观察相关能力抽象为行为契约，应经过真实链路验证与跨模块消费确认。

## 硬性规则

1. `behavior_contracts/` 不得依赖任何实现包。
2. `behavior_contracts/` 不得读取 `config/`。
3. `behavior_contracts/` 不得调用外部 SDK。
4. `behavior_contracts/` 不得承接业务执行逻辑。
5. 新增行为契约时，必须说明生产方、消费方、装配位置与稳定性边界。
6. 修改行为契约时，必须同步评估 schemas、config_contexts、contract_core、runtime、composition、observability 与相关 adapter 的影响。
7. 模块内部能力接口不得因为名称相似而直接搬入 `behavior_contracts/`；必须先通过真实链路与跨模块消费验证。

## 当前适合承接的内容

本包当前适合承接已经稳定的行为能力契约，例如：

- WorkflowRunner
- InvocationTracker
- EventPublisher
- ArtifactStore
- ClockProvider
- IdGenerator

以下内容当前不应直接作为已稳定行为契约宣传：

- 旧控制面记录构建能力
- 旧自然语言消费闭环能力
- 旧输出渲染能力
- 未完成真实链路验证的外部运行能力

这些能力如需进入公共契约层，应在后续经过真实链路验证、跨模块消费确认和行为契约上升评估。

## 发布面口径

在 v0.5.0 单一发布面表达中，`behavior_contracts/` 应归入：

```text
v0.5.0 正式支撑面 / 公共契约支撑面
```

不应归入：

```text
历史遗留资产
独立主入口
实现层
旧 cognition_engine 单包能力层
```

## 一句话收口

`behavior_contracts/` 是认知引擎的公共行为契约包，用于把跨模块能力边界从口头约定变成稳定接口，使 runtime、composition、observability、adapter、workflow 等模块通过契约协作，而不是直接依赖彼此实现。
