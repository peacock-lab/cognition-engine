# 认知引擎

认知引擎是一个面向 AI 协作研发场景的治理型运行控制面项目。

当前公开版本：`v0.5.0`

v0.5.0 是认知引擎的模块化包结构基线版本。本版本重点建立公开仓库的包级组织方式，明确核心能力区域与基础验证路径，为后续运行时、适配器、观测、契约、配置与控制面能力继续演进提供稳定基础。

## 当前版本定位

v0.5.0 聚焦于公开主线的结构基线，重点包括：

1. 建立 `packages/` 源码布局；
2. 明确主要包级能力边界；
3. 建立包级测试入口；
4. 验证构建、安装、依赖解析与基础导入路径；
5. 将当前公开主线收敛到模块化包结构基线。

## 当前包结构

当前公开主线包含以下主要能力区域：

- `contract_core`
- `runtime_container`
- `adk_adapter`
- `observability_hub`

同时包含以下支撑性结构：

- schemas
- behavior contracts
- configuration contexts
- configuration assembly
- runtime primitives
- composition

## 安装方式

从 PyPI 安装：

```bash
uv pip install --prerelease=allow cognition-engine
```

说明：v0.5.0 当前依赖 `google-adk>=2.0.0b1`，安装时需要允许预发布依赖解析。

或从源码安装：

```bash
git clone https://github.com/peacock-lab/cognition-engine.git
cd cognition-engine
pip install .
```

## 最小验证路径

完成安装后，可执行 v0.5.0 主线包导入 smoke 验证：

```bash
python -c "import contract_core, runtime_container, adk_adapter, observability_hub; print('cognition-engine v0.5.0 import ok')"
```

如需在源码开发环境中运行测试，可执行：

```bash
pytest
```

## 当前能力边界

v0.5.0 主要验证模块化包结构、包级边界和公开发布基础，不承诺完整产品化运行时平台。

当前版本不承诺：

1. 完整智能体治理闭环；
2. 完整控制台或可视化后台；
3. 完整生产级多模型调度；
4. 完整企业级配置中心；
5. 完整 ADK 能力封装替代。

## 文档入口

- 快速开始：`QUICKSTART.md`
- 版本历史：`CHANGELOG.md`
- 版本发布记录：GitHub Releases
- 包发布记录：PyPI
