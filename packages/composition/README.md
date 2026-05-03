# composition

## 目录定位

`composition/` 是认知引擎的装配支撑包，属于 `runtime_container` 背后的正式支撑面之一。

当前 v0.5.0 四层主入口中，运行时治理容器的主入口已经由以下物理包承担：

```text
packages/runtime_container/
```

因此，`composition/` 不再被表述为早期未落地阶段的替代入口，也不再与 `runtime/` 共同充当 `runtime_container` 的过渡承载形态。

当前正确关系是：

```text
runtime_container = 运行时治理容器主入口 / facade
runtime = runtime_container 背后的运行组织支撑包
composition = runtime_container 背后的装配支撑包
```

本包负责把配置链路、公共契约与具体实现组合成可调用的运行形态。

本包是系统装配支撑包，不是四层主入口，不是运行组织层，不是具体 adapter 实现层，也不承接被装配实现的内部 SDK 调用、协议适配或业务执行细节。

本包回答的问题是：

**认知引擎如何把已经拆分的标准模块按规则装配为可运行对象。**

## 职责边界

本包负责：

1. 调用 `config_assembly` 获取标准配置载荷。
2. 调用 `config_contexts` 构建模块消费级 Config View。
3. 接收并选择由外部提供的行为契约实现。
4. 构建 `RuntimeDependencies`。
5. 构建 `StandardRuntimeRunner`。
6. 向 app、CLI、gateway、测试入口等调用方提供已装配的 runtime runner。
7. 作为 `runtime_container` 的正式装配支撑面，被上层通过运行容器入口理解和复用。

本包不负责：

1. 不定义行为契约。
2. 不定义公共数据模型。
3. 不定义配置上下文契约。
4. 不承担运行组织职责。
5. 不承担具体 adapter 实现职责。
6. 不承担外部 SDK 调用、协议适配或事件转换职责。
7. 不构建 EvidenceBundle。
8. 不承担完整发布入口职责。

本包的核心边界是：

```text
composition 的特权是依赖和装配，边界是不承接实现细节。
```

## 与其他层的关系

### 与 runtime_container 的关系

- `runtime_container/` 是运行时治理容器主入口。
- `composition/` 是 `runtime_container` 背后的装配支撑包。
- 后续对外表达时，应把 `composition/` 归入运行时治理容器背后的正式支撑面，而不是把它表述为四层主入口。

### 与 runtime 的关系

- `runtime/` 是运行组织支撑包。
- `composition/` 负责把配置上下文、运行依赖与具体实现装配为可运行对象。
- `runtime/` 负责执行组织与结果聚合。
- 二者都属于 `runtime_container` 背后的正式支撑面，但职责不同。

### 与 config_assembly 的关系

- `config_assembly/` 负责把 `config/` 配置事实与环境覆盖装配成标准配置载荷。
- `composition/` 可以调用 `config_assembly` 获取标准配置载荷。
- `composition/` 不应把配置装配规则复制到自身内部。

### 与 config_contexts 的关系

- `config_contexts/` 负责配置上下文契约与 Config View。
- `composition/` 使用配置上下文契约来构建运行依赖。
- `composition/` 不定义配置上下文契约。

### 与 behavior_contracts 的关系

- `behavior_contracts/` 定义行为能力契约。
- `composition/` 负责把行为契约与具体实现绑定起来。
- `composition/` 不定义行为契约，也不把实现细节写入行为契约。

### 与 schemas 的关系

- `schemas/` 定义公共数据契约。
- `composition/` 可以使用这些数据契约构建标准运行对象。
- `composition/` 不定义公共数据模型。

### 与 adapter 实现的关系

- `composition/` 可以依赖并装配具体 adapter 实现，例如 `adk_adapter/`。
- adapter 负责外部 SDK 调用、协议适配、事件转换、artifact 转换等内部细节。
- `composition/` 只负责选择、注入和返回可运行对象，不吞并 adapter 内部职责。

### 与 observability_hub 的关系

- `observability_hub/` 消费 RuntimeResult 等运行事实并构建内部候选观察记录。
- `composition/` 不构建 EvidenceBundle。
- 如果未来需要把观测能力纳入装配链，应通过明确的行为契约和配置上下文注入，而不是由 `composition/` 直接承担观察记录构建职责。

## 标准装配链路

```text
config/
→ config_assembly.RuntimeConfigPayload
→ config_contexts.RuntimeConfigContext / Config View
→ composition.build_standard_runtime_runner
→ runtime.StandardRuntimeRunner
→ runtime_container facade
```

## 依赖原则

当前第一批装配链路允许依赖：

```text
behavior_contracts
schemas
config_assembly
config_contexts
runtime
```

允许通过明确装配入口依赖并注入的实现包括：

```text
adk_adapter
mcp_adapter
a2a_adapter
litellm_adapter
hermes_adapter
openclaw_adapter
```

但 `composition/` 不应把这些 adapter 的外部 SDK 调用、协议适配、事件转换、artifact 转换等内部细节吸收到自身模块中。

## 发布面口径

在 v0.5.0 单一发布面表达中，`composition/` 应归入：

```text
v0.5.0 正式支撑面 / 装配支撑面
```

不应归入：

```text
历史遗留资产
独立主入口
运行组织层
具体 adapter 实现层
早期未落地阶段的替代入口
```

四层主入口中与本包对应的入口是：

```text
packages/runtime_container/
```

## 一句话收口

`composition/` 是 `runtime_container` 背后的装配支撑包，负责选择、创建、注入和返回可运行对象；它可以看见并装配契约与实现，但不吞并被装配模块的内部职责。