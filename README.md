# Cognition Engine｜认知引擎

`cognition-engine` 是一个基于 Google ADK 的轻量级认知产品闭环项目。

当前公开版本：

```text
v0.3.1
```

`v0.3.1` 定位为：**认知引擎 ADK 底座承接与本地真实模型链路稳定版**。

本 README 只描述当前 `main` 分支的最新公开口径。历史版本通过 `CHANGELOG.md`、`docs/releases/`、GitHub Releases 和 Git tag 保留，不在 README 中展开。

---

## 1. v0.3.1 阶段边界

`v0.3.1` 已完成：

1. ADK-backed workflow 主链稳定；
2. 纯安装态 `CE_DATA_DIR` 运行入口；
3. `CE_INSIGHTS_DIR` 细粒度 insight 覆盖入口；
4. 真实 provider 可通过环境变量进入 workflow 主链；
5. 默认 provider 继续保持 `mock`；
6. `google-adk>=2.0.0b1,<2.1` 依赖主路；
7. `adk-2.0.0b1` framework metadata 最低入口；
8. `adk-2.0.0a3` 历史 smoke / fixtures / 回归数据资产保留；
9. `ce workflow` 的 product brief + decision pack + model enhancement 组合结果；
10. output / metadata 留痕。

`v0.3.1` 不宣称：

1. provider 已公开；
2. `--model-provider` CLI 参数已公开；
3. 真实 provider 已成为默认；
4. Eval 已完成；
5. 完整 Observability 已完成；
6. 正式配置中心已建立；
7. Runner / 观测 / 上下文三条主线已系统梳理完成。

Runner / 观测 / 上下文三条主线统一移交后续版本继续梳理。

---

## 2. 安装

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

安装项目：

```bash
python -m pip install -U pip
python -m pip install -e .
```

确认 CLI 可用：

```bash
ce --help
python -m cognition_engine.cli --help
```

---

## 3. 最小运行方式

`v0.3.1` 推荐使用外置数据根目录运行：

```bash
CE_DATA_DIR="$PWD/data" ce workflow --insight insight-adk-runner-centrality --json
```

也可以显式覆盖 insight 数据目录：

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

## 4. Provider 使用边界

当前默认 provider 为：

```text
mock
```

自 `v0.3.1` 起，普通安装已包含本地模型路径所需的 LiteLLM 依赖，并锁定为：

```text
litellm==1.82.6
```

真实 provider 可通过环境变量显式启用：

```bash
CE_MODEL_PROVIDER=adk_litellm_ollama \
CE_DATA_DIR="$PWD/data" \
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

## 5. Google ADK 依赖说明

`cognition-engine` 当前以 Google ADK 2.0.0b1+ 作为受控智能体框架依赖。

依赖已在 `pyproject.toml` 中声明：

```toml
google-adk>=2.0.0b1,<2.1
```

通常不需要单独手动安装 Google ADK。安装本项目时，Python 包安装流程会读取 `pyproject.toml` 并安装声明依赖。

本项目不是复制 Google ADK 源码，而是在 Google ADK 依赖之上构建面向认知产出的产品化闭环。

---

## 6. 当前公开能力

当前公开能力包括：

1. `ce` CLI 入口；
2. `python -m cognition_engine.cli` 包入口；
3. `ce workflow` 主工作流入口；
4. `CE_DATA_DIR` 外置数据根目录；
5. `CE_INSIGHTS_DIR` insight 数据目录覆盖入口；
6. 默认 mock provider；
7. 环境变量显式启用真实 provider；
8. product brief / decision pack / model enhancement 组合结果；
9. Markdown 输出；
10. metadata 留痕；
11. 最小公开数据资产与样例。

---

## 7. 当前不包含

当前版本不包含：

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

## 8. 数据资产边界

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

## 9. 项目结构

当前公开发布面聚焦最小可用产品路径：

```text
cognition-engine/
├── cognition_engine/
├── data/
│   ├── frameworks/
│   └── insights/
├── docs/
│   └── releases/
├── examples/
├── outputs/
├── tests/
├── pyproject.toml
├── README.md
├── QUICKSTART.md
├── CHANGELOG.md
└── LICENSE
```

内部任务链、治理过程文件、私仓取证记录、本地缓存、构建产物和未清洗运行产物不属于公开发布面。

---

## 10. 输出契约

关于公开输出结构，可查看：

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

## 11. 测试

安装测试依赖：

```bash
python -m pip install -e ".[test]"
```

运行当前公开单元测试：

```bash
python -m pytest tests/unit -q
```

---

## 12. 版本历史

当前 README 描述 `main` 分支最新公开口径。

历史版本说明通过以下位置保留：

1. `CHANGELOG.md`；
2. `docs/releases/`；
3. GitHub Releases；
4. 对应 Git tag。

当前版本发布说明见：

```text
docs/releases/v0.3.1-release-note.md
```

---

## License

Apache License 2.0
