# OUTPUT_CONTRACTS

## 1. 文档定位

`outputs/OUTPUT_CONTRACTS.md` 是当前项目输出层对象契约说明文件。

本文件只描述当前最小转化链与输出追踪链中已经真实存在的对象和字段，并补充已完成轻量挂接实施落点但尚未形成真实样本的同层预留对象，不把签发流、发布流、审核流等未落地能力写成当前契约。

本文件当前覆盖：

- `article`
- `product-brief`
- `decision-pack`
  - 当前仅覆盖轻量挂接实施落点，不写成已形成真实稳定输出类型
- `code-sample`
  - 当前仅覆盖轻量挂接实施落点，不写成已形成真实稳定输出类型
- `output metadata record`
- `workflow formal entry record`
- `agent runtime result formal entry record`
  - 包括其当前已固化的 `failure-side minimal record`
- `artifact formal entry record`
- `structured output formal entry record`
- `single agent tool call formal entry record`

本文件不覆盖：

- 对外发布流程
- 人工审稿流程
- 多模板系统
- 更多预留输出类型
- `validation` 主对象模型

关于 `validation` 的对象边界、阶段分层、`validation_execution` 子结构职责与 formal entry 排除项，当前主表达面已经独立收口到：

- `VALIDATION_MODEL.md`

关于 `validation` 的状态层与状态转换关系，请同步阅读：

- `VALIDATION_STATE_FLOW.md`

---

## 2. 证据来源

本文件基于以下真实依据整理：

- `engine/transformer/generate_outputs.py`
- `engine/analyzer/run_adk_workflow_minimal_execution.py`
- `engine/analyzer/run_adk_agent_runtime_result_minimal_capture.py`
- `engine/analyzer/run_adk_artifact_minimal_access.py`
- `outputs/articles/` 下真实 Markdown 文件
- `outputs/product-briefs/` 下真实 Markdown 文件
- `outputs/decision-packs/README.md`
- `outputs/code-samples/README.md`
- `outputs/.metadata/` 下真实 JSON 记录
- `outputs/workflow/056-formal-entry-smoke.json`
- `outputs/agent_runtime_result/062-formal-entry-smoke.json`
- `outputs/agent_runtime_result/065-formal-entry-failure-smoke-01.json`
- `outputs/agent_runtime_result/065-formal-entry-failure-smoke-02.json`
- `outputs/artifact/051-formal-entry-smoke.json`
- `outputs/structured_output/042-formal-entry-smoke.json`
- `outputs/structured_output/044-formal-failure-recognition-smoke.json`
- `outputs/structured_output/045-formal-state-protection-smoke.json`
- `outputs/structured_output/046-formal-evidence-trace-smoke.json`
- `outputs/single_agent_tool_call/076-formal-entry-smoke.json`

---

## 3. 当前输出链路

当前最小转化链的真实路径为：

1. 从 `data/insights/{framework_id}/{insight_id}.json` 读取目标 insight
2. 从 `data/frameworks/{framework_id}/metadata.json` 读取对应 framework metadata
3. 由 `engine/transformer/generate_outputs.py` 生成 Markdown 内容
4. 将文件写入 `outputs/articles/` 或 `outputs/product-briefs/`
5. 将追踪记录写入 `outputs/.metadata/`

当前补充说明：

- `framework metadata formal entry` 已按根层直承接实施
- 输出层消费的是现有 framework metadata 主对象，而不是额外的内嵌 formal entry 子结构
- 当前 article / product-brief 两条消费链都会先对 framework metadata 做 formal-entry-normalized 读取
- `metadata.source_documents[]`、`metadata.input_channels[]`、`timestamps.first_analyzed / last_updated` 已进入 framework metadata 的最小正式承接面
- `version_schema`、`metadata.source`、`metadata.migration_spec`、`timestamps.next_review` 仍不进入输出层正式输入契约
- `insight formal entry` 已按根层直承接实施
- 输出层消费的是现有 insight 主对象，而不是额外的内嵌 formal entry 子结构
- 当前 article / product-brief 两条消费链都已以 formal-entry-normalized insight 作为稳定输入
- `trace_id` 当前不进入 insight 输出层的正式输入契约
- `connection-formal-entry` 的正式主表达面当前收口在 `DATA_MODELS.md`，而不是输出层契约
- 输出层当前不直接消费 `connection` 主对象生成 article / product-brief，也不反向定义 `connection.connections[]` 的关系子面
- 因此 `connection-formal-entry` 与输出层的当前稳定边界是：
  - 输出层只保持“不误吞并上游 formal entry”的边界说明
  - `connection` 主对象与 `connections[]` 的正式表达继续由数据对象契约负责
- `decision-pack` 当前已完成内部真实生成链、metadata `type = decision-pack` 追踪写入能力、Markdown fixture 与结构契约测试；但尚未形成正式 `ce` 产品入口、稳定展示样例或公开发布面
- `code-sample` 当前已完成同层目录与契约落点挂接，但尚未进入真实脚本写入链与 metadata 追踪链

---

## 4. 当前已稳定输出对象

### 4.1 Article

目录落位：

```text
outputs/articles/
```

当前生成入口：

```bash
python engine/transformer/generate_outputs.py --insight <insight_id> --type article
```

#### 4.1.1 最小输入契约

当前脚本对 `article` 的输入依赖包括：

来自 insight 的字段：

- `id`
- `framework_id`
- `title`
- `description`
- `confidence`
- `impact.architectural`
- `impact.migration`
- `impact.product`
- `evidence`
- `connections`
- `tags`
- `category`

来自 framework metadata 的字段：

- `name`
- `version`
- `metadata.analysis_depth`

当前结论：

**`article` 不是从任意 JSON 直接生成，而是至少依赖一条结构完整的 insight 和其对应 framework metadata。**

当前边界补充：

- 输出层当前直接使用的 framework metadata 字段仍是 `name`、`version`、`metadata.analysis_depth`
- formal-entry-normalized 读取的价值在于保证 framework metadata 的根层主字段面与正式背景子面稳定，不等于输出层一次性消费全部字段

#### 4.1.2 最小输出契约

当前输出格式：

- Markdown 文本文件

当前已在真实文件中稳定出现的结构块：

1. 一级标题，标题来源于 insight `title`
2. `## 框架背景`
3. `## 洞察摘要`
4. `## 架构影响`
5. `## 证据支撑`
6. `## 相关洞察`
7. `## 标签`
8. `## 产品化建议`
9. `## 技术细节`
10. `## 总结`
11. 尾部生成时间与来源信息

当前注意事项：

- 内容是模板化生成稿
- 文中“代码示例”是概念性示例，不是实际 ADK 代码
- 当前不应被写成“已发布文章”

#### 4.1.3 文件命名契约

当前命名规则：

```text
articles-{framework_id}-{insight_id}-{YYYYMMDD-HHMMSS-ffffff}.md
```

当前样例：

```text
outputs/articles/articles-adk-2.0.0a3-insight-adk-event-system-20260416-004116.md
```

### 4.2 Product Brief

目录落位：

```text
outputs/product-briefs/
```

当前生成入口：

```bash
python engine/transformer/generate_outputs.py --insight <insight_id> --type product-brief
```

#### 4.2.1 最小输入契约

当前脚本对 `product-brief` 的输入依赖包括：

来自 insight 的字段：

- `id`
- `title`
- `description`
- `category`
- `confidence`
- `impact.architectural`
- `impact.migration`
- `impact.product`
- `tags`
- `evidence`
- `connections`

来自 framework metadata 的字段：

- `name`
- `version`

说明：

- 当前实现已经把 `product-brief` 从泛化商业模板推进为“场景驱动的正式简报模板”
- 当前正式 CLI 闭环 `ce brief` 只接受单个 `insight_id`
- `--insight` 缺失、`insight_id` 不存在、额外位置参数或多 ID 写法，当前都应视为输入失败而不是成功降级

#### 4.2.2 最小输出契约

当前输出格式：

- Markdown 文本文件

当前已在真实文件中稳定出现的结构块：

1. 一级标题，格式为 `# 产品简报: {insight_title}`
2. `## 一页结论`
3. `## 适用场景`
4. `## 目标使用者`
5. `## 用户问题`
6. `## 产品主张`
7. `## 上线边界`
8. `## 证据与可信度`
9. `## 相关洞察`
10. `## 下一步行动`
11. 尾部生成时间、洞察来源与置信度

