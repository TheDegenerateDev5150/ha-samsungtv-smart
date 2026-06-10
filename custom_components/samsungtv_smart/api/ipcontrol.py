"""Samsung IP Control (JSON-RPC) client.

Talks to recent Samsung TVs over the undocumented JSON-RPC interface on
HTTPS port 1516. This is used as a reliable, SmartThings-free power path on
Frame TVs: the WebSocket KEY_POWER command only toggles between normal viewing
and Art Mode, whereas `powerControl` issues an explicit hardware on/off that
works from any state (including Art Mode).

Protocol notes (confirmed on Frame 2024 / 2025):
  * HTTPS POST to https://<ip>:1516/ with a self-signed certificate (no verify).
  * Only Accept + Content-Type headers are sent.
  * Two-step auth: `createAccessToken` returns a token after the user accepts an
    on-screen prompt; the token is then passed in `params.AccessToken` on every
    later call. The token persists across power cycles (pair once).
  * Pairing only works while the TV is OUT of Art Mode; in Art Mode the endpoint
    does not respond and the request times out.
  * The TV must have "IP Remote" enabled
    (Settings -> Connections -> Network -> Expert Settings).
  * Older Samsung TVs (Tizen <= 5.5, ~2020 Frames) negotiate a weak DH group
    that OpenSSL's default security level rejects ("dh key too small"). The
    client detects this and transparently retries with @SECLEVEL=1.

The blocking HTTP work runs in the executor so the event loop is never blocked.
The SSL context is also built lazily inside the executor — `create_default_context`
loads CA certs from disk, which would block the event loop if done at __init__.
"""

from __future__ import annotations

import http.client
import json
import logging
import ssl
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

DEFAULT_IP_CONTROL_PORT = 1516
JSONRPC_VERSION = "2.0"

CMD_TIMEOUT = 5  # seconds for normal commands
PAIR_TIMEOUT = 30  # seconds: pairing waits for the on-screen acceptance

# JSON-RPC error code returned when the access token is missing/expired.
ERROR_UNAUTHORIZED = -32010
# JSON-RPC "Parse error". Our requests are always well-formed JSON, and the 32"
# and other calls succeed, so in practice this firmware returns -32700 when the
# AccessToken is stale/unrecognized: a fresh pairing always clears it. Treated
# as an auth error (re-pair required) when a token was actually sent.
ERROR_PARSE_STALE_TOKEN = -32700


class SamsungIPControlError(Exception):
    """Base error for IP Control communication failures."""


class SamsungIPControlAuthError(SamsungIPControlError):
    """The access token is missing, invalid or expired — re-pairing is required."""


