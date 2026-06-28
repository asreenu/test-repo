from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_NAME = "config.yaml"


def expand_path(path: str) -> Path:
    return Path(os.path.expanduser(path)).resolve()


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent / DEFAULT_CONFIG_NAME
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    env_map = {
        "MIN_MEMORY_GB": ("search", "min_memory_gb", int),
        "MAX_PRICE_USD": ("search", "max_price_usd", int),
        "NOTIFY_ONLY_NEW": ("notifications", "notify_only_new", _env_bool),
        "MACOS_NOTIFY": ("notifications", "macos", _env_bool),
    }
    for env_key, (section, key, caster) in env_map.items():
        if env_key in os.environ:
            data.setdefault(section, {})[key] = caster(os.environ[env_key])
    return data


def _env_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def config_summary(config: dict[str, Any]) -> dict[str, Any]:
    search = config.get("search", {})
    enabled_sources = [
        name
        for name, src in config.get("sources", {}).items()
        if src.get("enabled", True)
    ]
    return {
        "min_memory_gb": search.get("min_memory_gb", 128),
        "max_price_usd": search.get("max_price_usd"),
        "enabled_sources": enabled_sources,
    }
