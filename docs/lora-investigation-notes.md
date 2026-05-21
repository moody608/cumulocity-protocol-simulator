# LoRaWAN Investigation Notes

## Purpose

These notes capture the findings from the initial investigation into adding LoRaWAN support to the IoT simulator. The goal was to determine whether LoRa support could be added as another protocol runtime similar to MQTT and Modbus, and whether a simulator could be built around the open-source `cumulocity-lora` plugin and The Things Stack (TTN/TTS).[cite:532][cite:536]

## Summary

The investigation found that LoRaWAN support is materially more complex than MQTT or Modbus in this project. The main reason is architectural: Cumulocity LoRa integrations operate through a LoRaWAN Network Server (LNS) integration layer rather than directly against end devices, which introduces connector configuration, provisioning, gateway representation, uplink/downlink event handling, and LNS-specific API behavior.[cite:536][cite:642][cite:532]

At the same time, the open-source `cumulocity-lora` plugin appears old and may no longer work cleanly on the latest Cumulocity version, which raises additional implementation and supportability risk.[page:2]

## What was initially assumed

The initial assumption was that LoRa could be added as another protocol adapter in the same general pattern as MQTT and Modbus. Under that assumption, the simulator would simply need:

- a LoRa protocol runtime,
- payload mapping from `AssetState`,
- and some configuration additions in `assets.yaml`.[cite:530][cite:532]

That assumption turned out to be too simple for LoRaWAN.

## What the architecture actually looks like

The `cumulocity-lora` technical documentation describes the overall flow as:

- physical LoRaWAN devices connect to gateways,
- gateways connect to a LoRaWAN Network Server (LNS),
- and Cumulocity integrates through an LNS integration microservice that processes uplinks/downlinks and calls the LNS APIs.[page:1]

The same documentation describes two major concerns in the framework:

- **LNS connectivity**, which handles integration with the external LNS, and [page:1]
- **device codecs**, which decode uplinks and encode downlinks. [page:1]

This means the plugin is not itself the LNS. It is the connector between Cumulocity and an external LNS.[page:1]

## Implication for simulation

Because of that architecture, a realistic simulator would not primarily be a fake end device. It would need to simulate an **LNS-facing integration surface** and likely enough gateway/device metadata to satisfy the connector.[page:1][page:2]

The working conclusion from the investigation was:

- do **not** start by simulating gateways as the protocol endpoint,
- do **not** try to model LoRa radio behavior,
- instead simulate a fake LNS or TTS-compatible surface if this work is resumed.[page:1][page:2]

## Why The Things Stack was selected as the likely target

Several LoRaWAN network servers are supported by the plugin, including TTN/TTS, ChirpStack, Loriot, Actility, and others.[page:2] Since Loriot and Actility are already supported out of the box in Cumulocity, the investigation focused on The Things Stack as a higher-value target for a simulator proof point.[page:2]

The Things Stack was also treated as a strong candidate because it is one of the most visible LoRaWAN network server ecosystems, while ChirpStack is commonly seen as a leading open-source/self-hosted alternative.[web:648][web:651][web:649]

## Screenshots reviewed

### Connector setup screen

The reviewed connector screen showed fields for:

- Name,
- LoRa network server = `TTN (push mode)`,
- Address,
- API Key,
- Application ID. [file:659]

This strongly suggested that the plugin acts as a client of an external LNS and stores credentials and endpoint configuration for that LNS.[file:659] The use of an API key was not considered a blocker for simulation, because a fake TTS/LNS service can simply accept a chosen static API key value.[file:659]

### Gateway creation screen

A second reviewed screen showed a gateway creation form with fields for:

- Name,
- Gateway Id,
- LoRa network server connector,
- Make status public,
- Frequency Plan. [file:660]

This indicated that gateways are represented as first-class objects in the LoRa plugin UI, most likely for inventory, gateway management, topology, or status views inside Cumulocity.[file:660][page:2] It did **not** change the core conclusion that the integration point is still the LNS rather than a raw gateway protocol surface.[page:1]

## What this means technically

To build a useful LoRaWAN simulator for this path, the likely minimum scope would include:

- an LNS-compatible API surface,
- authentication handling such as API key validation,
- device provisioning and lookup,
- webhook/routing configuration,
- uplink event delivery,
- downlink acceptance and status updates,
- gateway metadata and possibly gateway inventory. [page:1][page:2][file:659][file:660]

That makes the LoRaWAN simulator substantially more involved than MQTT publishing or Modbus register serving.[cite:536]

## Plugin supportability concern

A key practical concern was that the open-source LoRa plugin appears to be aging and may not work cleanly on the latest version of Cumulocity.[page:2] That matters because even a technically sound fake LNS implementation may still fail to provide value if the plugin itself is incompatible with the platform version being used for testing.[page:2]

This also makes reverse engineering more difficult because the expected connector behavior may be harder to validate through the UI if the app is not fully functional in the current tenant environment.[page:2]

## Comparison with MQTT and Modbus

| Protocol path | Main integration model | Relative complexity |
|---------------|------------------------|---------------------|
| MQTT | Direct publish path into platform ingestion/publisher logic.[cite:531] | Lower |
| Modbus | Direct server/client register model with simulator-managed values.[cite:536] | Lower to medium |
| LoRaWAN via plugin | Multi-layer LNS-based integration with connector behavior, codecs, gateway concepts, and external API assumptions.[page:1][page:2] | High |

The conclusion from the investigation was that LoRaWAN does not behave like “just another adapter” in the same sense as MQTT or Modbus.[cite:532][cite:536]

## Recommendation reached during investigation

The recommendation at the end of the investigation was:

- remove LoRa from the **active implementation path**,
- keep any LoRa/TTS design work as archived notes or an experimental branch,
- and avoid presenting LoRa as a currently supported protocol in the main simulator unless a real scoped effort is approved for it.[cite:532][cite:642]

This keeps the main codebase honest while preserving the research already completed.[cite:532]

## Suggested scope if LoRaWAN is revisited later

If LoRaWAN is revisited later, the best re-entry point would be a **fake TTS/LNS shim** rather than a gateway simulator or direct-device adapter.[page:1][page:2] The first milestone should probably be limited to:

1. connector configuration,
2. one provisioned device,
3. one synthetic gateway reference,
4. one uplink event reaching the plugin,
5. optional downlink receipt later. [page:1][page:2]

That would keep the effort bounded as a proof of concept rather than a full LoRaWAN ecosystem simulator.

## Why LwM2M became the better next step

Compared with LoRaWAN, LwM2M appears to be a better next protocol target because it is a more direct client-server integration path into Cumulocity and does not require simulating an LNS ecosystem, gateway layer, or plugin-specific cloud-to-cloud connector behavior.[web:676][web:677] For this simulator project, that makes LwM2M a more realistic next protocol after MQTT and Modbus.[web:676][cite:532]
