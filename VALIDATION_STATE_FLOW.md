# VALIDATION_STATE_FLOW

## 1. 文档定位

`VALIDATION_STATE_FLOW.md` 是当前 `cognition-engine/` 最小验证链的状态层说明文件。

本文件只描述当前真实脚本、真实 validation JSON、真实派生工件和真实测试所支持的状态语义，不把未来完整验证平台、自动调度器、审批流或重试流提前写成当前状态机。

关于 `validation` 的对象边界、根层职责、`validation_execution` 子结构职责与 formal entry 排除项，当前主表达面已经独立收口到：

- `VALIDATION_MODEL.md`

本文件重点解决：

- 当前 validation 至少有哪些真实状态层级
- 各状态是由哪些字段显式表达，还是只能由对象组合推断
- candidate、skeleton ready、executed success / executed failure 之间的真实关系是什么
- 当前是否存在明确失败态、中断态或仅存在工件侧观察态

---

## 2. 证据来源

本文件基于以下真实依据整理：

- `engine/analyzer/map_github_threads_to_validations.py`
- `engine/analyzer/generate_validation_skeleton.py`
- `engine/analyzer/write_validation_result.py`
- `engine/analyzer/validate_data.py`
- `data/validations/` 下真实 validation JSON
- `validation_samples/` 下真实派生工件
- `tests/unit/test_github_thread_validation_mapper.py`
- `tests/unit/test_validation_skeleton_generator.py`
- `DATA_MODELS.md`

---

## 3. 当前对象层级

当前与 validation 状态流直接相关的对象可分为三层：

### 3.1 主对象层

主对象层是 `data/validations/{framework_id}/{validation_id}.json` 下的 validation 记录。

当前正式状态判断优先以这一层为准。

### 3.2 派生工件层

派生工件层是 `validation_samples/{framework_id}/{validation_id}/` 下的脚手架目录，当前通常包含：

- `repro_case.py`
- `README.md`
- `context.json`

这一层表达的是“复现入口是否已准备”以及“局部执行观察”，不自动等于主对象状态已经升级。

### 3.3 线索来源层

线索来源层主要是 `data/connections/` 下的连接记录，尤其是 GitHub 线程 connection。

它不是 validation 本身，但会触发 candidate 的生成，并通过 `source_connection_id`、`source_thread_url` 与 validation 绑定。

---

## 4. 当前真实状态层级

基于真实脚本与真实样本，当前至少可以确认 4 个真实状态层级：

1. `pending candidate`
2. `scaffold ready`
3. `executed success`
4. `executed failure`

注意：

- 这 4 层并不是由单一枚举字段统一表达
- 它们当前由 `result`、`status`、`type`、`scaffold_status`、工件是否存在等多种信号共同表达

---

## 5. 当前正式状态语义

### 5.1 `pending candidate`

#### 定义

`pending candidate` 表示：

**该对象已经被识别为“值得验证的待办对象”，但还没有形成真实执行证据。**

#### 当前进入条件

依据 `map_github_threads_to_validations.py`，只有当 GitHub 线程同时满足以下条件时，才会生成 candidate：

1. 至少命中足够的问题信号
2. 至少命中最小可复现上下文
3. 至少命中明确技术对象
4. 综合得分达到阈值

#### 当前主对象表达

当前显式字段组合为：

- `result = "pending"`
- `status = "candidate"`
- `type = "external_signal_candidate"` 或后续回写后的 `type = "minimal_sample_candidate"`

辅助字段通常包括：

- `source_connection_id`
- `source_thread_url`
- `candidate_score`
- `signal_summary`
- `suggested_checks`

#### 当前落位

```text
data/validations/{framework_id}/{validation_id}.json
```

#### 边界

- 它表示“值得验证”
- 不表示“问题已经被复现”
- 不表示“验证已经执行完成”
- 不表示“结论已经成立”

### 5.2 `scaffold ready`

#### 定义

`scaffold ready` 表示：

