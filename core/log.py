import logging

_FORMAT = "%(asctime)s [%(protocol)-8s] [%(device_id)s] %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


class _Formatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.__dict__.setdefault("protocol", "system")
        record.__dict__.setdefault("device_id", "-")
        return super().format(record)


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_Formatter(_FORMAT, datefmt=_DATE_FMT))
    logging.root.handlers.clear()
    logging.root.addHandler(handler)
    logging.root.setLevel(level)


def get_logger(protocol: str, device_id: str) -> logging.LoggerAdapter:
    base = logging.getLogger(f"iot.{protocol}")
    return logging.LoggerAdapter(base, {"protocol": protocol, "device_id": device_id})
