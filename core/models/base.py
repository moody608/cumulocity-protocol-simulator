from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Channel:
    name: str
    min: float
    max: float
    precision: int = 2


@dataclass
class AssetConfig:
    device_id: str
    device_class: str
    protocol: str
    name: str
    interval_sec: int
    profile: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    protocol_config: Any | None = None
    channels: list[Channel] = field(default_factory=list)


@dataclass
class AlarmState:
    type: str
    text: str
    severity: str
    time: datetime
    status: str = "ACTIVE"
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AssetState:
    device_id: str
    device_class: str
    protocol: str
    timestamp: datetime
    identity: dict[str, Any]
    telemetry: dict[str, Any]
    operational: dict[str, Any]
    service: dict[str, Any]
    compliance: dict[str, Any]
    location: dict[str, Any] | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    alarms: list[AlarmState] = field(default_factory=list)


@dataclass
class LoraProtocolConfig:
    deveui: str
    server_uri: str
    device_protocol_name: str = "iot-simulator LoRa SensorNode"
    fport: int = 1


@dataclass
class Lwm2mObjectModelConfig:
    include_device_object: bool = True
    include_location_object: bool = False
    include_temperature_object: bool = True
    temperature_instance_id: int = 0
    send_mode: str = "observe"


@dataclass
class Lwm2mProtocolConfig:
    endpoint_id: str
    server_uri: str
    security_mode: str
    psk_identity: Optional[str] = None
    psk_key_hex: Optional[str] = None
    lifetime_sec: int = 300
    binding_mode: str = "U"
    object_model: Optional[Lwm2mObjectModelConfig] = None