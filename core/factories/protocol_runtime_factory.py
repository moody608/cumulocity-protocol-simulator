from core.models.base import AssetConfig
from core.runtimes.mqtt_runtime import MqttRuntime
from core.runtimes.modbus_runtime import ModbusRuntime
from adapters.modbus.register_map import smart_meter_to_registers


def get_modbus_register_mapper(device_class: str):
    if device_class == "smartMeter":
        return smart_meter_to_registers
    raise ValueError(f"No Modbus register mapper for deviceClass={device_class}")


def build_protocol_runtime(asset: AssetConfig, simulator, shared_context):
    protocol = asset.protocol.strip().lower()

    if protocol == "mqtt":
        return MqttRuntime(
            asset=asset,
            simulator=simulator,
            publisher=shared_context["mqtt_publisher"],
        )

    if protocol == "modbus":
        return ModbusRuntime(
            asset=asset,
            simulator=simulator,
            register_mapper=get_modbus_register_mapper(asset.device_class),
        )

    raise ValueError(f"Unsupported protocol: {asset.protocol}")