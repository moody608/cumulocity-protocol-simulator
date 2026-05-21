# LwM2M 1.1 client for Cumulocity over CoAP using aiocoap.
#
# Install:  pip install "aiocoap[tinydtls]"
#
# Cumulocity LwM2M server URIs (eu-latest):
#   NO_SEC:  coap://lwm2m.eu-latest.cumulocity.com:5783
#   PSK:     coaps://lwm2m.eu-latest.cumulocity.com:5784
#
# Devices must be pre-registered in Cumulocity (CSV or UI) with matching
# endpoint ID, security mode, lifetime, and binding mode before connect().
# No Bootstrap server is used.
#
# Data flow: Observe/Notify.
# 1. connect() builds a CoAP resource tree and starts a server context so
#    Cumulocity can send Observe requests back to the device.
# 2. Registration (POST /rd) tells Cumulocity which objects the device has.
# 3. Cumulocity responds with an Observe GET to /3303/{id}/5700.
# 4. send_report() updates the observable resource; aiocoap delivers a CON
#    Notify to all active observers automatically.
import socket as _socket
from urllib.parse import urlencode, urlparse

import aiocoap
import aiocoap.credentials
import aiocoap.resource as resource
from aiocoap.credentials import DTLS

# aiocoap[tinydtls] ships the Python transport module but needs the DTLSSocket C
# extension at runtime.  If it is absent (common on Windows without build tools),
# create_server_context() silently omits the tinydtls transport, so any coaps://
# request raises NoRequestInterface.  We detect this once at import time.
try:
    import DTLSSocket as _DTLSSocket  # noqa: F401
    _DTLS_AVAILABLE = True
except ImportError:
    _DTLS_AVAILABLE = False

from adapters.lwm2m.sensor_node_mapper import sensor_node_to_resources
from core.models.base import AssetState, Lwm2mObjectModelConfig, Lwm2mProtocolConfig

_MAPPERS = {
    "sensorNode": sensor_node_to_resources,
}


def _local_ipv4() -> str:
    """Return the outbound IPv4 address of this machine.

    Uses a connected (but not actually transmitting) UDP socket so the OS
    selects the correct interface without sending any packets.
    """
    with _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]


class _ObservableFloat(resource.ObservableResource):
    """Single-value observable float resource (e.g. /3303/0/5700).

    Cumulocity sends Observe GET after registration; each call to update()
    triggers a CON Notify to all active observers via aiocoap.
    """

    def __init__(self) -> None:
        super().__init__()
        self._value: float = 0.0

    def update(self, value: float) -> None:
        self._value = value
        self.updated_state()

    async def render_get(self, request):
        payload = f"{self._value:.6g}".encode("ascii")
        return aiocoap.Message(payload=payload, content_format=0)  # text/plain


