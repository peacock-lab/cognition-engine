# Cognition Engine｜认知引擎

`cognition-engine` 是一个基于 Google ADK 的轻量级认知产品闭环项目。

当前版本：`v0.2.0`

v0.2.0 的重点是：

1. 新增并稳定 `ce workflow` 阶段性能力。
2. 将 product brief、decision pack、model enhancement 串联为第一条 insight-to-decision workflow。
3. 生成 workflow-level Markdown 汇总产物。
4. 生成 workflow-level metadata。
5. 完成 ADK-backed workflow 最小承接。
6. 保持公开 CLI 使用面收敛、稳定、可验证。

---

## 安装

克隆仓库：

    git clone git@github.com:peacock-lab/cognition-engine.git
    cd cognition-engine

创建并激活虚拟环境：

    python -m venv .venv
    source .venv/bin/activate

安装项目及依赖：

    python -m pip install -U pip
    python -m pip install -e .

说明：这里使用 editable 安装方式，便于直接从当前源码目录运行 `ce` 命令；后续修改源码后通常不需要重新安装。

确认 CLI 可用：

    python -m cognition_engine.cli --help
    ce --help

---

## Google ADK 依赖说明

`cognition-engine` 当前以 Google ADK 2.0.0b1+ 作为受控智能体框架依赖。

依赖已经在 `pyproject.toml` 中声明：

    google-adk>=2.0.0b1,<2.1

通常不需要单独手动安装 Google ADK。

执行：

    python -m pip install -e .

时，Python 包安装流程会读取 `pyproject.toml`，并自动安装包括 `google-adk` 在内的声明依赖。

---

## 正式 CLI 入口

当前正式入口是：

    ce
    python -m cognition_engine.cli

当前公开主产品路径包括：

    ce brief
    ce decision-pack
    ce workflow

---

## 快速开始

### 1. 查看状态

    ce status --json

### 2. 生成产品简报

    ce brief --insight insight-adk-runner-centrality

JSON 输出：

    ce brief --insight insight-adk-runner-centrality --json

### 3. 生成决策包

    ce decision-pack --insight insight-adk-runner-centrality

JSON 输出：

    ce decision-pack --insight insight-adk-runner-centrality --json

### 4. 执行认知工作流

    ce workflow --insight insight-adk-runner-centrality

JSON 输出：

    ce workflow --insight insight-adk-runner-centrality --json

`ce workflow` 会执行第一条 `insight-to-decision workflow`，组合：

1. product brief
2. decision pack
3. model enhancement

并生成 workflow-level 汇总产物与 metadata。

---

## 输出目录

主要输出目录包括：

    outputs/product-briefs/
    outputs/decision-packs/
    outputs/model-enhancements/
    outputs/workflows/
    outputs/.metadata/

其中：

1. `outputs/product-briefs/` 保存产品简报 Markdown 产物。
2. `outputs/decision-packs/` 保存决策包 Markdown 产物。
3. `outputs/model-enhancements/` 保存模型增强 Markdown 产物。
4. `outputs/workflows/` 保存 workflow-level Markdown 汇总产物。
5. `outputs/.metadata/` 保存 metadata 记录。

输出契约说明见：

    outputs/OUTPUT_CONTRACTS.md

---

## v0.2.0 工作流能力

v0.2.0 引入了 ADK-backed workflow 最小承接。

这意味着 `ce workflow` 不再只是本地 Python 顺序编排路径，而是通过 ADK-backed adapter 承接最小 workflow 主链，并在结果中保留：

1. execution 映射字段。
2. session / context / invocation 映射字段。
3. event summary。
4. artifact refs。
5. 三个业务 step 的结构化结果。

这仍是阶段性最小承接，不代表所有 ADK 能力已经完整接入。

---

## 样例资产

经过人工确认的稳定产品简报样例位于：

    examples/product-briefs/

当前首批样例包括：

    examples/product-briefs/runner-centrality.md
    examples/product-briefs/event-system.md

经过人工确认的稳定决策包样例位于：

    examples/decision-packs/

当前首个样例为：

    examples/decision-packs/runner-centrality.md

这些样例用于阅读和展示，不等同于运行产物、metadata 留痕或测试基线。

---

## 测试

可运行当前阶段的核心测试：

    python -m pytest \
      tests/unit/test_product_brief_loop.py \
      tests/unit/test_decision_pack_loop.py \
      tests/unit/test_model_enhancement_loop.py \
      tests/unit/test_workflow_loop.py \
      tests/unit/test_cli_workflow_dispatch.py \
      tests/unit/test_adk_workflow_adapter.py \
      -q

---

## 发布说明

v0.2.0 发布说明见：

    docs/releases/v0.2.0-release-note.md

---

## 许可

见：

    LICENSE
