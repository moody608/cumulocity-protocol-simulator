from pathlib import Path
from typing import Any

import yaml

from core.models.base import AssetConfig


def _require_str(value: Any, field_name: str) -> str:
    if value is None:
        raise ValueError(f"Missing required field: {field_name}")
    return str(value)


def _require_int(value: Any, field_name: str) -> int:
    if value is None:
        raise ValueError(f"Missing required field: {field_name}")
    return int(value)


def _parse_asset(raw: dict[str, Any]) -> AssetConfig:
    return AssetConfig(
        device_id=_require_str(raw.get("deviceId"), "deviceId"),
        device_class=_require_str(raw.get("deviceClass"), "deviceClass"),
        protocol=_require_str(raw.get("protocol"), "protocol"),
        name=_require_str(raw.get("name"), "name"),
        interval_sec=_require_int(raw.get("intervalSec"), "intervalSec"),
        profile=dict(raw.get("profile", {})),
        metadata=dict(raw.get("metadata", {})),
    )


def load_assets(path: str | Path) -> list[AssetConfig]:
    path = Path(path)

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    raw_assets = data.get("assets", [])
    if not isinstance(raw_assets, list):
        raise ValueError("Expected 'assets' to be a list")

    return [_parse_asset(asset) for asset in raw_assets]