**针对某个 pending candidate，最小复现入口已经生成，验证工作可以进入人工补全与执行阶段。**

#### 当前生成条件

依据 `generate_validation_skeleton.py`，只有当 validation 同时满足以下条件时才会进入脚手架生成流程：

- `result = "pending"`
- `status = "candidate"`

#### 当前主对象表达

脚手架生成后，validation 记录会被回写为：

- `type = "minimal_sample_candidate"`
- `scaffold_status = "ready"`
- `code_sample = "validation_samples/.../repro_case.py"`
- `execution_command = "python validation_samples/.../repro_case.py"`
- `scaffold_generated_at = <timestamp>`
- `scaffold_files = [...]`

同时保留：

- `result = "pending"`
- `status = "candidate"`

这说明当前正式语义是：

**脚手架就绪不会自动把 candidate 提升为已执行验证。**

#### 当前工件表达

```text
validation_samples/{framework_id}/{validation_id}/
  - repro_case.py
  - README.md
  - context.json
```

#### 边界

- 它表示“复现入口已准备”
- 不表示“已拿到真实运行证据”
- 不表示“结果已经成功或失败”

### 5.3 已执行验证终态

#### 定义

`executed validation` 表示：

**validation 已经具备真实执行证据，主对象可以独立陈述预期、实际输出与结果。**

#### 当前主对象表达

当前已执行验证的正式收口需要分成“成功收口”和“失败收口”两部分理解。

成功收口样本通常具备以下核心特征：

- `result = "success"`
- `method` 为真实执行方式，如 `code_execution`、`test_execution`
- `expected_output` 与 `actual_output` 已被填写
- `run_timestamp` 已存在

失败收口样本当前也已进入最小正式语义，通常具备以下核心特征：

- `result = "failed"`
- `actual_output` 已被填写
- `run_timestamp` 已存在
- 可选附着 `validation_execution.runner_execution.*` 以表达运行失败、异常类型或错误消息

常见补充字段包括：

- `insight_id`
- `code_sample`
- `execution_command`
- `duration_seconds`
- `environment`
- `validation_execution`（仅在已进入 validation formal entry 实施链的样本上出现）

#### 当前落位

```text
data/validations/{framework_id}/{validation_id}.json
```

#### 当前边界

- 当前已执行验证终态不再只指成功样本，而同时包括 `result = "success"` 与 `result = "failed"` 两类最小正式收口。
- `write_validation_result.py` 已支持把脚手架执行结果正式收口为 `result = "success"` 或 `result = "failed"`
- 当前已进入 validation formal entry 实施链的 executed validation，会在主 validation JSON 内附着共享嵌入式子结构 `validation_execution`
- `validation_execution` 当前最小承接：
  - `reproduced_issue`
  - `internal_observation.observed_node_name`
  - `internal_observation.output_event_count`
  - `context_access.state_delta`
  - `runner_execution.process_returncode`
  - `runner_execution.fatal_error_type`
  - `runner_execution.fatal_error_message`
- 工件侧 `reproduced_issue` 只作为执行观察信号，不直接进入主对象 `result = "reproduced"`
- `duration_seconds`、`trace_id`、timing、HTTP 可见性、深层异常链以及 `stdout / stderr` 当前仍不进入 `validation_execution`

因此当前正式表述应写成：

**已执行验证在仓库中是明确存在的；当前最小回写实现已经支持 `success / failed` 两类正式收口，并且已在受控样本上把执行证据与三主线最小投影下沉到 `validation_execution`。**

若需查看 `executed validation` 在对象层上的完整职责分工，而不只是状态语义，请同步阅读：

- `VALIDATION_MODEL.md`

---

## 6. 当前状态表达矩阵

