# examples/decision-packs/README

## 1. 目录定位

`examples/decision-packs/` 是 `ce decision-pack` 正式产品入口的稳定决策包展示样例目录。

本文档用于说明：

1. 本目录为什么存在
2. 当前样例如何选择
3. 样例与运行产物的区别
4. 样例与 fixture 的区别
5. 样例当前不代表什么

---

## 2. 与 outputs/decision-packs 的区别

`outputs/decision-packs/` 是运行产物目录。

它保存 `ce decision-pack` 或底层生成器生成的 Markdown 文件，文件名通常带有运行时间戳。

`examples/decision-packs/` 是稳定展示样例目录。

它只保存经过人工确认、可被后续 README / QUICKSTART / Release / 公仓展示引用的样例文件。

一句话理解：

- `outputs/decision-packs/` = 运行产物
- `examples/decision-packs/` = 稳定展示样例

---

## 3. 与 tests/fixtures/decision-packs 的区别

`tests/fixtures/decision-packs/` 是 Markdown 回归测试基线目录。

它用于测试结构契约和轻量质量规则。

`examples/decision-packs/` 是阅读和展示目录。

它用于保存稳定、可读、可被产品说明引用的展示样例。

一句话理解：

- `tests/fixtures/decision-packs/` = 回归测试基线
- `examples/decision-packs/` = 稳定展示样例

---

## 4. 当前首批样例

当前首批稳定样例包括：

- `runner-centrality.md`

样例来源是正式 `ce decision-pack` 入口对以下对象的生成结果：

`ce decision-pack --insight insight-adk-runner-centrality`

该样例被选入本目录，是因为它已覆盖当前 `decision-pack` 的核心结构：

1. 一页结论
2. 决策问题
3. 背景与证据
4. 可选方案
5. 推荐方案
6. 取舍理由
7. 风险与边界
8. 下一步行动

---

## 5. 样例选择标准

进入本目录的样例至少应满足：

1. 来自当前正式 `ce decision-pack` 入口
2. 不是手写样例
3. 正文结构完整
4. 无明显过度承诺
5. 文件名稳定，不带运行时间戳
6. 只作为展示样例，不混同测试基线
7. 不包含发布签发证明

---

## 6. metadata 边界

本目录初期不配套 metadata。

原因是：

1. 样例首先服务阅读和展示
2. metadata 当前语义是运行留痕
3. 若给 examples 直接配 metadata，容易混淆展示样例与运行记录
4. 后续如果需要可复现测试基线，应单独设计 fixtures 或 baseline 策略

如需查看原始运行留痕，可回到：

`outputs/.metadata/`

---

## 7. ADK 版本口径说明

当前样例来源于历史 ADK 2.0.0a3 洞察数据，因此样例正文中可能出现：

`Google Agent Development Kit 2.0.0a3`

这表示样例来源数据的历史事实，不代表当前项目依赖版本锁死为 `2.0.0a3`。

---

## 8. 当前不代表事项

本目录当前不代表：

1. 已建立完整样例资产体系
2. 已建立 metadata fixture
3. 已建立 JSON 结果 fixture
4. 已建立外部签发流程
5. 已更新 README / QUICKSTART
6. 已启动公仓发布
7. 已宣布第二正式产品闭环完成

---

## 9. 后续增强方向

后续可考虑：

1. 在 README / QUICKSTART 中引用本目录
2. 判断是否需要 metadata fixture
3. 判断是否需要 JSON 结果 fixture
4. 判断是否需要英文样例
5. 判断是否需要更新公仓发布清单
6. 根据产品体验继续优化 `ce decision-pack` 输出质量

---

## 10. 一句话收口

**`examples/decision-packs/` 用于保存经过人工确认的稳定决策包展示样例；它不同于运行产物目录，也不同于测试基线目录，初期不配套 metadata，不触发发布动作。**
