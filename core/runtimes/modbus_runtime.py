"""
Modbus TCP runtime for the IoT simulator.

Starts a pymodbus TCP server as a background task, then periodically ticks the
assigned simulator and writes the resulting state into the server's holding
registers via the provided register_mapper. Requires PyModbus to be installed.
"""
import asyncio
import time

from adapters.modbus.server import ModbusSimulatorServer
from core.log import get_logger
from core.runtimes.base_runtime import BaseRuntime


class ModbusRuntime(BaseRuntime):
    def __init__(self, asset, simulator, register_mapper):
        self.asset = asset
        self.simulator = simulator
        self.register_mapper = register_mapper
        self.interval = asset.interval_sec
        self._next_tick = time.monotonic()
        self.log = get_logger("modbus", asset.device_id)

        self.server = ModbusSimulatorServer(
            log=self.log,
            host="0.0.0.0",
            port=int(asset.metadata.get("modbusPort", 5020)),
            device_id=int(asset.metadata.get("modbusUnitId", 1)),
            register_count=int(asset.metadata.get("modbusRegisterCount", 100)),
        )

    async def run_forever(self) -> None:
        self.log.info(
            "Starting modbus runtime: deviceId=%s class=%s interval=%ds",
            self.asset.device_id, self.asset.device_class, self.asset.interval_sec,
        )
        server_task = asyncio.create_task(self.server.start())
        try:
            while True:
                now = time.monotonic()

                if now >= self._next_tick:
                    try:
                        state = self.simulator.tick()
                        registers = self.register_mapper(state)
                        self.server.update_registers(registers)
                        self.log.info(
                            "updated deviceId=%s class=%s protocol=%s interval=%ds",
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
        finally:
            await self.server.stop()
            server_task.cancel()
