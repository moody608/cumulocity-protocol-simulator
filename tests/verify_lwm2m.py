"""
Smoke-check for LwM2M protocolConfig parsing.
Run: python verify_lwm2m.py
"""
from core.config.assets_loader import _parse_asset
from core.models.base import Lwm2mObjectModelConfig, Lwm2mProtocolConfig

_LWM2M_FULL = {
    "deviceId": "test-lwm2m-001",
    "deviceClass": "sensorNode",
    "protocol": "lwm2m",
    "name": "Test LwM2M Node",
    "intervalSec": 30,
    "protocolConfig": {
        "endpointId": "test-lwm2m-001",
        "serverUri": "coaps://demo.example.com:5684",
        "securityMode": "PSK",
        "pskIdentity": "test-lwm2m-001",
        "pskKeyHex": "DEADBEEF01234567",
        "lifetimeSec": 600,
        "bindingMode": "UQ",
        "objectModel": {
            "includeDeviceObject": True,
            "includeLocationObject": True,
            "includeTemperatureObject": True,
            "temperatureInstanceId": 2,
            "sendMode": "write",
        },
    },
}

_MQTT_NO_PROTOCOL_CONFIG = {
    "deviceId": "12345",
    "deviceClass": "sensorNode",
    "protocol": "mqtt",
    "name": "MQTT Node",
    "intervalSec": 10,
}


def check_lwm2m_full():
    cfg = _parse_asset(_LWM2M_FULL)

    pc = cfg.protocol_config
    assert isinstance(pc, Lwm2mProtocolConfig), f"expected Lwm2mProtocolConfig, got {type(pc)}"
    assert pc.endpoint_id == "test-lwm2m-001"
    assert pc.server_uri == "coaps://demo.example.com:5684"
    assert pc.security_mode == "PSK"
    assert pc.psk_identity == "test-lwm2m-001"
    assert pc.psk_key_hex == "DEADBEEF01234567"
    assert pc.lifetime_sec == 600
    assert pc.binding_mode == "UQ"

    om = pc.object_model
    assert isinstance(om, Lwm2mObjectModelConfig), f"expected Lwm2mObjectModelConfig, got {type(om)}"
    assert om.include_device_object is True
    assert om.include_location_object is True
    assert om.include_temperature_object is True
    assert om.temperature_instance_id == 2
    assert om.send_mode == "write"

    print("PASS  lwm2m full protocolConfig + nested objectModel")


def check_no_protocol_config():
    cfg = _parse_asset(_MQTT_NO_PROTOCOL_CONFIG)
    assert cfg.protocol_config is None
    print("PASS  mqtt asset without protocolConfig: protocol_config is None")


if __name__ == "__main__":
    check_lwm2m_full()
    check_no_protocol_config()
    print("All checks passed.")
