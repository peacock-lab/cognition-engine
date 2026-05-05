# 认知引擎

认知引擎是一个面向 AI 协作研发场景的治理型运行控制面项目。

当前公开版本：`v0.5.4`

v0.5.4 是认知引擎面向 Trusted Publishing 上线的发布工程增强版本。本版本重点上线公仓最小 PyPI publish workflow、完成 PyPI Trusted Publisher 配置链路，并保留 Keychain project token fallback 作为兜底路径。

## 当前版本定位

v0.5.4 聚焦于 Trusted Publishing 上线与发布工程可信闭环，重点包括：

1. 将根包与 10 个子包版本同步到 `0.5.4`；
2. 将根包依赖同步到 `cognition-engine-*==0.5.4`；
3. 上线公仓最小 PyPI publish workflow；
4. 完成 11 个 PyPI Trusted Publisher 配置链路；
5. 保留 Keychain project token fallback 作为发布兜底路径；
6. 固化公仓公开面边界检查；
7. 提供发布安全网总入口，用于统一聚合发布前与发布后检查结果。

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
uv pip install --prerelease=allow cognition-engine==0.5.4
```

说明：v0.5.4 当前依赖 `google-adk>=2.0.0b1`，安装时需要允许预发布依赖解析。

或从源码安装：

```bash
git clone https://github.com/peacock-lab/cognition-engine.git
cd cognition-engine
pip install .
```

## 最小验证路径

完成安装后，可执行 v0.5.4 主线包导入 smoke 验证：

```bash
python -c "import contract_core, runtime_container, adk_adapter, observability_hub; print('cognition-engine 0.5.4 import ok')"
```

如需在源码开发环境中运行测试，可执行：

```bash
pytest
```

## 当前能力边界

v0.5.4 主要增强 Trusted Publishing 上线与发布工程可信闭环能力，不承诺完整产品化运行时平台。

当前版本不承诺：

1. 完整智能体治理闭环；
2. 完整控制台或可视化后台；
3. 完整生产级多模型调度；
4. 完整企业级配置中心；
5. 完整 ADK 能力封装替代；
6. 自动 PyPI 上传、自动 tag 或自动 GitHub Release。

## 文档入口

- 快速开始：`QUICKSTART.md`
- 版本历史：`CHANGELOG.md`
- 版本发布记录：GitHub Releases
- 包发布记录：PyPI
