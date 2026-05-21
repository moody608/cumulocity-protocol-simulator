from pymodbus import ModbusDeviceIdentification
from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusSequentialDataBlock,
    ModbusServerContext,
)
from pymodbus.server import StartAsyncTcpServer, ServerAsyncStop


class ModbusSimulatorServer:
    def __init__(
        self,
        log,
        host="0.0.0.0",
        port=5020,
        device_id=1,
        register_count=100,
    ):
        self.log = log
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
                "VendorName": "iot-simulator",
                "ProductCode": "IOTSIM",
                "VendorUrl": "https://github.com/moody608/IoTSimulator",
                "ProductName": "IoT Simulator Modbus Adapter",
                "MajorMinorRevision": "0.1.0",
            }
        )

    def _to_unsigned_16(self, value: int) -> int:
        return int(value) & 0xFFFF

    def update_registers(self, registers: dict[int, int]) -> None:
        for address, value in registers.items():
            self.device_context.setValues(
                3,
                address,
                [self._to_unsigned_16(value)],
            )

    async def start(self) -> None:
        self.log.info("listening host=%s port=%s unit=%s", self.host, self.port, self.device_id)
        await StartAsyncTcpServer(
            context=self.context,
            identity=self.identity,
            address=(self.host, self.port),
        )

    async def stop(self) -> None:
        await ServerAsyncStop()
