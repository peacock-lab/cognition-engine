# outputs/README

## 1. 目录定位

`outputs/` 是当前项目的输出层入口目录。

它当前用于承接：

- 由 `engine/transformer/` 生成的正式文件型产出
- 对应产出的元数据记录

它当前不是：

- 全量内容发布中心
- 已经形成多渠道分发机制的成品层
- 包含所有规划输出类型的完整输出系统

---

## 2. 当前已实现事实

基于当前仓库真实结构，`outputs/` 下目前存在：

- `articles/`
- `product-briefs/`
- `decision-packs/`
- `code-samples/`
- `.metadata/`

其中：

1. `articles/` 已有真实 Markdown 产出文件
2. `product-briefs/` 已有真实 Markdown 产出文件
3. `decision-packs/` 已完成同层目录落位与目录级 README 落盘
4. `code-samples/` 已完成同层目录落位与目录级 README 落盘
5. `.metadata/` 已有对应输出记录，用于追踪产出类型、来源 insight、文件路径、生成时间与大小

当前必须明确：

1. `decision-packs/` 的存在，当前只代表轻量挂接实施已完成最小目录落位
2. 它当前不等于已存在真实 Markdown 样本
3. 它当前也不等于已存在稳定 metadata 类型或生成脚本分支
4. `code-samples/` 的存在，当前也只代表轻量挂接实施已完成最小目录落位
5. 它当前不等于已存在真实 Markdown 样本
6. 它当前也不等于已存在稳定 metadata 类型或生成脚本分支

这说明 `outputs/` 当前已经是：

**被真实脚本写入的正式输出位**

而不是纯占位目录。

---

## 3. 当前承接关系

当前输出链路基于真实脚本可以明确写成：

1. `data/insights/` 提供洞察输入
2. `engine/transformer/generate_outputs.py` 负责转化
3. 产出写入 `outputs/articles/` 或 `outputs/product-briefs/`
4. 元数据写入 `outputs/.metadata/`

根级脚本中的关系同样成立：

- `start.py --generate` 会调用转化脚本生成初始产出
- `daily_workflow.py` 会在每日流程中调用转化脚本生成当日产出

---

## 4. 当前子目录说明

### 4.1 `articles/`

当前定位：

- 承接文章类 Markdown 输出
- 适合面向技术阐释、洞察展开与产品化建议整理

详见 `outputs/articles/README.md`。

### 4.2 `product-briefs/`

当前定位：

- 承接产品简报类 Markdown 输出
- 适合把洞察压缩为机会概述、价值说明、路线图与风险摘要
- 当前也承接“面向不同受众的简报版本分层”的同骨架挂接说明，但该方向仍留在 `product-briefs` 内部，不单列为新目录类型

详见 `outputs/product-briefs/README.md`。

### 4.3 `decision-packs/`

当前定位：

- 承接 `decision-pack` 的同层目录落位与目录级挂接说明
- 作为后续若进入真实输出样本前的最小对象认知落点

当前必须明确：

1. 本目录当前已建立，但仍不等于真实稳定输出位
2. 当前不应写成已有真实 Markdown 样本
3. 当前不应写成已有 metadata 追踪类型或脚本生成入口

详见 `outputs/decision-packs/README.md`。

### 4.4 `code-samples/`

当前定位：

- 承接 `code-sample` 的同层目录落位与目录级挂接说明
- 作为后续若进入真实输出样本前的最小对象认知落点

当前必须明确：

1. 本目录当前已建立，但仍不等于真实稳定输出位
2. 当前不应写成已有真实 Markdown 样本
3. 当前不应写成已有 metadata 追踪类型或脚本生成入口

详见 `outputs/code-samples/README.md`。

### 4.5 `business-reports/`

当前定位：

- 承接 `business-report` 的同层目录落位与目录级挂接说明
- 作为后续若进入真实输出样本前的最小对象认知落点

当前必须明确：

1. 本目录当前若建立，只代表轻量挂接实施落位已完成
2. 当前不应写成已有真实 Markdown 样本
3. 当前不应写成已有 metadata 追踪类型或脚本生成入口

详见 `outputs/business-reports/README.md`。

### 4.6 `.metadata/`

当前定位：

- 记录每次产出的追踪信息
- 作为输出文件与洞察来源之间的最小追溯层

注意：

- `.metadata/` 当前虽为真实工作目录，但本轮不将其扩写成独立模块 README
- 历史秒级批次若出现同批次 `article` 记录被兄弟输出覆盖，可通过 `-article-backfill` 形式补录缺失 metadata
- 这类 backfill 记录只用于修复历史追踪缺口，不代表当前运行时 metadata 命名策略已回退

---

## 5. 输出层阶段总表

### 5.1 当前阶段定位

`outputs/README.md` 当前同时承担：

1. 输出层入口说明
2. 输出层阶段总表入口

本节用于把当前已经稳定成立、但此前分散在 `OUTPUT_CONTRACTS.md`、目录 README 与多份阶段记录中的阶段结论收回到一个更集中、更可检索的长期资产入口。

### 5.2 当前稳定双样板

当前输出层已形成稳定双样板结构：

1. `article`
   - 技术阐释型 Markdown 输出稿
   - 主样板对象
   - 详见 `outputs/articles/README.md` 与 `outputs/OUTPUT_CONTRACTS.md`
