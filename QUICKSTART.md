# 快速开始指南

本文描述当前 `main` 分支 / `v0.3.1` 的最小上手路径。

历史版本的快速开始说明请查看对应 Git tag 或 GitHub Release；当前 `main` 分支的 QUICKSTART 只维护最新公开基线。

当前公开版本：

```text
v0.3.1
```

`v0.3.1` 定位为：**认知引擎 ADK 底座承接与本地真实模型链路稳定版**。

---

## 1. 文档定位

本文用于说明 `cognition-engine` 当前公开版本的最小安装方式、正式 CLI 主入口、Google ADK 依赖关系、`CE_DATA_DIR` / `CE_INSIGHTS_DIR` 数据入口，以及 `ce workflow` 的最小运行方式。

本文不是：

1. 历史版本 QUICKSTART 汇总；
2. 内部迁移手册；
3. 全部 CLI 能力索引；
4. 内部治理过程记录；
5. release note；
6. CHANGELOG。

历史版本信息请查看：

1. `CHANGELOG.md`；
2. `docs/releases/`；
3. GitHub Releases；
4. 对应 Git tag。

---

## 2. 获取项目

```bash
git clone git@github.com:peacock-lab/cognition-engine.git
cd cognition-engine
```

如使用 HTTPS，可改用公开仓 HTTPS 地址克隆。

---

## 3. 创建并激活虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate
```

---

## 4. 安装项目

```bash
python -m pip install -U pip
python -m pip install -e .
```

说明：

1. `pyproject.toml` 是当前正式打包入口；
2. `cognition_engine/` 是当前正式包层；
3. 当前正式 CLI 主入口为 `ce`；
4. 安装时会读取 `pyproject.toml` 中声明的依赖。

---

## 5. Google ADK 依赖说明

当前版本以 Google ADK 2.0.0b1+ 作为受控智能体框架依赖。

该依赖已在 `pyproject.toml` 中声明：

```toml
google-adk>=2.0.0b1,<2.1
```

执行安装时，Python 包安装流程会自动安装 `google-adk` 等项目依赖。

通常不需要单独手动安装 Google ADK。

本项目不是复制 Google ADK 源码，而是在 Google ADK 依赖之上构建面向认知产出的产品化闭环。

---

## 6. 确认 CLI 主入口可用

```bash
ce --help
python -m cognition_engine.cli --help
```

如果这两条命令都能正常返回帮助信息，说明当前正式 CLI 主入口已经可用。

---

## 7. 最小运行方式

`v0.3.1` 推荐使用外置运行时数据根目录：

```bash
CE_DATA_DIR="$PWD/data" ce workflow --insight insight-adk-runner-centrality --json
```

`CE_DATA_DIR` 指向认知引擎外置运行时数据根目录。

`CE_INSIGHTS_DIR` 可作为 insight 数据目录的细粒度覆盖入口：

```bash
CE_DATA_DIR="$PWD/data" \
CE_INSIGHTS_DIR="$PWD/data/insights" \
ce workflow --insight insight-adk-runner-centrality --json
```

当前主入口：

```bash
ce workflow --insight insight-adk-runner-centrality
ce workflow --insight insight-adk-runner-centrality --json
```

`ce workflow` 会按顺序生成：

```text
product brief
→ decision pack
→ model enhancement
→ workflow-level result
→ metadata
```

---

## 8. Provider 使用边界

当前默认 provider 为：

```text
mock
```

自 `v0.3.1` 起，普通安装已包含本地模型路径所需的 LiteLLM 依赖，并锁定为：

```text
litellm==1.82.6
```

本地模型路径仍需要用户本机启动 Ollama，并准备对应模型。

真实 provider 可通过环境变量显式启用：

```bash
CE_MODEL_PROVIDER=adk_litellm_ollama \
CE_DATA_DIR="$PWD/data" \
CE_MODEL_TIMEOUT_SECONDS=180 \
OLLAMA_API_BASE=http://127.0.0.1:11434 \
ce workflow --insight insight-adk-runner-centrality --json
```

当前公开边界：

1. 真实 provider 可显式进入 workflow 主链；
2. 普通安装已包含 LiteLLM 依赖；
3. 本地模型路径仍需要用户本机启动 Ollama 并准备对应模型；
4. 当前不公开 `--model-provider` CLI 参数；
5. 当前不将真实 provider 设为默认；
6. provider 公开能力留待后续版本判断。

---

## 9. 当前输出

`ce workflow` 成功运行后，通常返回或生成以下内容：

1. product brief；
2. decision pack；
3. model enhancement；
4. workflow-level result；
5. metadata。

公开输出结构说明见：

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

## 10. 当前数据资产边界

当前正式依赖主路为：

```text
google-adk>=2.0.0b1,<2.1
```

当前数据资产边界：

1. `data/frameworks/adk-2.0.0b1/metadata.json` 是 b1 framework metadata 最低入口；
2. `data/frameworks/adk-2.0.0a3/metadata.json` 作为历史数据资产保留；
3. `data/insights/adk-2.0.0a3/` 中的历史样本用于 smoke / fixtures / 回归验证；
4. 不将 a3 样本伪改为 b1 样本；
5. b1 insight 样本体系不属于本版本完成边界。

---

## 11. 测试

如需运行当前公开单元测试，请先安装测试依赖：

```bash
python -m pip install -e ".[test]"
```

然后运行：

```bash
python -m pytest tests/unit -q
```

说明：

1. 测试依赖位于 `pyproject.toml` 的 `[project.optional-dependencies]`；
2. 如果只安装 `python -m pip install -e .`，可能不会安装 `pytest`。

---

## 12. 当前不包含的能力

当前公开版本不承诺：

1. provider 公开接口；
2. `--model-provider` CLI 参数公开；
3. Eval 完整能力；
4. 完整 Observability；
5. 正式配置中心；
6. GUI / Web / channel 支持；
7. 完整多智能体编排；
8. 完整成熟平台能力；
9. Runner / 观测 / 上下文三主线系统化治理接口。

---

## 13. 下一步阅读

建议继续阅读：

```text
README.md
README.en.md
CHANGELOG.md
docs/releases/v0.3.1-release-note.md
outputs/OUTPUT_CONTRACTS.md
```

---

## 一句话收口

安装项目后，运行以下命令即可体验当前 `v0.3.1` 的最小认知工作流：

```bash
CE_DATA_DIR="$PWD/data" ce workflow --insight insight-adk-runner-centrality --json
```
