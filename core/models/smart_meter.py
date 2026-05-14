import random
from datetime import datetime, timezone

from core.models.base import AssetState, AlarmState


class SmartMeterSimulator:
    def __init__(
        self,
        device_id: str,
        name: str,
        interval_sec: int = 5,
        profile=None,
        location=None,
        metadata=None
    ):
        self.device_id = str(device_id)
        self.name = name
        self.interval_sec = int(interval_sec)
        self.profile = profile or {}
        self.location = location
        self.metadata = metadata or {}

        self.energy_kwh = float(self.profile.get("startingEnergyKwh", 1250.0))
        self.base_voltage = float(self.profile.get("baseVoltageV", 120.0))
        self.base_current = float(self.profile.get("baseCurrentA", 18.0))
        self.base_frequency = float(self.profile.get("baseFrequencyHz", 60.0))
        self.base_power_factor = float(self.profile.get("basePowerFactor", 0.97))

        self.voltage_variation = float(self.profile.get("voltageVariationV", 2.5))
        self.current_variation = float(self.profile.get("currentVariationA", 3.0))
        self.frequency_variation = float(self.profile.get("frequencyVariationHz", 0.08))
        self.power_factor_drop = float(self.profile.get("powerFactorDropMax", 0.03))
        self.power_factor_rise = float(self.profile.get("powerFactorRiseMax", 0.01))

    def tick(self) -> AssetState:
        now = datetime.now(timezone.utc)

        voltage = round(
            self.base_voltage + random.uniform(-self.voltage_variation, self.voltage_variation),
            2
        )
        current = round(
            self.base_current + random.uniform(-self.current_variation, self.current_variation),
            2
        )
        frequency = round(
            self.base_frequency + random.uniform(-self.frequency_variation, self.frequency_variation),
            2
        )
        power_factor = round(
            max(
                0.75,
                min(
                    1.0,
                    self.base_power_factor + random.uniform(-self.power_factor_drop, self.power_factor_rise)
                )
            ),
            3
        )

        power_kw = round((voltage * current * power_factor) / 1000.0, 3)
        self.energy_kwh = round(
            self.energy_kwh + (power_kw * self.interval_sec / 3600.0),
            3
        )

        alarms = []

        if voltage < (self.base_voltage * 0.92):
            alarms.append(
                AlarmState(
                    type="underVoltage",
                    text="",
                    severity="",
                    time=now,
                    details={
                        "measuredVoltage": voltage,
                        "expectedVoltage": self.base_voltage
                    }
                )
            )

        if power_factor < 0.85:
            alarms.append(
                AlarmState(
                    type="powerFactorLow",
                    text="",
                    severity="",
                    time=now,
                    details={
                        "powerFactor": power_factor
                    }
                )
            )

        return AssetState(
            device_id=self.device_id,
            device_class="smartMeter",
            protocol="mqtt",
            timestamp=now,
            identity={
                "name": self.name,
                "manufacturer": self.metadata.get("manufacturer", "Demo Utilities"),
                "model": self.metadata.get("model", "SM-1000"),
                "serialNumber": self.metadata.get("serialNumber", self.device_id),
                "firmwareVersion": self.metadata.get("firmwareVersion", "1.0.0"),
                "hardwareRevision": self.metadata.get("hardwareRevision", "A1"),
            },
            telemetry={
                "voltageV": voltage,
                "currentA": current,
                "powerKw": power_kw,
                "energyKwh": self.energy_kwh,
                "frequencyHz": frequency,
                "powerFactor": power_factor,
            },
            operational={
                "status": "ONLINE",
                "connected": True,
            },
            service={
                "lastInspectionDate": self.metadata.get("lastInspectionDate", "2026-01-15"),
            },
            compliance={
                "calibrationStatus": self.metadata.get("calibrationStatus", "valid"),
            },
            location=self.location,
            events=[],
            alarms=alarms,
        )