当前注意事项：

- 当前内容是自动生成的简报稿
- 当前模板已优先围绕真实场景、证据、边界和下一步动作组织
- 当前不应被写成已经过业务签发的正式简报
- 当前模板稳定性已至少在以下真实样本中验证：
  - `insight-adk-runner-centrality`
  - `insight-adk-event-system`
- 对 `code_reference` 与 `call_chain` 两类证据，当前模板都已能生成可读摘要

#### 4.2.3 文件命名契约

当前命名规则：

```text
product-briefs-{framework_id}-{insight_id}-{YYYYMMDD-HHMMSS-ffffff}.md
```

当前样例：

```text
outputs/product-briefs/product-briefs-adk-2.0.0a3-insight-adk-event-system-20260416-004116.md
```

#### 4.2.4 `ce brief` 最小命令契约

当前正式命令：

```bash
ce brief --insight <insight_id>
```

当前输入边界：

- `--insight` 必填
- 当前只接受单个 `insight_id`
- 不接受额外位置参数或多 ID 列表

当前返回码约定：

- `0`：命令执行成功，并已生成 `product-brief` 与 metadata
- `2`：输入错误或命令使用错误
- `1`：未预期运行错误

#### 4.2.5 `ce brief --json` 最小结果契约

当前成功结果至少包含以下正式字段：

- `status`
- `command_name`
- `usage`
- `contract_version`
- `closure_id`
- `output_type`
- `insight_id`
- `output_file`
- `metadata_file`
- `generated_at`
- `validation`

当前失败结果至少包含以下正式字段：

- `status`
- `command_name`
- `usage`
- `contract_version`
- `closure_id`
- `output_type`
- `error_code`
- `error_message`

当前成功 `status` 固定为：

- `success`

当前失败 `status` 固定为：

- `error`

当前已稳定的失败 `error_code` 包括：

- `missing_insight`
- `invalid_insight_id`
- `insight_not_found`
- `framework_not_found`
- `unexpected_args`
- `internal_error`

当前成功样例中还稳定返回的增强字段包括：

- `brief_summary`
- `primary_use_case`
- `recommended_action`

#### 4.2.4 当前 formal entry 消费边界

当前 product brief 消费的是：

1. insight 根层正式主字段面
2. framework metadata 的最小背景字段

当前 product brief 不消费也不承接：

1. `connection` 快照本体
2. `quote / source_path / file / chain / entry_point`
3. `trace_id`
4. 关系类型闭集枚举

#### 4.2.5 当前轻量挂接固化

当前 `product-brief` 的兄弟对象轻量挂接，正式按以下方式固化：

1. 当前参照样板对象：
   - `article`
2. 参照理由：
   - 同属输出层文件型对象
   - 同属 `generate_outputs.py` 生成链
   - 同属 `outputs/.metadata/` 追踪链
   - 同属 `outputs/` 下的并列正式输出位

当前 `product-brief` 可直接继承的对象边界包括：

1. 同属“单条 insight + 对应 framework metadata 派生出的 Markdown 输出稿”
2. 同属“已生成稿，不等于已发布稿”
3. 不替代 `insight` 主对象
4. 不替代 `framework metadata` 主对象
5. 不吞并 `output metadata record`
6. 不把目录载体当成对象本体
7. 不把仪表盘或 README 示例当成对象契约层

当前 `product-brief` 必须单独补充的差异包括：

1. 输入字段面更薄：
   - insight 侧当前真正稳定消费 `id / title / category / confidence`
   - framework 侧当前真正稳定消费 `name`
2. 正文结构不同：
   - 当前围绕机会概述、目标用户、核心价值、市场规模、实施路线图、风险评估、成功指标、资源需求、建议展开
3. 用途定位不同：
   - 当前是业务压缩表达对象，不是技术阐释对象
4. 尾部来源说明不同：
   - 当前以洞察来源 ID 与置信度为主，而不是文章型来源路径说明

当前 `product-brief` 继续保持排除的内容包括：

1. 正式签发状态
2. 外部分发状态
3. 审核链、签发链与发布 URL
4. `connection` 快照本体与关系类型闭集枚举
5. `trace_id`
6. 证据摘要、相关洞察列表与技术细节展开

当前实施边界必须明确：

1. `product-brief` 可直接轻量挂入现有输出对象体系
2. 当前不需要新的承接载体
3. 当前不需要新的命名规则
4. 当前不需要新的长期资产主载体
5. 当前不应据此宣布 `product-brief-formal-entry` 已成立
6. 当前也不应把它重新拉回完整治理重链

#### 4.2.6 当前受众版本分层挂接契约

“面向不同受众的简报版本分层”当前作为 `product-brief` 目录内的同骨架延展方向，只补最小挂接契约，不写成新的真实稳定输出类型。

当前同骨架延展前提如下：

1. 仍沿用“单条 insight + 对应 framework metadata 派生出的 Markdown 输出稿”外层骨架
2. 文件继续落在 `outputs/product-briefs/`
3. 对象类型继续保持 `product-briefs`
4. 当前不引入新的目录主载体、对象类型或 formal entry 路径

当前命名预期如下：

1. 当前真实已生成 `product-brief` 样本仍保持既有命名规则
2. 若后续进入受众分层真实样本生成，当前应遵循的延展命名骨架为：

```text
product-briefs-{framework_id}-{insight_id}-{audience_key}-{YYYYMMDD-HHMMSS-ffffff}.md
```

3. 其中 `audience_key` 应保持为稳定、可枚举、可用于文件系统的 ASCII 标识
4. 该命名扩展用于稳定区分同一 `insight` 下的多个受众版本，不等于新对象族命名

当前 `audience` 追踪预期如下：

1. 当前真实 metadata 最小字段仍未包含 `audience`
2. 若后续进入受众分层真实追踪，现有 `product-briefs` metadata 记录应显式新增：
   - `audience`
3. `audience` 应与文件命名中的 `audience_key` 一致对应
4. 当前不需要新增新的 metadata 目录载体或新的 `type`

当前消费边界如下：

1. 仍以 insight 根层正式主字段面与 framework metadata 最小背景字段为输入边界
2. 当前对象差异主要体现在：
   - 围绕不同受众重排重点、语气、字段厚度与决策关注点
3. 当前不消费也不承接：
   - `connection` 快照本体
   - `quote / source_path / file / chain / entry_point`
   - `trace_id`
   - 审核链、签发链、发布 URL 与外部分发状态
4. 当前也不把“受众版本分层”外推为已建立版本发布对象、对外承诺对象或发布体系对象

当前实施边界如下：

1. 当前实施只代表 `product-brief` 同类型内部的受众维度挂接落点已补齐
2. 当前不代表仓内已经存在真实“受众分层”Markdown 样本
3. 当前不代表仓内已经存在带 `audience` 字段的真实 metadata 记录
4. 当前不代表 `generate_outputs.py` 已支持受众维度生成分支
5. 当前不需要新的长期资产主载体
6. 当前不应据此宣布“面向不同受众的简报版本分层”已成为独立正式输出对象
7. 当前也不应把它重新拉回完整治理重链

### 4.3 Decision Pack

目录落位：

```text
outputs/decision-packs/
```

当前生成入口：

    python engine/transformer/generate_outputs.py --insight <insight_id> --type decision-pack

当前正式 CLI 入口：

    ce decision-pack --insight <insight_id>
    ce decision-pack --insight <insight_id> --json

当前状态说明：

1. 当前已完成同层目录落位与对象级契约挂接
2. 当前已具备内部真实生成函数 `generate_decision_pack`
3. 当前已具备底层生成器分支 `generate_outputs.py --type decision-pack`
4. 当前已可写入 `outputs/decision-packs/` 运行产物
5. 当前 metadata `type` 已稳定使用 `decision-pack`
6. 当前已建立正式 `ce decision-pack` 产品入口
7. 当前已建立 JSON 结果契约 `ce-decision-pack-result/v1`
8. 当前已建立 Markdown fixture 与结构契约测试：
   - `tests/fixtures/decision-packs/runner-centrality.md`
   - `tests/unit/test_output_generator.py`
9. 当前已建立 JSON 结果 fixture：
   - `tests/fixtures/decision-packs/json/runner-centrality-result.json`
