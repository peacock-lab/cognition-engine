# VALIDATION_MODEL

## 1. 文档定位

`VALIDATION_MODEL.md` 是当前 `cognition-engine/` 中 `validation` 对象的显式模型主文档。

本文件只承接已经在任务链、`DATA_MODELS.md`、`VALIDATION_STATE_FLOW.md` 与实现导航中稳定下来的对象结论，不重复记录任务推导过程、样本值、实现细节或差异证据层细节。

本文件重点回答以下问题：

1. `validation` 当前在认知引擎中的正式对象定位是什么
2. `validation candidate / scaffold / executed success / executed failure` 当前应如何分层理解
3. `validation` 根层与 `validation_execution` 子结构各自承担什么职责
4. 当前 formal entry 最小承接面是什么
5. 哪些内容当前明确排除在主模型表达之外
6. `validation` 与 `connection`、`internal_observation`、`context_access`、`runner_execution` 的边界是什么

---

## 2. 对象定位

`validation` 当前的正式定位应表达为：

**主 validation JSON 层的验证状态与正式结果总账。**

其当前主落位为：

```text
data/validations/{framework_id}/{validation_id}.json
```

这意味着：

1. `validation` 承接验证对象自身的阶段、执行、结果与正式证据
2. `validation` 不是来源线程快照本体
3. `validation` 不是输出对象本体
4. `validation` 不是工件目录本体

---

## 3. 对象分层

### 3.1 `validation candidate`

`validation candidate` 表示：

**值得验证的待办对象，但尚未形成真实执行证据。**

当前最小特征是：

1. `result = "pending"`
2. `status = "candidate"`
3. 已绑定来源线索，如 `source_connection_id`、`source_thread_url`

### 3.2 `validation scaffold`

`validation scaffold` 表示：

**candidate 已派生出最小复现工件，但主对象尚未升级为已执行验证。**

它当前不是新的平级主对象类型，而是：

1. candidate 的派生工件准备态
2. 由脚手架工件与 `scaffold_status` 等辅助字段共同表达

### 3.3 已执行验证终态

已执行验证终态表示：

**validation 已经具备真实执行证据，并进入已执行验证终态，主对象可以独立陈述正式结果。**

当前最小正式完成态包括：

1. `success`
2. `failed`

它们都仍属于已执行验证终态的正式收口分支，而不是新的平级主对象类型。

---

## 4. 根层职责

`validation` 根层当前承担的是：

**正式结果总账层职责。**

当前最小正式结果面收敛为：

1. `result`
2. `actual_output`
3. `run_timestamp`

这三项分别表达：

1. 结果是否正式成立
2. 结果如何被正式摘要
3. 结果在何时被正式落账

当前不应把更细的执行证据、三主线投影或差异诊断字段重新平铺回根层。

---

## 5. `validation_execution` 子结构

### 5.1 结构定位

`validation_execution` 当前的正式定位应表达为：

**附着在已执行 validation 主对象内部的共享嵌入式承接子结构。**

它不是新的平级主对象类型。

### 5.2 结构职责

`validation_execution` 当前承担两类职责：

1. 最小执行证据包络
2. ADK 三主线在 validation 中的最小投影子面

### 5.3 最小承接面

当前最小承接面收敛为：

```text
validation_execution.reproduced_issue
validation_execution.internal_observation.observed_node_name
validation_execution.internal_observation.output_event_count
validation_execution.context_access.state_delta
validation_execution.runner_execution.process_returncode
validation_execution.runner_execution.fatal_error_type
validation_execution.runner_execution.fatal_error_message
```

### 5.4 最小职责表达

这组字段当前分别承担：

1. `reproduced_issue`
   - 是否形成可归档复现证据
2. `internal_observation.*`
   - 最小节点观测与输出事件显影
3. `context_access.state_delta`
   - 最小状态写入显影
4. `runner_execution.*`
   - 进程级执行成立判断与最小失败归因

