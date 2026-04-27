# Decision Packs

## 1. 目录定位

`outputs/decision-packs/` 是 `decision-pack` 在输出层中的同层目录落位。

当前目录只承接两类内容：

1. `decision-pack` 的目录级说明
2. 后续若进入真实样本生成时的 Markdown 文件落位

当前必须明确：

1. 本目录虽已建立，但当前不等于真实稳定输出类型已经成立
2. 当前不代表仓内已经存在真实 `decision-pack` Markdown 样本
3. 当前不代表仓内已经存在 `decision-pack` metadata `type`
4. 当前也不代表 `generate_outputs.py` 已支持 `--type decision-pack`

---

## 2. 当前实施背景

`decision-pack` 当前是沿输出层既有双样板体系完成的轻量挂接实施落点。

其最近邻样板对象是：

- `product-brief`

当前这样落位的原因如下：

1. `decision-pack` 与 `product-brief` 同属输出层文件型 Markdown 对象
2. 二者同属“单条 insight + 对应 framework metadata 派生 Markdown 输出稿”的外层骨架
3. `decision-pack` 当前表达目标更接近业务压缩表达继续上收为决策取舍材料，而不是技术阐释展开

---

## 3. 当前可继承边界

`decision-pack` 当前可直接继承以下边界：

1. 同属输出层文件型对象
2. 同属已生成稿，不等于已发布稿
3. 不替代 `insight` 主对象
4. 不替代 `framework metadata` 主对象
5. 不吞并 `outputs/.metadata/` 追踪职责
6. 不把目录壳、README、消费层入口反写成对象本体

当前若后续进入真实样本生成，仍应优先沿用同层命名骨架：

```text
decision-packs-{framework_id}-{insight_id}-{YYYYMMDD-HHMMSS-ffffff}.md
```

---

## 4. 当前必须补齐的对象差异

`decision-pack` 当前必须补齐的差异，不在分层规则，而在对象内部表达目标：

1. 用途定位
   - 当前偏决策取舍承接
   - 不是 `product-brief` 的改名版
2. 正文结构
   - 当前最小期望结构应显式体现待决问题、候选方案、取舍理由、建议结论、待确认项
3. 输入面
   - 当前需要明确哪些上游事实足以支撑“决策取舍”，而不只是“业务概述”
4. 对象名一致性
   - 标题模式、目录名、README 与后续 metadata `type` 都需与 `decision-pack` 对象名一致

---

## 5. 当前继续排除的内容

`decision-pack` 当前继续排除以下内容，不写成已成立事实：

1. 正式签发状态
2. 外部分发状态
3. 审核链、签发链与发布 URL
4. `connection` 快照本体与关系类型闭集枚举
5. `trace_id`
6. 技术细节、概念性代码示例与证据长展开
7. 尚未建立的评分、反馈与回收模型

---

## 6. 当前实施边界

本轮轻量挂接实施只固化以下事实：

1. `decision-pack` 已完成同层目录落位
2. `decision-pack` 已完成目录级说明落点
3. `decision-pack` 已完成对象级契约落点

本轮没有固化以下事实：

1. 真实 Markdown 样本已生成
2. metadata `type = decision-packs` 已进入真实追踪链
3. `generate_outputs.py` 已支持 `--type decision-pack`
4. `decision-pack` 已形成真实稳定输出体系

---

## 7. 后续接续建议

若后续继续推进，优先顺序应为：

1. 在实施任务中补齐总入口、对象契约与目录说明之间的一致性
2. 再判断是否需要新增真实目录样本、metadata `type` 与脚本生成分支
3. 始终避免把轻量挂接落点提前写成稳定输出体系
