from core.models.base import AssetConfig
from core.models.sensor_node import SensorNodeSimulator
from core.models.smart_meter import SmartMeterSimulator

SIMULATOR_REGISTRY = {
    "sensorNode": SensorNodeSimulator,
    "smartMeter": SmartMeterSimulator,
}


def build_simulator(asset: AssetConfig):
    simulator_cls = SIMULATOR_REGISTRY.get(asset.device_class)

    if simulator_cls is None:
        raise ValueError(f"Unsupported deviceClass: {asset.device_class}")

    return simulator_cls(
        device_id=str(asset.device_id),
        name=asset.name,
        interval_sec=int(asset.interval_sec),
        profile=asset.profile,
        metadata=asset.metadata,
    )