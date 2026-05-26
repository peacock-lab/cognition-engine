# 变更记录

本文档作为认知引擎公开版本历史索引和轻量摘要，不承载内部治理全过程。

## v0.8.3 未发布候选

`v0.8.3` 是当前 ADK 2.1.0 baseline patch release 候选版本号。

候选口径：

```text
认知系统产品控制台 + 可复查资料问答包：在 ADK 2.1.0 底座上，用户通过产品控制台读取授权资料，获得可复查回答，并可查看本轮问答运行引用。
```

主要变化：

1. ADK 底座同步到 `google-adk==2.1.0`；
2. 保持 `cognition-console ask --guided` 作为当前公开主产品入口；
3. `cognition-console ask --guided --json` 保留 answer run、artifact、trace、observability summary 与 trace inspect 的机器可读复查引用；
4. 068-071 已完成 ADK 2.1.0 取证、隔离兼容性 smoke、受控回归与产品入口体验验收；
5. 产品控制台继续支持 Gemma4 本地路径和 DeepSeek 已保存 key 路径；
6. 当前进程内支持围绕同一资料继续追问，也支持对上一轮答案做摘要、翻译、排版和改写；
7. 短证据长文、白皮书、未来路线图等超范围请求会返回受治理说明，不编造内容；
8. PyPI 安装态默认配置装配、Ctrl+C graceful interrupt、Trusted Publishing workflow 草案与安装态 smoke 硬门继承 v0.8.2 发布线；
9. 不打开 ADK Task API runtime、Workflow Runtime、MCP tools、ArtifactService 持久链路、durable Session、Memory、Skills、callbacks 或 plugins；
10. 可复查资料问答包是当前第一批可体验产品能力，不代表 Cognition System 只做资料问答。

正式发布时间、PyPI 上传、公仓 tag、GitHub Release 与发布后安装复验，等待后续发布链路任务定稿。

## v0.8.0 未发布候选

`v0.8.0` 是上一轮产品发布候选版本号，当前只保留为 v0.8.3 前的发布线记录。

当前候选口径：

```text
可复查资料问答：用户授权读取外部只读资料，基于证据回答，并展示证据、trace、artifact、阻断原因与恢复建议。
```

候选变化摘要：

1. 建立 `cognition external-readonly ask --guided` 作为可复查资料问答首用入口；
2. 成功、阻断、失败和证据不足路径均可外显 answer trace / answer artifact 状态；
3. 支持围绕同一 evidence digest 的当前进程内追问，并明确不冒充长期 Memory 或跨进程会话；
4. 支持 `deepseek` 与 `gemma4` 白名单模型别名，保持联网、live LLM、operator approval、audit 与 provider key 显性治理门；
5. DeepSeek 路径支持一次性输入 key 与 macOS Keychain 长期保存 / 显式读取；
6. Gemma4 路径保留为本地 Ollama 调试与试用路径；
7. ADK 基线已对齐 `google-adk==2.0.0` GA，LiteLLM 继续锁定 `1.82.6`；
8. 公开包命名已将早期任务工作流候选调整为 `cognition-system-operation-flows`，中文口径为受治理操作流包，避免与 ADK Task API / Workflow Runtime 混淆；
9. 当前公仓发布面先保留根级项目文档，包内 README 暂不作为公仓同步材料，待包独立演进后再按包更新；
10. `outputs/` 运行产物保持忽略，不进入公开发布材料；
11. 当前阶段不包含桌面 GUI、streaming 输出或任意模型开放接入。

正式发布时间、PyPI 发布动作、公仓 tag、GitHub Release 与发布后安装复验，等待后续发布链路任务定稿。

## v0.6.0 未发布候选

`v0.6.0` 当前处于架构建设与发布前同步阶段，尚未在本文件中定稿为正式发布记录。

当前候选口径：

```text
三大能力域 + 系统级公共设施 + legacy 资产池
```

候选变化摘要：

1. 将认知引擎公开边界收口到 `runtime_container`、`runtime`、`adk_adapter`、ADK Workflow / Runner / RunConfig / Service 能力承接，以及可发布 no-live 验证入口；
2. 将 `cognition_governance` 表达为独立认知治理能力域，当前保持 candidate-only，不作为正式治理决策控制面、发布阻断器、ADK RunConfig 生成器或 `runtime_container` 控制者；
3. 将 `cognition_agent` 表达为独立认知智能体能力域，当前保持极薄候选壳层，只读消费治理视图、LLM 调用摘要与 runtime 摘要，不作为 Agent runtime、Chat、Gateway、LLM 调用层或 ToolExecutor；
4. 将 `contract_core`、`schemas`、`behavior_contracts`、`config_assembly`、`config_contexts`、`composition`、`observability_hub` 等表达为系统级公共设施；
5. 明确 `runtime_container.dev_entry.no_live_llm_invocation` 是可发布 no-live 验证入口，不是正式 CLI，不新增 `console_scripts`，不触发真实模型调用；
6. 将历史 `cognition_engine/`、078 冻结产物和旧叙事资产归入 legacy 资产池处理。

正式发布时间、版本号同步、release note、PyPI 发布链路和 Trusted Publishing 状态，等待发布材料总审查与多包发布链路核查后定稿。

## v0.5.4

`v0.5.4` 聚焦 Trusted Publishing 上线与发布工程可信闭环，重点完成公仓最小发布 workflow、PyPI Trusted Publisher 配置链路和发布回退边界建设。

主要变化：

1. 将根包与 10 个子包版本升至 `0.5.4`；
2. 将根包依赖同步到 `cognition-engine-*==0.5.4`；
3. 新增公仓最小 PyPI publish workflow，用于 Trusted Publishing 发布路径；
4. 完成 11 个 PyPI 项目的 Trusted Publisher 配置链路；
5. 新增公开版 workflow 模板检查工具与对应测试；
6. 保留 Keychain project token fallback 作为发布失败时的兜底路径；
7. 继续保持公开主线为模块化包结构，不引入新的用户侧产品能力。

对应发布说明：`v0.5.4-release-note.md`

对应 tag：`v0.5.4`

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
