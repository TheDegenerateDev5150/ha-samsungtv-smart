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

The blocking HTTP work runs in the executor so the event loop is never blocked.
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
        # Panel presents a self-signed certificate -> disable verification.
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE

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

    def _sync_request(
        self,
        method: str,
        params: dict[str, Any] | None,
        include_token: bool,
        timeout: int,
    ) -> dict[str, Any]:
        """Blocking JSON-RPC request — runs in the executor."""
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
            raw = resp.read().decode("utf-8")
        except (TimeoutError, OSError) as ex:
            raise SamsungIPControlError(
                f"transport failure talking to {self._host}:{self._port}: {ex}"
            ) from ex
        finally:
            conn.close()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as ex:
            raise SamsungIPControlError(f"non-JSON response: {raw!r}") from ex

        error = data.get("error")
        if error is not None:
            code = error.get("code") if isinstance(error, dict) else None
            message = (
                error.get("message", str(error))
                if isinstance(error, dict)
                else str(error)
            )
            if code == ERROR_UNAUTHORIZED:
                raise SamsungIPControlAuthError(f"unauthorized: {message}")
            raise SamsungIPControlError(f"TV returned error {code}: {message}")

        result = data.get("result")
        if not isinstance(result, dict):
            return {}
        return result