10. 当前已建立 metadata fixture：
   - `tests/fixtures/decision-packs/metadata/runner-centrality-metadata.json`
11. 当前已建立稳定展示样例：
   - `examples/decision-packs/runner-centrality.md`
12. 当前已建立动态字段归一化测试：
   - `tests/unit/test_decision_pack_loop.py`
13. 当前 README / README.en / QUICKSTART 已完成首轮公开说明同步
14. 当前仍未进入公仓发布、版本号推进、tag / Release 或第二正式产品闭环公开宣布

#### 4.3.1 当前挂接前提

当前 `decision-pack` 的最小挂接前提如下：

1. 继续沿用“单条 insight + 对应 framework metadata 派生 Markdown 输出稿”的外层骨架
2. 当前不引入新的上游主对象关系
3. 当前不引入新的承接载体类型
4. 当前不把目录壳、README、消费层或 metadata 追踪反写成对象本体

当前必须继续保持的输入边界如下：

1. 当前不直接消费 `connection` 快照本体
2. 当前不直接消费 `quote / source_path / file / chain / entry_point`
3. 当前不消费 `trace_id`
4. 当前不反向定义关系类型闭集枚举

#### 4.3.2 当前最小对象结构期望

当前 `decision-pack` 内部真实生成链已固化以下最小结构期望，并已通过 Markdown fixture 与结构契约测试验证：

1. 输出格式应保持为 Markdown 文本文件
2. 标题应与对象名一致，当前最小期望格式为 `# 决策包: {insight_title}`
3. 正文应显式体现：
   - 待决问题
   - 候选方案
   - 取舍理由
   - 建议结论
   - 待确认项
4. 尾部来源说明应继续保留生成时间、洞察来源与置信度这类最小追溯信息

#### 4.3.3 当前同层命名预期

若后续进入真实样本生成，当前应遵循的同层命名骨架为：

```text
decision-packs-{framework_id}-{insight_id}-{YYYYMMDD-HHMMSS-ffffff}.md
```

当前说明：

1. 这属于同层对象命名规则
2. 当前内部生成链已经可按该规则写入运行产物
3. 当前 Markdown fixture 使用稳定文件名 `tests/fixtures/decision-packs/runner-centrality.md`，不等同于运行产物命名
4. 当前稳定展示样例使用稳定文件名 `examples/decision-packs/runner-centrality.md`，不等同于运行产物命名

#### 4.3.4 当前 formal entry 消费边界

当前 `decision-pack` 若进入真实生成，消费边界应先收口为：

1. insight 根层正式主字段面
2. framework metadata 的最小背景字段

当前 `decision-pack` 不消费也不承接：

1. `connection` 快照本体
2. `quote / source_path / file / chain / entry_point`
3. `trace_id`
4. 关系类型闭集枚举
5. 发布平台语义与分发状态

#### 4.3.5 当前轻量挂接实施边界

当前 `decision-pack` 的轻量挂接实施，正式按以下方式固化：

1. 当前参照样板对象：
   - `product-brief`
2. 参照理由：
   - 同属输出层文件型对象
   - 同属 `insight + framework metadata + Markdown` 外层骨架
   - 当前表达目标都更偏业务压缩表达，而非技术阐释

当前 `decision-pack` 可直接继承的对象边界包括：

1. 同属“单条 insight + 对应 framework metadata 派生出的 Markdown 输出稿”
2. 同属“已生成稿，不等于已发布稿”
3. 不替代 `insight` 主对象
4. 不替代 `framework metadata` 主对象
5. 不吞并 `output metadata record`
6. 不把目录载体当成对象本体
7. 不把仪表盘或 README 示例当成对象契约层

当前 `decision-pack` 必须单独补充的差异包括：

1. 用途定位差异：
   - 当前偏决策取舍承接，不是业务概述改名版
2. 正文结构差异：
   - 当前最小结构应显式体现待决问题、候选方案、取舍理由、建议结论、待确认项
3. 输入面差异：
   - 当前需要明确哪些上游事实足以支撑“决策取舍”而不只是“业务概述”
4. 对象名差异：
   - 目录名、标题模式、README 与后续 metadata `type` 都需与 `decision-pack` 对象名一致

当前 `decision-pack` 继续保持排除的内容包括：

1. 正式签发状态
2. 外部分发状态
3. 审核链、签发链与发布 URL
4. `connection` 快照本体与关系类型闭集枚举
5. `trace_id`
6. 技术细节、概念性代码示例与证据长展开

当前实施边界必须明确：

1. 当前实施代表内部真实生成链已经成立
2. 当前已可生成真实 Markdown 运行产物
3. 当前 metadata `type = decision-pack` 已可进入真实追踪链
4. 当前已建立 Markdown fixture 与结构契约测试
5. 当前不需要新的承接载体规则
6. 当前不需要新的命名规则
7. 当前不需要新的长期资产主载体
8. 当前已代表正式 `ce decision-pack` 产品入口首轮能力成立
9. 当前已代表 metadata fixture 首轮结构基线成立
10. 当前已代表稳定展示样例首轮建设成立
11. 当前已代表 README / README.en / QUICKSTART 首轮公开说明同步完成
12. 当前不代表公仓发布、版本号推进、tag / Release 已经启动
13. 当前不应据此宣布第二正式产品闭环已经公开完成
14. 当前也不应把它重新拉回完整治理重链

### 4.4 Code Sample

目录落位：

```text
outputs/code-samples/
```

当前生成入口：

- 当前尚无独立脚本生成入口

当前状态说明：

1. 当前仅完成同层目录落位与对象级契约挂接
2. 当前尚无真实 Markdown 样本
3. 当前尚无稳定 metadata `type`
4. 当前尚无 `generate_outputs.py --type code-sample` 分支

#### 4.4.1 当前挂接前提

当前 `code-sample` 的最小挂接前提如下：

1. 继续沿用“单条 insight + 对应 framework metadata 派生文件型输出稿”的外层骨架
2. 当前不引入新的上游主对象关系
3. 当前不引入新的 formal entry 路径
4. 当前不把目录壳、README、消费层或 metadata 追踪反写成对象本体

当前必须继续保持的输入边界如下：

1. 当前不直接消费 `connection` 快照本体
2. 当前不直接消费 `quote / source_path / file / chain / entry_point`
3. 当前不消费 `trace_id`
4. 当前不反向定义关系类型闭集枚举

#### 4.4.2 当前最小对象结构期望

当前 `code-sample` 轻量挂接实施只固化最小结构期望，不写成已形成稳定样本：

1. 输出格式应保持为 Markdown 文本文件
2. 标题应与对象名一致，当前最小期望格式为 `# 代码样例: {insight_title}`
3. 正文应显式体现：
   - 样例目标
   - 前置条件
   - 最小步骤
   - 示例代码
   - 验证方式
   - 边界说明
4. 尾部来源说明应继续保留生成时间、洞察来源与置信度这类最小追溯信息

#### 4.4.3 当前同层命名预期

若后续进入真实样本生成，当前应遵循的同层命名骨架为：

```text
code-samples-{framework_id}-{insight_id}-{YYYYMMDD-HHMMSS-ffffff}.md
```

当前说明：

1. 这属于同层对象命名预期
2. 当前不代表真实样本已经生成

#### 4.4.4 当前 formal entry 消费边界

当前 `code-sample` 若进入真实生成，消费边界应先收口为：

1. insight 根层正式主字段面
2. framework metadata 的最小背景字段

当前 `code-sample` 不消费也不承接：

1. `connection` 快照本体
2. `quote / source_path / file / chain / entry_point`
3. `trace_id`
4. 关系类型闭集枚举
5. 发布平台语义与分发状态

#### 4.4.5 当前轻量挂接实施边界

当前 `code-sample` 的轻量挂接实施，正式按以下方式固化：

1. 当前参照样板对象：
   - `article`
2. 参照理由：
   - 同属输出层文件型对象
   - 同属 `insight + framework metadata + Markdown` 外层骨架
   - 当前表达目标都更偏技术表达，而非业务压缩表达

当前 `code-sample` 可直接继承的对象边界包括：

