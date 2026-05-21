# IoT Simulator

A configurable IoT device simulator that runs multiple virtual devices simultaneously and exposes them over different protocols. Device behavior and protocol transport are separate concerns — the same device class can run over different protocols, and a single process can run a mixed fleet.

## Quick start

```bash
pip install -r requirements.txt
python main.py
```

The simulator reads `configs/assets.yaml`, builds a simulator for each asset, starts the matching protocol runtime, and runs everything concurrently.

---

## Project concepts

| Concept | Purpose |
|---------|---------|
| `AssetConfig` | Typed representation of one device loaded from `assets.yaml`. |
| `AssetState` | Canonical state emitted each tick: identity, telemetry, alarms. |
| Simulator | Device behavior model (`sensorNode`, `smartMeter`). |
| Runtime | Protocol transport layer (`mqtt`, `modbus`, `lora`, `lwm2m`). |
| Factory | Builds simulators and runtimes from config — keeps `main.py` clean. |

---

## Configuration files

| File | Purpose |
|------|---------|
| `configs/assets.yaml` | Defines simulated devices — class, protocol, timing, and profile. Strongly typed. |
| `configs/connection.yaml` | MQTT / Cumulocity connection settings. |
| `configs/cumulocity-mapping.yaml` | Measurement and alarm mappings for the MQTT publishing path. |

---

## assets.yaml reference

Every entry under `assets:` defines one simulated device. Only `assets.yaml` is strongly validated; the other config files are loaded as loose dictionaries.

