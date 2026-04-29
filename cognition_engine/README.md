# cognition_engine 源码包说明

## 1. 文件定位

`cognition_engine/` 是认知引擎项目的主源码包。

本目录承载认知引擎运行时、ADK 底座承接、治理控制面、产物绑定、事件治理、调用身份绑定等核心代码。

本 README 用于约束 `cognition_engine/` 下源码模块的基本架构、模块命名规则和后续扩展边界。

---

## 2. 基本架构原则

认知引擎当前采用：

```text
ADK 管运行底座；
认知引擎管治理控制面；
各底座能力通过并行绑定、治理投影和真实样本验证逐步转正。
```

源码组织原则：

1. 底座能力优先承接 ADK 原生能力；
2. 认知引擎不重复脑补 ADK 已有底座；
3. 新旧链路采用并行绑定，不推倒重来；
4. 旧链路保留为兼容层、回滚锚点和事实对照组；
5. 新链路成熟后，再逐步降级或替换旧链路；
6. `control_plane/` 负责治理视图总装，不吞并所有底座绑定逻辑；
7. 每个骨架级能力应拥有稳定模块边界，而不是长期寄宿在 `workflow.py`、`builder.py`、`adk_workflow_adapter.py` 等主干文件中。

---

## 3. 模块命名规则

后续 `cognition_engine/` 顶层模块命名优先遵守以下规则：

```text
顶层模块、子模块、文件名优先参考 ADK 命名；
去掉 ADK 前缀；
宁可帽子稍大，也要帽子稳定；
内部实现可以先很小，后续再逐步拆分；
避免为了当前代码量小而起过窄、临时、helper 化的模块名；
不用当前业务方向命名源码文件；
认知引擎增强语义写入 README、docstring、注释和任务文档，不塞进源码文件名。
```

模块命名目标：

1. 高内聚、低耦合；
2. 外围帽子稳定，减少后续反复改名；
3. 与 ADK 能力域天然对齐，降低认知负担；
4. 缺什么、已承接什么、尚未承接什么，一眼可见；
5. 允许模块初期只有一个文件；
6. 后续模块内部可以继续拆分，但外层模块名尽量稳定；
7. 业务产品方向不反向定义底座模块名；
8. 如必须新增 ADK 中没有的派生文件，使用英文通用技术名，并在文档中说明它与 ADK 能力的映射关系。

---

## 4. 当前与规划中的源码模块

当前和后续源码模块应逐步收敛为以下结构：

```text
cognition_engine/
  artifacts/
  invocation/
  events/
  telemetry/
  runtime/
  sessions/
  control_plane/
  workflow.py
  adk_workflow_adapter.py
```

说明：

| 模块 | 定位 |
| --- | --- |
| `artifacts/` | 对齐 ADK artifacts，负责产物底座绑定、保存、读取、版本与 artifact 账本映射。 |
| `invocation/` | 对齐 ADK invocation 语义，负责单次调用身份、项目侧 invocation_id 与 ADK invocation_id 的绑定和对账。 |
| `events/` | 对齐 ADK events，负责 ADK Event 原生字段、Event Trace、事件字段覆盖、错误/中断/partial/turn_complete 摘要等事件治理能力。 |
| `telemetry/` | 后续如接入 ADK telemetry / tracing / metrics / exporter，再单独建立；当前不提前创建。 |
| `runtime/` | 后续承接 ADK Runner / App / Workflow / BaseNode 等运行底座适配与运行入口。 |
| `sessions/` | 后续承接 ADK sessions、session_id、session service 与 Context Record 相关投影；`context_id` 当前作为治理投影字段存在，不提前扶正为顶层 `context/` 模块。 |
| `control_plane/` | 认知引擎自有治理控制面，负责四件套治理视图总装。 |
| `workflow.py` | 当前 workflow 编排入口，后续应逐步保持轻量。 |
| `adk_workflow_adapter.py` | 当前 ADK-backed workflow 适配层，后续应逐步回归 ADK 适配职责。 |

### 4.1 阶段性命名策略

当前阶段采用 ADK 对齐优先的命名策略。

原因是：

```text
ADK 是当前最稳定的底座锚点；
认知引擎的中台能力和业务层仍在孵化；
源码骨架需要先借助 ADK 的稳定能力域降低认知负担，形成标准产品骨架。
```

但这不是永久绑定 ADK 命名。

当认知引擎自身的中台能力、控制面、消费链路和产品形态足够稳定后，可以在保持兼容和可治理的前提下，逐步进行部分重构与重新命名，使 ADK 从当前的主要底座锚点，演进为认知引擎可治理底座之一。

当前阶段原则：

```text
先基于 ADK 稳定命名和能力域完成孵化；
后续再抽象出更独立的治理底座模型。
```

---

## 5. 已成立模块

### 5.1 `control_plane/`

`control_plane/` 是认知引擎治理控制面骨架。

当前承载：

```text
Context Record
Run Record
Event Trace
Artifact Manifest
Control Plane Bundle
```

定位：

```text
负责治理视图总装；
消费 artifacts / invocation / events / runtime / sessions 等模块的投影；
不长期吞并所有底座绑定逻辑。
```

### 5.2 `artifacts/`

`artifacts/` 已用于承接 ADK FileArtifactService 并行绑定骨架。

当前定位：

```text
outputs / metadata 保留为业务事实来源；
ADK FileArtifactService 作为 artifact 底座保存、加载、版本能力；
artifact_refs 记录 ADK artifact binding；
Artifact Manifest 展示业务账本与 ADK artifact 底座绑定关系。
```

该模块已经是 ADK artifacts 能力域在认知引擎中的源码承接位置。

