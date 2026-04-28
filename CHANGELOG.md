# Changelog

本文是 `cognition-engine` 公仓版本历史索引。

本文只记录公开版本的轻量摘要、release note 入口、GitHub Releases 与 Git tag 入口，不承载内部治理过程、任务链、取证记录或实施记录。

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
