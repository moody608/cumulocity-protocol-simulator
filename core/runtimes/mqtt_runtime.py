import asyncio
import time


class MqttRuntime:
    def __init__(self, asset, simulator, publisher):
        self.asset = asset
        self.simulator = simulator
        self.publisher = publisher
        self.interval = asset.interval_sec
        self.next_run = time.monotonic()

    async def run_forever(self):
        while True:
            now = time.monotonic()

            if now >= self.next_run:
                state = self.simulator.tick()
                mo_id = self.publisher.ensure_device(state)
                self.publisher.publish_measurements(state)
                self.publisher.publish_alarms(state)

                print(
                    f"{time.strftime('%H:%M:%S')} "
                    f"published deviceId={state.device_id} "
                    f"class={self.asset.device_class} "
                    f"protocol={self.asset.protocol} "
                    f"interval={self.interval} "
                    f"mo_id={mo_id}"
                )

                self.next_run = now + self.interval

            await asyncio.sleep(0.25)