1. 同属“单条 insight + 对应 framework metadata 派生出的文件型输出稿”
2. 同属“已生成稿，不等于已发布稿”
3. 不替代 `insight` 主对象
4. 不替代 `framework metadata` 主对象
5. 不吞并 `output metadata record`
6. 不把目录载体当成对象本体
7. 不把仪表盘或 README 示例当成对象契约层

当前 `code-sample` 必须单独补充的差异包括：

1. 用途定位差异：
   - 当前偏最小实现样例、调用方式、使用路径与验证方法承接，不是技术文章改名版
2. 正文结构差异：
   - 当前最小结构应显式体现样例目标、前置条件、最小步骤、示例代码、验证方式、边界说明
3. 输入面差异：
   - 当前需要明确哪些上游事实足以支撑“样例承接”而不只是“技术解释”
4. 对象名差异：
   - 目录名、标题模式、README 与后续 metadata `type` 都需与 `code-sample` 对象名一致

当前 `code-sample` 继续保持排除的内容包括：

1. 正式签发状态
2. 外部分发状态
3. 审核链、签发链与发布 URL
4. `connection` 快照本体与关系类型闭集枚举
5. `trace_id`
6. `article` 风格的证据长展开、相关洞察列表与产品化建议长文本
7. 未经锁定的多文件工程脚手架、完整项目模板、包管理与 CI 语义

当前实施边界必须明确：

1. 当前实施只代表最小挂接落盘成立
2. 当前不代表真实样本已稳定生成
3. 当前不代表 metadata `type` 已进入真实追踪链
4. 当前不需要新的承接载体规则
5. 当前不需要新的命名规则
6. 当前不需要新的长期资产主载体
7. 当前不应据此宣布 `code-sample-formal-entry` 已成立
8. 当前也不应把它重新拉回完整治理重链

### 4.5 Business Report

目录落位：

```text
outputs/business-reports/
```

当前生成入口：

- 当前尚无独立脚本生成入口

当前状态说明：

1. 当前仅完成同层目录落位与对象级契约挂接
2. 当前尚无真实 Markdown 样本
3. 当前尚无稳定 metadata `type` 进入真实追踪链
4. 当前尚无 `generate_outputs.py --type business-report` 分支

#### 4.5.1 当前挂接前提

当前 `business-report` 的最小挂接前提如下：

1. 继续沿用“单条 insight + 对应 framework metadata 派生 Markdown 输出稿”的外层骨架
2. 当前不引入新的上游主对象关系
3. 当前不引入新的承接载体类型
4. 当前不引入新的 formal entry 路径
5. 当前不把目录壳、README、消费层或 metadata 追踪反写成对象本体

当前稳定对象命名如下：

1. 中文对象名：
   - `业务汇报`
2. 英文对象名：
   - `business-report`
3. 目录名：
   - `business-reports`
4. metadata `type`：
   - `business-reports`

#### 4.5.2 当前最小对象结构期望

当前 `business-report` 轻量挂接实施只固化最小结构期望，不写成已形成稳定样本：

1. 输出格式应保持为 Markdown 文本文件
2. 标题应与对象名一致，当前最小期望格式为 `# 业务汇报: {insight_title}`
3. 正文应显式体现：
   - 汇报摘要
   - 业务背景
   - 核心判断
   - 关键风险
   - 资源与推进建议
4. 尾部来源说明应继续保留生成时间、洞察来源与置信度这类最小追溯信息

#### 4.5.3 当前同层命名预期

若后续进入真实样本生成，当前应遵循的同层命名骨架为：

```text
business-reports-{framework_id}-{insight_id}-{YYYYMMDD-HHMMSS-ffffff}.md
```

当前说明：

1. 这属于同层对象命名预期
2. 当前不代表真实样本已经生成

#### 4.5.4 当前 formal entry 消费边界

当前 `business-report` 若进入真实生成，消费边界应先收口为：

1. insight 根层正式主字段面
2. framework metadata 的最小背景字段

当前 `business-report` 不消费也不承接：

1. `connection` 快照本体
2. `quote / source_path / file / chain / entry_point`
3. `trace_id`
4. 关系类型闭集枚举
5. 审核链、签发链、发布 URL 与外部分发状态
6. 已发布版本、对外承诺对象与版本边界对象

#### 4.5.5 当前轻量挂接实施边界

当前 `business-report` 的轻量挂接实施，正式按以下方式固化：

1. 当前参照样板对象：
   - `product-brief`
2. 参照理由：
   - 同属输出层文件型对象
   - 同属 `insight + framework metadata + Markdown` 外层骨架
   - 当前表达目标都偏业务压缩表达，但 `business-report` 更偏正式汇报面

当前 `business-report` 可直接继承的对象边界包括：

1. 同属“单条 insight + 对应 framework metadata 派生出的 Markdown 输出稿”
2. 同属“已生成稿，不等于已发布稿”
3. 不替代 `insight` 主对象
4. 不替代 `framework metadata` 主对象
5. 不吞并 `output metadata record`
6. 不把目录载体当成对象本体
7. 不把仪表盘或 README 示例当成对象契约层

当前 `business-report` 必须单独补充的差异包括：

1. 用途定位差异：
   - 当前偏更正式业务汇报面承接，不是通用业务概述改名版
2. 正文结构差异：
   - 当前最小结构应显式体现汇报摘要、业务背景、核心判断、关键风险、资源与推进建议
3. 输入面差异：
   - 当前需要明确哪些上游事实会在更正式汇报场景下被前置、强化或重组
4. 对象名差异：
   - 目录名、标题模式、README 与后续 metadata `type` 都需与 `business-report` 对象名一致

当前 `business-report` 继续保持排除的内容包括：

1. 正式签发状态
2. 外部分发状态
3. 审核链、签发链与发布 URL
4. `connection` 快照本体与关系类型闭集枚举
5. `trace_id`
6. `decision-pack` 风格的待决问题、方案比较与取舍理由承接
7. `code-sample` 风格的技术样例、示例代码与验证路径
8. “面向不同受众的简报版本分层”风格的受众版本拆分语义

当前实施边界必须明确：

1. 当前实施只代表最小挂接落盘成立
2. 当前不代表真实样本已稳定生成
3. 当前不代表 metadata `type = business-reports` 已进入真实追踪链
4. 当前不代表 `generate_outputs.py` 已支持 `--type business-report`
5. 当前不需要新的承接载体规则
6. 当前不需要新的长期资产主载体
7. 当前不应据此宣布 `business-report-formal-entry` 已成立
8. 当前也不应把它重新拉回完整治理重链

### 4.6 Output Metadata Record

目录落位：

```text
outputs/.metadata/
```

当前真实样本中的最小字段：

```json
{
  "id": "output-20260416-004116",
  "type": "product-brief",
  "title": "产品简报: 基于Event和EventActions的事件收口机制",
  "insight_id": "insight-adk-event-system",
  "framework_id": "adk-2.0.0a3",
  "file_path": "outputs/product-briefs/product-briefs-adk-2.0.0a3-insight-adk-event-system-20260416-004116.md",
  "generated_at": "2026-04-16T00:41:16.590706",
  "format": "md",
  "size_bytes": 2265
}
```

当前边界补充：

- output metadata record 继续只承担输出追踪职责
- 它不反向定义 insight formal entry 主模型
- `trace_id` 当前也不提升为 output metadata record 与 insight formal entry 之间的正式关联字段

当前可视为稳定字段：

- `id`
- `type`
- `title`
- `insight_id`
- `framework_id`
- `file_path`
- `generated_at`
- `format`
- `size_bytes`

当前真实 `type` 取值：

- `article`
- `product-brief`

当前命名规则：

```text
outputs/.metadata/output-{YYYYMMDD-HHMMSS-ffffff}.json
```

历史补录约定：

1. 当前运行时新生成 metadata 仍遵循上述微秒级命名规则
2. 若需补录历史秒级批次中因同批次多输出导致被覆盖的记录，可使用：

```text
outputs/.metadata/output-{YYYYMMDD-HHMMSS}-article-backfill.json
```

3. 这类 `-article-backfill` 记录仅用于修复历史 `article` 覆盖缺口
4. 它不表示当前运行时命名规则已改回秒级或允许多类型共享同一 metadata id
5. 若原始 `article` metadata 已丢失而同批次 `product-brief` metadata 仍在，可沿用该批次已保留的 `generated_at` 秒级批次时间作为补录时间依据

