# IoT Simulator Guide

This project is a configurable IoT simulator that can run multiple simulated devices at the same time and expose them through different protocols such as MQTT and Modbus. The current design uses typed asset configuration, device-class-based simulator construction, and protocol runtimes so different device types and protocols can coexist in one run of the application.

## What the simulator does

The simulator reads device definitions from configuration, builds the correct simulator for each device class, and then starts the protocol runtime associated with each asset. In the current implementation, this means a single run can include MQTT-publishing devices and Modbus-serving devices at the same time, using the same overall orchestration flow.

Typical use cases include:

- Testing Cumulocity or other MQTT-based ingestion paths with realistic simulated telemetry.
- Exposing changing device values through Modbus TCP so external Modbus clients can poll them like real devices.
- Running mixed fleets of different device classes from a single configuration file.

## Project concepts

The simulator is organized around a few key concepts:

| Concept | Purpose |
|---------|---------|
| `AssetConfig` | Typed representation of one configured device loaded from `configs/assets.yaml`. |
| `AssetState` | Canonical runtime state emitted by a simulator tick, including identity, telemetry, alarms, and other operational fields. |
| Simulator | Device behavior model selected by `deviceClass`, such as a sensor node or smart meter. |
| Protocol runtime | Protocol-specific execution layer, such as MQTT publishing or Modbus serving. |
| Factory | Helper that builds simulators and runtimes from configuration instead of hardcoding those choices in `main.py`. |

This separation is important because device behavior and protocol behavior are different responsibilities. A smart meter simulator defines how voltage, current, power, and energy change over time, while a Modbus runtime defines how that state is exposed to a Modbus client.

## Configuration files

The simulator currently uses multiple YAML files, with different levels of typing and validation.

| File | Purpose | Parsing style |
|------|---------|---------------|
| `configs/assets.yaml` | Defines the simulated assets, their class, protocol, timing, and profile data. | Parsed into typed `AssetConfig` objects. |
| `configs/connection.yaml` | Stores MQTT or platform connection settings used by the publisher. | Loaded as a raw YAML dictionary for now.[1] |
| `configs/cumulocity-mapping.yaml` | Stores measurement mapping details used by the MQTT publishing path. | Loaded as a raw YAML dictionary for now.[1] |

The reason only `assets.yaml` is typed right now is that it already has a stable contract, while the connection and mapping files are still flexible and may continue evolving.

## assets.yaml format

Each entry under `assets:` defines one simulated device. A typical structure looks like this:

```yaml
assets:
  - deviceId: "12345"
    deviceClass: sensorNode
    protocol: mqtt
    name: Jake MQTT Device
    intervalSec: 10
    profile:
      startingBatteryPct: 88
      tempMinC: 19.5
      tempMaxC: 23.5
      humidityMinPct: 30
      humidityMaxPct: 50
      batteryDrainPerTickMax: 0.15
    metadata:
      manufacturer: Demo Devices
      model: SN-200
      firmwareVersion: "1.0.1"

  - deviceId: "20001"
    deviceClass: smartMeter
    protocol: mqtt
    name: Building Smart Meter
    intervalSec: 5
    profile:
      startingEnergyKwh: 5400.0
      baseVoltageV: 120.0
      baseCurrentA: 22.0
      baseFrequencyHz: 60.0
      basePowerFactor: 0.96
      voltageVariationV: 1.5
      currentVariationA: 2.0
      frequencyVariationHz: 0.03
      powerFactorDropMax: 0.02
      powerFactorRiseMax: 0.005
    metadata:
      manufacturer: Schneider Demo
      model: PowerLogic Virtual
      firmwareVersion: "2.3.1"
```

### Asset fields

| Field | Required | Meaning |
|-------|----------|---------|
| `deviceId` | Yes | Unique ID for the simulated asset. |
| `deviceClass` | Yes | Selects the simulator/model implementation, such as `sensorNode` or `smartMeter`. |
| `protocol` | Yes | Selects the runtime behavior, such as `mqtt` or `modbus`. |
| `name` | Yes | Human-readable asset name used for identity and registration. |
| `intervalSec` | Yes | Tick interval for the simulator model. |
| `profile` | Yes, in practice | Device-specific simulation inputs such as min/max values or base electrical parameters. |
| `metadata` | Optional but recommended | Device identity details such as manufacturer, model, firmware version, or protocol-specific settings used during transition. |

### profile

The `profile` block contains simulator-specific behavior inputs. Different `deviceClass` values can define different profile fields, which means the exact keys inside `profile` depend on the simulator implementation rather than the global YAML schema.

Examples:

- A `sensorNode` profile may define battery level, temperature range, and humidity range.
- A `smartMeter` profile may define base voltage, current, frequency, power factor, and energy starting point.

### metadata

The `metadata` block is intended for descriptive identity data such as manufacturer, model, and firmware version. In the current stage of the project, it may also temporarily hold protocol-specific settings such as Modbus port or unit ID until a dedicated protocol config block is introduced.

A likely future refinement is to split protocol execution settings out into something like `protocolConfig`, but that is not required to use the current version of the simulator.

## Running the simulator

The main entrypoint loads assets, builds simulators using the simulator factory, builds protocol runtimes using the runtime factory, and starts those runtimes together. The current runtime pattern supports mixed-protocol execution, which means MQTT and Modbus devices can be active simultaneously in a single process.

