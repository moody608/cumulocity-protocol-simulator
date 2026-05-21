import asyncio
import logging
from typing import Any

import yaml

from adapters.mqtt.publisher import C8yMqttPublisher
from core.config.assets_loader import load_assets
from core.factories.protocol_runtime_factory import build_protocol_runtime
from core.factories.simulator_factory import build_simulator
from core.log import setup_logging


ASSET_FILE = "configs/assets.yaml"
CONNECTION_FILE = "configs/connection.yaml"
MEASUREMENT_FILE = "configs/cumulocity-mapping.yaml"


def load_yaml(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


_log = logging.getLogger("iot.main")


async def main():
    setup_logging()
    assets = load_assets(ASSET_FILE)
    conn_cfg = load_yaml(CONNECTION_FILE)
    measurement_cfg = load_yaml(MEASUREMENT_FILE)

    publisher = C8yMqttPublisher(conn_cfg["cumulocity"], measurement_cfg)
    publisher.connect()

    c8y = conn_cfg["cumulocity"]
    shared_context = {
        "mqtt_publisher": publisher,
        "cumulocity_credentials": {
            "tenant": c8y["tenant"],
            "username": c8y["username"],
            "password": c8y["password"],
        },
    }

    runtime_tasks = []

    try:
        for asset in assets:
            simulator = build_simulator(asset)
            runtime = build_protocol_runtime(asset, simulator, shared_context)
            runtime_tasks.append(runtime.run_forever())

        if not runtime_tasks:
            _log.warning("No runtimes created. Exiting.")
            return

        await asyncio.gather(*runtime_tasks)

    finally:
        publisher.disconnect()


if __name__ == "__main__":
    asyncio.run(main())