from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AssetConfig:
    device_id: str
    device_class: str
    protocol: str
    name: str
    interval_sec: int
    profile: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


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