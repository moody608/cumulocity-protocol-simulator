import json
from datetime import timezone

import paho.mqtt.client as mqtt
import requests


class C8yMqttPublisher:
    def __init__(self, cfg: dict, mapping_cfg: dict):
        self.base_url = cfg["base_url"].rstrip("/")
        self.tenant = cfg["tenant"]
        self.username = cfg["username"]
        self.password = cfg["password"]
        self.client_id = cfg.get("client_id", "iot-simulator")
        self.external_id_type = cfg.get("external_id_type", "c8y_Serial")
        self.device_type = cfg.get("device_type", "demo_Device")
        self.mqtt_host = cfg.get(
            "mqtt_host",
            self.base_url.replace("https://", "").replace("http://", "")
        )
        self.mqtt_port = cfg.get("mqtt_port", 1883)
        self.request_timeout = cfg.get("request_timeout", 30)

        self.client = mqtt.Client(
            client_id=self.client_id,
            protocol=mqtt.MQTTv311
        )
        self.client.username_pw_set(f"{self.tenant}/{self.username}", self.password)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

        self.measurement_map = mapping_cfg.get("measurements", {})
        self.measurement_defaults = mapping_cfg.get("defaults", {}).get("measurement", {})
        self.alarm_mapping = mapping_cfg.get("alarms", {})
        self.event_mapping = mapping_cfg.get("events", {})
        self.inventory_mapping = mapping_cfg.get("inventory", {})

        self.known_devices = {}

    def on_connect(self, client, userdata, flags, rc):
        print(f"MQTT connected with result code {rc}")

    def on_disconnect(self, client, userdata, rc):
        print(f"MQTT disconnected with result code {rc}")

    def connect(self):
        self.client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
        self.client.loop_start()

    def disconnect(self):
        try:
            self.client.loop_stop()
        finally:
            self.client.disconnect()
            self.session.close()

    def ensure_device(self, state):
        if state.device_id in self.known_devices:
            return self.known_devices[state.device_id]

        mo_id = self.get_managed_object_id(state.device_id)
        if mo_id:
            self.patch_managed_object(mo_id, state)
            self.known_devices[state.device_id] = mo_id
            return mo_id

        mo_id = self.create_device_managed_object(state)
        self.create_external_id(mo_id, state.device_id)
        self.patch_managed_object(mo_id, state)

        self.known_devices[state.device_id] = mo_id
        return mo_id

    def get_managed_object_id(self, external_id: str):
        url = f"{self.base_url}/identity/externalIds/{self.external_id_type}/{external_id}"
        r = self.session.get(url, timeout=self.request_timeout)

        if r.status_code == 200:
            body = r.json()
            return body["managedObject"]["id"]

        if r.status_code == 404:
            return None

        r.raise_for_status()

    def create_device_managed_object(self, state):
        url = f"{self.base_url}/inventory/managedObjects"

        body = {
            "name": state.identity["name"],
            "type": self.device_type,
            "c8y_IsDevice": {},
            "com_cumulocity_model_Agent": {},
            "c8y_Hardware": {
                "model": state.identity.get("model", ""),
                "serialNumber": state.identity.get("serialNumber", state.device_id),
                "revision": state.identity.get("hardwareRevision", "")
            },
            "c8y_Firmware": {
                "version": state.identity.get("firmwareVersion", "")
            },
            "demo_DeviceInfo": {
                "deviceClass": state.device_class,
                "manufacturer": state.identity.get("manufacturer", "")
            },
            "demo_Operational": state.operational,
            "demo_Service": state.service,
            "demo_Compliance": state.compliance
        }

        if state.location:
            body["c8y_Position"] = {
                "lat": state.location["lat"],
                "lng": state.location["lng"],
                "alt": state.location.get("alt")
            }

        r = self.session.post(
            url,
            data=json.dumps(body),
            timeout=self.request_timeout
        )
        r.raise_for_status()
        return r.json()["id"]

    def create_external_id(self, mo_id: str, external_id: str):
        url = f"{self.base_url}/identity/globalIds/{mo_id}/externalIds"
        body = {
            "externalId": external_id,
            "type": self.external_id_type
        }

        r = self.session.post(
            url,
            data=json.dumps(body),
            timeout=self.request_timeout
        )

        if r.status_code not in (201, 409):
            r.raise_for_status()

    def patch_managed_object(self, mo_id: str, state):
        url = f"{self.base_url}/inventory/managedObjects/{mo_id}"

        body = {
            "name": state.identity["name"],
            "type": self.device_type,
            "c8y_Hardware": {
                "model": state.identity.get("model", ""),
                "serialNumber": state.identity.get("serialNumber", state.device_id),
                "revision": state.identity.get("hardwareRevision", "")
            },
            "c8y_Firmware": {
                "version": state.identity.get("firmwareVersion", "")
            },
            "demo_DeviceInfo": {
                "deviceClass": state.device_class,
                "manufacturer": state.identity.get("manufacturer", "")
            },
            "demo_Operational": state.operational,
            "demo_Service": state.service,
            "demo_Compliance": state.compliance
        }

        if state.location:
            body["c8y_Position"] = {
                "lat": state.location["lat"],
                "lng": state.location["lng"],
                "alt": state.location.get("alt")
            }

        r = self.session.put(
            url,
            data=json.dumps(body),
            timeout=self.request_timeout
        )
        r.raise_for_status()

    def publish_measurements(self, state):
        mo_id = self.ensure_device(state)
        payload = self.build_measurement_payload(state, mo_id)

        if not payload:
            return

        url = f"{self.base_url}/measurement/measurements"
        r = self.session.post(
            url,
            data=json.dumps(payload),
            timeout=self.request_timeout
        )
        r.raise_for_status()

    def build_measurement_payload(self, state, mo_id: str):
        telemetry = state.telemetry or {}
        if not telemetry:
            return None

        payload = {
            "time": state.timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "type": self.resolve_measurement_type(telemetry),
            "source": {"id": str(mo_id)}
        }

        added = False

        for field_name, raw_value in telemetry.items():
            if raw_value is None:
                continue

            if isinstance(raw_value, bool):
                continue

            if not isinstance(raw_value, (int, float)):
                continue

            mapping = self.measurement_map.get(field_name)

            if mapping:
                fragment = mapping["fragment"]
                series = mapping["series"]
                unit = mapping.get("unit", self.measurement_defaults.get("unit", "value"))
            else:
                fragment = self.measurement_defaults.get("fragment", "demo_Custom")
                series = field_name
                unit = self.measurement_defaults.get("unit", "value")

            if fragment not in payload:
                payload[fragment] = {}

            payload[fragment][series] = {
                "value": raw_value,
                "unit": unit
            }
            added = True

        if not added:
            return None

        return payload

    def resolve_measurement_type(self, telemetry: dict):
        types = []
        for field_name in telemetry.keys():
            mapping = self.measurement_map.get(field_name)
            if mapping and "type" in mapping:
                types.append(mapping["type"])

        if not types:
            return self.measurement_defaults.get("type", "demo_GenericMeasurement")

        if len(set(types)) == 1:
            return types[0]

        return "demo_MixedMeasurement"

    def publish_alarms(self, state):
        mo_id = self.ensure_device(state)

        for alarm in state.alarms:
            mapped = self.alarm_mapping.get(alarm.type, {})

            alarm_type = mapped.get("type", alarm.type)
            severity = mapped.get("severity", alarm.severity)
            status = mapped.get("status", alarm.status)

            template = mapped.get("text")
            details = alarm.details or {}

            if alarm.text:
                text = alarm.text
            elif template:
                try:
                    text = template.format_map(details)
                except KeyError:
                    text = template
            else:
                text = alarm.type

            payload = {
                "source": {"id": str(mo_id)},
                "type": alarm_type,
                "text": text,
                "severity": severity,
                "status": status,
                "time": alarm.time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            }

            if details:
                payload["details"] = details

            url = f"{self.base_url}/alarm/alarms"
            r = self.session.post(
                url,
                data=json.dumps(payload),
                timeout=self.request_timeout
            )
            r.raise_for_status()

    def publish_event(self, state, event_type: str, text: str, extra: dict | None = None):
        mo_id = self.ensure_device(state)

        payload = {
            "source": {"id": str(mo_id)},
            "type": event_type,
            "text": text,
            "time": state.timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        }

        if extra:
            payload.update(extra)

        url = f"{self.base_url}/event/events"
        r = self.session.post(
            url,
            data=json.dumps(payload),
            timeout=self.request_timeout
        )
        r.raise_for_status()

    def clear_cache(self):
        self.known_devices = {}

    def refresh_device(self, state):
        mo_id = self.get_managed_object_id(state.device_id)
        if mo_id:
            self.patch_managed_object(mo_id, state)
            self.known_devices[state.device_id] = mo_id
            return mo_id
        return self.ensure_device(state)