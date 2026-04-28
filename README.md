# Cognition Engine｜认知引擎


## v0.3.0 阶段边界

`v0.3.0` 定位为认知引擎 ADK 底座承接与本地真实模型链路稳定版。

本阶段已经压实：ADK-backed workflow、纯安装态 `CE_DATA_DIR` 运行入口、`CE_INSIGHTS_DIR` 细粒度覆盖入口、真实 provider 通过环境变量进入 workflow 主链，以及 ADK b1 framework metadata 最低入口。

当前默认 provider 仍为 `mock`。真实 provider 可通过 `CE_MODEL_PROVIDER=adk_litellm_ollama` 显式启用，当前不公开 `--model-provider` CLI 参数，也不将真实 provider 设为默认。

`adk-2.0.0a3` 仍作为历史 smoke / fixtures / 回归数据资产保留；当前正式依赖主路为 `google-adk>=2.0.0b1,<2.1`，并已建立 `adk-2.0.0b1` framework metadata 最低入口。

Runner / 观测 / 上下文三条主线统一移交 `v0.4.0` 系统梳理。`v0.3.0` 不宣称 provider 公开、Eval 完成、完整 Observability 完成或配置中心已建立。

`cognition-engine` 是一个基于 Google ADK 的轻量级认知产品闭环项目。

当前公开面优先展示已经压实的正式 CLI 产品能力：

```text
正式 CLI 入口
→ ce brief
→ 产品简报输出
→ metadata 留痕

正式 CLI 入口
→ ce decision-pack
→ 决策包输出
→ metadata 留痕

正式 CLI 入口
→ ce workflow
→ product brief + decision pack + model enhancement 组合结果
→ 子产物 metadata 留痕
```

换句话说，当前最重要的使用方式是：

```bash
ce brief --insight <insight_id>
ce decision-pack --insight <insight_id>
ce workflow --insight <insight_id>
```

其中：

1. `ce brief` 会把一条结构化洞察转换为一份可阅读、可追踪的产品简报。
2. `ce decision-pack` 会把一条结构化洞察转换为一份可阅读、可追踪的决策包。
3. `ce workflow` 会执行第一条 `insight-to-decision workflow`，顺序组合产品简报、决策包和模型增强产物，并返回组合结果。

英文摘要入口：

```text
README.en.md
```

---

## 当前版本

当前版本：

```text
v0.1.1
```

`v0.1.1` 是 `v0.1.0` 之后的一次公开说明面小修补版本。

它主要澄清：

1. Google ADK 依赖关系
2. 安装路径
3. 正式 CLI 入口
4. 第一条产品闭环边界

当前版本已补充 `ce decision-pack` 说明面能力，但这不等于已经触发公仓发布、版本号推进或第二正式产品闭环公开宣布。

---

## Google ADK 依赖说明

`cognition-engine` 当前以 Google ADK 2.0.0b1+ 作为受控智能体框架依赖。

依赖已经在 `pyproject.toml` 中声明：

```toml
google-adk>=2.0.0b1,<2.1
```

通常不需要单独手动安装 Google ADK。

执行：

```bash
python -m pip install -e .
```

时，Python 包安装流程会读取 `pyproject.toml`，并自动安装包括 `google-adk` 在内的声明依赖。

本项目不是复制 Google ADK 源码，而是在 Google ADK 依赖之上构建面向认知产出的产品化闭环。

---

## 安装

克隆公开仓：

```bash
git clone git@github.com:peacock-lab/cognition-engine.git
cd cognition-engine
```

