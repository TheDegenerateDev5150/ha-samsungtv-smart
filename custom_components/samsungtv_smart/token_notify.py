"""Persistent-notification helpers for Samsung TV token problems.

Two of the three authentication paths used by this integration have no native
Home Assistant surface for an invalid credential:

  * the local WebSocket token (PAT) on port 8002, and
  * the IP Control AccessToken (JSON-RPC) on port 1516.

When either token is rejected by the TV, the integration would otherwise loop —
re-requesting a local token re-arms the on-screen "Allow to connect?" prompt, and
IP Control calls keep failing silently. These helpers raise a single, stable,
self-clearing persistent notification per (entry, method) so the user knows
exactly which credential is bad and how to fix it.

SmartThings OAuth is deliberately NOT handled here: it already surfaces through
the Repairs issue registry (see media_player._raise_oauth_issue), which is the
native path and auto-clears on a successful refresh.

All functions are Home Assistant callbacks and must run on the event loop. The
threaded WebSocket layer (samsungws) reaches them via run_callback_threadsafe
through media_player's loop-side callbacks, never directly.
"""

from __future__ import annotations

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN

# Token methods that use this maison notification (SmartThings excluded — it
# uses the native Repairs issue registry instead).
METHOD_LOCAL = "local"
METHOD_IP_CONTROL = "ip_control"

_TITLES: dict[str, str] = {
    METHOD_LOCAL: "Samsung TV — local connection not authorized",
    METHOD_IP_CONTROL: "Samsung TV — IP Control token rejected",
}

_MESSAGES: dict[str, str] = {
    METHOD_LOCAL: (
        "The Samsung TV **{device_name}** keeps rejecting the local WebSocket "
        "token, so Home Assistant stopped reconnecting to avoid repeatedly "
        "re-triggering the on-screen authorization prompt.\n\n"
        "To fix it: open **Settings → Devices & services → Samsung TV Smart → "
        "Reconfigure**, leave *reauth_oauth* unchecked, and accept the "
        "authorization prompt **once** on the TV.\n\n"
        "This notification clears automatically once the connection is "
        "authorized again."
    ),
    METHOD_IP_CONTROL: (
        "The IP Control access token for **{device_name}** was rejected by the "
        "TV (unauthorized). IP Control power features (including the reboot "
        "button) are paused until it is re-paired.\n\n"
        "To fix it: re-pair IP Control from the integration options while the "
        "TV is ON and **not** in Art Mode, and accept the prompt on screen.\n\n"
        "This notification clears automatically once IP Control works again."
    ),
}


def _notification_id(entry_id: str, method: str) -> str:
    """Build a stable notification id so re-raising never spams the user."""
    return f"{DOMAIN}_token_{method}_{entry_id}"


@callback
def notify_token_problem(
    hass: HomeAssistant,
    entry_id: str,
    method: str,
    device_name: str,
) -> None:
    """Raise (or refresh) the persistent notification for a bad token."""
    if method not in _MESSAGES:
        return
    persistent_notification.async_create(
        hass,
        _MESSAGES[method].format(device_name=device_name),
        title=_TITLES[method],
        notification_id=_notification_id(entry_id, method),
    )


@callback
def clear_token_problem(hass: HomeAssistant, entry_id: str, method: str) -> None:
    """Dismiss the persistent notification once the token works again."""
    persistent_notification.async_dismiss(hass, _notification_id(entry_id, method))