| 状态层级 | 主判断依据 | 典型字段组合 | 是否已有真实样本 | 是否可视为当前正式语义 |
| --- | --- | --- | --- | --- |
| pending candidate | 主 validation JSON | `result=pending` + `status=candidate` | 是 | 是 |
| scaffold ready | 主 validation JSON + 脚手架工件 | `result=pending` + `status=candidate` + `scaffold_status=ready` | 是 | 是 |
| executed validation | 主 validation JSON | `result=success` + 已填写 `expected_output` / `actual_output` / `run_timestamp` + 可选 `validation_execution` | 是 | 是 |
| executed failure | 主 validation JSON | `result=failed` + 已填写 `actual_output` / `run_timestamp` + 可选 `validation_execution.runner_execution.*` | 否（当前实现能力已支持） | 是 |
| interrupted / abandoned | 主 validation JSON | 明确中断字段或状态 | 否 | 否 |
| reproduced observation | 脚手架 README / 脚本输出 | 工件内文本或脚本运行结果 | 是 | 否，当前仅是工件侧观察 |

---

## 7. 当前真实状态转换

### 7.1 Connection 到 Candidate

当前真实链路：

1. GitHub 线程 connection 被读取
2. 脚本抽取问题信号、复现线索与技术对象
3. 满足阈值后生成 validation JSON
4. connection 被回链一条 `type = validation_candidate` 的关系

状态层表述：

`source thread signal` -> `pending candidate`

### 7.2 Candidate 到 Scaffold Ready

当前真实链路：

1. `generate_validation_skeleton.py` 扫描全部 validation
2. 仅接受 `result = pending` 且 `status = candidate` 的记录
3. 生成脚手架目录与 3 个派生文件
4. 回写 `scaffold_status = ready` 等字段

状态层表述：

`pending candidate` -> `scaffold ready`

注意：

- 这一步不会改变 `result`
- 这一步不会改变 `status`
- 它只说明“候选已有最小复现入口”

### 7.3 Scaffold Ready 到已执行验证终态

当前真实脚本中已经存在最小回写链，但它仍不是完整自动执行平台。

当前真实链路是：

1. 人工或任务链先把 `repro_case.py` 补成真实可执行脚本
2. `write_validation_result.py` 执行 validation 的 `execution_command`
3. 回写器读取脚手架脚本输出的结构化 JSON 结果
4. 将工件侧 `reproduced_issue` 折叠为主对象正式结果：
   - `reproduced_issue = true` -> `result = "success"`
   - 其他情况 -> `result = "failed"`
5. 回写主 validation JSON，并移除 `status = "candidate"` 这类候选阶段标记

状态层表述：

`scaffold ready` -> `executed success / executed failure`

但注意：

- 这是当前已经落地的最小回写闭环
- 它是单对象回写器，不是批量调度器

---

## 8. 当前“结果”和“状态”的关系

当前 validation 没有单一状态枚举字段，至少涉及两类信号：

### 8.1 `result`

当前 `result` 更接近“验证证据层结果”：

- `pending` 表示尚未形成执行证据
- `success` 表示已形成可归档的成功执行证据
- `failed` 表示已执行，但未形成成功复现证据或执行过程发生受控失败

当前不作为主对象正式 `result` 的仍包括：

- `failure`
- `partial`
- `reproduced`

### 8.2 `status`

当前 `status` 不是所有 validation 的统一字段。

当前已观察到的正式写入只有：

- `status = "candidate"`

这说明：

- `status` 当前主要承担“候选身份标记”
- 它还不是“所有 validation 全生命周期统一状态枚举”

### 8.3 `scaffold_status`

当前 `scaffold_status` 是局部辅助字段。

当前已观察到的正式写入只有：

- `scaffold_status = "ready"`

它表达的是：

- 脚手架工件是否已准备

它不表达：

- 验证是否已经执行
- 验证结论是否已经成立

---

## 9. 当前失败态、中断态与缺失态

### 9.1 明确失败态

当前需要区分“历史样本覆盖”与“当前实现能力”：

- 历史落盘样本中仍未观察到正式写入的 `result = "failed"`
- `write_validation_result.py` 已把 `result = "failed"` 纳入当前最小正式收口，但当前仓库中仍应谨慎区分“实现能力已支持”与“历史样本已普遍覆盖”