当前必须额外明确：

- 当前真实 `type` 取值仍未包含 `decision-packs`
- 当前真实 `type` 取值仍未包含 `code-samples`
- 当前真实 metadata 最小字段仍未包含 `audience`

### 4.7 Workflow Formal Entry Record

> 当前边界说明：本节原有 `workflow formal entry` 内容主要记录早期 ADK workflow formal entry 取证契约，涉及 `engine/analyzer/run_adk_workflow_minimal_execution.py` 与 `outputs/workflow/`。
>
> v0.2.0 当前公开发布口径中的 `ce workflow` 是另一条产品化入口链路，其 workflow-level Markdown 汇总产物位于 `outputs/workflows/`，workflow-level metadata 仍写入 `outputs/.metadata/`，并已完成 ADK-backed workflow 最小承接。
>
> 因此，早期 `outputs/workflow/` formal entry 契约不得直接等同于当前 `ce workflow` 产品化输出契约；后续如需正式发布 `ce workflow` 输出契约，应另行补充独立条目。

#### 4.7.0 当前 ce workflow 产品化输出边界

当前 `ce workflow` 的产品化输出边界如下：

1. 公开入口：`ce workflow --insight <insight_id>` 与 `ce workflow --insight <insight_id> --json`。
2. 子产物：product brief、decision pack、model enhancement。
3. workflow-level Markdown 汇总产物目录：`outputs/workflows/`。
4. workflow-level metadata 目录：`outputs/.metadata/`。
5. workflow result 包含 execution / session / context / invocation 映射字段。
6. workflow result 包含 `event_summary`。
7. workflow result 包含 `artifact_refs`。
8. 当前公开 CLI 不暴露真实 provider 参数。
9. 当前不把业务 metadata 宣传为 ADK 原生 observability。
10. 当前不把 `outputs/` 宣传为完整 ADK Artifact store。


目录落位：

```text
outputs/workflow/
```

当前生成入口：

```bash
python engine/analyzer/run_adk_workflow_minimal_execution.py --json-only
```

显式指定输出文件时：

```bash
python engine/analyzer/run_adk_workflow_minimal_execution.py \
  --output-file outputs/workflow/manual-workflow.json \
  --json-only
```

当前真实样本：

```text
outputs/workflow/056-formal-entry-smoke.json
```

#### 4.6.1 最小输入边界

当前 workflow formal entry 直接暴露的输入参数只有：

- `--input-text`
- `--output-file`
- `--json-only`

说明：

- 当前脚本确实支持传入 `input_text`
- 但它目前只服务于最小两节点串行 workflow 样板
- 因此，当前不应把“任意输入业务语义”写成稳定输出契约前提

#### 4.6.2 最小输出契约

当前 workflow formal entry 的成功输出格式为：

- JSON 文件

当前已在真实 smoke 文件中出现，且可视为最小正式契约的字段包括：

- `entry_id`
- `entry_type`
- `framework_id`
- `capability_surface`
- `engine_entry`
- `probe_reference`
- `result`
- `output_file`
- `workflow_name`
- `workflow_node_count`
- `workflow_execution_order`
- `final_output_text`
- `boundary_judgement`
- `workflow_graph_built`
- `workflow_serial_execution_completed`
- `formal_output_written`

当前最小契约含义如下：

1. `entry_id / entry_type` 用于标识这是哪一个正式入口对象
2. `framework_id / capability_surface` 用于标识当前能力面与底层来源框架
3. `engine_entry / probe_reference` 用于回链实现文件与验证基线
4. `result` 用于表达本次正式入口是否成功
5. `output_file` 用于指向正式结果文件落点
6. `workflow_name / workflow_node_count / workflow_execution_order` 用于表达当前最小 workflow 样板
7. `final_output_text` 用于表达当前最小串行闭环最终产物
8. `boundary_judgement` 用于固定当前允许宣称与禁止外推边界
9. `workflow_graph_built / workflow_serial_execution_completed / formal_output_written` 用于表达最小正式闭环是否成立

#### 4.6.3 当前保留在 smoke、但不升级为正式契约的字段

以下字段当前已真实存在于 smoke 文件中，但不升级为最小正式输出契约：

- `started_at`
- `completed_at`
- `duration_seconds`
- `python_version`
- `os`
- `input_text`

原因如下：

1. 它们主要用于证明某次运行与当时环境确实存在
2. 它们不是后续消费 workflow 正式结果所必需依赖的稳定字段
3. `input_text` 当前只是最小样板输入，不宜提前升级为稳定业务契约

#### 4.6.4 文件命名契约

当前 workflow smoke 文件命名规则已固定为：

```text
outputs/workflow/<task-id>-formal-entry-smoke.json
```

当前真实样例：

```text
outputs/workflow/056-formal-entry-smoke.json
```

当用户显式传入 `--output-file` 时，可写出自定义文件名；但这不改变默认目录与最小字段契约。

### 4.8 Agent Runtime Result Formal Entry Record

目录落位：

```text
outputs/agent_runtime_result/
```

当前生成入口：

```bash
python engine/analyzer/run_adk_agent_runtime_result_minimal_capture.py --json-only
```

显式指定输出文件时：

```bash
python engine/analyzer/run_adk_agent_runtime_result_minimal_capture.py \
  --output-file outputs/agent_runtime_result/manual-agent-runtime-result.json \
  --json-only
```

当前真实样本：

```text
outputs/agent_runtime_result/062-formal-entry-smoke.json
outputs/agent_runtime_result/065-formal-entry-failure-smoke-01.json
outputs/agent_runtime_result/065-formal-entry-failure-smoke-02.json
```

#### 4.7.1 最小输入边界

当前 agent runtime result formal entry 直接暴露的输入参数只有：

- `--input-text`
- `--output-file`
- `--mock-response-text`
- `--json-only`

说明：

- 当前脚本确实支持传入 `input_text`
- 但它目前只服务于 `LlmAgent(single_turn)` 的最小 runtime result 样板
- `--mock-response-text` 只用于在既有 formal entry 下触发可重复的 failure-side minimal record，不表示独立 failure 入口
- 因此，当前不应把“任意输入业务语义”写成稳定输出契约前提

#### 4.7.2 最小输出契约

当前 agent runtime result formal entry 的成功输出格式为：

- JSON 文件

当前已在真实 smoke 文件中出现，且可视为最小正式契约的字段包括：

- `entry_id`
- `entry_type`
- `framework_id`
- `capability_surface`
- `engine_entry`
- `probe_reference`
- `result`
- `selected_runtime_path`
- `output_file`
- `agent_name`
- `agent_mode`
- `output_key`
- `runtime_result_text`
- `internal_observation`
- `context_access`
- `runner_execution`
- `boundary_judgement`
- `entered_agent_runtime_semantics`
- `runtime_result_captured`
- `output_key_state_observed`
- `formal_output_written`

当前最小契约含义如下：

1. `entry_id / entry_type` 用于标识这是哪一个正式入口对象
2. `framework_id / capability_surface` 用于标识当前能力面与底层来源框架
3. `engine_entry / probe_reference` 用于回链实现文件与验证基线
4. `result` 用于表达本次正式入口是否成功
5. `selected_runtime_path` 用于固定当前已被正式承认的最小执行路径
6. `output_file` 用于指向正式结果文件落点
7. `agent_name / agent_mode / output_key` 用于表达当前最小 agent 样板
8. `runtime_result_text` 用于表达当前统一正式结果值
9. `internal_observation` 用于承接共享嵌入式观测子结构：
   - `observed_node_names`
   - `semantic_observation`
   - `event_records[]`
10. `context_access` 用于承接共享嵌入式上下文子结构：
   - `state_delta`
   - `session_state`
11. `runner_execution` 用于承接共享嵌入式执行承接子结构：
   - `Runner`
   - `request_acceptance`
   - `event_consumption`
   - `append_progression`
   - `response_return`
12. `boundary_judgement` 用于固定当前允许宣称与禁止外推边界
13. `entered_agent_runtime_semantics / runtime_result_captured / output_key_state_observed / formal_output_written` 用于表达最小正式闭环是否成立

#### 4.7.3 当前保留在 smoke、但不升级为正式契约的字段

以下字段当前已真实存在于 smoke 文件中，但不升级为最小正式输出契约：

