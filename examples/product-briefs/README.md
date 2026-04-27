# examples/product-briefs/README

## 1. 目录定位

`examples/product-briefs/` 是 `ce brief` 第一正式产品闭环的稳定产品简报样例目录。

本文档用于说明：

1. 本目录为什么存在
2. 当前样例如何选择
3. 样例与运行产物的区别
4. 样例与 metadata 的关系
5. 样例当前不代表什么

---

## 2. 与 outputs/product-briefs 的区别

`outputs/product-briefs/` 是运行产物目录。

它保存 `ce brief` 或历史输出脚本生成的 Markdown 文件，文件名通常带有运行时间戳。

`examples/product-briefs/` 是稳定展示样例目录。

它只保存经过人工确认、可被 README / QUICKSTART / Release / 公仓展示引用的样例文件。

一句话理解：

```text
outputs/product-briefs/  = 运行产物
examples/product-briefs/ = 稳定展示样例
```

---

## 3. 当前首批样例

当前首批稳定样例包括：

```text
runner-centrality.md
event-system.md
```

样例来源分别是：

```text
outputs/product-briefs/product-briefs-adk-2.0.0a3-insight-adk-runner-centrality-20260424-124103-525412.md
outputs/product-briefs/product-briefs-adk-2.0.0a3-insight-adk-event-system-20260424-124110-709876.md
```

这两个样例被选入本目录，是因为它们更接近当前 `ce brief` 正式产品简报结构。

---

## 4. 样例选择标准

进入本目录的样例至少应满足：

1. 来自当前 `ce brief` 正式结构
2. 不是旧模板历史产物
3. 正文结构完整
4. 无明显过度承诺
5. 不包含 `MVP`、收入影响、NPS、市场规模等旧模板口径
6. 文件名稳定，不带运行时间戳
7. 只作为展示样例，不混同测试基线

当前推荐的正文结构包括：

1. 一页结论
2. 适用场景
3. 目标使用者
4. 用户问题
5. 产品主张
6. 上线边界
7. 证据与可信度
8. 相关洞察
9. 下一步行动

---

## 5. metadata 边界

本目录初期不配套 metadata。

原因是：

1. 样例首先服务阅读和展示
2. metadata 当前语义是运行留痕
3. 若给 examples 直接配 metadata，容易混淆展示样例与运行记录
4. 后续如果需要可复现测试基线，应单独设计 fixtures 或 baseline 策略

如需查看原始运行留痕，可回到：

```text
outputs/.metadata/
```

---

## 6. ADK 版本口径说明

当前样例来源于历史 ADK 2.0.0a3 洞察数据，因此样例正文中可能出现：

```text
Google Agent Development Kit 2.0.0a3
```

这表示样例来源数据的历史事实。

当前项目依赖已经在 `pyproject.toml` 中声明为：

```text
google-adk>=2.0.0b1,<2.1
```

因此，本目录样例用于展示 `ce brief` 输出结构，不代表当前项目依赖版本锁死为 `2.0.0a3`。

---

## 7. 当前不代表事项

本目录当前不代表：

1. 已建立完整样例资产体系
2. 已建立回归测试基线
3. 已建立外部签发流程
4. 已建立 metadata 配套样例体系
5. 已新增 CLI 能力
6. 已清理全部历史运行产物

---

## 8. 后续增强方向

后续可考虑：

1. 在 README / QUICKSTART 中引用本目录
2. 为样例建立更清晰的说明页
3. 判断是否需要英文样例
4. 判断是否需要 tests/fixtures 基线
5. 判断是否需要更新公仓发布清单
6. 根据产品体验继续优化 `ce brief` 输出质量

---

## 9. 一句话收口

**`examples/product-briefs/` 用于保存经过人工确认的稳定产品简报展示样例；它不同于运行产物目录，也不同于测试基线目录，初期不配套 metadata，不新增 CLI 能力。**