2. `product-brief`
   - 业务压缩表达型 Markdown 输出稿
   - 兄弟样板对象
   - 详见 `outputs/product-briefs/README.md` 与 `outputs/OUTPUT_CONTRACTS.md`

当前阶段结论：

- 双样板已足以支撑输出层阶段性收口判断
- 当前不再默认继续扩第三个输出对象
- “面向不同受众的简报版本分层”当前已完成在 `product-briefs` 内部的轻量挂接实施落点，但仍不计入新的稳定样板对象
- `decision-pack` 当前虽已完成同层目录落位，但仍只处于轻量挂接实施位，不计入稳定样板数
- `code-sample` 当前虽已完成同层目录落位，但仍只处于轻量挂接实施位，不计入稳定样板数
- `business-report` 当前已完成同层目录落位与对象级挂接落点，但仍只处于轻量挂接实施位，不计入稳定样板数

### 5.3 当前样板差异总表

当前两类输出对象的最小差异如下：

1. 输入字段厚度
   - `article` 更厚
   - `product-brief` 更薄
2. 正文结构
   - `article` 偏技术背景、洞察展开、架构影响、证据与技术细节
   - `product-brief` 偏机会、用户、价值、路线图、风险、资源与指标
3. 用途定位
   - `article` 面向技术阐释与人工复核
   - `product-brief` 面向业务压缩表达
4. 当前状态
   - 二者都属于“已生成稿”
   - 二者都不等于“已发布稿”

### 5.4 当前统一排除项

当前输出层仍统一排除以下能力或语义，不写成已成立事实：

1. 正式签发状态
2. 对外发布状态
3. 审核链、签发链与发布 URL
4. 多渠道分发机制
5. 投放链路与外部分发语义
6. 尚未建立的更多输出子类型

对象级补充排除仍以 `outputs/OUTPUT_CONTRACTS.md` 为准。

### 5.5 当前分层关系

当前输出层分层关系应统一理解为：

1. 上游来源层
   - `insight`
   - `framework metadata`
2. 输出对象层
   - `article`
   - `product-brief`
3. 追踪层
   - `outputs/.metadata/`
4. 消费层
   - `dashboard/metrics/show_metrics.py`
   - 根级命令入口与 README 示例

当前不得把目录壳、metadata 或消费层反向写成输出对象本体。

### 5.6 当前扩面控制原则

当前输出层的扩面控制原则如下：

1. 双样板既已成立，不再默认继续扩对象
2. 若后续对象不会改变输出层分层规则、承接载体规则或命名规则，应优先判断是否可轻量挂接
3. 若稳定结论已经形成但分散，应优先更新长期资产 / 总表，而不是继续开号扩对象
4. 若出现系统性污染、显著边界漂移或发布前回归压力，再优先插入阶段审计或盘点

### 5.7 当前长期资产入口分工

当前输出层长期资产建议按以下入口理解：

1. `outputs/README.md`
   - 输出层总入口
   - 当前阶段总表入口
2. `outputs/OUTPUT_CONTRACTS.md`
   - 对象级契约入口
3. `outputs/articles/README.md`
   - `article` 目录级说明入口
4. `outputs/product-briefs/README.md`
   - `product-brief` 目录级说明入口
5. `outputs/decision-packs/README.md`
   - `decision-pack` 目录级挂接说明入口
6. `outputs/code-samples/README.md`
   - `code-sample` 目录级挂接说明入口
7. `outputs/business-reports/README.md`
   - `business-report` 目录级挂接说明入口

这意味着当前不需要新增新的输出层长期资产主载体。

---

## 6. 第一阶段拟补齐事项

当前阶段可继续补齐的是：

1. 输出目录级 README
2. 文章与产品简报的最小内容契约
3. 输出元数据字段说明
4. 人工审阅与放行规则

---

## 7. 中后期预留方向

与上游蓝图保持一致，以下输出类型当前尚未建立：

- 其他更细粒度专题输出位

其中必须额外明确：

1. `outputs/decision-packs/` 当前已完成目录级挂接落位
2. `outputs/code-samples/` 当前已完成目录级挂接落位
3. 但二者当前仍不应写成已建立真实输出样本、metadata 类型或生成分支的正式输出位

这些目录当前都不应写成已存在正式输出位。

---

## 8. 当前可执行入口

```bash
# 生成文章
python engine/transformer/generate_outputs.py --insight <insight_id> --type article

# 生成产品简报
python engine/transformer/generate_outputs.py --insight <insight_id> --type product-brief

# 同时生成两类输出
python engine/transformer/generate_outputs.py --insight <insight_id> --type both
```

---

## 9. 治理说明

- `outputs/` 中的文件当前属于生成产物，不等于已经对外发布
- 任何新增输出类型、目录边界调整或元数据结构调整，都应通过 `tasks/` 留痕
- 未经用户确认，当前文章或产品简报不应被标记为正式发布稿
- 若只是补充目录说明或样例说明，可在边界清晰时直接修订 README

---

## 10. 一句话收口

**`outputs/` 当前不仅是被真实脚本写入的输出层，也已经成为承接 `article + product-brief` 双样板阶段结论的总入口，但整体仍处于“已生成、未发布”的最小可用阶段。**