- `started_at`
- `completed_at`
- `duration_seconds`
- `python_version`
- `os`
- `input_text`
- `content_text_result`
- `state_delta`
- `session_state`

原因如下：

1. 前 `5` 个字段主要用于证明某次运行与当时环境确实存在
2. `input_text` 当前只是最小样板输入，不宜提前升级为稳定业务契约
3. `content_text_result` 只是结果被观察到的一条证据通道，当前统一正式结果应以 `runtime_result_text` 表达
4. host 顶层 `state_delta / session_state` 属于内部状态证据，不宜把其序列化细节升级为稳定消费契约

这里必须额外明确：

- `internal_observation.event_records[].state_delta` 已作为共享嵌入式观测子结构的一部分进入正式契约
- `context_access.session_state` 是 `session.state` 的 formal entry 承接位，不等于 host 顶层 `session_state` 证明字段
- `runner_execution` 只承接 `Runner` 与执行主协调闭环，不承接 `Runner(node=...)`、`Runner(agent=...)`、`Session / InvocationContext / Context` 或 `/run*` 入口差异
- 但这不等于把 host 顶层的 `state_delta / session_state` 升级为稳定消费字段

#### 4.7.4 文件命名契约

当前 agent runtime result smoke 文件命名规则已固定为：

```text
outputs/agent_runtime_result/<task-id>-formal-entry-smoke.json
```

当前真实样例：

```text
outputs/agent_runtime_result/062-formal-entry-smoke.json
```

当用户显式传入 `--output-file` 时，可写出自定义文件名；但这不改变默认目录与最小字段契约。

#### 4.7.5 Failure-Side Minimal Record 契约

当前 `agent runtime result formal entry` 在 `result = failed` 时，允许写出：

- `agent runtime result formal entry failure-side minimal record`

该对象的物理落位仍为：

```text
outputs/agent_runtime_result/
```

它是既有 `agent runtime result formal entry record` 的 failure 侧最小记录，不是新的平级输出对象类型。

当前真实触发方式示例：

```bash
python engine/analyzer/run_adk_agent_runtime_result_minimal_capture.py \
  --mock-response-text unexpected-agent-runtime-result \
  --output-file outputs/agent_runtime_result/manual-agent-runtime-failure.json \
  --json-only
```

```bash
python engine/analyzer/run_adk_agent_runtime_result_minimal_capture.py \
  --omit-agent-output-key \
  --output-file outputs/agent_runtime_result/manual-agent-runtime-missing-output-key.json \
  --json-only
```

当前已在真实 failure smoke 中出现，且可视为最小正式契约的字段包括：

- `entry_id`
- `entry_type`
- `framework_id`
- `capability_surface`
- `engine_entry`
- `probe_reference`
- `result`
- `selected_runtime_path`
- `output_file`
- `agent_name`
- `agent_mode`
- `output_key`
- `error_type`
- `boundary_judgement`

当前最小契约含义如下：

1. `entry_id / entry_type` 用于标识这是既有 formal entry 写出的 failure 侧记录
2. `framework_id / capability_surface` 用于固定当前能力面与来源框架
3. `engine_entry / probe_reference / selected_runtime_path` 用于回链最小实现路径与验证基线
4. `result / error_type` 用于表达这次正式入口失败已真实发生，以及最小错误分类
5. `output_file` 用于指向已真实落盘的 failure 结果文件
6. `agent_name / agent_mode / output_key` 用于固定当前最小 agent 样板
7. `boundary_judgement` 用于约束当前 failure 记录的可宣称范围，防止被外推成完整 failure 契约体系

以下字段当前仍保留在 failure smoke / 运行证明 / 排障层，但不升级为 failure-side minimal record 的正式契约：

- `started_at`
- `completed_at`
- `duration_seconds`
- `python_version`
- `os`
- `input_text`
- `error_message`

原因如下：

1. 前 `5` 个字段主要用于证明某次运行与当时环境确实存在
2. `input_text` 当前只是最小样板输入，不宜提前升级为稳定业务契约
3. `error_message` 当前仍是自由文本，不宜升级为稳定正式字段

当前必须明确：

1. 当前 failure-side minimal record 已至少覆盖既有 formal entry 下 `2` 类已真实补证的最小失败记录：
   - “结果文本不符合预期”
   - “未观察到 output_key 状态结果”
2. 当前不应据此宣布独立 `agent runtime failure formal entry`、独立 failure probe 或完整 failure 契约体系已经成立
3. 当前 failure-side minimal record 与 success 侧正式契约共享同一 formal entry 骨架，但两者的契约字段集合不同
4. 当前 failure-side minimal record 不接入 `internal_observation`
   - 原因：其职责只限于最小失败归因、落盘证明与边界声明，不承担共享事件观测承接
5. 当前 failure-side minimal record 也不接入 `context_access`
   - 原因：其职责不包括共享上下文承接，不能把一次 formal entry 失败记录误写成共享上下文层已稳定成立
6. 当前 failure-side minimal record 也不接入 `runner_execution`
   - 原因：其职责不包括共享执行承接，不能把一次 formal entry 失败记录误写成 Runner 执行闭环已稳定成立

### 4.9 Artifact Formal Entry Record

目录落位：

```text
outputs/artifact/
```

当前生成入口：

```bash
python engine/analyzer/run_adk_artifact_minimal_access.py --json-only
```

显式指定输出文件时：

```bash
python engine/analyzer/run_adk_artifact_minimal_access.py \
  --output-file outputs/artifact/manual-artifact.json \
  --json-only
```

当前真实样本：

```text
outputs/artifact/051-formal-entry-smoke.json
```

#### 4.8.1 最小输入边界

当前 artifact formal entry 直接暴露的输入参数只有：

- `--input-text`
- `--output-file`
- `--json-only`

说明：

- 当前脚本确实支持传入 `input_text`
- 但它目前只服务于 `artifact-note.txt` 的最小 `save / load / list` 样板
- 因此，当前不应把“任意输入业务语义”写成稳定输出契约前提

#### 4.8.2 最小输出契约

当前 artifact formal entry 的成功输出格式为：

- JSON 文件

当前已在真实 smoke 文件中出现，且可视为最小正式契约的字段包括：

- `entry_id`
- `entry_type`
- `framework_id`
- `capability_surface`
- `engine_entry`
- `probe_reference`
- `result`
- `selected_runtime_path`
- `output_file`
- `artifact_name`
- `artifact_service_class`
- `artifact_version`
- `loaded_artifact_text`
- `boundary_judgement`
- `artifact_saved`
- `artifact_loaded`
- `artifact_listed`

当前最小契约含义如下：

1. `entry_id / entry_type` 用于标识这是哪一个正式入口对象
2. `framework_id / capability_surface` 用于标识当前能力面与底层来源框架
3. `engine_entry / probe_reference` 用于回链实现文件与验证基线
4. `result` 用于表达本次正式入口是否成功
5. `selected_runtime_path` 用于固定当前已被正式承认的最小执行路径
6. `output_file` 用于指向正式结果文件落点
7. `artifact_name / artifact_service_class` 用于表达当前最小 artifact 样板
8. `artifact_version / loaded_artifact_text` 用于表达当前最小 artifact 结果
9. `boundary_judgement` 用于固定当前允许宣称与禁止外推边界
10. `artifact_saved / artifact_loaded / artifact_listed` 用于表达最小正式闭环是否成立

#### 4.8.3 当前保留在 smoke、但不升级为正式契约的字段

以下字段当前已真实存在于 smoke 文件中，但不升级为最小正式输出契约：

- `started_at`
- `completed_at`
- `duration_seconds`
- `python_version`
- `os`
- `input_text`

原因如下：

1. 它们主要用于证明某次运行与当时环境确实存在
2. 它们不是后续消费 artifact 正式结果所必需依赖的稳定字段
3. `input_text` 当前只是最小样板输入，不宜提前升级为稳定业务契约

#### 4.8.4 文件命名契约

当前 artifact smoke 文件命名规则已固定为：

```text
outputs/artifact/<task-id>-formal-entry-smoke.json
```

当前真实样例：

```text
outputs/artifact/051-formal-entry-smoke.json
```

当用户显式传入 `--output-file` 时，可写出自定义文件名；但这不改变默认目录与最小字段契约。

### 4.10 Structured Output Formal Entry Record