class SamsungIPControl:
    """Minimal async client for the Samsung IP Control JSON-RPC interface."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        *,
        port: int = DEFAULT_IP_CONTROL_PORT,
        token: str | None = None,
    ) -> None:
        """Initialize the client."""
        self._hass = hass
        self._host = host
        self._port = port
        self._token = token
        # SSL context is built lazily inside the executor (see _build_ssl_context).
        # `ssl.create_default_context()` loads CA certificates from disk, which
        # blocks the event loop — HA raises a warning if that happens here.
        self._ctx: ssl.SSLContext | None = None
        # Older TVs (Tizen <= 5.5, ~2020 Frames) negotiate a weak DH group and
        # are rejected by OpenSSL's default security level. When that happens
        # we retry once with @SECLEVEL=1 and remember it for subsequent calls.
        self._tls_legacy = False

    @property
    def token(self) -> str | None:
        """Return the current access token, if any."""
        return self._token

    def set_token(self, token: str | None) -> None:
        """Update the stored access token."""
        self._token = token

    # -- public API ----------------------------------------------------------

    async def async_pair(self) -> str:
        """Create and store an access token. TV must be OUT of Art Mode."""
        result = await self._async_request(
            "createAccessToken", include_token=False, timeout=PAIR_TIMEOUT
        )
        token = result.get("AccessToken")
        if not token or not isinstance(token, str):
            raise SamsungIPControlError(f"no AccessToken in response: {result!r}")
        self._token = token
        return token

    async def async_get_power_state(self) -> str:
        """Return 'powerOn' or 'powerOff'. A TV in Art Mode reports 'powerOn'."""
        result = await self._async_request("powerControl")
        return result.get("power", "unknown")

    async def async_power_on(self) -> str:
        """Power the TV on (returns into its last state, e.g. Art Mode)."""
        result = await self._async_request("powerControl", {"power": "powerOn"})
        return result.get("power", "unknown")

    async def async_power_off(self) -> str:
        """Power the TV off (works from Art Mode)."""
        result = await self._async_request("powerControl", {"power": "powerOff"})
        return result.get("power", "unknown")

    async def async_reboot(self) -> str:
        """Reboot the TV.

        Uses the same ``powerControl`` method as power on/off, with the
        ``reboot`` argument (confirmed empirically on Frame 2024/2025). The
        access token survives the reboot, so no re-pairing is needed afterwards.
        Issued over the JSON-RPC channel (port 1516), which is independent of
        the WebSocket channels — so it still lands when the Art WebSocket has
        gone unresponsive ("zombie"), making it a recovery path for that case.
        """
        result = await self._async_request("powerControl", {"power": "reboot"})
        return result.get("power", "unknown")

    async def async_get_art_mode(self) -> bool | None:
        """Return whether the TV is currently in Art Mode.

        Returns ``True`` if in Art Mode, ``False`` if in normal viewing, and
        ``None`` if the TV returned an unexpected value (e.g. firmware update
        changed the protocol). Raises on transport/auth errors.

        Calls ``artModeControl`` with no ``artMode`` parameter — the same
        method then behaves as a getter, returning ``{"artMode": "artModeOn"}``
        or ``{"artMode": "artModeOff"}``. This is the authoritative local read
        for the Frame's Art Mode state, independent of the WebSocket art
        channel (which goes silent when the TV powers off) and of any cached
        ``art_api.art_mode`` value the integration may be holding.

        PowerState is checked first and wins: in true standby the artModeControl
        getter still returns the LAST value (typically ``artModeOn``), which
        would wrongly report Art Mode as active after a restart. A powered-off
        TV is never in Art Mode, so ``powerOff`` short-circuits to ``False``
        without consulting artModeControl. (Art Mode itself reports
        ``powerOn``, so it is unaffected.)
        """
        if await self.async_get_power_state() == "powerOff":
            return False
        result = await self._async_request("artModeControl")
        art_mode = result.get("artMode")
        if art_mode == "artModeOn":
            return True
        if art_mode == "artModeOff":
            return False
        return None

    async def async_set_art_mode_on(self) -> None:
        """Switch the TV to Art Mode."""
        await self._async_request("artModeControl", {"artMode": "artModeOn"})

    async def async_set_art_mode_off(self) -> None:
        """Switch the TV out of Art Mode, back to normal viewing.

        Combined with :meth:`async_power_on`, this gives a deterministic path
        to normal viewing: ``power_on`` lands the TV in Art Mode, then
        ``set_art_mode_off`` exits to live content.
        """
        await self._async_request("artModeControl", {"artMode": "artModeOff"})

    # -- transport -----------------------------------------------------------

    async def _async_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        include_token: bool = True,
        timeout: int = CMD_TIMEOUT,
    ) -> dict[str, Any]:
        """Run a JSON-RPC request in the executor and return the `result` dict."""
        return await self._hass.async_add_executor_job(
            self._sync_request, method, params, include_token, timeout
        )

    def _build_ssl_context(self, legacy: bool) -> ssl.SSLContext:
        """Build the SSL context for talking to the TV.

        Does file system I/O (CA cert loading) — must only be called from the
        executor, never on the event loop.

        :param legacy: when ``True``, lower OpenSSL's security level so the
            handshake accepts the weak DH group used by older Samsung TVs
            (Tizen <= 5.5, ~2020 Frames).
        """
        ctx = ssl.create_default_context()
        # Panels present a self-signed certificate.
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        if legacy:
            try:
                ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
            except ssl.SSLError as ex:
                _LOGGER.warning(
                    "Could not lower TLS security level for %s: %s", self._host, ex
                )
        return ctx

    def _sync_request(
        self,
        method: str,
        params: dict[str, Any] | None,
        include_token: bool,
        timeout: int,
    ) -> dict[str, Any]:
        """Blocking JSON-RPC request — runs in the executor.

        Retries once with @SECLEVEL=1 on a "dh key too small" SSL error so the
        client transparently handles older Samsung TVs.
        """
        body: dict[str, Any] = {
            "jsonrpc": JSONRPC_VERSION,
            "id": 1,
            "method": method,
        }
        if include_token:
            if not self._token:
                raise SamsungIPControlAuthError("no access token — pairing required")
            merged: dict[str, Any] = {"AccessToken": self._token}
            if params:
                merged.update(params)
            body["params"] = merged
        elif params:
            body["params"] = params

        payload = json.dumps(body).encode("utf-8")
        raw = self._sync_post(payload, timeout)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as ex:
            raise SamsungIPControlError(f"non-JSON response: {raw!r}") from ex

        # The TV reports JSON-RPC errors in TWO shapes: the spec-compliant
        # nested {"error": {"code", "message"}}, AND a flat top-level form
        # {"code": -32700, "message": "Parse error"} with no "result" key
        # (observed e.g. when the AccessToken is stale/invalid). The flat form
        # must be detected explicitly, otherwise a real error slips through as
        # a fake empty success.
        error = data.get("error")
        if error is None and "code" in data and "result" not in data:
            error = {"code": data.get("code"), "message": data.get("message")}
        if error is not None:
            code = error.get("code") if isinstance(error, dict) else None
            message = (
                error.get("message", str(error))
                if isinstance(error, dict)
                else str(error)
            )
            if code == ERROR_UNAUTHORIZED or (
                code == ERROR_PARSE_STALE_TOKEN and include_token
            ):
                raise SamsungIPControlAuthError(
                    f"token rejected (code {code}): {message} — re-pair required"
                )
            raise SamsungIPControlError(f"TV returned error {code}: {message}")

        result = data.get("result")
        if not isinstance(result, dict):
            return {}
        return result

    def _sync_post(self, payload: bytes, timeout: int) -> str:
        """Issue the HTTPS POST and return the raw response body.

        Builds the SSL context lazily in the executor; retries once with a
        lowered TLS security level on a "dh key too small" error so the client
        works on older Samsung TVs (Tizen <= 5.5).
        """
        for attempt in (0, 1):
            if self._ctx is None:
                self._ctx = self._build_ssl_context(legacy=self._tls_legacy)
            conn = http.client.HTTPSConnection(
                self._host, self._port, timeout=timeout, context=self._ctx
            )
            try:
                # Keep headers minimal: Host (auto) + Content-Length + Accept +
                # Content-Type. skip_accept_encoding suppresses the default
                # "Accept-Encoding: identity" header.
                conn.putrequest("POST", "/", skip_accept_encoding=True)
                conn.putheader("Accept", "application/json")
                conn.putheader("Content-Type", "application/json")
                conn.putheader("Content-Length", str(len(payload)))
                conn.endheaders()
                conn.send(payload)
                resp = conn.getresponse()
                return resp.read().decode("utf-8")
            except ssl.SSLError as ex:
                if (
                    attempt == 0
                    and not self._tls_legacy
                    and "dh key too small" in str(ex).lower()
                ):
                    _LOGGER.debug(
                        "TLS DH key too small from %s — retrying with legacy "
                        "security level",
                        self._host,
                    )
                    self._tls_legacy = True
                    self._ctx = None
                    continue
                raise SamsungIPControlError(
                    f"TLS error talking to {self._host}:{self._port}: {ex}"
                ) from ex
            except (TimeoutError, OSError) as ex:
                raise SamsungIPControlError(
                    f"transport failure talking to {self._host}:{self._port}: {ex}"
                ) from ex
            finally:
                conn.close()
        # Loop only retries on the DH error and re-enters; any other path either
        # returns or raises, so reaching here means both attempts somehow fell
        # through without raising — treat as a generic error rather than crash.
        raise SamsungIPControlError("IP Control request failed after retry")
