"""
LoRa runtime for the IoT simulator.

Periodically ticks the assigned simulator, encodes the resulting state into a
binary hex payload via a device-class-specific mapper, and delivers it to a
LoRa network server or codec endpoint over HTTP. Requires the requests library
and Cumulocity credentials in shared_context["cumulocity_credentials"].
"""
import asyncio
import time

import requests

from adapters.lora.sensor_node_mapper import sensor_node_to_hex
from core.log import get_logger
from core.models.base import LoraProtocolConfig
from core.runtimes.base_runtime import BaseRuntime

_MAPPERS = {
    "sensorNode": sensor_node_to_hex,
}


class LoraRuntime(BaseRuntime):
    def __init__(
        self,
        asset,
        simulator,
        protocol_config: LoraProtocolConfig,
        auth: tuple[str, str],
    ):
        self.asset = asset
        self.simulator = simulator
        self.protocol_config = protocol_config
        self.interval = asset.interval_sec
        self._next_tick = time.monotonic()
        self.log = get_logger("lora", asset.device_id)

        self._session = requests.Session()
        self._session.auth = auth
        self._session.headers["Content-Type"] = "application/json"
        self._session.headers["Accept"] = "application/json"

    async def run_forever(self) -> None:
        self.log.info(
            "Starting lora runtime: deviceId=%s class=%s interval=%ds",
            self.asset.device_id, self.asset.device_class, self.asset.interval_sec,
        )
        while True:
            now = time.monotonic()

            if now >= self._next_tick:
                try:
                    state = self.simulator.tick()
                    mapper = _MAPPERS.get(state.device_class)
                    if mapper is None:
                        self.log.warning("no mapper for deviceClass=%s", state.device_class)
                    else:
                        await self._send(state, mapper(state))
                except Exception as exc:
                    self.log.warning(
                        "tick failed deviceId=%s error=%s",
                        self.asset.device_id, exc,
                    )
                self._next_tick = now + self.interval

            await asyncio.sleep(0.25)

    async def _send(self, state, hex_payload: str) -> None:
        cfg = self.protocol_config
        meta = self.asset.metadata

        body = {
            "deveui":             cfg.deveui,
            "payload":            hex_payload.lower(),
            "time":               state.timestamp.isoformat(),
            "manufacturer":       meta.get("manufacturer", ""),
            "model":              meta.get("model", ""),
            "firmwareVersion":    meta.get("firmwareVersion", ""),
            "deviceProtocolName": cfg.device_protocol_name,
        }

        self.log.info(
            "sending deveui=%s payload=%s endpoint=%s",
            cfg.deveui, hex_payload, cfg.server_uri,
        )

        try:
            resp = await asyncio.to_thread(
                self._session.post,
                cfg.server_uri,
                json=body,
                timeout=10,
            )

            if resp.ok:
                self.log.info(
                    "delivered deviceId=%s class=%s protocol=%s interval=%ds",
                    self.asset.device_id, self.asset.device_class,
                    self.asset.protocol, self.asset.interval_sec,
                )
                try:
                    decoded = resp.json().get("decoded")
                    if decoded:
                        self.log.info("decoded fields: %s", decoded)
                except Exception:
                    pass
            else:
                self.log.warning(
                    "uplink failed deveui=%s status=%s body=%s",
                    cfg.deveui, resp.status_code, resp.text[:200],
                )

        except Exception as exc:
            self.log.warning("uplink error deveui=%s error=%s", cfg.deveui, exc)
