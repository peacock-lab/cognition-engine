# Cognition System / 认知系统

[English](README.md) | 简体中文

Cognition System 是面向外部只读资料问答、受控 CLI 工作流、配置装配、运行编排、证据观测和产品入口实验的 Python 3.14 多包发布候选。

当前公开版本：`v0.8.0`

`v0.8.0` 发布候选包含 `cognition-system` 根聚合包和 18 个 `cognition-system-*` 子包。当前候选用于公仓本地发布面验证，不表示已经完成 PyPI 正式发布。

## 安装

```bash
python -m pip install --upgrade pip
python -m pip install "cognition-system==0.8.0"
```

如果使用 uv：

```bash
uv pip install "cognition-system==0.8.0"
```

## 验证

```bash
python -c "import importlib.metadata as m; print(m.version('cognition-system'))"
python -c "import importlib.metadata as m; print('cognition-system', m.version('cognition-system'), 'import ok')"
cognition --help
```

预期 smoke 文本：

```text
cognition-system 0.8.0 import ok
```

## CLI

公开控制台命令是：

```bash
cognition
```

主要试用入口是：

```bash
cognition external-readonly ask --guided
```

引导模式会询问只读资料来源、问题、模型别名、联网和模型调用授权，以及外部 provider 的凭据处理方式。

可用模型别名：

1. `deepseek`：适合低硬件用户的线上 DeepSeek V4 Flash 路径。
2. `gemma4`：适合本地模型用户的 Ollama / Gemma4 路径。

自动化、CI 和 JSON 输出场景应显式传入完整参数，不使用 `--guided`。`cognition external-readonly ask --guided --json` 应被阻断。

## 配置

仓库级 `config/` 目录不是独立发布包，也不会复制进公仓发布面。安装态默认配置资源由 `cognition-system-config-assembly` 通过 `config_assembly/default_config/` 携带。

需要时可创建用户侧配置目录：

```bash
cognition config init --config-root ./config
```

## 包结构

`v0.8.0` 候选包含 19 个 distribution：

1. `cognition-system`
2. `cognition-system-schemas`
3. `cognition-system-behavior-contracts`
4. `cognition-system-config-assembly`
5. `cognition-system-config-contexts`
6. `cognition-system-runtime`
7. `cognition-system-contract-core`
8. `cognition-system-adk-adapter`
9. `cognition-system-observability-hub`
10. `cognition-system-cognition-agent`
11. `cognition-system-cognition-governance`
12. `cognition-system-composition`
13. `cognition-system-external-readonly`
14. `cognition-system-runtime-container`
15. `cognition-system-task-workflows`
16. `cognition-system-product-gateway`
17. `cognition-system-product-runtime-assembly`
18. `cognition-system-product-application-assembly`
19. `cognition-system-cli`

## 安全边界

CLI 保持以下边界：

1. 不静默联网。
2. 不静默调用 live model。
3. 不静默读取或保存 provider key。
4. 不在产品输出中暴露 raw HTML、raw provider response、response headers、traceback 或 provider key。
5. 不接受任意模型名，只接受已配置别名。
6. 本候选验证不包含 PyPI 上传、Git tag、GitHub Release 或远程 push。

运行产物应留在本地忽略的 `outputs/` 目录中，不属于公开发布面。

## 文档

- 快速开始：[QUICKSTART.zh-CN.md](QUICKSTART.zh-CN.md)
- 英文快速开始：[QUICKSTART.md](QUICKSTART.md)
- 版本历史：[CHANGELOG.md](CHANGELOG.md)
- 源码仓库：https://github.com/peacock-lab/cognition-engine