A simplified flow is:

1. Load `assets.yaml` into `AssetConfig` objects.
2. Load connection and measurement mapping YAML files as raw dictionaries.[1]
3. Build a shared MQTT publisher context for MQTT-backed assets.
4. For each configured asset, build the simulator selected by `deviceClass`.
5. Build the protocol runtime selected by `protocol`.
6. Start all runtimes together.

## Simulator and runtime selection

### Simulator factory

The simulator factory maps `deviceClass` to the correct simulator implementation. For example:

- `sensorNode` -> `SensorNodeSimulator`.
- `smartMeter` -> `SmartMeterSimulator`.

This keeps `main.py` from hardcoding simulator construction logic throughout the orchestration flow.

### Protocol runtime factory

The protocol runtime factory maps `protocol` to the correct runtime behavior. For example:

- `mqtt` -> `MqttRuntime`, which periodically ticks the simulator and publishes state through the shared MQTT publisher.
- `modbus` -> `ModbusRuntime`, which starts a Modbus server and exposes simulator values through a register map.

This separation allows the same simulator class to be reused with different protocols if needed, depending on the adapter and mapper implementation.

## MQTT behavior

For MQTT assets, the runtime periodically calls the simulator `tick()` method and then sends the resulting state through the MQTT publisher. The publisher is responsible for registration/ensure-device logic, measurement publishing, and alarm publishing against the target platform.

When an MQTT asset is configured correctly, the expected runtime behavior is:

- simulator state updates on the configured interval,
- device existence is verified or created as needed,
- measurements are published,
- alarms are published if present.

## Modbus behavior

For Modbus assets, the runtime starts a Modbus server rather than publishing on a broker-style schedule. External Modbus clients poll the server, and the current register values represent the current simulated device state at the time of the read.

The current working implementation uses PyModbus 3.11.2 with the classic mutable datastore model rather than the newer `SimData`/`SimDevice` path, because the older approach supports the live-updating register behavior expected for simulated telemetry devices.[2][3]

The earlier `Illegal Data Address` issue came from client-side address interpretation rather than a broken server implementation. Once the client offset and valid register range matched the datastore base address, live values appeared as expected.[4][5]

## Example mixed fleet

A mixed `assets.yaml` can include both MQTT and Modbus devices together. For example:

```yaml
assets:
  - deviceId: "12345"
    deviceClass: sensorNode
    protocol: mqtt
    name: Jake MQTT Device
    intervalSec: 10
    profile:
      startingBatteryPct: 88
      tempMinC: 19.5
      tempMaxC: 23.5
      humidityMinPct: 30
      humidityMaxPct: 50
      batteryDrainPerTickMax: 0.15
    metadata:
      manufacturer: Demo Devices
      model: SN-200
      firmwareVersion: "1.0.1"

  - deviceId: "20001"
    deviceClass: smartMeter
    protocol: modbus
    name: Building Smart Meter
    intervalSec: 5
    profile:
      startingEnergyKwh: 5400.0
      baseVoltageV: 120.0
      baseCurrentA: 22.0
      baseFrequencyHz: 60.0
      basePowerFactor: 0.96
      voltageVariationV: 1.5
      currentVariationA: 2.0
      frequencyVariationHz: 0.03
      powerFactorDropMax: 0.02
      powerFactorRiseMax: 0.005
    metadata:
      manufacturer: Schneider Demo
      model: PowerLogic Virtual
      firmwareVersion: "2.3.1"
      modbusPort: 5020
      modbusUnitId: 1
      modbusRegisterCount: 100
```

This kind of config allows the simulator to run one asset through MQTT and another through Modbus at the same time using the same factory-driven orchestration path.

## Identity and state

Runtime state is represented canonically through `AssetState`, which lets different protocol adapters consume a common model instead of reading raw YAML directly. A useful pattern is to populate `AssetState.identity` with stable descriptive fields such as device ID, name, device class, protocol, manufacturer, model, and firmware version.

This keeps the state model clear:

- `identity` describes what the asset is,
- `telemetry` describes what the asset is doing right now,
- `alarms` describe exceptional conditions attached to that asset.

## Extending the simulator

To add a new device class:

1. Create a new simulator/model class that emits `AssetState`.
2. Add the class to the simulator factory registry.
3. Define its expected `profile` fields in configuration documentation.
4. Add any protocol-specific mapping needed for MQTT payloads or Modbus registers.

To add a new protocol:

1. Create a runtime class that exposes a common execution interface such as `run_forever()`.
2. Add protocol selection logic in the protocol runtime factory.
3. Add any protocol-specific config conventions or mappings.

## Practical notes

- Keep `assets.yaml` typed and stable, because it now serves as the main contract between configuration and runtime behavior.
- Keep `main.py` focused on orchestration, not simulator or protocol branching.
- Use factories to prevent `main.py` from becoming MQTT-specific or Modbus-specific again.
- Introduce dedicated protocol config sections later if protocol-specific settings begin to outgrow `metadata`.

## Current status

The current implementation has already demonstrated simultaneous MQTT and Modbus execution, which validates the core architecture direction and confirms that mixed-protocol assets can be driven from the same configuration and orchestration flow.