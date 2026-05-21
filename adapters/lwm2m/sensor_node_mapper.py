from core.models.base import AssetState

# (object_id, instance_id, resource_id) -> value
ResourceMap = dict[tuple[int, int, int], object]


def _device_object(state: AssetState) -> ResourceMap:
    i = state.identity
    t = state.telemetry
    return {
        (3, 0, 0):  str(i.get("manufacturer", "")),
        (3, 0, 1):  str(i.get("model", "")),
        (3, 0, 2):  str(i.get("serialNumber", state.device_id)),
        (3, 0, 3):  str(i.get("firmwareVersion", "")),
        (3, 0, 9):  int(t.get("batteryPct", 0)),
        (3, 0, 13): state.timestamp,
        (3, 0, 17): state.device_class,
        (3, 0, 18): str(i.get("hardwareRevision", "")),
    }


def _temperature_object(state: AssetState, instance_id: int = 0) -> ResourceMap:
    t = state.telemetry
    return {
        (3303, instance_id, 5700): float(t.get("temperatureC", 0.0)),
        (3303, instance_id, 5701): "Cel",
    }


def _location_object(state: AssetState) -> ResourceMap:
    if not state.location:
        return {}
    loc = state.location
    resources: ResourceMap = {}
    if "lat" in loc and "lng" in loc:
        resources[(6, 0, 0)] = float(loc["lat"])
        resources[(6, 0, 1)] = float(loc["lng"])
    if "alt" in loc:
        resources[(6, 0, 2)] = float(loc["alt"])
    if "timestamp" in loc:
        resources[(6, 0, 5)] = loc["timestamp"]
    return resources


def sensor_node_to_resources(
    state: AssetState,
    include_device_object: bool = True,
    include_temperature_object: bool = True,
    temperature_instance_id: int = 0,
    include_location_object: bool = False,
) -> ResourceMap:
    resources: ResourceMap = {}
    if include_device_object:
        resources.update(_device_object(state))
    if include_temperature_object:
        resources.update(_temperature_object(state, instance_id=temperature_instance_id))
    if include_location_object:
        resources.update(_location_object(state))
    return resources
