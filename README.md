# 认知引擎

认知引擎是一个面向 AI 协作研发场景的治理型运行控制面项目。

当前公开版本：`v0.5.1`

v0.5.1 是认知引擎在 `v0.5.0` 模块化包结构基线之后的发布工程补丁版本。本版本重点补强 PyPI 包元数据、子包发布说明接入、多包构建检查与公开安装验证路径，为后续更稳定的发布流程和运行控制面能力演进提供基础。

## 当前版本定位

v0.5.1 聚焦于发布工程补丁，重点包括：

1. 将 10 个子包的 README 接入 PyPI long_description；
2. 清零子包 `twine check` 中的 long_description 相关 warning；
3. 将根包与 10 个子包版本同步到 `0.5.1`；
4. 将根包依赖同步到 `cognition-engine-*==0.5.1`；
5. 保持根聚合包与子包的模块化发布结构；
6. 保持公开主线为模块化包结构，不扩大为完整产品化运行时平台。

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
uv pip install --prerelease=allow cognition-engine==0.5.1
```

说明：v0.5.1 当前依赖 `google-adk>=2.0.0b1`，安装时需要允许预发布依赖解析。

或从源码安装：

```bash
git clone https://github.com/peacock-lab/cognition-engine.git
cd cognition-engine
pip install .
```

## 最小验证路径

完成安装后，可执行 v0.5.1 主线包导入 smoke 验证：

```bash
python -c "import contract_core, runtime_container, adk_adapter, observability_hub; print('cognition-engine 0.5.1 import ok')"
```

如需在源码开发环境中运行测试，可执行：

```bash
pytest
```

## 当前能力边界

v0.5.1 主要修补公开包发布元数据、构建检查和安装验证基础，不承诺完整产品化运行时平台。

当前版本不承诺：

1. 完整智能体治理闭环；
2. 完整控制台或可视化后台；
3. 完整生产级多模型调度；
4. 完整企业级配置中心；
5. 完整 ADK 能力封装替代；
6. 自动 PyPI 发布、自动 tag 或自动 GitHub Release。

## 文档入口

- 快速开始：`QUICKSTART.md`
- 版本历史：`CHANGELOG.md`
- 版本发布记录：GitHub Releases
- 包发布记录：PyPI
