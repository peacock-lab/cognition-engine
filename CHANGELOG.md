# Changelog

本文是 `cognition-engine` 公仓版本历史索引。

本文只记录公开版本的轻量摘要、release note 入口、GitHub Releases 与 Git tag 入口，不承载内部治理过程、任务链、取证记录或实施记录。

---

## v0.3.2

版本定位：`v0.3.1` 发布后的依赖与虚拟环境治理小版本。

关键变化：

1. 引入并提交双仓 `uv.lock`；
2. 将 `uv` 明确为用户级全局工具，当前路径为 `/Users/peacock/.local/bin/uv`；
3. 确认当前 `uv` 版本为 `0.11.8`；
4. 明确不把 `uv` 安装进各仓 `.venv`；
5. 明确私仓与公仓继续复用各自既有 `.venv`；
6. `release` extra 增加 `twine>=6.2.0`；
7. 明确 `uv sync` 分场景使用规则；
8. 完成双仓 `uv sync --all-extras` 实测；
9. 建立发布前干净环境验证规则；
10. 明确用户视角测试继续使用普通 `pip install`。

发布说明：

```text
docs/releases/v0.3.2-release-note.md
```

发布状态：

```text
待发布。
```

---

## v0.3.1

版本定位：`v0.3.0` 发布后的本地模型依赖修复版本。

关键变化：

1. 将 LiteLLM 从可选 `llm` extra 提升为基础依赖；
2. 将 LiteLLM 锁定为 `litellm==1.82.6`；
3. 修复普通安装后显式启用本地模型 provider 时缺少 LiteLLM 依赖的问题；
4. 保持默认 provider 为 `mock`；
5. 保持真实 provider 通过 `CE_MODEL_PROVIDER=adk_litellm_ollama` 显式启用；
6. 保持 `--model-provider` CLI 参数暂不公开；
7. 暂不采用 `litellm` 1.83.7，因为其依赖 `pydantic==2.12.5`，与当前 `pydantic>=2.13.0` 基线冲突；暂不采用 `litellm` 1.83.10 及以上版本，因为当前 Python 3.14 环境会被其 `Requires-Python <3.14` 约束拦截。后续等待 LiteLLM 新版本恢复对 Python 3.14 / Pydantic 2.13+ 的兼容后再升级。

发布说明：

```text
docs/releases/v0.3.1-release-note.md
```

发布状态：

```text
待发布。
```

---

## v0.3.0

版本定位：认知引擎 ADK 底座承接与本地真实模型链路稳定版。

关键变化：

1. ADK-backed workflow 主链稳定；
2. 纯安装态 `CE_DATA_DIR` 运行入口；
3. `CE_INSIGHTS_DIR` 细粒度 insight 覆盖入口；
4. 真实 provider 可通过环境变量显式进入 workflow 主链；
5. 默认 provider 继续保持 `mock`；
6. `google-adk>=2.0.0b1,<2.1` 依赖主路；
7. `adk-2.0.0b1` framework metadata 最低入口；
8. `adk-2.0.0a3` 历史 smoke / fixtures / 回归数据资产保留。

发布说明：

```text
docs/releases/v0.3.0-release-note.md
```

发布状态：

```text
公仓 main 已同步；Git tag / GitHub Release / PyPI 以正式发布记录为准。
```

---

## v0.2.0

版本定位：历史公开基线版本。

说明：

1. `v0.2.0` 作为历史公开基线保留；
2. 详细发布记录以 GitHub Releases 与对应 Git tag 为准；
3. 当前 main 分支 README 不再展开 `v0.2.0` 旧使用口径。

---

## 版本记录规则

后续版本继续按以下方式追加：

```text
## vX.Y.Z

版本定位：...

关键变化：

1. ...

发布说明：

docs/releases/vX.Y.Z-release-note.md

发布状态：

GitHub Releases / Git tag / PyPI 以正式发布记录为准。
```
