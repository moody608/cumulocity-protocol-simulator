import asyncio

from pymodbus import ModbusDeviceIdentification
from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusSequentialDataBlock,
    ModbusServerContext,
)
from pymodbus.server import StartAsyncTcpServer


class ModbusSimulatorServer:
    def __init__(
        self,
        simulator,
        register_mapper,
        host="0.0.0.0",
        port=5020,
        device_id=1,
        register_count=100,
    ):
        self.simulator = simulator
        self.register_mapper = register_mapper
        self.host = host
        self.port = port
        self.device_id = device_id
        self.register_count = register_count

        self.device_context = ModbusDeviceContext(
            di=ModbusSequentialDataBlock(0, [0] * self.register_count),
            co=ModbusSequentialDataBlock(0, [0] * self.register_count),
            hr=ModbusSequentialDataBlock(0, [0] * self.register_count),
            ir=ModbusSequentialDataBlock(0, [0] * self.register_count),
        )

        self.context = ModbusServerContext(
            devices={self.device_id: self.device_context},
            single=False,
        )

        self.identity = ModbusDeviceIdentification(
            info_name={
                "VendorName": "IoTSimulator",
                "ProductCode": "IOTSIM",
                "VendorUrl": "https://github.com/moody608/IoTSimulator",
                "ProductName": "IoT Simulator Modbus Adapter",
                "ModelName": type(self.simulator).__name__,
                "MajorMinorRevision": "0.1.0",
            }
        )

    def _to_unsigned_16(self, value: int) -> int:
        return int(value) & 0xFFFF

    async def _write_holding_registers(self, registers: dict[int, int]) -> None:
        for address, value in registers.items():
            self.device_context.setValues(
                3,
                address,
                [self._to_unsigned_16(value)],
            )

    async def update_loop(self):
        while True:
            state = self.simulator.tick()
            registers = self.register_mapper(state)

            await self._write_holding_registers(registers)

            print(
                f"Updated deviceId={state.device_id} "
                f"voltage={state.telemetry.get('voltageV')} "
                f"current={state.telemetry.get('currentA')} "
                f"power={state.telemetry.get('powerKw')} "
                f"registers={ {k: registers[k] for k in sorted(registers.keys())[:10]} }"
            )

            await asyncio.sleep(self.simulator.interval_sec)

    async def start(self):
        asyncio.create_task(self.update_loop())

        await StartAsyncTcpServer(
            context=self.context,
            identity=self.identity,
            address=(self.host, self.port),
        )