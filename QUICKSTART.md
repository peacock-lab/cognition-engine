# 快速开始指南

## 文档定位

本文档用于说明 `cognition-engine` 当前公开版本的最小安装方式、正式 CLI 主入口、Google ADK 依赖关系，以及当前已具备的 `ce brief`、`ce decision-pack` 与 `ce workflow` 使用方式。

本文档不是：

- 内部迁移手册
- 历史脚本时代的兼容入口索引
- 全部底层脚本的穷举清单
- 第二正式产品闭环公开宣布文档

本文档当前优先服务于：

- 首次安装公开仓的使用者
- 需要确认正式 CLI 主入口的使用者
- 需要运行当前 `ce brief`、`ce decision-pack` 与 `ce workflow` 能力的使用者

---

## 1 分钟启动认知引擎

### 第一步：获取项目

```bash
git clone git@github.com:peacock-lab/cognition-engine.git
cd cognition-engine
```

如你使用 HTTPS，也可以改用公开仓 HTTPS 地址克隆。

### 第二步：创建并激活虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate
```

### 第三步：安装项目

```bash
python -m pip install -U pip
python -m pip install -e .
```

说明：

- `pyproject.toml` 是当前正式打包入口
- `cognition_engine/` 是当前正式包层
- 当前正式 CLI 主入口为：`ce`
- 安装时会自动读取 `pyproject.toml` 中声明的依赖

---

## Google ADK 依赖说明

当前版本以 Google ADK 2.0.0b1+ 作为受控智能体框架依赖。

该依赖已经在 `pyproject.toml` 中声明：

```toml
google-adk>=2.0.0b1,<2.1
```

执行：

```bash
python -m pip install -e .
```

时，Python 包安装流程会自动安装 `google-adk` 等项目依赖。

通常不需要单独手动安装 Google ADK。

本项目不是复制 Google ADK 源码，而是在 Google ADK 依赖之上构建面向认知产出的第一条正式产品化闭环。

---

## 确认正式主入口可用

```bash
python -m cognition_engine.cli --help
ce --help
```

如果这两条命令都能正常返回帮助信息，说明当前正式 CLI 主入口已经可用。

---

## 查看当前项目状态

```bash
ce status --json
```

这一步用于确认：

- 当前结构化数据是否存在
- 当前统计与健康度是否可读取
- 当前环境是否具备运行第一条正式闭环的基本条件

---

## 运行第一条正式产品化闭环

```bash
ce brief --insight insight-adk-runner-centrality
```

这条命令会：

1. 读取一个真实存在的 `insight`
2. 生成一份正式 `product-brief`
3. 在 `outputs/product-briefs/` 下留下 Markdown 产物
4. 在 `outputs/.metadata/` 下留下元数据记录

如需查看经过人工确认的稳定产品简报样例，可查看：

```text
examples/product-briefs/
```

该目录用于展示，不等同于运行产物、metadata 留痕或测试基线。

---

## 运行决策包能力

```bash
ce decision-pack --insight insight-adk-runner-centrality
```

这条命令会：

1. 读取一个真实存在的 `insight`
2. 生成一份正式 `decision-pack`
3. 在 `outputs/decision-packs/` 下留下 Markdown 产物
4. 在 `outputs/.metadata/` 下留下元数据记录

如需查看经过人工确认的稳定决策包样例，可查看：

```text
examples/decision-packs/
```

当前首个稳定样例为：

```text
examples/decision-packs/runner-centrality.md
```

该目录用于展示，不等同于运行产物、metadata 留痕或测试基线。

---

## 运行认知工作流

```bash
ce workflow --insight insight-adk-runner-centrality
```

这条命令会按顺序生成产品简报、决策包和模型增强产物，并返回一份 workflow-level 组合结果。

当前公开 CLI 不暴露真实 provider 参数，模型增强步骤默认走 mock provider。

如需 JSON 输出：

```bash
ce workflow --insight insight-adk-runner-centrality --json
```

当前 `ce workflow` JSON 结果契约为：

```text
ce-insight-to-decision-workflow-result/v1
```

---

## 获取 JSON 结果

```bash
ce brief --insight insight-adk-runner-centrality --json
```

当前 `ce brief` JSON 结果契约为：

```text
ce-brief-result/v1
```

`ce decision-pack` JSON 输出命令为：

```bash
ce decision-pack --insight insight-adk-runner-centrality --json
```

当前 `ce decision-pack` JSON 结果契约为：

```text
ce-decision-pack-result/v1
```

`ce workflow` JSON 输出命令为：

```bash
ce workflow --insight insight-adk-runner-centrality --json
```

当前 `ce workflow` JSON 结果契约为：

```text
ce-insight-to-decision-workflow-result/v1
```

成功结果通常包含：

- `status`
- `contract_version`
- `closure_id`
- `output_type`
- `insight_id`
- `output_file`
- `metadata_file`
- `generated_at`
- `validation`
- `brief_summary`
- `primary_use_case`
- `recommended_action`

---

## 当前推荐工作流

```bash
# 1. 查看状态
ce status --json

