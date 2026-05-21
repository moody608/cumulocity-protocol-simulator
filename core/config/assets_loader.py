from pathlib import Path
from typing import Any

import yaml

from core.models.base import AssetConfig, Channel, LoraProtocolConfig, Lwm2mObjectModelConfig, Lwm2mProtocolConfig


def _require_str(value: Any, field_name: str) -> str:
    if value is None:
        raise ValueError(f"Missing required field: {field_name}")
    return str(value)


def _require_int(value: Any, field_name: str) -> int:
    if value is None:
        raise ValueError(f"Missing required field: {field_name}")
    return int(value)


def _parse_channels(profile: dict[str, Any]) -> list[Channel]:
    raw = profile.get("channels") or []
    channels = []
    for i, c in enumerate(raw):
        name = c.get("name")
        if name is None:
            raise ValueError(f"channels[{i}]: missing required field 'name'")
        min_val = c.get("min")
        if min_val is None:
            raise ValueError(f"channel '{name}': missing required field 'min'")
        max_val = c.get("max")
        if max_val is None:
            raise ValueError(f"channel '{name}': missing required field 'max'")
        channels.append(Channel(
            name=str(name),
            min=float(min_val),
            max=float(max_val),
            precision=int(c.get("precision", 2)),
        ))
    return channels


def _parse_lora_protocol_config(raw: dict[str, Any]) -> LoraProtocolConfig:
    return LoraProtocolConfig(
        deveui=_require_str(raw.get("deveui"), "protocolConfig.deveui"),
        server_uri=_require_str(raw.get("serverUri"), "protocolConfig.serverUri"),
        device_protocol_name=str(raw.get("deviceProtocolName", "iot-simulator LoRa SensorNode")),
        fport=int(raw.get("fport", 1)),
    )


def _parse_lwm2m_object_model(raw: dict[str, Any]) -> Lwm2mObjectModelConfig:
    return Lwm2mObjectModelConfig(
        include_device_object=bool(raw.get("includeDeviceObject", True)),
        include_location_object=bool(raw.get("includeLocationObject", False)),
        include_temperature_object=bool(raw.get("includeTemperatureObject", True)),
        temperature_instance_id=int(raw.get("temperatureInstanceId", 0)),
        send_mode=str(raw.get("sendMode", "observe")),
    )


def _parse_lwm2m_protocol_config(raw: dict[str, Any]) -> Lwm2mProtocolConfig:
    om_raw = raw.get("objectModel")
    return Lwm2mProtocolConfig(
        endpoint_id=_require_str(raw.get("endpointId"), "protocolConfig.endpointId"),
        server_uri=_require_str(raw.get("serverUri"), "protocolConfig.serverUri"),
        security_mode=_require_str(raw.get("securityMode"), "protocolConfig.securityMode"),
        psk_identity=raw.get("pskIdentity"),
        psk_key_hex=raw.get("pskKeyHex"),
        lifetime_sec=int(raw.get("lifetimeSec", 300)),
        binding_mode=str(raw.get("bindingMode", "U")),
        object_model=_parse_lwm2m_object_model(om_raw) if om_raw else None,
    )


def _parse_protocol_config(raw: dict[str, Any]) -> Any:
    pc = raw.get("protocolConfig")
    if pc is None:
        return None
    protocol = str(raw.get("protocol", "")).lower()
    if protocol == "lora":
        return _parse_lora_protocol_config(pc)
    if protocol == "lwm2m":
        return _parse_lwm2m_protocol_config(pc)
    return pc


def _parse_asset(raw: dict[str, Any]) -> AssetConfig:
    profile = dict(raw.get("profile", {}))
    return AssetConfig(
        device_id=_require_str(raw.get("deviceId"), "deviceId"),
        device_class=_require_str(raw.get("deviceClass"), "deviceClass"),
        protocol=_require_str(raw.get("protocol"), "protocol"),
        name=_require_str(raw.get("name"), "name"),
        interval_sec=_require_int(raw.get("intervalSec"), "intervalSec"),
        profile=profile,
        metadata=dict(raw.get("metadata", {})),
        protocol_config=_parse_protocol_config(raw),
        channels=_parse_channels(profile),
    )


def load_assets(path: str | Path) -> list[AssetConfig]:
    path = Path(path)

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    raw_assets = data.get("assets", [])
    if not isinstance(raw_assets, list):
        raise ValueError("Expected 'assets' to be a list")

    return [_parse_asset(asset) for asset in raw_assets]