# 变更记录

本文档作为认知引擎公开版本历史索引和轻量摘要，不承载内部治理全过程。

## v0.5.3

`v0.5.3` 聚焦发布治理准备能力增强，重点强化发布材料组织、发布前取证、发布流程检查点和人工授权边界。

主要变化：

1. 将根包与 10 个子包版本升至 `0.5.3`；
2. 将根包依赖同步到 `cognition-engine-*==0.5.3`；
3. 增强发布准备材料组织能力，形成发布材料模板池与汇总入口；
4. 增强发布前状态取证、公开材料更新判断和发布准备记录链路；
5. 保持真实发布动作的人工授权边界，不引入自动 PyPI 上传、自动 tag、自动 GitHub Release、Trusted Publishing 或 CI 发布 workflow。

对应发布说明：`v0.5.3-release-note.md`

对应 tag：`v0.5.3`

## v0.5.2

发布时间：待发布。

版本定位：发布治理准备能力增强版本。

关键变化：

1. 将根包与 10 个子包版本升至 `0.5.2`；
2. 将根包依赖同步到 `cognition-engine-*==0.5.2`；
3. 增加 PyPI 发布后安装复验脚本；
4. 增加公仓公开面边界检查脚本；
5. 增加 PyPI 目标版本存在性检查脚本；
6. 增加 token 环境变量轻量检查脚本；
7. 增加发布安全网总入口脚本，用于统一聚合发布前与发布后检查结果；
8. 保持根包作为聚合元包，不恢复 legacy `cognition_engine` import shell；
9. 保持公开主线为模块化包结构，不引入新的产品能力。

对应发布说明：`v0.5.2-release-note.md`

对应 tag：`v0.5.2`

## v0.5.1

发布时间：待发布。

版本定位：发布工程补丁版本。

关键变化：

1. 将 10 个子包 README 接入 PyPI long_description；
2. 清零 10 个子包 `twine check` 的 long_description 相关 warning；
3. 将根包与 10 个子包版本升至 `0.5.1`；
4. 将根包依赖同步到 `cognition-engine-*==0.5.1`；
5. 保持根包作为聚合元包，不恢复 legacy `cognition_engine` import shell；
6. 明确公仓不暴露内部发布检查脚本；
7. 保持公开主线为模块化包结构，不引入新的产品能力。

对应发布说明：`v0.5.1-release-note.md`

对应 tag：`v0.5.1`

## v0.5.0

发布时间：2026-05-03。

版本定位：模块化包结构基线。

关键变化：

1. 建立 `packages/` 源码布局；
2. 增加主要包级能力区域，包括 `contract_core`、`runtime_container`、`adk_adapter`、`observability_hub`；
3. 增加 schemas、behavior contracts、configuration contexts、configuration assembly、runtime primitives、composition 等支撑性结构；
4. 更新根级包元数据，使其对齐 v0.5.0 模块化包基线；
5. 增加 `tests/packages/` 下的包级测试；
6. 完成包构建、隔离安装、依赖解析与包导入 smoke 路径验证；
7. 当前公开主线以模块化包结构为准，不再将历史单包兼容资产作为 v0.5.0 公开基线表达。

对应发布说明：`v0.5.0-release-note.md`

对应 tag：`v0.5.0`

## v0.4.0

发布时间：2026-04-30。

版本定位：核心骨架稳定化。

关键变化：

1. 稳定认知引擎核心骨架；
2. 为后续模块化包结构基线提供前置基础。

对应 tag：`v0.4.0`
