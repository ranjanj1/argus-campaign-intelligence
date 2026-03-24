from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict

import yaml
from deepmerge import always_merger

from argus.paths import SETTINGS_DIR
from argus.settings.settings import Settings

_ENV_VAR_RE = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")


def _substitute_env_vars(value: Any) -> Any:
    """Recursively replace ${VAR:default} placeholders with environment variable values."""
    if isinstance(value, str):
        def _replace(match: re.Match) -> str:
            var_name = match.group(1)
            default = match.group(2) if match.group(2) is not None else ""
            return os.environ.get(var_name, default)
        return _ENV_VAR_RE.sub(_replace, value)
    if isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute_env_vars(v) for v in value]
    return value


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open() as f:
        return yaml.safe_load(f) or {}


def load_settings() -> Settings:
    """
    Load and merge config:
    1. settings.yaml          (base)
    2. settings-{profile}.yaml for each profile in ARGUS_PROFILES (comma-separated)
    3. Substitute ${ENV_VAR:default} placeholders
    4. Validate via Pydantic Settings
    """
    base = _load_yaml(SETTINGS_DIR / "settings.yaml")

    profiles = os.environ.get("ARGUS_PROFILES", "")
    for profile in [p.strip() for p in profiles.split(",") if p.strip()]:
        override = _load_yaml(SETTINGS_DIR / f"settings-{profile}.yaml")
        if override:
            base = always_merger.merge(base, override)

    base = _substitute_env_vars(base)
    return Settings(**base)
