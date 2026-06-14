"""Base entity for Gendome BLE integration."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, MANUFACTURER, MODEL
from .gendome import GendomeDevice


class GendomeEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: GendomeDevice, prop: str) -> None:
        self._device = device
        self._prop = prop
        self._attr_unique_id = f"{device.address}_{prop}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.address)},
            connections={(CONNECTION_BLUETOOTH, self._device.address)},
            name=self._device.name,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def available(self) -> bool:
        return self._device.is_connected and getattr(self._device, self._prop) is not None

    @callback
    def _handle_state_update(self, _value: Any) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self._device.register_state_update_callback(self._handle_state_update, self._prop)

    async def async_will_remove_from_hass(self) -> None:
        self._device.remove_state_update_callback(self._handle_state_update, self._prop)
