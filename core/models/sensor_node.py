"""
Sensor node simulator for the IoT simulator.

Models a battery-powered environmental sensor that emits temperature, humidity,
signal RSSI, and battery level each tick. Battery drains gradually over time and
raises a batteryLow alarm when it falls below 20%. Supports additional user-defined
channels declared in the asset profile.
"""
import random
from datetime import datetime, timezone

from core.models.base import AssetState, AlarmState, Channel
from core.models.base_simulator import BaseSimulator


class SensorNodeSimulator(BaseSimulator):
    def __init__(
        self,
        device_id: str,
        name: str,
        protocol: str = "mqtt",
        interval_sec: int = 5,
        profile=None,
        location=None,
        metadata=None,
        channels: list[Channel] | None = None,
    ):
        self.device_id = str(device_id)
        self.name = name
        self.protocol = protocol
        self.interval_sec = int(interval_sec)
        self.profile = profile or {}
        self.location = location
        self.metadata = metadata or {}
        self.channels: list[Channel] = channels or []

        self.battery = float(self.profile.get("startingBatteryPct", random.randint(70, 95)))

        self.temp_min = float(self.profile.get("tempMinC", 20.5))
        self.temp_max = float(self.profile.get("tempMaxC", 24.5))
        self.humidity_min = float(self.profile.get("humidityMinPct", 35.0))
        self.humidity_max = float(self.profile.get("humidityMaxPct", 55.0))
        self.rssi_min = int(self.profile.get("rssiMin", -78))
        self.rssi_max = int(self.profile.get("rssiMax", -55))
        self.battery_drain_max = float(self.profile.get("batteryDrainPerTickMax", 0.2))

    def tick(self) -> AssetState:
        now = datetime.now(timezone.utc)

        self.battery = max(5.0, self.battery - random.uniform(0.0, self.battery_drain_max))
        temperature = round(random.uniform(self.temp_min, self.temp_max), 1)
        humidity = round(random.uniform(self.humidity_min, self.humidity_max), 1)
        rssi = random.randint(self.rssi_min, self.rssi_max)
        health = max(1, min(100, int(round(self.battery))))

        alarms = []
        if self.battery < 20:
            alarms.append(
                AlarmState(
                    type="batteryLow",
                    text="",
                    severity="",
                    time=now,
                    details={
                        "batteryPct": round(self.battery, 1)
                    }
                )
            )

        telemetry = {
            "temperatureC": temperature,
            "humidityPct": humidity,
            "batteryPct": round(self.battery, 1),
            "signalRssi": rssi,
        }
        for channel in self.channels:
            telemetry[channel.name] = round(random.uniform(channel.min, channel.max), channel.precision)

        return AssetState(
            device_id=self.device_id,
            device_class="sensorNode",
            protocol=self.protocol,
            timestamp=now,
            identity={
                "name": self.name,
                "model": self.metadata.get("model", "SN-200"),
                "serialNumber": self.metadata.get("serialNumber", self.device_id),
                "firmwareVersion": self.metadata.get("firmwareVersion", "1.0.0"),
                "manufacturer": self.metadata.get("manufacturer", "Demo Devices"),
                "hardwareRevision": self.metadata.get("hardwareRevision", "A1"),
            },
            telemetry=telemetry,
            operational={
                "status": "ONLINE",
                "availability": "AVAILABLE",
                "healthScore": health,
            },
            service={
                "otaEligible": self.metadata.get("otaEligible", True),
            },
            compliance={
                "certificateStatus": self.metadata.get("certificateStatus", "valid"),
                "policyVersion": self.metadata.get("policyVersion", "2026.04"),
            },
            location=self.location,
            events=[],
            alarms=alarms,
        )
