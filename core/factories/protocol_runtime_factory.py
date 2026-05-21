from core.models.base import AssetConfig, LoraProtocolConfig, Lwm2mProtocolConfig
from core.runtimes.mqtt_runtime import MqttRuntime
from core.runtimes.modbus_runtime import ModbusRuntime
from core.runtimes.lwm2m_runtime import Lwm2mRuntime
from core.runtimes.lora_runtime import LoraRuntime
from adapters.modbus.register_map import smart_meter_to_registers


def get_modbus_register_mapper(device_class: str):
    if device_class == "smartMeter":
        return smart_meter_to_registers
    raise ValueError(f"No Modbus register mapper for deviceClass={device_class}")


def build_protocol_runtime(asset: AssetConfig, simulator, shared_context):
    protocol = asset.protocol.strip().lower()

    if protocol == "lora":
        if not isinstance(asset.protocol_config, LoraProtocolConfig):
            raise ValueError(
                f"deviceId={asset.device_id}: protocol_config must be a LoraProtocolConfig "
                f"for protocol=lora (got {type(asset.protocol_config).__name__})"
            )
        creds = shared_context["cumulocity_credentials"]
        return LoraRuntime(
            asset=asset,
            simulator=simulator,
            protocol_config=asset.protocol_config,
            auth=(f"{creds['tenant']}/{creds['username']}", creds["password"]),
        )

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

    if protocol == "lwm2m":
        if not isinstance(asset.protocol_config, Lwm2mProtocolConfig):
            raise ValueError(
                f"deviceId={asset.device_id}: protocol_config must be a Lwm2mProtocolConfig "
                f"for protocol=lwm2m (got {type(asset.protocol_config).__name__})"
            )
        return Lwm2mRuntime(
            asset=asset,
            simulator=simulator,
            protocol_config=asset.protocol_config,
        )

    raise ValueError(f"Unsupported protocol: {asset.protocol}")