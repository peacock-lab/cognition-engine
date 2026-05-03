# contract_core

## 目录定位

`contract_core` 是认知引擎四层架构中 `contract-core` 的薄 facade 物理入口。

它是公共契约入口，不是行为契约、数据模型、配置上下文的源码合并包。

当前真实承接面仍包括：

- `packages/behavior_contracts`
- `packages/schemas`
- `packages/config_contexts`
- `packages/config_assembly`
- `config/`

## 当前职责

`contract_core` 当前负责：

1. 为稳定公共契约提供统一入口。
2. 聚合已稳定的行为契约、数据契约、配置上下文等公共交互窗口。
3. 对外提供薄 re-export 面，降低调用方直接分散依赖多个专业包的成本。

`contract_core` 当前不负责：

1. 不读取配置事实。
2. 不执行 runtime 逻辑。
3. 不装配具体实现。
4. 不承接 ADK 原生对象。

## 架构边界

公共契约层是模块间交互的唯一稳定窗口。

因此：

1. `contract_core` 不依赖 `runtime_container`。
2. `contract_core` 不依赖 `adk_adapter`。
3. `contract_core` 不依赖 `observability_hub`。
4. `contract_core` 不依赖 `google.adk`。

装配根可以识别并注入具体实现，但公共契约层本身不感知实现模块细节。

## 契约吸收规则

后续公共契约补强必须基于真实链路差额，而不是提前脑补。

`contract_core` 只应吸收以下类型的契约：

1. 已在真实链路中被验证需要跨模块稳定消费的契约。
2. 通用、稳定、供应商无关的契约。
3. 明确不属于单一实现模块内部细节的契约。

以下内容不应直接进入 `contract_core`：

1. `runtime_container` 内部运行组织细节。
2. `adk_adapter` 的 ADK 专属实现细节。
3. `observability_hub` 的内部候选模型。
4. 仍只在单一模块内部使用、尚未稳定复用的对象。

## 与专业包的关系

`contract_core` 不替代各专业包的语义归属。

规则是：

1. 新契约先进入语义归属明确的专业包。
2. 当确有统一入口需要时，再由 `contract_core` 做 re-export。
3. 模块内部模型可以存在，但不能被其他模块直接依赖。
4. 一旦某个内部模型被两个以上模块稳定消费，必须评估是否上升为公共契约。

## 当前阶段说明

截至 `v0.5.0` 当前阶段：

1. 四层最小闭环已经成立。
2. `contract_core` 已作为公共契约入口参与闭环。
3. 当前收口重点是保持边界清晰，而不是扩大公共契约面。

因此，`contract_core` 的当前口径是：

```text
公共契约入口
= 稳定交互窗口
= 不依赖实现模块
= 只吸收真实验证后稳定、通用、供应商无关的契约
```
