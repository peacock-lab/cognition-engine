#!/usr/bin/env python3
"""认知引擎多包发布前检查与本地构建验证脚本。

首轮只实现 check-only / build-only / dry-run。
真实上传、tag、GitHub Release 与 token 使用均不在本轮执行。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path


ROOT_DISTRIBUTION = "cognition-engine"


@dataclass(frozen=True)
class PackageSpec:
    path: str
    distribution: str
    token_env: str

    @property
    def project_dir(self) -> Path:
        return Path(self.path)


SUBPACKAGES: tuple[PackageSpec, ...] = (
    PackageSpec(
        "packages/schemas",
        "cognition-engine-schemas",
        "TWINE_TOKEN_COGNITION_ENGINE_SCHEMAS",
    ),
    PackageSpec(
        "packages/behavior_contracts",
        "cognition-engine-behavior-contracts",
        "TWINE_TOKEN_COGNITION_ENGINE_BEHAVIOR_CONTRACTS",
    ),
    PackageSpec(
        "packages/config_contexts",
        "cognition-engine-config-contexts",
        "TWINE_TOKEN_COGNITION_ENGINE_CONFIG_CONTEXTS",
    ),
    PackageSpec(
        "packages/config_assembly",
        "cognition-engine-config-assembly",
        "TWINE_TOKEN_COGNITION_ENGINE_CONFIG_ASSEMBLY",
    ),
    PackageSpec(
        "packages/runtime",
        "cognition-engine-runtime",
        "TWINE_TOKEN_COGNITION_ENGINE_RUNTIME",
    ),
    PackageSpec(
        "packages/composition",
        "cognition-engine-composition",
        "TWINE_TOKEN_COGNITION_ENGINE_COMPOSITION",
    ),
    PackageSpec(
        "packages/contract_core",
        "cognition-engine-contract-core",
        "TWINE_TOKEN_COGNITION_ENGINE_CONTRACT_CORE",
    ),
    PackageSpec(
        "packages/adk_adapter",
        "cognition-engine-adk-adapter",
        "TWINE_TOKEN_COGNITION_ENGINE_ADK_ADAPTER",
    ),
    PackageSpec(
        "packages/observability_hub",
        "cognition-engine-observability-hub",
        "TWINE_TOKEN_COGNITION_ENGINE_OBSERVABILITY_HUB",
    ),
    PackageSpec(
        "packages/runtime_container",
        "cognition-engine-runtime-container",
        "TWINE_TOKEN_COGNITION_ENGINE_RUNTIME_CONTAINER",
    ),
)

ROOT_PACKAGE = PackageSpec(".", ROOT_DISTRIBUTION, "TWINE_TOKEN_COGNITION_ENGINE")
ACCOUNT_FALLBACK_TOKEN_ENV = "TWINE_TOKEN_COGNITION_ENGINE_ACCOUNT_FALLBACK"
ALL_PACKAGES: tuple[PackageSpec, ...] = (*SUBPACKAGES, ROOT_PACKAGE)


@dataclass
class Check:
    status: str
    item: str
    detail: str = ""
    blocking: bool = False


class ReleaseScriptError(RuntimeError):
    """脚本执行失败。"""


def print_check(check: Check) -> None:
    detail = f" - {check.detail}" if check.detail else ""
    print(f"{check.status} {check.item}{detail}")


def emit_section(title: str) -> None:
    print()
    print(f"== {title} ==")


def run_command(
    command: list[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if check and result.returncode != 0:
        joined = " ".join(command)
        raise ReleaseScriptError(f"命令失败({result.returncode}): {joined}")
    return result


def git_output(args: list[str], root: Path) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def load_pyproject(project_dir: Path) -> dict:
    path = project_dir / "pyproject.toml"
    with path.open("rb") as file:
        return tomllib.load(file)


def project_name(pyproject: dict) -> str | None:
    return pyproject.get("project", {}).get("name")


def project_version(pyproject: dict) -> str | None:
    return pyproject.get("project", {}).get("version")


def project_readme(pyproject: dict) -> object:
    return pyproject.get("project", {}).get("readme")


def project_dependencies(pyproject: dict) -> list[str]:
    dependencies = pyproject.get("project", {}).get("dependencies", [])
    return [item for item in dependencies if isinstance(item, str)]


def dependency_matches_version(dependency: str, distribution: str, version: str) -> bool:
    return dependency == f"{distribution}=={version}"


def repo_root_from_git(cwd: Path) -> Path | None:
    top_level = git_output(["rev-parse", "--show-toplevel"], cwd)
    if top_level is None:
        return None
    return Path(top_level).resolve()


def check_project_root(root: Path) -> list[Check]:
    checks: list[Check] = []
    git_root = repo_root_from_git(root)
    if git_root == root.resolve() and (root / "pyproject.toml").is_file():
        checks.append(Check("OK", "项目根目录", str(root)))
    else:
        detail = "当前目录不是 git 项目根目录，或缺少 pyproject.toml"
        checks.append(Check("BLOCK", "项目根目录", detail, True))
    return checks


def check_git_state(root: Path) -> list[Check]:
    checks: list[Check] = []

    branch = git_output(["branch", "--show-current"], root)
    if branch == "main":
        checks.append(Check("OK", "当前分支", "main"))
    else:
        checks.append(Check("BLOCK", "当前分支", f"当前为 {branch or '<unknown>'}", True))

    status = git_output(["status", "--short"], root)
    if status == "":
        checks.append(Check("OK", "git status --short", "工作区干净"))
    else:
        checks.append(Check("BLOCK", "git status --short", "工作区存在未提交变更", True))
        for line in status.splitlines():
            print(f"BLOCK dirty: {line}")

    local = git_output(["rev-parse", "--verify", "main"], root)
    remote = git_output(["rev-parse", "--verify", "origin/main"], root)
    if not local or not remote:
        checks.append(Check("BLOCK", "main 与 origin/main 同步", "无法解析 main 或 origin/main", True))
    elif local != remote:
        detail = f"main={local[:12]} origin/main={remote[:12]}"
        checks.append(Check("BLOCK", "main 与 origin/main 同步", detail, True))
    else:
        checks.append(Check("OK", "main 与 origin/main 同步", local[:12]))

    return checks


def check_versions(root: Path, version: str) -> list[Check]:
    checks: list[Check] = []

    for package in ALL_PACKAGES:
        pyproject = load_pyproject(root / package.project_dir)
        name = project_name(pyproject)
        actual_version = project_version(pyproject)
        label = f"{package.distribution} 版本"
        if name != package.distribution:
            detail = f"pyproject name={name!r}，期望 {package.distribution!r}"
            checks.append(Check("BLOCK", label, detail, True))
        elif actual_version == version:
            checks.append(Check("OK", label, version))
        else:
            detail = f"当前 {actual_version!r}，目标 {version!r}"
            checks.append(Check("BLOCK", label, detail, True))

    root_pyproject = load_pyproject(root)
    root_dependencies = project_dependencies(root_pyproject)
    for package in SUBPACKAGES:
        label = f"根包依赖 {package.distribution}"
        if any(dependency_matches_version(dep, package.distribution, version) for dep in root_dependencies):
            checks.append(Check("OK", label, f"=={version}"))
        else:
            expected = f"{package.distribution}=={version}"
            checks.append(Check("BLOCK", label, f"缺少 {expected}", True))

    return checks


def check_metadata(root: Path) -> list[Check]:
    checks: list[Check] = []

    for package in SUBPACKAGES:
        package_dir = root / package.project_dir
        readme = package_dir / "README.md"
        if readme.is_file():
            checks.append(Check("OK", f"{package.path}/README.md", "存在"))
        else:
            checks.append(Check("BLOCK", f"{package.path}/README.md", "缺失", True))

        pyproject = load_pyproject(package_dir)
        if project_readme(pyproject) == "README.md":
            checks.append(Check("OK", f"{package.distribution} readme", 'readme = "README.md"'))
        else:
            checks.append(Check("BLOCK", f"{package.distribution} readme", "未配置 README.md", True))

    root_pyproject = load_pyproject(root)
    setuptools = root_pyproject.get("tool", {}).get("setuptools", {})
    packages = setuptools.get("packages")
    py_modules = setuptools.get("py-modules")
    if packages == [] and py_modules == []:
        checks.append(Check("OK", "根聚合包 setuptools", "packages = []，py-modules = []"))
        checks.append(Check("OK", "legacy cognition_engine shell", "根包不会发布 legacy shell"))
    else:
        detail = f"packages={packages!r}, py-modules={py_modules!r}"
        checks.append(Check("BLOCK", "根聚合包 setuptools", detail, True))
        checks.append(Check("BLOCK", "legacy cognition_engine shell", "根包可能发布代码包", True))

    return checks


def check_tokens() -> list[Check]:
    checks: list[Check] = []
    for package in ALL_PACKAGES:
        if os.environ.get(package.token_env):
            checks.append(Check("OK", f"token env exists: {package.token_env}"))
        else:
            checks.append(Check("MISS", f"token env: {package.token_env}", "首轮不阻断 check-only"))

    if os.environ.get(ACCOUNT_FALLBACK_TOKEN_ENV):
        checks.append(
            Check(
                "MISS",
                f"account fallback token env exists: {ACCOUNT_FALLBACK_TOKEN_ENV}",
                "默认不得使用账号级兜底 token",
            )
        )
    else:
        checks.append(Check("OK", f"account fallback token env absent: {ACCOUNT_FALLBACK_TOKEN_ENV}"))
    return checks


def run_check_only(root: Path, version: str) -> int:
    emit_section("发布前检查")
    print(f"目标版本: {version}")

    all_checks: list[Check] = []
    check_steps = (
        ("项目根目录", lambda: check_project_root(root)),
        ("git 状态", lambda: check_git_state(root)),
        ("版本一致性", lambda: check_versions(root, version)),
        ("PyPI 元数据", lambda: check_metadata(root)),
        ("token 环境变量", check_tokens),
    )
    for title, collect_checks in check_steps:
        emit_section(title)
        checks = collect_checks()
        all_checks.extend(checks)
        for check in checks:
            print_check(check)

    blocking = [check for check in all_checks if check.blocking]
    emit_section("结论")
    if blocking:
        print(f"BLOCK check-only: {len(blocking)} 个阻断项")
        return 1
    print("OK check-only: 发布前检查通过；MISS token 项仅用于提示，首轮不执行上传")
    return 0


def safe_build_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for name in ("dist", "build"):
        paths.append(root / name)
    paths.extend(root.glob("*.egg-info"))

    packages_dir = root / "packages"
    for package_dir in packages_dir.iterdir() if packages_dir.is_dir() else []:
        if not package_dir.is_dir():
            continue
        paths.extend((package_dir / name for name in ("dist", "build")))
        paths.extend(package_dir.glob("*.egg-info"))

    return sorted(set(paths), key=lambda path: str(path))


def clean_build_artifacts(root: Path) -> None:
    removed = 0
    for path in safe_build_paths(root):
        if path.is_dir():
            shutil.rmtree(path)
            print(f"OK clean: {path.relative_to(root)}")
            removed += 1
        elif path.exists():
            path.unlink()
            print(f"OK clean: {path.relative_to(root)}")
            removed += 1
    if removed == 0:
        print("OK clean: 无构建产物残留")


def artifact_files(project_dir: Path) -> list[Path]:
    dist_dir = project_dir / "dist"
    if not dist_dir.is_dir():
        return []
    return sorted(path for path in dist_dir.iterdir() if path.is_file())


def assert_no_twine_warning(output: str, package: PackageSpec) -> None:
    normalized = output.upper()
    if "WARNING" in normalized or "WARNINGS" in normalized:
        raise ReleaseScriptError(f"twine check 出现 warning: {package.distribution}")


def build_package(root: Path, package: PackageSpec, python: Path) -> None:
    project_dir = root / package.project_dir
    print(f"OK build start: {package.distribution} ({package.path})")
    run_command([str(python), "-m", "build", "--outdir", "dist"], cwd=project_dir)

    artifacts = artifact_files(project_dir)
    if not artifacts:
        raise ReleaseScriptError(f"构建产物缺失: {package.distribution}")

    relative_artifacts = ", ".join(str(path.relative_to(root)) for path in artifacts)
    print(f"OK build artifacts: {relative_artifacts}")

    result = run_command(
        [str(python), "-m", "twine", "check", *[str(path) for path in artifacts]],
        cwd=root,
    )
    assert_no_twine_warning(result.stdout or "", package)
    print(f"OK twine check: {package.distribution}")


def build_wheelhouse(root: Path, version: str) -> Path:
    wheelhouse = Path(tempfile.gettempdir()) / f"ce-{version}-wheelhouse"
    if wheelhouse.exists():
        shutil.rmtree(wheelhouse)
    wheelhouse.mkdir(parents=True)

    for package in ALL_PACKAGES:
        project_dir = root / package.project_dir
        for artifact in artifact_files(project_dir):
            shutil.copy2(artifact, wheelhouse / artifact.name)

    copied = sorted(path.name for path in wheelhouse.iterdir() if path.is_file())
    if not copied:
        raise ReleaseScriptError("wheelhouse 未收集到任何构建产物")

    print(f"OK wheelhouse: {wheelhouse}")
    for name in copied:
        print(f"OK wheelhouse artifact: {name}")
    return wheelhouse


def run_smoke(root: Path, version: str, wheelhouse: Path, python: Path) -> None:
    uv = shutil.which("uv")
    if not uv:
        raise ReleaseScriptError("未找到 uv，无法执行本地 wheelhouse 安装 smoke")

    with tempfile.TemporaryDirectory(prefix=f"ce-{version}-smoke-") as tmp:
        venv_dir = Path(tmp) / ".venv"
        run_command([uv, "venv", "--python", str(python), str(venv_dir)], cwd=root)
        smoke_python = venv_dir / "bin" / "python"
        run_command(
            [
                uv,
                "pip",
                "install",
                "--python",
                str(smoke_python),
                "--prerelease=allow",
                "--find-links",
                str(wheelhouse),
                f"{ROOT_DISTRIBUTION}=={version}",
            ],
            cwd=root,
        )
        smoke_code = (
            "import contract_core, runtime_container, adk_adapter, observability_hub; "
            f"print('cognition-engine {version} import ok')"
        )
        run_command([str(smoke_python), "-c", smoke_code], cwd=root)
    print("OK wheelhouse smoke: 本地安装与主线 import 通过")


def versions_match_target(root: Path, version: str) -> bool:
    return all(project_version(load_pyproject(root / package.project_dir)) == version for package in ALL_PACKAGES)


def run_build_only(root: Path, version: str, python: Path) -> int:
    emit_section("本地构建验证")
    print(f"目标版本: {version}")
    if not versions_match_target(root, version):
        print("BLOCK build-only: 当前 pyproject 版本与目标版本不一致，未执行构建")
        print("BLOCK build-only: 不会为了通过验证而修改版本号")
        return 1

    wheelhouse: Path | None = None
    try:
        emit_section("清理构建产物")
        clean_build_artifacts(root)

        emit_section("构建子包")
        for package in SUBPACKAGES:
            build_package(root, package, python)

        emit_section("构建根聚合包")
        build_package(root, ROOT_PACKAGE, python)

        emit_section("本地 wheelhouse smoke")
        wheelhouse = build_wheelhouse(root, version)
        run_smoke(root, version, wheelhouse, python)

        emit_section("结论")
        print("OK build-only: 构建、twine check、wheelhouse smoke 全部通过")
        return 0
    except ReleaseScriptError as error:
        emit_section("结论")
        print(f"BLOCK build-only: {error}")
        return 1
    finally:
        emit_section("最终清理构建产物")
        clean_build_artifacts(root)
        if wheelhouse and wheelhouse.exists():
            shutil.rmtree(wheelhouse)
            print(f"OK clean wheelhouse: {wheelhouse}")


def run_dry_run(version: str) -> int:
    emit_section("dry-run 发布计划")
    print(f"目标版本: {version}")

    emit_section("计划检查项")
    for item in (
        "项目根目录",
        "当前分支 main",
        "git status --short 干净",
        "main 与 origin/main 同步",
        "根包与 10 个子包版本一致",
        "根包依赖的子包版本一致",
        "10 个子包 README.md 与 readme 元数据",
        "根聚合包 packages = [] 且 py-modules = []",
        "token 环境变量存在性，只显示变量名，不显示内容",
    ):
        print(f"OK plan check: {item}")

    emit_section("子包发布顺序")
    for index, package in enumerate(SUBPACKAGES, start=1):
        print(f"OK plan order {index:02d}: {package.distribution} ({package.path})")
    print(f"OK plan order 11: {ROOT_PACKAGE.distribution} ({ROOT_PACKAGE.path})")

    emit_section("token 环境变量名称")
    for package in ALL_PACKAGES:
        print(f"OK plan token env: {package.distribution} -> {package.token_env}")
    print(f"OK plan account fallback env: {ACCOUNT_FALLBACK_TOKEN_ENV} (默认禁用)")

    emit_section("首轮不会执行的动作")
    for item in (
        "不会上传 PyPI",
        "不会创建或移动 tag",
        "不会创建 GitHub Release",
        "不会读取或输出 token 内容",
        "不会修改版本号或发布材料",
    ):
        print(f"BLOCK not implemented: {item}")

    emit_section("结论")
    print("OK dry-run: 仅打印计划，未执行构建或不可逆发布动作")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="认知引擎多包发布前检查与本地构建验证脚本。"
    )
    parser.add_argument("--version", required=True, help="目标发布版本，例如 0.5.1")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-only", action="store_true", help="只做发布前检查")
    mode.add_argument("--build-only", action="store_true", help="只做本地构建与 smoke")
    mode.add_argument("--dry-run", action="store_true", help="只打印发布计划")
    mode.add_argument("--upload", action="store_true", help="首轮预留；真实上传未实现")
    mode.add_argument("--post-verify", action="store_true", help="首轮预留；PyPI 复验未实现")
    parser.add_argument(
        "--allow-account-fallback",
        action="store_true",
        help="首轮预留；默认不得使用账号级兜底 token",
    )
    parser.add_argument("--yes", action="store_true", help="首轮预留；不会触发上传确认")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path.cwd().resolve()
    python = Path(sys.executable)

    if args.upload or args.post_verify:
        emit_section("未实现动作")
        print("BLOCK upload/post-verify: 首轮未实现真实上传或 PyPI 发布后复验")
        print("BLOCK upload/post-verify: 未读取 token，未上传 PyPI，未创建 tag，未创建 GitHub Release")
        return 1

    if args.allow_account_fallback:
        print("MISS allow-account-fallback: 参数已识别，但首轮不会使用账号级兜底 token")
    if args.yes:
        print("MISS yes: 参数已识别，但首轮没有需要确认的真实上传动作")

    if args.dry_run:
        return run_dry_run(args.version)
    if args.check_only:
        return run_check_only(root, args.version)
    if args.build_only:
        return run_build_only(root, args.version, python)

    print("BLOCK 参数错误: 未选择有效模式")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
