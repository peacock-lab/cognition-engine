# adk_adapter

## 目录定位

`adk_adapter` 是认知引擎四层架构中的 ADK 能力适配实现层。

它不是新的公共契约中心，而是公共契约中标准接口的具体实现包。

它当前通过 `AdkWorkflowRunner` 实现公共契约层中的 `WorkflowRunner`。

## 当前职责

`adk_adapter` 当前负责：

1. 在内部调用 `google-adk`。
2. 将 ADK Workflow、Runner、Event、Session 等原生对象映射为认知引擎标准对象。
3. 对外输出 `WorkflowResult`、`RuntimeEvent`、`InvocationRef`、`ArtifactDelta` 等公共事实。
4. 隔离 `google-adk` 依赖与版本变化。

`adk_adapter` 当前不负责：

1. 不定义公共契约。
2. 不替代 `runtime_container`。
3. 不替代 `contract_core`。
4. 不替代 `observability_hub`。
5. 不做万能 `ADKRuntime` 总接口。

## 对外边界

ADK Event、Runner、Workflow、Session 等原生对象仅在 `adk_adapter` 内部处理。

因此：

1. `adk_adapter` 对外不输出 ADK 原生对象作为公共交互契约。
2. 其他模块应只依赖 `WorkflowRunner`、`WorkflowResult`、`RuntimeEvent` 等公共契约。
3. `runtime_container` 不应直接 import `google.adk` 原生对象。
4. `runtime_container` 不应直接依赖 `adk_adapter` 实现细节。

装配根或测试可以直接识别具体 adapter 实现，但普通模块之间不应直接耦合实现细节。

## 第一批实现范围

当前第一批范围收敛为：

```text
AdkWorkflowRunner
AdkEventMapper
AdkInvocationMapper
AdkArtifactMapper
```

这些对象属于模块内部实现细节。

对应职责为：

1. `AdkWorkflowRunner`：实现公共契约中的 `WorkflowRunner`。
2. `AdkEventMapper`：把 ADK Event 映射为 `RuntimeEvent`。
3. `AdkInvocationMapper`：把 ADK invocation / session 事实映射为 `InvocationRef` 或 metadata。
4. `AdkArtifactMapper`：处理 artifact delta 候选映射边界。

## 当前真实链路状态

截至 `v0.5.0` 当前阶段，以下事实已经成立：

1. `adk_adapter` 已作为 ADK 能力实现层落地。
2. `runtime_container -> adk_adapter` 真实链路已通过测试验证。
3. 四层最小闭环已通过测试复验成立。

当前真实链路口径为：

```text
contract_core
-> runtime_container
-> WorkflowRunner
-> adk_adapter.AdkWorkflowRunner
-> ADK Workflow / Runner
-> WorkflowResult / RuntimeEvent
```

## 当前限制

当前仍需保持以下保守表述：

1. 不宣称 `adk_adapter` 已产品化承接全部 ADK 能力面。
2. 不宣称 artifact 真实链路已经完整。
3. 不宣称正式 ADK-backed 装配入口已经产品化。
4. 不把 ADK 专属细节上升为公共契约层。

第一批稳定运行样例当前采用自定义 `BaseNode._run_impl` 路线。

`FunctionNode` 暂不作为第一批稳定路径。

## 架构规则

`adk_adapter` 应遵守以下规则：

1. 公共契约层是模块间交互的唯一稳定窗口。
2. 实现模块不直接互相依赖实现细节。
3. 模块内部模型可以存在，但不能被其他模块直接依赖。
4. 模块内部模型一旦被两个以上模块稳定消费，必须评估是否上升为公共契约。
5. 外部能力适配模块不必拥有独立公共契约层，只要实现公共契约中的标准接口，即可通过装配根被注入系统。

## 当前阶段说明

`adk_adapter` 当前口径应统一为：

```text
ADK 能力适配实现层
= 实现公共契约中的 WorkflowRunner
= 内部处理 ADK 原生对象与 RuntimeEvent / WorkflowResult 映射
= ADK 专属细节不进入公共契约层
```
