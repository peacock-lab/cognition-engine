# runtime_container

## 目录定位

`runtime_container` 是认知引擎四层架构中 `runtime-container` 的薄 facade 物理入口。

它是运行时治理容器入口，也是统一运行组织 facade。

当前真实承接面仍包括：

- `packages/runtime`
- `packages/composition`

`runtime_container` 不合并、不移动、不复制 `runtime` 与 `composition` 源码。

## 当前职责

`runtime_container` 当前负责：

1. 提供统一运行入口。
2. 通过公共契约接收 `WorkflowRunner` 等标准能力实现。
3. 对未来 app、CLI、gateway 等调用方提供单一 runtime-container 导入面。

`runtime_container` 当前不负责：

1. 不定义公共契约。
2. 不定义公共数据模型。
3. 不定义配置上下文。
4. 不直接承接 ADK 原生对象。

公共契约、数据契约、配置上下文仍归属于 `contract_core` 及其真实承接面。

## 架构边界

公共契约层是模块间交互的唯一稳定窗口。

因此 `runtime_container` 的正式源码必须保持：

1. 不直接依赖 `adk_adapter`。
2. 不直接依赖 `google.adk`。
3. 通过 `WorkflowRunner` 等公共契约接收具体能力实现。
4. 不直接依赖 `observability_hub` 的内部模型。

实现模块之间不直接互相依赖实现细节。

装配根可以识别并注入具体实现，但 `runtime_container` 本身只面向公共契约。

## 当前真实链路状态

截至 `v0.5.0` 当前阶段，以下事实已经成立：

1. `runtime_container` 已作为统一运行入口落地。
2. `runtime_container -> adk_adapter` 真实链路已通过测试验证。
3. 四层最小闭环已通过测试复验成立。

当前真实链路口径为：

```text
contract_core
-> runtime_container
-> adk_adapter
-> ADK Workflow / Runner
-> RuntimeResult
-> observability_hub
```

## 当前限制

虽然最小闭环已经成立，但以下边界仍需保持保守表述：

1. `runtime_container` 不直接感知 ADK Workflow、BaseNode、Runner 等原生对象。
2. 正式 ADK-backed 装配入口尚未产品化。
3. 当前成立的是“最小闭环”，不是完整产品化系统。

因此不应宣称：

1. 已存在正式产品化的 ADK-backed 装配入口。
2. `runtime_container` 已经吸收 `adk_adapter` 实现细节。
3. `runtime_container` 已合并 `runtime` 与 `composition`。

## 模块关系规则

`runtime_container` 应遵守以下规则：

1. 公共契约层是唯一稳定交互窗口。
2. 模块内部模型可以存在，但不能被其他模块直接依赖。
3. 模块内部模型一旦被两个以上模块稳定消费，必须评估是否上升为公共契约。
4. 外部能力适配模块不必拥有独立公共契约层，只要实现公共契约中的标准接口，即可通过装配根被注入系统。

## 当前阶段说明

`runtime_container` 当前口径应统一为：

```text
运行时治理容器入口
= 统一运行组织 facade
= 通过公共契约接收 WorkflowRunner
= 正式源码不直接依赖 adk_adapter / google.adk
= 最小闭环已成立，但正式 ADK-backed 装配入口尚未产品化
```
