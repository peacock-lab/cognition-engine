# engine/transformer/README

## 1. 目录定位

`engine/transformer/` 是当前项目的转化层目录。

它当前负责把已经存在的结构化洞察转成可阅读的 Markdown 产出，并将结果落到 `outputs/`。

它当前不是：

- 通用内容编排平台
- 多阶段发布流水线
- 已经覆盖多种输出类型的成熟转化系统

---

## 2. 当前已实现事实

当前目录下真实存在的脚本只有：

- `generate_outputs.py`

这意味着 `transformer/` 当前已经落地的职责很明确，也比较收敛：

1. 读取 `data/insights/` 中的指定洞察
2. 读取 `data/frameworks/` 中对应框架元数据
3. 生成文章或产品简报
4. 将文件保存到 `outputs/articles/` 或 `outputs/product-briefs/`
5. 将产出元数据记录到 `outputs/.metadata/`

当前还没有看到：

- 独立模板管理目录
- 多输出类型插件系统
- 审稿、发布、回滚等正式发布链

因此，`transformer/` 当前是：

**最小可用的洞察转产出脚本入口**

当前补充事实：

- `generate_outputs.py` 读取 insight 时，已经统一走 `insight formal entry` 的根层直承接结构
- 因此输出层消费的不是“任意松散 insight JSON”，而是 formal-entry-normalized 的 insight 主对象

---

## 3. 当前脚本职责

### 3.1 `generate_outputs.py`

当前支持：

- `--type article`
- `--type product-brief`
- `--type both`

当前行为：

1. 通过 `--insight <insight_id>` 定位目标洞察
2. 根据洞察内容和框架元数据生成 Markdown 文本
3. 以时间戳文件名写入对应输出目录
4. 写入一份输出元数据到 `outputs/.metadata/`

当前真实输出位与脚本行为保持一致：

- 文章输出写入 `outputs/articles/`
- 产品简报输出写入 `outputs/product-briefs/`

当前关于 `insight formal entry` 的消费边界补充如下：

1. 主字段面继续由 insight 根层提供
2. `evidence[]` 与 `connections[]` 以“最小正式子面 + 细节层并存”的方式被消费
3. 输出层不会把 `quote / source_path / file / chain / entry_point` 反向提升为 insight 正式字段
4. `trace_id` 当前也不属于 transformer 层的正式输入契约

---

## 4. 与 `outputs/` 的关系

`transformer/` 与 `outputs/` 的承接关系是当前仓库中最清晰的一条链路之一：

1. 输入来自 `data/insights/` 与 `data/frameworks/`
2. 转化逻辑位于 `engine/transformer/generate_outputs.py`
3. 正式文件输出到 `outputs/articles/` 与 `outputs/product-briefs/`
4. 追踪信息写到 `outputs/.metadata/`

这说明 `outputs/` 当前不是纯占位目录，而是已经被真实脚本消费的产出层。

当前进一步收口如下：

1. article 与 product brief 都建立在 formal-entry-normalized insight 读取链上
2. 输出层只消费 `insight` 与 `framework metadata`
3. 输出层不承接 `connection` 快照本体，也不承接 `trace_id` 作为正式关联元字段

---

## 5. 当前可执行入口

```bash
# 生成文章
python engine/transformer/generate_outputs.py --insight <insight_id> --type article

# 生成产品简报
python engine/transformer/generate_outputs.py --insight <insight_id> --type product-brief

# 同时生成两类产出
python engine/transformer/generate_outputs.py --insight <insight_id> --type both
```

根级联动入口：

```bash
python start.py --generate
python daily_workflow.py
```

---

## 6. 当前边界

当前已经明确做到：

- 从单个 insight 派生两类 Markdown 产出
- 自动记录输出元数据
- 被根级工作流复用

当前还没有明确做到：

- 输出模板版本管理
- 多轮编辑与人工审稿闭环
- 对外发布机制
- 新输出类型的标准扩展接口

因此，后续若讨论“发布链”“内容工厂”“多模板编排”，都应被视为扩展方向，而不是现状。

---

## 7. 第一阶段拟补齐事项

当前阶段可继续补齐的内容包括：

1. 输出文件命名与元数据字段说明
2. `article` 与 `product-brief` 的最小内容契约
3. 产出质量人工复核规则
4. `--output-dir` 参数的实际边界与是否保留

---

## 8. 中后期预留方向

以下方向当前尚未建立：

- 更多输出类型，例如代码样例包、决策包
- 更明确的模板层与渲染层分离
- 产出评分、排序与批量编排
- 对外发布或同步机制

这些方向当前都只能作为预留项记录。

---

## 9. 治理说明

- 本目录说明只以现有脚本和现有输出目录为依据
- 若新增正式输出类型，应同步说明其目标目录、元数据记录方式和人工复核要求
- 若改变 `transformer/` 与 `outputs/` 的边界，应留下清晰的变更记录与阶段记录
- 未经用户确认，当前生成内容不应被表述为已进入正式发布态

---

## 10. 一句话收口

**`engine/transformer/` 当前已经承担洞察到 Markdown 产出的最小转化职责，但还没有扩展成完整发布流水线。**
