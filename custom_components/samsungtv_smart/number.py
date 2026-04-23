"""Samsung TV Smart - Number entities for Frame TV Art Mode.

Provides interactive Number entities (sliders in HA UI) for:
- Art Mode brightness (0-100)
- Art Mode color temperature (-5 to +5)

Both wrap the existing art_api methods and only appear on Frame TVs.
"""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_ID, CONF_NAME, CONF_PORT, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er

from .api.art import SamsungTVAsyncArt
from .const import (
    CONF_IS_FRAME_TV,
    CONF_WS_NAME,
    DATA_ART_API,
    DATA_CFG,
    DEFAULT_PORT,
    DOMAIN,
    WS_PREFIX,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Samsung TV number entities from config entry."""
    config = hass.data[DOMAIN][entry.entry_id][DATA_CFG]
    host = config[CONF_HOST]
    port = config.get(CONF_PORT, DEFAULT_PORT)
    token = config.get(CONF_TOKEN)
    ws_name = config.get(CONF_WS_NAME, "HomeAssistant")
    device_unique_id = config.get(CONF_ID, entry.entry_id)
    device_name = config.get(CONF_NAME) or entry.title or host

    session = async_get_clientsession(hass)

    # Reuse shared art_api if already created by sensor.py / select.py,
    # otherwise create one (same pattern as select.py).
    art_api = hass.data[DOMAIN][entry.entry_id].get(DATA_ART_API)
    if not art_api:
        art_api = SamsungTVAsyncArt(
            host=host,
            port=port,
            token=token,
            session=session,
            timeout=5,
            name=f"{WS_PREFIX} {ws_name} Art Number",
        )

    # Use persisted flag if available, otherwise probe live
    is_frame_tv_cached = entry.data.get(CONF_IS_FRAME_TV, False)
    if is_frame_tv_cached:
        is_frame_supported = True
    else:
        try:
            async with asyncio.timeout(5):
                is_frame_supported = await art_api.supported()
        except Exception:
            is_frame_supported = False

    if not is_frame_supported:
        _LOGGER.debug(
            "Not a Frame TV, skipping art number entities for %s", device_name
        )
        return

    entities = [
        SamsungTVArtBrightnessNumber(
            hass, entry, art_api, device_name, device_unique_id
        ),
        SamsungTVArtColorTemperatureNumber(
            hass, entry, art_api, device_name, device_unique_id
        ),
    ]
    async_add_entities(entities)
    _LOGGER.debug(
        "Frame Art number entities (brightness, color temperature) created for %s",
        device_name,
    )


# ══════════════════════════════════════════════════════════════════════════
# Base class
# ══════════════════════════════════════════════════════════════════════════


class SamsungTVArtNumberBase(NumberEntity):
    """Base class for Samsung Frame TV Art Mode number entities."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        art_api: SamsungTVAsyncArt,
        device_name: str,
        device_unique_id: str,
    ) -> None:
        self.hass = hass
        self._entry = entry
        self._art_api = art_api
        self._device_name = device_name
        self._device_unique_id = device_unique_id
        self._attr_native_value: float | None = None
        self._media_player_entity_id: str | None = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_unique_id)},
            name=self._device_name,
        )

    def _is_tv_in_art_mode(self) -> bool:
        """Return True only if the media_player is on and in Art Mode.

        Checks the HA state of the media_player entity for this config entry.
        This avoids hitting the WebSocket Art API when the TV is off/standby,
        which would cause async_update to block for the full timeout duration
        and trigger HA's '> 10 seconds' warning.
        """
        if self._media_player_entity_id is None:
            entity_registry = er.async_get(self.hass)
            for entity in entity_registry.entities.values():
                if (
                    entity.config_entry_id == self._entry.entry_id
                    and entity.domain == "media_player"
                ):
                    self._media_player_entity_id = entity.entity_id
                    break

        if not self._media_player_entity_id:
            return False

        state = self.hass.states.get(self._media_player_entity_id)
        if state is None:
            return False

        # Art Mode brightness/color temp are only meaningful (and readable) when
        # the TV is actually in Art Mode.  The media_player state is "on" both
        # for normal TV use and Art Mode; we use the "art_mode" attribute that
        # the sensor/media_player exposes to distinguish them.
        # Fall back to just checking "on" so we still poll when art_mode attr
        # is absent (e.g. older firmware or attribute not yet populated).
        if state.state in ("off", "unavailable", "unknown"):
            return False

        art_mode_attr = state.attributes.get("art_mode")
        if art_mode_attr is not None:
            return bool(art_mode_attr)

        # art_mode attribute not present — TV is on, allow polling
        return True


