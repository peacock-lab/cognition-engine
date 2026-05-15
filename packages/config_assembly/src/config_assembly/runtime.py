"""Runtime configuration assembly for Cognition System."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class RuntimeConfigAssemblyError(RuntimeError):
    """Raised when runtime configuration assembly fails."""


@dataclass(frozen=True)
class ConfigInitFileStatus:
    """Status for one initialized configuration file."""

    relative_path: str
    status: str

    def to_json_dict(self) -> dict[str, str]:
        """Return a JSON-serializable status mapping."""

        return {
            "relative_path": self.relative_path,
            "status": self.status,
        }


@dataclass(frozen=True)
class ConfigInitResult:
    """Result of initializing a user-owned configuration root."""

    config_root: str
    source: str
    files: tuple[ConfigInitFileStatus, ...]

    def to_json_dict(self) -> dict[str, object]:
        """Return a JSON-serializable result mapping."""

        return {
            "config_root": self.config_root,
            "source": self.source,
            "files": [file.to_json_dict() for file in self.files],
        }


class RuntimeConfigPayload(BaseModel):
    """Assembled runtime configuration payload."""

    model_config = ConfigDict(extra="forbid")

    source_root: str
    environment: str
    base_file: str
    env_file: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


_DEFAULT_CONFIG_RESOURCE_ROOT = "default_config"
_DEFAULT_CONFIG_FILES: tuple[str, ...] = (
    "base/runtime.yaml",
    "templates/runtime.template.yaml",
)


def init_default_config_root(
    config_root: Path,
    *,
    overwrite: bool = False,
) -> ConfigInitResult:
    """Initialize a user-owned config root from packaged sanitized defaults."""

    root = config_root.expanduser()
    files: list[ConfigInitFileStatus] = []
    resource_root = resources.files("config_assembly").joinpath(
        _DEFAULT_CONFIG_RESOURCE_ROOT
    )

    for relative_path in _DEFAULT_CONFIG_FILES:
        resource_file = resource_root.joinpath(*relative_path.split("/"))
        target_file = root / relative_path
        target_file.parent.mkdir(parents=True, exist_ok=True)
        existed = target_file.exists()

        if existed and not overwrite:
            files.append(ConfigInitFileStatus(relative_path, "skipped"))
            continue

        target_file.write_text(resource_file.read_text(encoding="utf-8"), encoding="utf-8")
        files.append(
            ConfigInitFileStatus(
                relative_path,
                "overwritten" if existed else "created",
            )
        )

    return ConfigInitResult(
        config_root=str(root),
        source="package://config_assembly/default_config",
        files=tuple(files),
    )


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a YAML file into a dictionary."""

    if not path.exists():
        raise RuntimeConfigAssemblyError(f"Configuration file not found: {path}")

    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))

    if loaded is None:
        return {}

    if not isinstance(loaded, dict):
        raise RuntimeConfigAssemblyError(f"Configuration file must contain a mapping: {path}")

    return loaded


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic deep merge of base and override mappings."""

    result = deepcopy(base)

    for key, value in override.items():
        existing = result.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            result[key] = deep_merge(existing, value)
        else:
            result[key] = deepcopy(value)

    return result


def assemble_runtime_config_payload(
    config_root: Path,
    environment: str = "local",
) -> RuntimeConfigPayload:
    """Assemble runtime configuration payload from config/base and config/env."""

    base_file = config_root / "base" / "runtime.yaml"
    env_file = config_root / "env" / f"{environment}.yaml"

    base_payload = load_yaml_file(base_file)
    env_payload = load_yaml_file(env_file) if env_file.exists() else {}

    assembled_payload = deep_merge(base_payload, env_payload)

    return RuntimeConfigPayload(
        source_root=str(config_root),
        environment=environment,
        base_file=str(base_file),
        env_file=str(env_file) if env_file.exists() else None,
        payload=assembled_payload,
    )
