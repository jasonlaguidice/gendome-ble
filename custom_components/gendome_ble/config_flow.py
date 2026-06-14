"""Config flow for Gendome BLE integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak, async_discovered_service_info
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class GendomeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow — handles both BLE auto-discovery and manual setup."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Called by HA when a matching BLE device is discovered."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user to confirm the discovered device."""
        if user_input is not None or self._discovery_info is not None and user_input is None:
            # Auto-confirm when triggered by discovery (no form shown yet) — show confirm form
            if user_input is not None:
                return self._create_entry()

        assert self._discovery_info is not None
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovery_info.name},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual setup: let user pick from currently visible Gendome devices."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            # Find the matching discovery info so we have the BLEDevice object
            for info in async_discovered_service_info(self.hass, connectable=True):
                if info.address == address:
                    self._discovery_info = info
                    break
            return self._create_entry()

        # Build list of visible Gendome devices not already configured
        current = {
            entry.data[CONF_ADDRESS]
            for entry in self._async_current_entries()
            if CONF_ADDRESS in entry.data
        }
        found = {
            info.address: info.name
            for info in async_discovered_service_info(self.hass, connectable=True)
            if info.name and info.name.startswith("Gendome") and info.address not in current
        }

        if not found:
            return self.async_abort(reason="no_devices_found")

        import voluptuous as vol
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In({k: f"{v} ({k})" for k, v in found.items()})}
            ),
        )

    def _create_entry(self) -> ConfigFlowResult:
        assert self._discovery_info is not None
        return self.async_create_entry(
            title=self._discovery_info.name,
            data={CONF_ADDRESS: self._discovery_info.address},
        )
