"""
LwM2M runtime for the IoT simulator.

Registers the simulated device with a LwM2M server over CoAP, then periodically
ticks the simulator and notifies active observers of updated resource values.
Requires aiocoap; DTLS/PSK mode additionally requires the DTLSSocket C extension.
"""
import asyncio
import time

from adapters.lwm2m.client import Lwm2mClientAdapter
from core.log import get_logger
from core.models.base import Lwm2mProtocolConfig
from core.runtimes.base_runtime import BaseRuntime


class Lwm2mRuntime(BaseRuntime):
    def __init__(self, asset, simulator, protocol_config: Lwm2mProtocolConfig):
        self.asset = asset
        self.simulator = simulator
        self.protocol_config = protocol_config
        self.log = get_logger("lwm2m", asset.device_id)
        self.client = Lwm2mClientAdapter(protocol_config, self.log)
        self.interval = asset.interval_sec
        self._next_tick = time.monotonic()

    async def run_forever(self) -> None:
        self.log.info(
            "Starting lwm2m runtime: deviceId=%s class=%s interval=%ds",
            self.asset.device_id, self.asset.device_class, self.asset.interval_sec,
        )
        await self.client.connect()

        while True:
            now = time.monotonic()

            if now >= self._next_tick:
                try:
                    state = self.simulator.tick()
                    await self.client.send_report(state)
                    self.log.info(
                        "reported deviceId=%s class=%s protocol=%s interval=%ds",
                        self.asset.device_id, self.asset.device_class,
                        self.asset.protocol, self.asset.interval_sec,
                    )
                except Exception as exc:
                    self.log.warning(
                        "tick failed deviceId=%s error=%s",
                        self.asset.device_id, exc,
                    )
                self._next_tick = now + self.interval

            await asyncio.sleep(0.25)