创建并激活虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
```

以 editable 模式安装项目：

```bash
python -m pip install -U pip
python -m pip install -e .
```

确认 CLI 可用：

```bash
python -m cognition_engine.cli --help
ce --help
```

---

## 正式 CLI 入口

当前正式入口是：

```bash
ce
python -m cognition_engine.cli
```

推荐首次执行：

```bash
python -m cognition_engine.cli --help
ce status --json
ce brief --insight insight-adk-runner-centrality
ce brief --insight insight-adk-runner-centrality --json
ce decision-pack --insight insight-adk-runner-centrality
ce decision-pack --insight insight-adk-runner-centrality --json
ce workflow --insight insight-adk-runner-centrality
ce workflow --insight insight-adk-runner-centrality --json
```

当前公开主产品路径包括：

```text
ce brief
ce decision-pack
ce workflow
```

---

## 稳定产品简报样例

经过人工确认的稳定产品简报样例位于：

```text
examples/product-briefs/
```

当前首批样例包括：

```text
examples/product-briefs/runner-centrality.md
examples/product-briefs/event-system.md
```

这些样例用于阅读和展示，不等同于运行产物、metadata 留痕或测试基线。

---

## 稳定决策包样例

经过人工确认的稳定决策包样例位于：

```text
examples/decision-packs/
```

当前首个样例为：

```text
examples/decision-packs/runner-centrality.md
```

该样例来源于正式 `ce decision-pack` 入口，用于阅读和展示，不等同于运行产物、metadata 留痕或测试基线。

---

## 第一条产品闭环

当前第一条正式产品闭环是：

```bash
ce brief --insight insight-adk-runner-centrality
```

它会执行：

1. 读取结构化洞察
2. 生成产品简报
3. 在 `outputs/product-briefs/` 下写入 Markdown 产物
4. 在 `outputs/.metadata/` 下写入 metadata 留痕

如需 JSON 输出：

```bash
ce brief --insight insight-adk-runner-centrality --json
```

当前 JSON 结果遵循：

```text
ce-brief-result/v1
```

---

## 决策包能力

当前已具备决策包生成能力：

```bash
ce decision-pack --insight insight-adk-runner-centrality
```

它会执行：

1. 读取结构化洞察
2. 生成决策包
3. 在 `outputs/decision-packs/` 下写入 Markdown 产物
4. 在 `outputs/.metadata/` 下写入 metadata 留痕

如需 JSON 输出：

```bash
ce decision-pack --insight insight-adk-runner-centrality --json
```

当前 JSON 结果遵循：

```text
ce-decision-pack-result/v1
```

当前说明只表示 `ce decision-pack` 能力已具备，不等于公仓发布、版本号推进或第二正式产品闭环公开宣布已经完成。

---

## 认知工作流能力

当前已具备第一条认知工作流入口：

```bash
ce workflow --insight insight-adk-runner-centrality
```

它会按顺序执行：

1. 生成产品简报
2. 生成决策包
3. 生成模型增强产物
4. 返回 workflow-level 组合结果

如需 JSON 输出：

```bash
ce workflow --insight insight-adk-runner-centrality --json
```

当前 JSON 结果遵循：

```text
ce-insight-to-decision-workflow-result/v1
```

当前公开 CLI 中，模型增强步骤默认使用 mock provider；真实 provider 参数暂不作为公开 CLI 使用面。

当前 `ce workflow` 会生成 workflow-level Markdown 汇总产物与 workflow-level metadata；workflow 主路径已完成 ADK-backed 最小承接，但真实 provider 参数仍不进入公开 CLI 使用面。

---

## 当前已验证样本

当前已用于稳定性验证的样本包括：

```text
insight-adk-runner-centrality
insight-adk-event-system
```

这些样本用于验证第一条产品闭环可以稳定生成产品简报输出。

---

## 项目结构

当前公开发布面聚焦最小产品路径：

```text
cognition-engine/
├── pyproject.toml
├── cognition_engine/
├── examples/
│   ├── product-briefs/
│   └── decision-packs/
├── outputs/
│   └── OUTPUT_CONTRACTS.md
├── tests/
│   └── unit/
├── docs/
│   ├── strategy/
│   └── 项目/
├── README.md
├── README.en.md
├── QUICKSTART.md
├── VALIDATION_MODEL.md
├── VALIDATION_STATE_FLOW.md
└── LICENSE
```

内部任务链、原始数据、历史探测报告、本地缓存和私有来源材料不属于公开发布面。

---

## 输出契约

关于输出结构、metadata 和 JSON 结果契约，可查看：

```text
outputs/OUTPUT_CONTRACTS.md
```

当前核心结果契约包括：

```text
ce-brief-result/v1
ce-decision-pack-result/v1
ce-insight-to-decision-workflow-result/v1
```

---

## 当前范围

当前版本支持：

1. 通过 `pyproject.toml` 进行正式包安装
2. 通过 `ce` 使用正式 CLI 入口
3. 通过 `python -m cognition_engine.cli` 使用包入口
4. 通过 `ce brief` 运行第一条产品闭环
5. 通过 `ce decision-pack` 生成决策包
6. 通过 `ce workflow` 执行第一条 `insight-to-decision workflow`
7. Markdown 产品简报输出
8. Markdown 决策包输出
9. metadata 留痕输出
10. 产品简报、决策包与 workflow 的最小单元测试覆盖
11. 稳定产品简报样例展示
12. 稳定决策包样例展示

---

## 当前不包含

当前版本不声明：

1. 第二正式产品闭环公开宣布完成
2. 公仓发布或版本号推进已经触发
3. Docker 支持
3. GUI / Web / channel 支持
4. 完整多智能体编排
5. 高级评估工作流
6. 所有输出类型达到同等成熟度
7. 完整成熟平台
8. 测试基线样例体系
10. 完整 metadata 样例体系

---

## 测试

安装测试依赖：

```bash
python -m pip install -e ".[test]"
```

运行最小单元测试：

```bash
python -m pytest tests/unit/test_decision_pack_loop.py tests/unit/test_output_generator.py tests/unit/test_product_brief_loop.py -q
```

---

## 推荐阅读

```text
QUICKSTART.md
README.en.md
examples/product-briefs/README.md
examples/decision-packs/README.md
outputs/OUTPUT_CONTRACTS.md
VALIDATION_MODEL.md
VALIDATION_STATE_FLOW.md
docs/strategy/002-v0.1.0对外发布收口说明.md
docs/strategy/004-v0.1.0最终发布放行清单.md
docs/strategy/007-双仓发布流程固化方案.md
```

---

## License

Apache License 2.0