---

## 6. Formal Entry 最小承接面

`validation formal entry` 当前最小正式承接面应理解为两层：

### 6.1 根层正式结果面

1. `result`
2. `actual_output`
3. `run_timestamp`

### 6.2 `validation_execution` 子结构承接面

1. `reproduced_issue`
2. `internal_observation.observed_node_name`
3. `internal_observation.output_event_count`
4. `context_access.state_delta`
5. `runner_execution.process_returncode`
6. `runner_execution.fatal_error_type`
7. `runner_execution.fatal_error_message`

当前 formal entry 的关键边界是：

1. 根层继续承担正式结果总账
2. `validation_execution` 承担最小执行证据与三主线最小投影
3. 不把完整 `internal_observation / context_access / runner_execution` 子结构整体搬入 `validation`

---

## 7. 排除项

以下内容当前明确不进入 `validation` 显式模型主表达面：

1. `duration_seconds`
2. `trace_id`
3. timing 明细
4. HTTP 可见性相关字段
5. 深层异常链与 `fatal_traceback`
6. `stdout / stderr`
7. `last_observed_payload` 的 host / runtime 差异细节
8. success / failure 样本值
9. 实现脚本细节与回写命令
10. 任务链取证与推导过程

当前排除这些内容的原因是：

1. 它们更偏向运行证明、排障细节或实现痕迹
2. 它们跨样板存在明显漂移
3. 它们不是解释 `validation` 对象骨架所必需的最小内容

---

## 8. 边界关系

### 8.1 与 `connection` 的边界

`connection` 继续承担：

1. 来源线索连接承载体
2. 来源线程、来源快照与来源关系表达

`validation` 不承接这些来源快照本体，只保留与验证对象直接相关的来源引用。

### 8.2 与 `internal_observation` 的边界

`validation` 不整体承接 `internal_observation`。

当前只承接其在 validation 中已稳定成立的最小投影：

1. `observed_node_name`
2. `output_event_count`

### 8.3 与 `context_access` 的边界

`validation` 不整体承接 `context_access`。

当前只承接其最小稳定投影：

1. `state_delta`

### 8.4 与 `runner_execution` 的边界

`validation` 不整体承接 `runner_execution`。

当前只承接其最小稳定投影：

1. `process_returncode`
2. `fatal_error_type`
3. `fatal_error_message`

---

## 9. 状态流关系

当前 `validation` 的最小真实状态链应表达为：

```text
source thread signal -> pending candidate -> scaffold ready -> executed success / executed failure
```

其中：

1. `pending candidate`
   - 已进入主 validation JSON，但尚未形成真实执行证据
2. `scaffold ready`
   - 已具备最小复现入口，但不等于已执行
3. `executed success / executed failure`
   - 已形成真实执行证据，并进入正式结果收口

当前已执行验证终态的最小正式收口为：

1. `success`
2. `failed`

更细粒度失败态、中断态或放弃态当前尚未进入正式语义。

---

## 10. 与其他长期资产的分工

当前长期资产分工应收敛为：

1. `VALIDATION_MODEL.md`
   - `validation` 对象骨架、职责、边界与 formal entry 主表达面
2. `VALIDATION_STATE_FLOW.md`
   - 状态层、状态矩阵与状态转换主表达面
3. `DATA_MODELS.md`
   - 全局对象总表与压缩式对象说明
4. `engine/analyzer/README.md`
   - 实现入口、脚本职责与导航说明
5. `outputs/OUTPUT_CONTRACTS.md`
   - 输出层对象契约说明
   - 仅承担与 `validation` 相关的边界提示和导航回链，不替代主模型表达

这意味着：

1. 主模型表达不再只分散在多个文档中
2. 状态流说明与实现导航继续保留各自独立职责
3. 输出层契约文档继续只描述输出对象，不反向吞并 `validation` 对象模型
4. `validation` 的显式模型资产已经具备单独阅读与复用条件
