# 快速开始

本文档用于说明认知引擎当前公开版本 `v0.5.0` 的最小上手路径。

v0.5.0 是模块化包结构基线版本，重点验证公开主线的包结构、安装路径、基础导入路径和源码测试入口；不是完整产品化控制台或完整治理平台版本。

## 1. 安装

从 PyPI 安装：

```bash
pip install cognition-engine
```

或从源码安装：

```bash
git clone https://github.com/peacock-lab/cognition-engine.git
cd cognition-engine
pip install .
```

## 2. 验证安装

执行 v0.5.0 主线包导入 smoke 验证：

```bash
python -c "import contract_core, runtime_container, adk_adapter, observability_hub; print('cognition-engine v0.5.0 import ok')"
```

预期结果：命令能够正常导入 v0.5.0 主线包，并输出导入成功提示。

## 3. 源码测试

如需在源码开发环境中运行测试，可执行：

```bash
pytest
```

## 4. 当前版本适用范围

v0.5.0 适合用于：

1. 查看认知引擎当前公开包结构；
2. 验证模块化源码布局；
3. 检查包级导入路径；
4. 理解运行时、适配器、观测、契约、配置与控制面能力的结构基础。

## 5. 当前版本不适合用于

v0.5.0 暂不适合作为：

1. 完整生产级智能体治理平台；
2. 完整低代码控制台；
3. 完整多智能体运行时；
4. 完整 ADK 替代框架；
5. 完整模型调度平台。

## 6. 文档入口

- 项目首页：`README.md`
- 版本历史：`CHANGELOG.md`
- 版本发布说明：`v0.5.0-release-note.md`