目录落位：

```text
outputs/structured_output/
```

当前生成入口：

```bash
python engine/analyzer/run_adk_single_agent_structured_output.py --json-only
python engine/analyzer/run_adk_single_agent_structured_output_failure_recognition.py --json-only
python engine/analyzer/run_adk_single_agent_structured_output_state_protection.py --json-only
python engine/analyzer/run_adk_single_agent_structured_output_evidence_trace.py --json-only
```

显式指定输出文件时：

```bash
python engine/analyzer/run_adk_single_agent_structured_output.py \
  --output-file outputs/structured_output/manual-story.json \
  --json-only

python engine/analyzer/run_adk_single_agent_structured_output_failure_recognition.py \
  --output-file outputs/structured_output/manual-failure-recognition.json \
  --json-only

python engine/analyzer/run_adk_single_agent_structured_output_state_protection.py \
  --output-file outputs/structured_output/manual-state-protection.json \
  --json-only

python engine/analyzer/run_adk_single_agent_structured_output_evidence_trace.py \
  --matrix-cell-id M-11 \
  --output-file outputs/structured_output/manual-evidence-trace.json \
  --json-only
```

当前真实样本：

```text
outputs/structured_output/042-formal-entry-smoke.json
outputs/structured_output/044-formal-failure-recognition-smoke.json
outputs/structured_output/045-formal-state-protection-smoke.json
outputs/structured_output/046-formal-evidence-trace-smoke.json
```

#### 4.9.1 最小输入边界

当前 structured output formal entry 直接暴露的输入参数只有：

- `--input-text`
- `--output-file`
- `--json-only`
- `--matrix-cell-id`（仅 `CA-04`）

说明：

- 当前四个脚本确实支持最小命令行输入
- 但它们只服务于 `CA-01 ~ CA-04` 已成立的最小正式入口
- 因此，当前不应把“任意输入业务语义”或“任意 schema 结构”写成稳定输出契约前提

#### 4.9.2 最小输出契约

当前 structured output formal entry 的成功输出格式为：

- JSON 文件

当前 `CA-01 ~ CA-04` 四类正式入口共享的最小正式骨架字段包括：

- `entry_id`
- `entry_type`
- `framework_id`
- `capability_id`
- `matrix_cell_id`
- `engine_entry`
- `result`
- `output_file`
- `boundary_judgement`

这些字段的最小含义如下：

1. `entry_id / entry_type` 用于标识当前写出的 structured output formal entry 对象
2. `framework_id / capability_id / matrix_cell_id` 用于固定当前能力面、来源框架与矩阵落点
3. `engine_entry` 用于回链对应正式入口脚本
4. `result` 用于表达本次正式入口是否成功
5. `output_file` 用于指向正式结果文件落点
6. `boundary_judgement` 用于约束当前允许宣称与禁止外推边界

在共享骨架之外，当前按能力面稳定成立、且可进入正式契约的字段如下：

`CA-01 / M-01` 成功路径正式入口：

- `probe_reference`
- `selected_runtime_path`
- `output_key`
- `structured_output_payload`
- `final_text_result`
- `response_schema_request_count`
- `state_delta_write_observed`
- `session_state_write_observed`
- `internal_observation`
- `context_access`
- `runner_execution`

`CA-02 / M-02` 失败识别正式入口：

- `matrix_scope_ids`
- `probe_reference`
- `selected_runtime_path`
- `output_key`
- `recognized_error_type`
- `recognized_failure_kind`
- `recognized_failure_location_shape`
- `recognized_missing_field`
- `recognized_location_path`
- `recognized_matrix_cell_id`
- `response_schema_request_count`
- `entered_structured_output_constraint_semantics`
- `entered_schema_validation_failure_semantics`
- `formal_failure_recognition_established`
- `state_delta_write_observed`
- `session_state_write_observed`
- `internal_observation`
- `context_access`
- `runner_execution`

`CA-03 / M-02` 状态保护正式入口：

- `matrix_scope_ids`
- `probe_reference`
- `failure_recognition_reference`
- `selected_runtime_path`
- `output_key`
- `recognized_error_type`
- `response_schema_request_count`
- `entered_structured_output_constraint_semantics`
- `entered_schema_validation_failure_semantics`
- `formal_state_protection_established`
- `state_delta_write_observed`
- `session_state_write_observed`
- `protected_state_channels`
- `internal_observation`
- `context_access`
- `runner_execution`

`CA-04 / M-01 ~ M-12` 证据追踪正式入口：

- `matrix_scope_ids`
- `selected_matrix_cell_id`
- `matrix_trace_total_count`
- `matrix_trace_coverage_count`
- `formal_evidence_trace_established`
- `selected_trace`
- `matrix_overview`
- `related_formal_assets`
- `matrix_table_reference`
- `controlled_access_reference`
- `capability_mapping_reference`
- `formal_entry_reference`

当前最小契约必须明确两件事：

1. `structured output formal entry record` 是一个统一对象类型，但其内部按 `CA-01 ~ CA-04` 分层，而不是把四个入口硬写成同构字段集合
2. `CA-01 ~ CA-03` 共享 runtime 约束语义，`CA-04` 共享的是治理追证语义；二者都属于当前正式入口对象，但消费关注点不同
3. `internal_observation`、`context_access` 与 `runner_execution` 当前只进入 `CA-01 ~ CA-03` 三类 runtime-based host，不进入 `CA-04`

#### 4.9.3 当前保留在 smoke、但不升级为正式契约的字段

以下字段当前已真实存在于 smoke 文件中，但不升级为最小正式输出契约：

- `started_at`
- `completed_at`
- `duration_seconds`
- `python_version`
- `os`
- `input_text`
- `adk_module_path`
- `runner_app_name`
- `agent_name`
- `output_schema_name`
- `observed_node_names`
- `llm_requests`
- `event_count`
- `state_delta`
- `invalid_structured_output_payload`
- `invalid_output_json`
- `recognized_error_message`
- `normalized_validation_errors`
- `session_state`
- `selected_trace_assets_complete`

原因如下：

1. 前 `6` 个字段主要用于证明某次运行与当时环境确实存在
2. `adk_module_path / runner_app_name / agent_name / observed_node_names / event_count` 更偏向运行诊断与排障取证，不是后续消费正式结果所必需依赖的稳定字段
3. `output_schema_name` 当前只是最小样板的 schema 名称，不宜提前升级为跨版本稳定契约
4. `llm_requests / invalid_structured_output_payload / invalid_output_json / recognized_error_message / normalized_validation_errors / state_delta / session_state` 属于运行证明、排障细节或内部状态证据，不宜升级为稳定消费字段
5. `selected_trace_assets_complete` 只是 `CA-04` 的一个闭环辅助信号，当前正式契约应以 `formal_evidence_trace_established`、`selected_trace` 与 `matrix_overview` 表达

这里必须额外明确：

- `CA-01 ~ CA-03` 当前已通过 `internal_observation` 承接共享嵌入式观测子结构
- `CA-01 ~ CA-03` 当前已通过 `context_access` 承接共享嵌入式上下文子结构
- `CA-01 ~ CA-03` 当前已通过 `runner_execution` 承接共享嵌入式执行承接子结构
- 但顶层 `observed_node_names` 仍保留在 smoke / 诊断层，不应与 `internal_observation.observed_node_names` 混写
- `context_access.session_state` 是 `session.state` 的 formal entry 承接位，不等于顶层 `session_state` 证明字段
- `runner_execution` 只承接 `Runner` 与执行主协调闭环，不承接 `Runner(agent=...)`、`Runner(node=...)`、`Session / InvocationContext / Context` 或 `/run*` 入口差异

#### 4.9.4 文件命名契约

当前 structured output smoke 文件命名规则已固定为：

```text
outputs/structured_output/<task-id>-formal-entry-smoke.json
```

当前真实样例：

```text
outputs/structured_output/042-formal-entry-smoke.json
outputs/structured_output/044-formal-failure-recognition-smoke.json
outputs/structured_output/045-formal-state-protection-smoke.json
outputs/structured_output/046-formal-evidence-trace-smoke.json
```

当用户显式传入 `--output-file` 时，可写出自定义文件名；但这不改变默认目录与最小字段契约。

### 4.11 Single Agent Tool Call Formal Entry Record

