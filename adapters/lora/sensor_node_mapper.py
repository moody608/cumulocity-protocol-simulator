import struct

from core.models.base import AssetState


def sensor_node_to_hex(state: AssetState) -> str:
    """Pack sensorNode telemetry into a compact 3-byte LoRa payload.

    Wire format (big-endian):
      Bytes 0-1: temperatureC as signed int16, scaled ×10  (e.g. 22.3 → 223 → 0x00DF)
      Byte  2:   humidityPct as uint8                       (e.g. 50   →      0x32)

    Returns the bytes as a lowercase hex string (e.g. "00df32").
    """
    t = state.telemetry
    temp_raw = int(round(float(t.get("temperatureC", 0.0)) * 10))
    humidity_raw = max(0, min(255, int(round(float(t.get("humidityPct", 0.0))))))
    return struct.pack(">hB", temp_raw, humidity_raw).hex()
