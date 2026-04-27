# outputs/product-briefs/README

## 1. 目录定位

`outputs/product-briefs/` 是 `cognition-engine` 的产品简报输出目录。

当前最重要的正式入口是：

```bash
ce brief --insight <insight_id>
```

该命令会读取一条结构化洞察，并生成一份 Markdown 格式的产品简报。

本目录用于保存这些产品简报运行产物。

---

## 2. 当前正式产品闭环

当前已成立的第一条正式产品化闭环是：

```text
formal CLI entry
→ ce brief
→ product brief output
→ metadata trace
```

对应关系如下：

1. `ce brief` 负责触发产品简报生成。
2. `outputs/product-briefs/` 保存 Markdown 简报产物。
3. `outputs/.metadata/` 保存对应 metadata 留痕。
4. `ce brief --json` 返回结构化执行结果与文件路径。

---

## 3. 运行产物边界

本目录中的 Markdown 文件首先应理解为：

**运行产物。**

它们证明产品简报生成链路曾经运行成功，但不自动等于：

1. 正式发布稿
2. 对外签发稿
3. 回归测试基线
4. 稳定示例样例
5. 公仓发布资产

换句话说：

**运行产物不自动等于可发布样例。**

---

## 4. 当前文件命名

当前产品简报文件通常采用如下命名形态：

```text
product-briefs-{framework_id}-{insight_id}-{YYYYMMDD-HHMMSS-ffffff}.md
```

示例：

```text
product-briefs-adk-2.0.0a3-insight-adk-runner-centrality-20260424-123953-725719.md
```

命名中包含：

1. 输出类型
2. framework_id
3. insight_id
4. 生成时间戳

时间戳用于避免覆盖历史运行产物。

---

## 5. 与 metadata 的关系

每次成功生成产品简报时，通常会产生一条对应 metadata 记录。

metadata 文件保存在：

```text
outputs/.metadata/
```

metadata 负责记录：

1. metadata_id
2. output_type
3. insight_id
4. output_file
5. framework_id
6. generated_at
7. validation 结果

因此，本目录只保存简报正文；追踪信息由 `outputs/.metadata/` 承接。

---

## 6. 取证产物与可发布样例

后续应区分以下几类对象：

### 6.1 临时取证运行产物

用于证明命令可运行。

特征：

1. 由临时命令运行生成
2. 带有当前时间戳
3. 不一定需要入库
4. 不应默认进入公仓或发布清单

### 6.2 可发布示例样例

用于对外展示或说明功能。

特征：

1. 经过人工确认
2. 具备说明价值
3. 文件名和内容稳定
4. 可在 README / QUICKSTART / Release 中引用

### 6.3 回归测试基线

用于测试或质量回归。

特征：

1. 有明确测试目的
2. 内容稳定
3. 可重复比较
4. 不与普通运行产物混同

当前本目录已经存在历史运行产物，但尚未正式建立独立的稳定示例样例目录或回归基线目录。

---

## 7. 历史样本质量分层

本目录中存在不同阶段生成的历史 product brief 文件。

这些文件不应被统一理解为当前 `ce brief` 正式闭环的质量基线。

当前建议这样区分：

### 7.1 当前推荐参考样本

较新的 `runner-centrality` 与 `event-system` 样本更接近当前正式产品简报结构。

它们通常包含：

1. 一页结论
2. 适用场景
3. 目标使用者
4. 用户问题
5. 产品主张
6. 上线边界
7. 证据与可信度
8. 相关洞察
9. 下一步行动

这类样本可作为当前 `ce brief` 正文质量的优先参考。

### 7.2 旧模板历史样本

较早生成的部分样本可能仍保留旧式通用商业计划模板。

这类样本可能包含：

1. 市场规模
2. MVP 开发
3. 收入影响
4. NPS 指标
5. 资源需求
6. 立即行动

这类表达不代表当前 `v0.1.0 / v0.1.1` 后的正式产品简报质量基线。

### 7.3 当前治理结论

在正式建立稳定示例样例目录或回归基线目录前：

1. 不应把本目录下所有历史 Markdown 都视为当前推荐样例。
2. 不应把旧模板样本作为当前质量判断依据。
3. 若需要引用样例，应优先选择较新的 `runner-centrality` 与 `event-system` 样本。
4. 若需要对外展示，应先进行人工确认。
5. 若需要测试基线，应单独建立基线规则。

---

## 8. 当前可用示例命令

生成 Markdown 产品简报：

```bash
ce brief --insight insight-adk-runner-centrality
```

生成 JSON 执行结果：

```bash
ce brief --insight insight-adk-runner-centrality --json
```

另一个当前可用样例：

```bash
ce brief --insight insight-adk-event-system
```

---

## 9. 当前不承诺事项

本目录当前不承诺：

1. 所有 Markdown 文件都已人工审核
2. 所有 Markdown 文件都可对外发布
3. 已形成稳定样例资产体系
4. 已形成回归测试基线体系
5. 已形成签发、审核或投放链路
6. 已支持受众分层产品简报稳定生成

---

## 10. 后续增强方向

后续可考虑：

1. 新增稳定示例目录，例如 `examples/` 或 `outputs/examples/`
2. 明确哪些 product brief 可作为公开样例
3. 为 `ce brief` 增加更清晰的示例输出说明
4. 为 metadata 留痕建立 README
5. 区分运行产物、样例资产、测试基线和公仓展示资产
6. 必要时设计 `--output-dir`、`--dry-run` 或 `--sample` 等能力

这些方向需要单独判断，不应未经设计直接加入 CLI 承诺。

---

## 11. 一句话收口

**`outputs/product-briefs/` 是 `ce brief` 第一正式产品闭环的 Markdown 运行产物目录；其中的运行产物证明链路可用，但不自动等于可发布样例、测试基线或正式签发稿。**