目录落位：

```text
outputs/single_agent_tool_call/
```

当前生成入口：

```bash
python engine/analyzer/run_adk_single_agent_tool_call_minimal_execution.py --json-only
```

显式指定输出文件时：

```bash
python engine/analyzer/run_adk_single_agent_tool_call_minimal_execution.py \
  --output-file outputs/single_agent_tool_call/manual-tool-call.json \
  --json-only
```

当前真实样本：

```text
outputs/single_agent_tool_call/076-formal-entry-smoke.json
```

#### 4.10.1 最小输入边界

当前 single agent tool call formal entry 直接暴露的输入参数只有：

- `--input-text`
- `--output-file`
- `--json-only`

说明：

- 当前脚本确实支持传入 `input_text`
- 但它目前只服务于 `LlmAgent(mode='chat', tools=[add])` 的最小单 tool 调用样板
- 因此，当前不应把“任意输入业务语义”写成稳定输出契约前提

#### 4.10.2 最小输出契约

当前 single agent tool call formal entry 的成功输出格式为：

- JSON 文件

当前已在真实 smoke 文件中出现，且可视为最小正式契约的字段包括：

- `entry_id`
- `entry_type`
- `framework_id`
- `capability_surface`
- `engine_entry`
- `probe_reference`
- `result`
- `selected_runtime_path`
- `output_file`
- `agent_name`
- `agent_mode`
- `tool_name`
- `tool_call_args`
- `tool_response_payload`
- `tool_result_value`
- `final_text_result`
- `internal_observation`
- `context_access`
- `runner_execution`
- `boundary_judgement`
- `entered_tool_call_semantics`
- `tool_call_observed`
- `tool_response_observed`
- `formal_output_written`

当前最小契约含义如下：

1. `entry_id / entry_type` 用于标识这是哪一个正式入口对象
2. `framework_id / capability_surface` 用于标识当前能力面与底层来源框架
3. `engine_entry / probe_reference` 用于回链实现文件与验证基线
4. `result` 用于表达本次正式入口是否成功
5. `selected_runtime_path` 用于固定当前已被正式承认的最小执行路径
6. `output_file` 用于指向正式结果文件落点
7. `agent_name / agent_mode / tool_name` 用于表达当前最小 agent + tool 样板
8. `tool_call_args / tool_response_payload / tool_result_value / final_text_result` 用于表达当前最小工具调用结果
9. `internal_observation` 用于承接共享嵌入式观测子结构：
   - `observed_node_names`
   - `semantic_observation`
   - `event_records[]`
10. `context_access` 用于承接共享嵌入式上下文子结构：
   - `state_delta`
   - `session_state`
11. `runner_execution` 用于承接共享嵌入式执行承接子结构：
   - `Runner`
   - `request_acceptance`
   - `event_consumption`
   - `append_progression`
   - `response_return`
12. `boundary_judgement` 用于固定当前允许宣称与禁止外推边界
13. `entered_tool_call_semantics / tool_call_observed / tool_response_observed / formal_output_written` 用于表达最小正式闭环是否成立

#### 4.10.3 当前保留在 smoke、但不升级为正式契约的字段

以下字段当前已真实存在于 smoke 文件中，但不升级为最小正式输出契约：

- `started_at`
- `completed_at`
- `duration_seconds`
- `python_version`
- `os`
- `input_text`
- `state_delta`
- `session_state`

原因如下：

1. 它们主要用于证明某次运行与当时环境确实存在
2. 它们不是后续消费 single agent tool call 正式结果所必需依赖的稳定字段
3. `input_text` 当前只是最小样板输入，不宜提前升级为稳定业务契约
4. `context_access` 当前承接的是共享嵌入式上下文子结构；host 顶层 `state_delta / session_state` 仍只属于证明层
5. `runner_execution` 当前承接的是共享嵌入式执行承接子结构；host 顶层 `selected_runtime_path`、`agent_mode`、`tool_name` 等仍属于 host-specific 正式字段或说明层

#### 4.10.4 文件命名契约

当前 single agent tool call smoke 文件命名规则已固定为：

```text
outputs/single_agent_tool_call/<task-id>-formal-entry-smoke.json
```

当前真实样例：

```text
outputs/single_agent_tool_call/076-formal-entry-smoke.json
```

当用户显式传入 `--output-file` 时，可写出自定义文件名；但这不改变默认目录与最小字段契约。

---

## 5. 当前契约边界

### 5.1 已生成 与 已发布

当前正式边界必须写清：

- `outputs/articles/` 和 `outputs/product-briefs/` 中的文件是已生成产出
- 它们当前不等于已发布稿
- 当前仓库没有独立签发字段、发布字段或审核字段

### 5.2 单文件产出 与 双类型同时产出

当前脚本支持：

- `--type article`
- `--type product-brief`
- `--type both`

当前实现已按真实代码修正同秒双产出的 metadata 覆盖风险：

- `save_output()` 的 metadata `id` 与文件名已使用带微秒的时间戳
- 当同一次命令连续生成 `article` 和 `product-brief` 时，当前实现可以为两份输出分别写入独立 metadata

但当前仍需写清一个历史边界：

- 旧样本中曾存在秒级时间戳写法
- 因此，历史目录下仍可能出现“输出文件数多于 metadata 记录数”的遗留现象

因此，当前正式契约只能写成：

- 当前实现层面，metadata 目录已可用于稳定追踪新生成输出
- 但对历史样本是否完整一一回补，仍需单独治理，不应直接宣称历史记录已天然完整

---

## 6. 当前正式契约字段

### 6.1 当前可视为正式契约

对 `article` 与 `product-brief`，以下内容已可视为当前正式契约的一部分：

- 输入对象来源于单条 insight 与其 framework metadata
- 输出文件格式为 Markdown
- 输出目录分别是 `outputs/articles/` 与 `outputs/product-briefs/`
- 文件命名包含输出类型、`framework_id`、`insight_id` 与秒级时间戳
- metadata 记录至少包含 `id`、`type`、`title`、`insight_id`、`framework_id`、`file_path`、`generated_at`、`format`、`size_bytes`
- `ce brief` 当前只接受单个 `insight_id`
- `ce brief --json` 的成功/失败字段集合已形成当前最小正式契约

### 6.2 当前阶段拟标准化但尚未完全稳定

以下内容当前已出现或被需要，但尚不宜写成硬性稳定契约：

- 历史输出文件与 metadata 的追补策略
- article 内容结构的更细粒度段落级字段化
- product-brief 的标准模板版本号
- workflow formal entry 的失败结果字段集合
- workflow 输入文本的业务语义标准化
- 输出审核状态
- 输出发布状态

### 6.3 中后期预留方向

当前只能作为预留项记录：

- `outputs/code-samples/`
- `decision-pack` 的正式 `ce` 产品入口、稳定展示样例、metadata fixture 与公开发布面
- `code-sample` 的真实样本、metadata `type` 与脚本生成分支
- 对外发布渠道字段
- 人工审校人与签发记录
- 输出评分与回收反馈模型

---

## 7. 当前不包含的事项

以下内容当前明确不属于正式输出契约：

- 已发布 URL
- 外部浏览量、点赞量、反馈指标
- 审批链、签发链
- 平台分发状态
- 多模板版本协商机制
- workflow 分支 / 并发 / nested / resume 语义

---

## 8. 下一轮建议

在本文件基础上，下一轮更适合处理的是：

1. `validation` 状态流说明补写
2. 历史输出文件与 metadata 遗留缺口的专项回补
3. workflow formal entry 失败结果是否需要形成独立契约条目
4. `QUICKSTART.md` 中“可发布文章”等超前表述的精修

---

## 9. 一句话收口

**当前输出层已经形成 `article`、`product-brief`、`decision-pack`、`output metadata record`、`workflow formal entry record`、`agent runtime result formal entry record`、`artifact formal entry record`、`structured output formal entry record` 与 `single agent tool call formal entry record` 等真实对象；其中 `decision-pack` 当前只成立到内部生成链、metadata 追踪写入能力、Markdown fixture 与结构契约测试层，不代表正式 `ce` 产品入口、稳定展示样例或公开发布面已经成立；`code-sample` 仍处在轻量挂接实施落点阶段。整体仍处在“最小可用、边界明确、不得超前外推”的阶段。**