# ══════════════════════════════════════════════════════════════════════════
# Brightness (0-100, mapped to TV's 1-10 scale)
# ══════════════════════════════════════════════════════════════════════════


class SamsungTVArtBrightnessNumber(SamsungTVArtNumberBase):
    """Number entity for Art Mode brightness (0-100, mapped to TV 1-10)."""

    _attr_icon = "mdi:brightness-6"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 10
    _attr_native_unit_of_measurement = "%"

    def __init__(self, hass, entry, art_api, device_name, device_unique_id):
        super().__init__(hass, entry, art_api, device_name, device_unique_id)
        self._attr_unique_id = f"{device_unique_id}_art_brightness"
        self._attr_name = "Art Mode Brightness"

    async def async_set_native_value(self, value: float) -> None:
        """Set brightness on the TV.

        Accepts 0-100 from UI, converts to TV's 1-10 scale.
        """
        ui_brightness = int(value)
        if ui_brightness == 0:
            tv_brightness = 0
        else:
            tv_brightness = max(1, min(10, round(ui_brightness / 10)))
        try:
            _LOGGER.debug(
                "Frame Art: Setting brightness UI=%d -> TV=%d",
                ui_brightness,
                tv_brightness,
            )
            await self._art_api.set_brightness(tv_brightness)
            self._attr_native_value = ui_brightness
            self.async_write_ha_state()
        except Exception as ex:
            _LOGGER.error("Error setting art mode brightness: %s", ex)

    async def async_update(self) -> None:
        """Read current brightness from TV (TV scale 1-10) and convert to 0-100."""
        if not self._is_tv_in_art_mode():
            return
        try:
            async with asyncio.timeout(5):
                result = await self._art_api.get_brightness()
            if result is not None:
                # API may return a dict {"value": N} or a raw int depending on path
                tv_value = result.get("value") if isinstance(result, dict) else result
                if tv_value is not None:
                    self._attr_native_value = int(tv_value) * 10
        except Exception as ex:
            _LOGGER.debug("Could not refresh art mode brightness: %s", ex)


# ══════════════════════════════════════════════════════════════════════════
# Color Temperature (-5 to +5, native TV scale)
# ══════════════════════════════════════════════════════════════════════════


class SamsungTVArtColorTemperatureNumber(SamsungTVArtNumberBase):
    """Number entity for Art Mode color temperature (-5 = warm to +5 = cool)."""

    _attr_icon = "mdi:thermometer"
    _attr_native_min_value = -5
    _attr_native_max_value = 5
    _attr_native_step = 1

    def __init__(self, hass, entry, art_api, device_name, device_unique_id):
        super().__init__(hass, entry, art_api, device_name, device_unique_id)
        self._attr_unique_id = f"{device_unique_id}_art_color_temperature"
        self._attr_name = "Art Mode Color Temperature"

    async def async_set_native_value(self, value: float) -> None:
        """Set color temperature on the TV (-5 to +5)."""
        ct_value = int(value)
        try:
            _LOGGER.debug("Frame Art: Setting color temperature to %d", ct_value)
            await self._art_api.set_color_temperature(ct_value)
            self._attr_native_value = ct_value
            self.async_write_ha_state()
        except Exception as ex:
            _LOGGER.error("Error setting art mode color temperature: %s", ex)

    async def async_update(self) -> None:
        """Read current color temperature from TV."""
        if not self._is_tv_in_art_mode():
            return
        try:
            async with asyncio.timeout(5):
                result = await self._art_api.get_color_temperature()
            if result is not None:
                tv_value = result.get("value") if isinstance(result, dict) else result
                if tv_value is not None:
                    self._attr_native_value = int(tv_value)
        except Exception as ex:
            _LOGGER.debug("Could not refresh art mode color temperature: %s", ex)
