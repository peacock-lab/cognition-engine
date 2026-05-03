"""Runtime configuration assembly for Cognition Engine."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class RuntimeConfigAssemblyError(RuntimeError):
    """Raised when runtime configuration assembly fails."""


class RuntimeConfigPayload(BaseModel):
    """Assembled runtime configuration payload."""

    model_config = ConfigDict(extra="forbid")

    source_root: str
    environment: str
    base_file: str
    env_file: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


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
