# config_assembly

## 目录定位

`config_assembly/` 是认知引擎的配置装配支撑包，属于 v0.5.0 正式支撑面中的配置装配支撑。

它位于配置事实与配置上下文契约之间：

```text
config/ = 配置事实来源
config_assembly/ = 配置装配与环境覆盖
config_contexts/ = 配置上下文契约与 Config View
```

本包负责从项目级配置事实来源 `config/` 读取基础配置、环境配置与模板资产，并装配为 `config_contexts/` 可消费的标准配置载荷。

本包不是配置事实来源，也不是配置上下文契约包，更不是行为契约或数据契约包。

本包回答的问题是：

**`config/` 中的配置事实如何被读取、覆盖、归一并形成可供配置上下文契约层消费的标准配置载荷。**

## 职责边界

本包负责：

1. 读取 `config/base/` 基础配置。
2. 读取 `config/env/` 环境差异配置。
3. 读取必要的配置模板资产。
4. 按确定规则执行覆盖、归一与装配。
5. 输出供 `config_contexts/` 消费的标准配置载荷。
6. 保证配置事实进入运行时前经过统一装配链路。
7. 支撑 `contract_core` 背后的配置上下文契约链路。

本包不负责：

1. 不负责充当新的集中配置管理入口。
2. 不负责替代 `config/` 的配置事实来源职责。
3. 不负责定义模块最终消费的 Config View。
4. 不负责定义行为契约。
5. 不负责定义普通跨模块数据契约。
6. 不负责业务模块实现逻辑。
7. 不负责系统级装配。
8. 不负责外部 SDK 调用。

## 与其他层的关系

### 与 config 的关系

- `config/` 是配置事实来源。
- `config_assembly/` 是读取并装配 `config/` 的标准代码模块。
- 除明确允许的配置装配入口外，业务模块不得直接读取根目录 `config/`。

### 与 config_contexts 的关系

- `config_contexts/` 是配置上下文契约包。
- `config_assembly/` 输出标准配置载荷。
- `config_contexts/` 基于标准配置载荷定义模块消费级配置上下文契约与 Config View。
- `config_assembly/` 不定义最终 Config View，也不承接配置上下文契约职责。

### 与 contract_core 的关系

- `contract_core/` 是公共契约入口。
- `config_contexts/` 是 `contract_core` 背后的配置上下文契约支撑面。
- `config_assembly/` 支撑配置上下文契约链路，但自身不是公共契约入口，也不是配置上下文契约包。

### 与 behavior_contracts / schemas 的关系

- `behavior_contracts/` 负责行为契约。
- `schemas/` 负责公共数据契约。
- `config_assembly/` 可使用稳定数据契约表达配置载荷，但不得承接行为契约职责，也不得替代 `schemas/` 的公共数据契约职责。

### 与 composition / runtime 的关系

- `composition/` 可以调用 `config_assembly/` 获取标准配置载荷，并通过 `config_contexts/` 构建模块可消费的配置视图。
- `runtime/` 只消费被注入的配置上下文，不直接读取 `config/`，也不承担配置装配。
- `config_assembly/` 不承担运行组织职责。

## 标准链路

```text
config/ → config_assembly → config_contexts → composition/runtime/adapter/observability
```

这条链路的含义是：

```text
配置事实
→ 配置装配与环境覆盖
→ 配置上下文契约 / Config View
→ 模块消费
```

## 硬性规则

1. `config_assembly/` 是读取根目录 `config/` 的标准配置装配模块。
2. 业务模块不得绕过 `config_assembly/` 直接读取配置事实。
3. `config_assembly/` 不定义模块最终消费的 Config View。
4. `config_assembly/` 不承接配置上下文契约职责。
5. `config_assembly/` 不承接业务执行逻辑。
6. 配置覆盖与装配规则必须确定、可测试、可审计。
7. 任何新增配置读取入口必须说明其与 `config/` 配置事实来源的关系。
8. 修改配置装配规则时，必须同步评估 `config_contexts/`、`composition/`、`runtime/` 以及相关 adapter 的影响。

## 发布面口径

在 v0.5.0 单一发布面表达中，`config_assembly/` 应归入：

```text
v0.5.0 正式支撑面 / 配置装配支撑面
```

不应归入：

```text
历史遗留资产
独立主入口
配置上下文契约包
行为契约包
数据契约包
运行组织层
```

## 一句话收口

`config_assembly/` 是认知引擎的配置装配支撑包，用于把 `config/` 中的配置事实装配为标准配置载荷，再交给 `config_contexts/` 形成契约化 Config View，防止业务模块各自读取配置、各自拼装差异、各自制造默认值。