---

## 6. 待补正模块

### 6.1 `invocation/`

`invocation/` 是单次调用身份与 ADK invocation 语义绑定模块。

它应回答：

```text
这次运行是谁？
项目侧 invocation_id 是什么？
ADK Event 中的 invocation_id 是什么？
二者是否绑定一致？
```

规划职责：

1. 承接 `ProjectInvocationBindingPlugin`；
2. 负责项目侧 invocation_id 与 ADK invocation_id 绑定；
3. 负责 ADK Event invocation_id 对账；
4. 输出 bound / mismatch / missing_count / event_count 等绑定摘要；
5. 向 `control_plane/` 提供运行身份投影。

建议初始结构：

```text
cognition_engine/invocation/
  __init__.py
  invocation_context.py
```

说明：

```text
ADK 中已取证存在 google.adk.agents.invocation_context；
认知引擎使用 invocation_context.py 承接 ADK invocation_context 的绑定、投影和对账适配；
ProjectInvocationBindingPlugin、ADK Event invocation_id 提取、bound / mismatch / missing_count 计算等实现可放入该文件；
业务语义通过 docstring 和 README 说明，不使用 binding.py 这类过泛文件名作为长期锚点。
```

### 6.2 `events/`

`events/` 是 ADK Event 与事件轨迹治理模块。

它应承接：

```text
ADK Event 原生字段；
Event Trace 结构化事件记录；
字段覆盖统计；
error / interrupted / partial / turn_complete 摘要；
author / node / branch 摘要；
事件治理状态投影。
```

建议初始结构：

```text
cognition_engine/events/
  __init__.py
  event.py
  event_trace.py
```

说明：

```text
events/ 对齐 ADK events；
event.py 对齐 ADK Event / google.adk.events.event，承接 ADK Event 原生字段标准化、JSON 化和字段提取；
event_trace.py 承接 ADK Event 进入 control_plane 的事件轨迹投影，包括 records、coverage、error / interrupted / partial / turn_complete、author / node / branch 摘要；
本轮不使用 governance.py 作为 events 内部文件名，治理语义由 event_trace.py 的 docstring、README 和任务文档说明；
telemetry/ 后续如接 ADK telemetry / tracing / metrics，再单独建立；
不使用 observability/ 作为当前源码顶层模块名，避免与 ADK 实际模块名不一致并造成混淆。
```

---

## 7. 不使用 `observability/` 作为当前源码顶层模块名

当前源码层默认不使用 `observability/` 作为顶层模块名。

原因：

1. 当前 ADK 已明确存在 `events` 与 `telemetry` 能力域；
2. 当前建设内容主要是 ADK Event 原生字段与 Event Trace 治理；
3. telemetry / tracing / metrics / exporter 尚未接入；
4. 使用 `observability/` 容易误导为已进入全量观测体系；
5. 后续若接入 ADK telemetry，应建立 `telemetry/`，而不是提前用 `observability/` 混合承载。

叙事规则：

```text
默认使用 events / telemetry / tracing / metrics 等实际模块名；
不把 observability 作为源码模块帽子；
如需表达一流观测能力，只作为架构概念说明，不作为当前源码顶层模块名。
```

---

## 8. 骨架级任务完成标准

凡是 ADK 核心基座转正任务，如果定义为“骨架级”，必须同时满足：

1. 能力接入；
2. 独立模块边界；
3. 清晰调用边界；
4. 字段契约稳定；
5. 失败降级策略；
6. 单元测试；
7. 真实 workflow 样本验证；
8. 文档与任务结果收口。

不得只以“字段出现、测试通过、真实样本通过”作为骨架级完成标准。

---

## 9. control_plane 与各模块的关系

`control_plane/` 不应承担所有治理算法。

推荐关系：

```text
artifacts/      → 产物底座绑定投影   → control_plane/Artifact Manifest
invocation/     → 调用身份绑定投影   → control_plane/Run Record / Event Trace / Context Record
events/         → 事件轨迹治理投影   → control_plane/Event Trace / Run Record
runtime/        → 运行底座投影       → control_plane/Run Record
sessions/       → 会话与上下文投影   → control_plane/Context Record
control_plane/  → 四件套总装
```

也就是说：

```text
各模块负责自身能力域内的绑定、对账、统计与投影；
control_plane 负责统一组装治理视图。
```

---

## 10. 后续演进提醒

后续新增或整理源码模块时，优先遵守：

1. 顶层模块、子模块和文件名先参考 ADK 命名；
2. 再判断是否需要认知引擎自有派生技术名；
3. 外层模块名尽量稳定；
4. 内部文件可小步拆分；
5. 不因当前实现很小而使用临时命名；
6. 不用当前业务产品方向命名底座源码文件；
7. 业务语义、治理语义和产品解释写入 README、docstring、注释、任务包和设计文档；
8. 不把所有治理逻辑堆入 `control_plane/builder.py`；
9. 不把所有 ADK 适配与绑定逻辑堆入 `adk_workflow_adapter.py`。
10. 当前不将 `context/` 作为顶层源码模块名；如后续需要承接 ADK session 相关能力，优先评估 `sessions/`；
11. `context_id` 当前作为治理投影字段存在，是否需要独立模块需经 ADK sessions / invocation_context / Context Record 取证后再裁定；
12. 当前阶段 ADK 对齐优先，成熟后可在保持兼容的前提下评估更独立的治理底座命名体系。

一句话原则：

```text
帽子要稳，内部可迭代；
模块与文件优先对齐 ADK；
业务语义写注释和文档；
治理高内聚、低耦合。
```