# 2. 跑产品简报能力
ce brief --insight insight-adk-runner-centrality

# 3. 跑决策包能力
ce decision-pack --insight insight-adk-runner-centrality

# 4. 跑认知工作流
ce workflow --insight insight-adk-runner-centrality

# 5. 如需结构化结果
ce brief --insight insight-adk-runner-centrality --json
ce decision-pack --insight insight-adk-runner-centrality --json
ce workflow --insight insight-adk-runner-centrality --json
```

规则：

- 优先先跑 `ce brief`
- 如需决策包，再运行 `ce decision-pack`
- 如需一次性组合产品简报、决策包和模型增强产物，可运行 `ce workflow`
- `ce` 与 `python -m cognition_engine.cli` 是当前正式主入口
- 旧脚本链不再作为公开主路径说明
- 当前文档说明 `ce decision-pack` 能力已具备，但不等于公仓发布、版本号推进或第二正式产品闭环公开宣布完成

---

## 当前已压实的真实样本

当前已用于稳定性验证的样本包括：

```text
insight-adk-runner-centrality
insight-adk-event-system
```

建议首次体验优先使用：

```bash
ce brief --insight insight-adk-runner-centrality
```

---

## 输出位置

### Product brief

```text
outputs/product-briefs/
```

### Decision pack

```text
outputs/decision-packs/
```

### Model enhancement

```text
outputs/model-enhancements/
```

### Metadata

```text
outputs/.metadata/
```

### 输出契约说明

```text
outputs/OUTPUT_CONTRACTS.md
```

---

## 常用命令速查

```bash
# 查看 CLI 帮助
python -m cognition_engine.cli --help
ce --help

# 查看状态
ce status --json

# 生成 product brief
ce brief --insight insight-adk-runner-centrality

# 生成 decision pack
ce decision-pack --insight insight-adk-runner-centrality

# 执行 insight-to-decision workflow
ce workflow --insight insight-adk-runner-centrality

# 生成 JSON 结果
ce brief --insight insight-adk-runner-centrality --json
ce decision-pack --insight insight-adk-runner-centrality --json
ce workflow --insight insight-adk-runner-centrality --json
```

---

## 测试

如需运行当前最小测试，请先安装测试依赖：

```bash
python -m pip install -e ".[test]"
```

然后运行：

```bash
python -m pytest tests/unit/test_decision_pack_loop.py tests/unit/test_output_generator.py tests/unit/test_product_brief_loop.py -q
```

说明：

- 测试依赖位于 `pyproject.toml` 的 `[project.optional-dependencies]`
- 如果只安装 `python -m pip install -e .`，可能不会安装 `pytest`

---

## 故障排除

### Q: `ce` 命令不可用

先确认已经激活虚拟环境并完成 editable install：

```bash
source .venv/bin/activate
python -m pip install -e .
ce --help
```

### Q: `python -m pytest` 找不到 `pytest`

安装测试依赖：

```bash
python -m pip install -e ".[test]"
python -m pytest tests/unit/test_decision_pack_loop.py tests/unit/test_output_generator.py tests/unit/test_product_brief_loop.py -q
```

### Q: `insight_id` 不存在

先使用当前已验证样本：

```bash
ce brief --insight insight-adk-runner-centrality
```

或：

```bash
ce brief --insight insight-adk-event-system
```

### Q: 生成结果在哪里

查看：

```text
outputs/product-briefs/
outputs/decision-packs/
outputs/model-enhancements/
outputs/workflows/
outputs/.metadata/
```

---

## 当前不包含的能力

当前公开版本不承诺：

- 第二正式产品闭环公开宣布完成
- Docker / GUI / Web / channel 支持
- 完整多智能体编排
- 高阶评估工作流
- 所有输出类型达到同等成熟度
- 完整成熟平台状态

---

## 下一步阅读

建议继续阅读：

```text
README.md
outputs/OUTPUT_CONTRACTS.md
VALIDATION_MODEL.md
VALIDATION_STATE_FLOW.md
```

---

## 一句话收口

安装项目后，运行 `ce brief --insight insight-adk-runner-centrality` 可体验产品简报能力；运行 `ce decision-pack --insight insight-adk-runner-centrality` 可体验决策包能力；运行 `ce workflow --insight insight-adk-runner-centrality` 可体验第一条认知工作流组合能力。