class Lwm2mClientAdapter:

    def __init__(self, protocol_config: Lwm2mProtocolConfig, log) -> None:
        self.protocol_config = protocol_config
        self._log = log
        self._context: aiocoap.Context | None = None
        self._registration_path: str | None = None
        self._temp_resource: _ObservableFloat | None = None

    async def connect(self) -> None:
        cfg = self.protocol_config
        parsed = urlparse(cfg.server_uri)
        scheme = parsed.scheme.lower()  # "coap" or "coaps"

        om = cfg.object_model or Lwm2mObjectModelConfig()

        # Build CoAP resource tree so Cumulocity can Observe /3303/{id}/5700.
        self._temp_resource = _ObservableFloat()
        site = resource.Site()
        site.add_resource(
            ["3303", str(om.temperature_instance_id), "5700"],
            self._temp_resource,
        )

        # Server context: listens for incoming Observe/Read from Cumulocity
        # and can also send outgoing requests (registration, keepalive).
        # aiocoap's simplesocketserver transport on Windows rejects 0.0.0.0,
        # so we resolve the outbound interface address explicitly.
        bind_ip = _local_ipv4()
        self._context = await aiocoap.Context.create_server_context(
            site, bind=(bind_ip, 5683)
        )
        self._log.info("listening on %s:5683 for Observe requests", bind_ip)

        if scheme == "coaps":
            if not _DTLS_AVAILABLE:
                raise RuntimeError(
                    "coaps:// requires the DTLSSocket C extension which is not installed. "
                    "Fix: pip install DTLSSocket  (needs C build tools on Windows). "
                    "Alternatively use coap:// on port 5783 with securityMode=NO_SEC. "
                    f"(endpoint={cfg.endpoint_id})"
                )
            if cfg.security_mode.upper() != "PSK":
                raise ValueError(
                    f"coaps:// requires security_mode=PSK "
                    f"(endpoint={cfg.endpoint_id}, got {cfg.security_mode})"
                )
            if not cfg.psk_identity or not cfg.psk_key_hex:
                raise ValueError(
                    f"PSK requires psk_identity and psk_key_hex "
                    f"(endpoint={cfg.endpoint_id})"
                )
            host = parsed.hostname
            # Cumulocity PSK port is 5784; Leshan default is 5684.
            port = parsed.port or 5684
            self._context.client_credentials[f"coaps://{host}:{port}/*"] = DTLS(
                psk=bytes.fromhex(cfg.psk_key_hex),
                client_identity=cfg.psk_identity.encode("ascii"),
            )
        # scheme == "coap": NO_SEC — simple6 UDP transport handles it.

        await self._register()

    async def _register(self) -> None:
        # LwM2M 1.1 Register — POST /rd (OMA-TS-LightweightM2M_Core §5.4.2).
        # lwm2m=1.1 required so Cumulocity knows Observe/Notify is supported.
        # Cumulocity matches ep against the pre-registered entry; unknown → 4.03.
        cfg = self.protocol_config
        query = urlencode({
            "ep": cfg.endpoint_id,
            "lt": str(cfg.lifetime_sec),
            "lwm2m": "1.1",
            "b": cfg.binding_mode,
        })

        request = aiocoap.Message(
            code=aiocoap.Code.POST,
            uri=f"{cfg.server_uri.rstrip('/')}/rd?{query}",
            payload=self._object_list().encode("ascii"),
        )
        request.opt.content_format = 40  # application/link-format

        try:
            response = await self._context.request(request).response
        except Exception as exc:
            raise RuntimeError(
                f"LwM2M connect failed "
                f"endpoint={cfg.endpoint_id} server={cfg.server_uri}: {exc}"
            ) from exc

        if not response.code.is_successful():
            raise RuntimeError(
                f"LwM2M registration rejected: {response.code} "
                f"endpoint={cfg.endpoint_id} server={cfg.server_uri}"
            )

        location = response.opt.location_path  # tuple of path segments, e.g. ("rd", "xK9m")
        if not location:
            raise RuntimeError(
                f"No Location-Path in registration response (endpoint={cfg.endpoint_id})"
            )
        self._registration_path = "/" + "/".join(location)
        self._log.info("registered endpoint=%s location=%s", cfg.endpoint_id, self._registration_path)

    def _object_list(self) -> str:
        om = self.protocol_config.object_model or Lwm2mObjectModelConfig()
        links = ["</1/0>"]  # LwM2M Server object — required for Cumulocity pre-registered devices
        if om.include_device_object:
            links.append("</3/0>")
        if om.include_temperature_object:
            links.append(f"</3303/{om.temperature_instance_id}>")
        if om.include_location_object:
            links.append("</6/0>")
        return ",".join(links)

    async def send_report(self, state: AssetState) -> None:
        if not self._context or not self._registration_path:
            return

        cfg = self.protocol_config
        base = cfg.server_uri.rstrip("/")

        # --- 1. Registration Update -------------------------------------------
        # PUT to the registration path (empty body) resets the lifetime timer.
        # Without this, Cumulocity will de-register the device after lifetime_sec.
        try:
            reg_update = aiocoap.Message(
                code=aiocoap.Code.PUT,
                uri=base + self._registration_path,
            )
            await self._context.request(reg_update).response
        except Exception as exc:
            self._log.warning("registration update error endpoint=%s error=%s", cfg.endpoint_id, exc)

        # --- 2. Observable resource update ------------------------------------
        # Calling update() sets the new value and calls notify_change().
        # aiocoap delivers a CON Notify to every active observer automatically.
        # If Cumulocity has not yet sent an Observe for this resource, this is
        # a silent no-op until the first Observe arrives.
        mapper = _MAPPERS.get(state.device_class)
        if mapper is None:
            return

        om = cfg.object_model or Lwm2mObjectModelConfig()
        resources = mapper(
            state,
            include_device_object=om.include_device_object,
            include_temperature_object=om.include_temperature_object,
            temperature_instance_id=om.temperature_instance_id,
            include_location_object=om.include_location_object,
        )

        temp = resources.get((3303, om.temperature_instance_id, 5700))
        if temp is not None:
            self._log.info("report endpoint=%s temp=%sC", cfg.endpoint_id, temp)
            self._temp_resource.update(float(temp))

    async def disconnect(self) -> None:
        cfg = self.protocol_config
        if self._context and self._registration_path:
            try:
                request = aiocoap.Message(
                    code=aiocoap.Code.DELETE,
                    uri=cfg.server_uri.rstrip("/") + self._registration_path,
                )
                await self._context.request(request).response
                self._log.info("de-registered endpoint=%s", cfg.endpoint_id)
            except Exception as exc:
                self._log.warning("de-register error endpoint=%s error=%s (ignored)", cfg.endpoint_id, exc)

        if self._context:
            await self._context.shutdown()
            self._context = None
        self._registration_path = None
