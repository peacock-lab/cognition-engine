# tests/fixtures/product-briefs/README

## 1. 目录定位

`tests/fixtures/product-briefs/` 是 `ce brief` 第一正式产品闭环的 Markdown 回归测试基线目录。

本目录不同于：

1. `outputs/product-briefs/`：运行产物目录
2. `outputs/.metadata/`：运行留痕目录
3. `examples/product-briefs/`：稳定展示样例目录

一句话理解：

- `examples/product-briefs/` = 稳定展示样例
- `tests/fixtures/product-briefs/` = 回归测试基线

---

## 2. 当前首批 fixture

当前首批 Markdown fixture 包括：

1. `runner-centrality.md`
2. `event-system.md`

它们来源于已经人工确认的稳定展示样例：

1. `examples/product-briefs/runner-centrality.md`
2. `examples/product-briefs/event-system.md`

---

## 3. 当前测试用途

本目录当前只用于 Markdown 正文结构契约测试。

当前检查内容包括：

1. 必备标题结构
2. 必备正文段落
3. 禁止旧模板口径
4. 稳定样例文件可读取
5. fixture 与展示样例分层存在

---

## 4. 范围边界

本目录范围边界：

1. metadata fixture
2. JSON 结果 fixture
3. 完整黄金文本比对
4. 输出生成逻辑
5. 发布签发证明

metadata 是否进入 fixture，需要后续单独判断。

---

## 5. 一句话收口

**`tests/fixtures/product-briefs/` 用于把 `ce brief` 稳定 Markdown 样例提升为回归测试基线；当前只检查结构契约，不引入 metadata fixture。**
