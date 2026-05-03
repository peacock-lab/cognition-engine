# config_contexts

## 目录定位

`config_contexts/` 是认知引擎的配置上下文契约包，属于 `contract_core` 背后的公共契约支撑面之一。

它与 `behavior_contracts/`、`schemas/` 平行：

```text
behavior_contracts = 行为契约
schemas = 数据契约
config_contexts = 配置上下文契约
```

本包负责定义模块最终消费的配置上下文契约与 Config View，使 runtime、workflow、composition、observability、adapter 等模块只依赖被注入的配置消费视图，而不是直接读取配置事实或理解配置装配过程。

本包不是配置事实层，也不是配置装配层：

```text
config/ = 配置事实来源
config_assembly/ = 配置装配与环境覆盖
config_contexts/ = 配置上下文契约与消费视图
```

## 职责边界

本包负责：

1. 定义模块消费级 Config View。
2. 定义配置上下文契约对象。
3. 表达配置消费语义、策略、护栏与不变式。
4. 为 runtime、workflow、composition、observability、adapter 等模块提供稳定配置消费边界。
5. 作为 `contract_core` 公共契约支撑面的一部分，被上层通过契约窗口理解和复用。

本包不负责：

1. 不负责直接读取 `config/`。
2. 不负责配置文件加载。
3. 不负责环境覆盖装配。
4. 不负责运行时系统装配。
5. 不负责业务执行。
6. 不负责外部 SDK 调用。
7. 不作为普通业务数据模型仓库替代 `schemas/`。

## 与其他层的关系

### 与 contract_core 的关系

- `contract_core/` 是公共契约入口。
- `config_contexts/` 是 `contract_core` 背后的正式契约支撑面之一。
- 后续对外表达时，应把 `config_contexts/` 归入公共契约支撑面，而不是归入配置实现层。

### 与 behavior_contracts 的关系

- `behavior_contracts/` 定义行为能力契约。
- `config_contexts/` 定义行为实现、运行组织与装配过程所需的配置消费契约。
- 二者同属公共契约支撑面，分别回答“能做什么”和“在什么配置上下文中做”。

### 与 schemas 的关系

- `schemas/` 负责普通跨模块数据契约。
- `config_contexts/` 负责配置消费上下文契约与 Config View。
- 配置上下文对象默认归属 `config_contexts/`，不应混入普通业务数据契约。

### 与 config_assembly 的关系

- `config_assembly/` 负责把配置事实与环境覆盖装配为标准配置载荷。
- `config_contexts/` 基于标准配置载荷定义模块可消费的契约化配置视图。
- `config_contexts/` 不直接读取 `config/`，也不承担装配职责。

### 与 config/ 的关系

- `config/` 是配置事实来源。
- `config_contexts/` 不直接读取 `config/`。
- 配置事实必须先经过装配，再形成配置上下文契约视图供模块消费。

## 标准链路

```text
config/ → config_assembly → config_contexts → composition/runtime/workflow/observability/adapter
```

这条链路的含义是：

```text
配置事实
→ 配置装配
→ 配置上下文契约 / Config View
→ 模块消费
```

## 硬性规则

1. `config_contexts/` 必须被视为配置上下文契约包，而不是配置实现层。
2. `config_contexts/` 不得直接读取根目录 `config/`。
3. `config_contexts/` 不得执行配置文件加载与环境覆盖装配。
4. `config_contexts/` 不得承接业务执行逻辑。
5. 配置上下文对象必须表达清楚消费方、策略语义、护栏与不变式。
6. 新增 Config View 时，必须说明其配置事实来源、装配链路、消费模块与注入位置。
7. 修改 Config View 时，必须同步评估 behavior_contracts、schemas、contract_core、composition、runtime 与相关 adapter 的影响。

## 发布面口径

在 v0.5.0 单一发布面表达中，`config_contexts/` 应归入：

```text
v0.5.0 正式支撑面 / 公共契约支撑面
```

不应归入：

```text
历史遗留资产
配置实现层
独立主入口
```

## 一句话收口

`config_contexts/` 是认知引擎的配置上下文契约包，用于把装配后的配置载荷表达为模块可消费的契约化 Config View，使模块依赖稳定配置上下文，而不是直接依赖配置事实或配置装配过程。
