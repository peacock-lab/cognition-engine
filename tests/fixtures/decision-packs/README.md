# tests/fixtures/decision-packs/README

## 1. 目录定位

`tests/fixtures/decision-packs/` 是 `decision-pack` Markdown 回归测试基线目录。

本目录不同于：

1. `outputs/decision-packs/`：运行产物目录
2. `outputs/.metadata/`：运行留痕目录
3. `examples/decision-packs/`：后续若建立，才作为稳定展示样例目录

一句话理解：

- `outputs/decision-packs/` = 运行产物
- `tests/fixtures/decision-packs/` = 回归测试基线

---

## 2. 当前首批 fixture

当前首批 Markdown fixture 包括：

1. `runner-centrality.md`

它来源于当前真实 `generate_decision_pack` 函数对以下对象的渲染结果：

1. `insight-adk-runner-centrality`
2. `adk-2.0.0a3`

---

## 3. 当前测试用途

本目录当前用于 `decision-pack` 的回归测试基线。

当前检查内容包括：

1. Markdown 必备标题结构
2. Markdown 必备正文段落
3. 一页结论质量 marker
4. 背景与证据质量 marker
5. 下一步行动数量
6. 风险与边界非空
7. JSON 结果契约字段稳定性
8. metadata 输出结构稳定性
9. fixture 与运行产物分层存在

---

## 4. 当前 JSON / metadata fixture

当前已建立：

1. `json/runner-centrality-result.json`
2. `metadata/runner-centrality-metadata.json`

这两个 fixture 使用动态字段归一化策略：

1. `generated_at = <generated_at>`
2. `metadata_id / id = <metadata_id>`
3. `metadata_file = <metadata_file>`
4. `output_file / file_path = <output_file>`

这些 fixture 只作为结构基线，不等于真实运行留痕本体。

---

## 5. 范围边界

本目录范围边界：

1. 完整黄金文本比对
2. 输出生成逻辑
3. 发布签发证明
4. 稳定展示样例本体

metadata fixture 当前只用于结构基线，不替代 `outputs/.metadata/` 运行留痕。

---

## 6. 一句话收口

**`tests/fixtures/decision-packs/` 用于把 `decision-pack` Markdown 输出提升为回归测试基线；当前检查 Markdown 结构、JSON 结果契约与 metadata 输出结构，不引入稳定展示样例或正式发布语义。**