### Top-level fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `deviceId` | Yes | string | Unique identifier for this device. Also used as the external ID in Cumulocity. |
| `deviceClass` | Yes | string | Selects the simulator model. See [Device classes](#device-classes). |
| `protocol` | Yes | string | Selects the protocol runtime. See [Protocols](#protocols). |
| `name` | Yes | string | Human-readable display name used in registration and logs. |
| `intervalSec` | Yes | integer | How often the simulator ticks and emits new state, in seconds. |
| `profile` | Yes (in practice) | dict | Simulator behavior inputs. Schema depends on `deviceClass`. |
| `metadata` | No | dict | Descriptive identity fields passed to the device model. Fields not listed here are ignored. |
| `protocolConfig` | Required for `lora` and `lwm2m` | dict | Protocol-specific connection config. Schema depends on `protocol`. |

---

## Device classes

### `sensorNode`

Simulates a battery-powered environmental sensor that reports temperature, humidity, signal strength, and battery level. Battery drains each tick and raises a `batteryLow` alarm below 20%.

#### `profile` fields

| Field | Default | Description |
|-------|---------|-------------|
| `startingBatteryPct` | Random 70–95 | Initial battery percentage. Drains each tick. |
| `tempMinC` | `20.5` | Low end of the temperature range in °C. |
| `tempMaxC` | `24.5` | High end of the temperature range in °C. |
| `humidityMinPct` | `35.0` | Low end of the humidity range in %. |
| `humidityMaxPct` | `55.0` | High end of the humidity range in %. |
| `rssiMin` | `-78` | Low end of the signal RSSI range in dBm. |
| `rssiMax` | `-55` | High end of the signal RSSI range in dBm. |
| `batteryDrainPerTickMax` | `0.2` | Maximum battery percentage drained per tick. Actual drain is a random value between 0 and this. |

#### `metadata` fields

| Field | Default | Description |
|-------|---------|-------------|
| `manufacturer` | `"Demo Devices"` | Manufacturer name reported in device identity. |
| `model` | `"SN-200"` | Model name. |
| `firmwareVersion` | `"1.0.0"` | Firmware version string. |
| `serialNumber` | Device ID | Serial number. Defaults to `deviceId` if omitted. |
| `hardwareRevision` | `"A1"` | Hardware revision string. |
| `otaEligible` | `true` | Whether the device is marked eligible for OTA updates. |
| `certificateStatus` | `"valid"` | Certificate status reported in compliance state. |
| `policyVersion` | `"2026.04"` | Policy version reported in compliance state. |

#### Alarms emitted

| Alarm type | Trigger condition | Severity |
|------------|------------------|---------|
| `batteryLow` | Battery drops below 20% | `MINOR` |

#### Example

```yaml
- deviceId: "sensor-001"
  deviceClass: sensorNode
  protocol: mqtt
  name: Warehouse Sensor A
  intervalSec: 10
  profile:
    startingBatteryPct: 88
    tempMinC: 19.5
    tempMaxC: 23.5
    humidityMinPct: 30
    humidityMaxPct: 50
    rssiMin: -85
    rssiMax: -50
    batteryDrainPerTickMax: 0.15
  metadata:
    manufacturer: Demo Devices
    model: SN-200
    firmwareVersion: "1.0.1"
    serialNumber: "SN-001"
```

---

### `smartMeter`

Simulates an electrical smart meter that reports voltage, current, frequency, power factor, active power, and cumulative energy. Energy accumulates each tick. Alarms fire when voltage or power factor fall outside acceptable thresholds.

#### `profile` fields

| Field | Default | Description |
|-------|---------|-------------|
| `startingEnergyKwh` | `1250.0` | Initial cumulative energy reading in kWh. Increases each tick. |
| `baseVoltageV` | `120.0` | Centre voltage in volts. Typical values: `120.0` (North America), `230.0` (Europe). |
| `baseCurrentA` | `18.0` | Centre current in amps. |
| `baseFrequencyHz` | `60.0` | Centre frequency in Hz. Typical values: `60.0` (North America), `50.0` (Europe). |
| `basePowerFactor` | `0.97` | Centre power factor. Valid range: 0.0–1.0. |
| `voltageVariationV` | `2.5` | Maximum random deviation from `baseVoltageV` each tick (±). |
| `currentVariationA` | `3.0` | Maximum random deviation from `baseCurrentA` each tick (±). |
| `frequencyVariationHz` | `0.08` | Maximum random deviation from `baseFrequencyHz` each tick (±). |
| `powerFactorDropMax` | `0.03` | Maximum downward shift applied to power factor each tick. |
| `powerFactorRiseMax` | `0.01` | Maximum upward shift applied to power factor each tick. |

Power factor is clamped to the range 0.75–1.0 regardless of variation settings.

#### `metadata` fields

| Field | Default | Description |
|-------|---------|-------------|
| `manufacturer` | `"Demo Utilities"` | Manufacturer name. |
| `model` | `"SM-1000"` | Model name. |
| `firmwareVersion` | `"1.0.0"` | Firmware version. |
| `serialNumber` | Device ID | Serial number. |
| `hardwareRevision` | `"A1"` | Hardware revision. |
| `lastInspectionDate` | `"2026-01-15"` | Last inspection date reported in service state (ISO 8601 date). |
| `calibrationStatus` | `"valid"` | Calibration status reported in compliance state. |

#### `metadata` fields (Modbus only)

These fields are only used when `protocol` is `modbus`.

| Field | Default | Description |
|-------|---------|-------------|
| `modbusPort` | `5020` | TCP port the Modbus server listens on. |
| `modbusUnitId` | `1` | Modbus unit (slave) ID. |
| `modbusRegisterCount` | `100` | Number of holding registers allocated in the datastore. |

#### Alarms emitted

| Alarm type | Trigger condition | Severity |
|------------|------------------|---------|
| `underVoltage` | Voltage drops below 92% of `baseVoltageV` | `MINOR` |
| `powerFactorLow` | Power factor drops below 0.85 | `WARNING` |

#### Example

```yaml
- deviceId: "meter-001"
  deviceClass: smartMeter
  protocol: modbus
  name: Building A Smart Meter
  intervalSec: 5
  profile:
    startingEnergyKwh: 5400.0
    baseVoltageV: 230.0
    baseCurrentA: 16.0
    baseFrequencyHz: 50.0
    basePowerFactor: 0.95
    voltageVariationV: 3.0
    currentVariationA: 2.0
    frequencyVariationHz: 0.05
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

---

## Protocols

### `mqtt`

Ticks the simulator on `intervalSec` and publishes state to Cumulocity via the shared MQTT publisher. Creates or updates the managed object in Cumulocity on first run.

**Requirements**: valid `configs/connection.yaml` with Cumulocity credentials.

**No `protocolConfig` needed.**

**Supported device classes**: `sensorNode`, `smartMeter`

```yaml
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
```

---

### `modbus`

Starts a Modbus TCP server and maps the current simulator state into holding registers. External Modbus clients poll the server address to read live values.

**Requirements**: PyModbus installed. Port specified in `metadata.modbusPort` (default `5020`) must be available.

**No `protocolConfig` needed.**

**Supported device classes**: `smartMeter`

#### Modbus register map (smartMeter)

| Register | Value | Scale | Type |
|----------|-------|-------|------|
| 0 | `voltageV` × 10 | e.g., 1200 = 120.0 V | signed int16 |
| 1 | `currentA` × 100 | e.g., 1800 = 18.0 A | signed int16 |
| 2 | `powerKw` × 1000 | e.g., 2098 = 2.098 kW | signed int16 |
| 3 | `powerFactor` × 1000 | e.g., 970 = 0.970 | signed int16 |
| 4 | `frequencyHz` × 100 | e.g., 6000 = 60.0 Hz | signed int16 |
| 5 | `temperatureC` × 10 | e.g., 215 = 21.5 °C | signed int16 |
| 6–7 | `energyKwh` converted to Wh, big-endian split | | 2 × int16 |

```yaml
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
  metadata:
    modbusPort: 5020
    modbusUnitId: 1
    modbusRegisterCount: 100
```

---

### `lora`

Ticks the simulator on `intervalSec` and sends an HTTP POST to a LoRa network server or codec endpoint with a binary payload packed as a 3-byte hex string.

**Supported device classes**: `sensorNode`

**Requires `protocolConfig`**:

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `deveui` | Yes | — | LoRa device EUI (16 hex characters). |
| `serverUri` | Yes | — | HTTP endpoint to POST the uplink payload to (e.g., a Cumulocity LoRa codec decode URL). |
| `fport` | No | `1` | LoRa FPort number included in the uplink payload. |
| `deviceProtocolName` | No | `"iot-simulator LoRa SensorNode"` | Protocol name sent in the payload body; used by codec endpoints to select the decoder. |

#### Payload format

The uplink body sent to `serverUri` is a JSON object:

```json
{
  "deveui": "70B3D57ED0001234",
  "payload": "00df32",
  "time": "2026-05-21T10:00:00Z",
  "manufacturer": "Demo Devices",
  "model": "LORA-SN-100",
  "firmwareVersion": "1.0.0",
  "deviceProtocolName": "IoTSimulator LoRa SensorNode"
}
```

The `payload` hex encodes 3 bytes:
- Bytes 0–1: `temperatureC × 10` as signed int16, big-endian
- Byte 2: `humidityPct` as unsigned int8 (clamped 0–255)

```yaml
- deviceId: "lora-sensor-001"
  deviceClass: sensorNode
  protocol: lora
  name: LoRa Sensor Node 001
  intervalSec: 60
  profile:
    startingBatteryPct: 90
    tempMinC: 18.0
    tempMaxC: 25.0
    humidityMinPct: 35
    humidityMaxPct: 60
    batteryDrainPerTickMax: 0.05
  metadata:
    manufacturer: Demo Devices
    model: LORA-SN-100
    firmwareVersion: "1.0.0"
  protocolConfig:
    deveui: "70B3D57ED0001234"
    serverUri: "https://your-tenant.cumulocity.com/service/lora-codec/decode"
    fport: 2
    deviceProtocolName: "IoTSimulator LoRa SensorNode"
```

---

### `lwm2m`

Registers the device with a LwM2M server using CoAP and exposes observable resources. The simulator ticks on `intervalSec`, updates the temperature resource value, and refreshes the registration lifetime. Cumulocity can observe `/3303/{instance}/5700` for temperature readings.

**Supported device classes**: `sensorNode`

**Requires `protocolConfig`**:

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `endpointId` | Yes | — | LwM2M endpoint name used during registration. Must be unique on the server. |
| `serverUri` | Yes | — | CoAP server URI. Use `coap://` for `NO_SEC` and `coaps://` for `PSK`. |
| `securityMode` | Yes | — | `"NO_SEC"` or `"PSK"`. |
| `pskIdentity` | No | `""` | PSK identity string. Required when `securityMode` is `"PSK"`. |
| `pskKeyHex` | No | `""` | PSK key as a hex string. Required when `securityMode` is `"PSK"`. |
| `lifetimeSec` | No | `300` | Registration lifetime in seconds. |
| `bindingMode` | No | `"U"` | LwM2M binding mode. See [Binding modes](#binding-modes) below. |
| `objectModel` | No | See below | Controls which LwM2M objects are advertised during registration. |

#### `objectModel` fields

| Field | Default | Description |
|-------|---------|-------------|
| `includeDeviceObject` | `true` | Advertise Object 3 (Device). Exposes manufacturer, model, firmware, battery, etc. |
| `includeLocationObject` | `false` | Advertise Object 6 (Location). Exposes lat/lng/alt if the asset has a `location` configured. |
| `includeTemperatureObject` | `true` | Advertise Object 3303 (Temperature Sensor). |
| `temperatureInstanceId` | `0` | Instance ID used for the temperature object. Increment if multiple temperature objects are needed. |
| `sendMode` | `"observe"` | How temperature values are delivered. `"observe"` sends a CoAP Notify to active observers each tick. |

#### Binding modes

| Value | Meaning |
|-------|---------|
| `"U"` | UDP (default) |
| `"T"` | TCP |
| `"S"` | DTLS-secured UDP |
| `"UT"` | UDP + TCP |

#### Security modes

| Value | Server URI scheme | Notes |
|-------|------------------|-------|
| `"NO_SEC"` | `coap://` | No security. Works without C extensions on Windows. |
| `"PSK"` | `coaps://` | DTLS pre-shared key. Requires the `DTLSSocket` C extension (`pip install DTLSSocket`; needs C build tools on Windows). |

```yaml
- deviceId: "lwm2m-sensor-001"
  deviceClass: sensorNode
  protocol: lwm2m
  name: LwM2M Sensor Node 001
  intervalSec: 30
  profile:
    startingBatteryPct: 96
    tempMinC: 18.0
    tempMaxC: 24.5
    humidityMinPct: 35
    humidityMaxPct: 55
    batteryDrainPerTickMax: 0.05
  metadata:
    manufacturer: Demo Devices
    model: LWM2M-SN-100
    firmwareVersion: "1.0.0"
  protocolConfig:
    endpointId: "lwm2m-sensor-001"
    serverUri: "coap://lwm2m.eu-latest.cumulocity.com:5783"
    securityMode: "NO_SEC"
    lifetimeSec: 300
    bindingMode: "U"
    objectModel:
      includeDeviceObject: true
      includeLocationObject: false
      includeTemperatureObject: true
      temperatureInstanceId: 0
      sendMode: "observe"
```

To use PSK instead:

```yaml
  protocolConfig:
    endpointId: "lwm2m-sensor-001"
    serverUri: "coaps://lwm2m.eu-latest.cumulocity.com:5784"
    securityMode: "PSK"
    pskIdentity: "your-identity"
    pskKeyHex: "aabbccddeeff00112233445566778899"
    lifetimeSec: 300
    bindingMode: "U"
```

---

## Mixed fleet example

A single `assets.yaml` can contain devices of different classes and protocols running simultaneously:

```yaml
assets:
  - deviceId: "sensor-001"
    deviceClass: sensorNode
    protocol: mqtt
    name: MQTT Sensor
    intervalSec: 10
    profile:
      startingBatteryPct: 85
      tempMinC: 20.0
      tempMaxC: 25.0
      humidityMinPct: 40
      humidityMaxPct: 60
      batteryDrainPerTickMax: 0.2
    metadata:
      manufacturer: Demo Devices
      model: SN-200
      firmwareVersion: "1.0.1"

  - deviceId: "meter-001"
    deviceClass: smartMeter
    protocol: modbus
    name: Building Meter
    intervalSec: 5
    profile:
      startingEnergyKwh: 1000.0
      baseVoltageV: 230.0
      baseCurrentA: 16.0
      baseFrequencyHz: 50.0
      basePowerFactor: 0.95
      voltageVariationV: 3.0
      currentVariationA: 2.5
      frequencyVariationHz: 0.05
      powerFactorDropMax: 0.02
      powerFactorRiseMax: 0.005
    metadata:
      modbusPort: 5020
      modbusUnitId: 1
      modbusRegisterCount: 100

  - deviceId: "lora-001"
    deviceClass: sensorNode
    protocol: lora
    name: LoRa Field Sensor
    intervalSec: 60
    profile:
      startingBatteryPct: 95
      tempMinC: 15.0
      tempMaxC: 30.0
      humidityMinPct: 30
      humidityMaxPct: 70
      batteryDrainPerTickMax: 0.05
    metadata:
      manufacturer: Demo Devices
      model: LORA-SN-100
      firmwareVersion: "1.0.0"
    protocolConfig:
      deveui: "70B3D57ED0001234"
      serverUri: "https://your-tenant.cumulocity.com/service/lora-codec/decode"
      fport: 1
      deviceProtocolName: "IoTSimulator LoRa SensorNode"

  - deviceId: "lwm2m-001"
    deviceClass: sensorNode
    protocol: lwm2m
    name: LwM2M Field Sensor
    intervalSec: 30
    profile:
      startingBatteryPct: 90
      tempMinC: 18.0
      tempMaxC: 26.0
      humidityMinPct: 35
      humidityMaxPct: 65
      batteryDrainPerTickMax: 0.05
    metadata:
      manufacturer: Demo Devices
      model: LWM2M-SN-100
      firmwareVersion: "1.0.0"
    protocolConfig:
      endpointId: "lwm2m-001"
      serverUri: "coap://lwm2m.eu-latest.cumulocity.com:5783"
      securityMode: "NO_SEC"
      lifetimeSec: 300
      bindingMode: "U"
      objectModel:
        includeDeviceObject: true
        includeLocationObject: false
        includeTemperatureObject: true
        temperatureInstanceId: 0
        sendMode: "observe"
```

---

## Extending the simulator

### Adding a new device class

1. Create a simulator class that produces `AssetState` on each `tick()` call.
2. Register it in `core/factories/simulator_factory.py` under a new `deviceClass` string.
3. Add any Modbus register mapping in `adapters/modbus/` if Modbus support is needed.
4. Document the `profile` and `metadata` fields for the new class.

### Adding a new protocol

1. Create a runtime class with a `run_forever()` coroutine.
2. Register it in `core/factories/protocol_runtime_factory.py` under a new `protocol` string.
3. Add any protocol-specific payload encoding in `adapters/`.
4. Document the `protocolConfig` fields for the new protocol.

---

## Architecture summary

```
assets.yaml
    │
    ▼
AssetConfig ──► SimulatorFactory ──► Simulator (SensorNode / SmartMeter)
                                              │
                                           tick()
                                              │
                                         AssetState
                                              │
               ProtocolRuntimeFactory ──► Runtime
                                              │
                    ┌─────────────────────────┼──────────────────────────┐
                    ▼                         ▼                          ▼
              MqttRuntime              ModbusRuntime              LoraRuntime / Lwm2mRuntime
                    │                         │                          │
             Cumulocity REST           Modbus TCP server          HTTP POST / CoAP
```

All runtimes execute concurrently via `asyncio.gather()`.
