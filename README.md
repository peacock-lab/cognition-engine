# 认知引擎

认知引擎是一个面向 AI 协作研发场景的治理型运行控制面项目。

当前公开版本：`v0.5.3`

v0.5.3 是认知引擎在 `v0.5.1` 发布工程补丁之后的发布治理准备能力增强版本。本版本重点增强发布材料组织、发布前取证、发布流程检查点与发布准备过程中的人工授权边界，为后续更稳定的受控发布流程提供基础。

## 当前版本定位

v0.5.3 聚焦于发布治理准备能力增强，重点包括：

1. 将根包与 10 个子包版本同步到 `0.5.3`；
2. 将根包依赖同步到 `cognition-engine-*==0.5.3`；
3. 固化 PyPI 目标版本存在性检查；
4. 固化发布 token 环境变量轻量检查；
5. 固化 PyPI 发布后安装复验；
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
uv pip install --prerelease=allow cognition-engine==0.5.3
```

说明：v0.5.3 当前依赖 `google-adk>=2.0.0b1`，安装时需要允许预发布依赖解析。

或从源码安装：

```bash
git clone https://github.com/peacock-lab/cognition-engine.git
cd cognition-engine
pip install .
```

## 最小验证路径

完成安装后，可执行 v0.5.3 主线包导入 smoke 验证：

```bash
python -c "import contract_core, runtime_container, adk_adapter, observability_hub; print('cognition-engine 0.5.3 import ok')"
```

如需在源码开发环境中运行测试，可执行：

```bash
pytest
```

## 当前能力边界

v0.5.3 主要增强发布治理准备能力与发布前材料组织能力，不承诺完整产品化运行时平台。

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