因此当前不能把以下状态写成已落地能力：

- `status = failed`
- `status = reproduced`
- `status = blocked`

### 9.2 明确中断态

当前仓库中也没有观察到正式写入的中断态或放弃态，例如：

- `abandoned`
- `cancelled`
- `interrupted`

因此这类状态当前只能视为未来可能需要的治理扩展，而不是现状。

### 9.3 当前真实缺失态

当前真实存在的“未完成”表达方式，其实主要是：

- `pending candidate`
- `scaffold ready` 但主对象仍 `result = pending`

也就是说，当前仓库不是通过大量中间状态枚举来表达缺失，而是通过：

- `result` 保持 `pending`
- `status` 保持 `candidate`
- `scaffold_status` 补充“复现入口是否准备好”

---

## 10. 工件侧观察 与 主对象正式状态

当前仓库里已经出现一个很重要的现实情况：

- 主 validation JSON 仍然是 `result = pending`、`status = candidate`
- 但脚手架目录中的 `README.md` 已被写成 `Current result: reproduced`
- `repro_case.py` 中也已存在 `reproduced_issue` 相关逻辑和退出码判断

这说明当前存在：

**工件侧观察已经推进，但主对象正式状态尚未同步升级。**

因此本文件明确规定：

1. 主状态判断优先以 `data/validations/*.json` 为准
2. `validation_samples/` 中的 README、脚本输出、局部执行结果，只能作为辅助证据或观察记录
3. 若未同步回写主 validation JSON，则不能把工件侧 `reproduced` 直接表述为正式 validation 状态

---

## 11. 当前目录与状态流映射

### 11.1 Candidate 落位

```text
data/validations/{framework_id}/{validation_id}.json
```

### 11.2 Scaffold 落位

```text
validation_samples/{framework_id}/{validation_id}/
```

### 11.3 来源回链落位

```text
data/connections/{channel}/{connection_id}.json
```

当前真实映射关系：

- `connection` 触发 `candidate`
- `candidate` 派生 `validation_samples/` 工件
- 主 validation JSON 持续作为正式状态总账

---

## 12. 当前正式语义、当前阶段抽象与中后期预留

### 12.1 当前正式语义

以下状态语义已经可以视为当前正式语义：

- `pending candidate`
- `scaffold ready`
- `executed success` 与 `executed failure` 两类最小正式终态

### 12.2 当前阶段抽象

以下语义当前可以合理抽象，但尚未完全标准化成统一字段：

- 工件侧 `reproduced observation`
- `failed` 之外更细的失败子类
- 中断、取消、人工放弃等未完成终态

### 12.3 中后期预留

以下状态当前没有真实实现依据，只能作为中后期预留：

- 统一失败态
- 统一中断态
- 自动执行态
- 自动重试态
- 人工审核 / 审批态
- 批量验证调度态

---

## 13. 当前不应写成事实的内容

以下内容当前都不应写成现状：

- 完整闭环的自动 validation 状态机
- 已标准化的 `partial` / `blocked` / `reproduced` 主对象状态
- 候选自动升级为执行完成态
- 批量自动调度并回写全部 validation

---

## 14. 后续可考虑的增强方向

在本文件完成后，下一轮优先建议从以下两个方向中选一个：

1. 发起“validation 失败态 / 中断态扩展”任务，把 `failed` 继续拆分为更细粒度正式终态
2. 发起“`QUICKSTART.md` 与 validation 使用说明精修”任务，把当前运行路径、回写命令和状态判断口径写清

如果只选一个优先级更高的方向，建议先做第 2 项。

---

## 15. 一句话收口

**当前最小验证链已经形成 `pending candidate -> scaffold ready -> executed success / executed failure` 的真实状态层，并已具备 `success / failed` 两类最小正式收口，但更细粒度失败态与中断态仍未进入当前正式语义。**
