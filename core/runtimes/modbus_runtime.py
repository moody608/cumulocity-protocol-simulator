class ModbusRuntime:
    def __init__(self, asset, simulator, register_mapper):
        self.asset = asset
        self.simulator = simulator

        from adapters.modbus.server import ModbusSimulatorServer

        self.server = ModbusSimulatorServer(
            simulator=simulator,
            register_mapper=register_mapper,
            host="0.0.0.0",
            port=int(asset.metadata.get("modbusPort", 5020)),
            device_id=int(asset.metadata.get("modbusUnitId", 1)),
            register_count=int(asset.metadata.get("modbusRegisterCount", 100)),
        )

    async def run_forever(self):
        print(
            f"Starting Modbus runtime: deviceId={self.asset.device_id} "
            f"class={self.asset.device_class} "
            f"protocol={self.asset.protocol}"
        )
        await self.server.start()