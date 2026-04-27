# 产品简报: Runner 是请求总控与主要收口器

## 一页结论
ADK 已经被多份正式结果文件共同坐实：Runner 负责获取或创建 session、创建 InvocationContext、驱动执行、消费事件、append 到 session，并向外回传结果。 这意味着我们可以把“Runner 是请求总控与主要收口器”从技术判断进一步沉淀为面向真实团队协作的产品化能力表达。

- **推荐落点**: 将 Runner 视为正式请求总控层，并围绕它定义统一的执行主链、状态收口约束和对外回传接口。
- **主要适用场景**: 把请求执行、事件消费、状态收口和结果回传统一收进一个可治理的运行总控层。
- **影响判断**: 架构影响 高 / 迁移影响 高 / 产品影响 中
- **标签**: adk、coordination、runner、entry point

## 适用场景
- 适用于正在梳理 Google Agent Development Kit 相关架构主链、迁移路径或产品能力边界的团队。
- 适用于需要把单条技术洞察直接转成内部简报、设计说明或最小决策材料的场景。
- 当前最适合从单洞察、单能力切入，而不是一次性拉起多闭环产品面。

## 目标使用者
1. 架构负责人：需要把技术主链讲清并转成团队共识。
2. 技术负责人：需要把洞察转成可执行的系统设计或迁移动作。
3. 产品负责人：需要理解该技术能力会怎样影响交付边界与价值主张。

## 用户问题
当执行主链分散在多个入口、节点或回调里时，团队很难解释谁负责创建上下文、谁负责收口结果、谁对外回传。

## 产品主张
1. 减少请求执行责任散落导致的架构歧义。
2. 让 Session、InvocationContext 和事件链的职责边界更容易讲清楚。
3. 为后续验证、观测和回归检查提供单一主锚点。

## 上线边界
当前先聚焦普通请求主链与结果收口，不把不同协议层或发布层一次性并入改造范围。

## 证据与可信度
- **框架**: Google Agent Development Kit 2.0.0a3
- **洞察来源**: insight-adk-runner-centrality
- **置信度**: 97%
- **证据摘要**:
- 证据来源: documentation_reference | 文件 `core_runtime_map` | 章节 `6. 单次请求运行主链` | 摘录: `外部入口 -> Runner -> Session/InvocationContext -> 根 agent 或根 node -> NodeRunner/workflow -> Event 入队 -> Runner 消费事件 -> session_service.append_event -> 对外回传`
- 证据来源: result_package_reference | 文件 `anchor_evidence_package` | 章节 `4.2 谁承担请求协调与主要收口已经坐实` | 摘录: Runner 承担请求协调与主要收口，其依据已经在全仓审计中明确体现为 session 获取、InvocationContext 创建、事件消费、append 和回传。

## 相关洞察
- 状态在 Session、InvocationContext、Context 间分层寄宿: Runner 负责把状态宿主、执行上下文与事件链串成一个稳定闭环。
- 事件 append、状态收口与对外回传形成统一收口链: Runner 既消费 Event 队列，也负责 append 和回传。

## 下一步行动
1. 把 Runner 主链职责整理成内部架构说明和接口约束。
2. 围绕 Session 创建、事件 append、结果回传补一轮回归检查点。
3. 将相关洞察串成执行主链蓝图，支撑后续产品化表达。

---
*生成时间: 2026-04-24 12:41:03*  
*洞察来源: insight-adk-runner-centrality*  
*置信度: 97%*
