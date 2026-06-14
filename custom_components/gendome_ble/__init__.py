"""Gendome BLE — Home Assistant integration."""
from __future__ import annotations

import logging

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothCallbackMatcher, BluetoothChange, BluetoothScanningMode, BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .gendome import GendomeDevice

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]

type GendomeConfigEntry = ConfigEntry[GendomeDevice]

_REAPPEAR_KEY = f"{DOMAIN}_reappear_callbacks"


async def async_setup_entry(hass: HomeAssistant, entry: GendomeConfigEntry) -> bool:
    address = entry.data[CONF_ADDRESS]

    if not bluetooth.async_address_present(hass, address, connectable=True):
        _register_reappear_callback(hass, entry, address)
        raise ConfigEntryNotReady(f"Gendome device {address} is not in range")

    _cancel_reappear_callback(hass, entry)

    service_info = bluetooth.async_last_service_info(hass, address, connectable=True)
    device: GendomeDevice | None = getattr(entry, "runtime_data", None)

    if device is None:
        device = GendomeDevice(service_info.device, address)
        entry.runtime_data = device
    else:
        device.update_ble_device(service_info.device)

    try:
        await device.connect()
    except Exception as err:
        _LOGGER.exception("Failed to connect to %s", address)
        await device.disconnect()
        raise ConfigEntryNotReady(f"Could not connect to Gendome: {err}") from err

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    def _on_disconnect(_exc):
        async def _reload():
            await hass.config_entries.async_reload(entry.entry_id)
        hass.async_create_task(_reload())

    entry.async_on_unload(device.on_disconnect(_on_disconnect))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: GendomeConfigEntry) -> bool:
    _cancel_reappear_callback(hass, entry)
    device: GendomeDevice = entry.runtime_data
    await device.disconnect()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _register_reappear_callback(hass: HomeAssistant, entry: ConfigEntry, address: str) -> None:
    callbacks: dict = hass.data.setdefault(_REAPPEAR_KEY, {})
    if entry.entry_id in callbacks:
        return

    def _on_reappear(service_info: BluetoothServiceInfoBleak, change: BluetoothChange) -> None:
        _cancel_reappear_callback(hass, entry)
        hass.config_entries.async_schedule_reload(entry.entry_id)

    cancel = bluetooth.async_register_callback(
        hass,
        _on_reappear,
        BluetoothCallbackMatcher(address=address, connectable=True),
        BluetoothScanningMode.PASSIVE,
    )
    callbacks[entry.entry_id] = cancel


def _cancel_reappear_callback(hass: HomeAssistant, entry: ConfigEntry) -> None:
    callbacks: dict = hass.data.get(_REAPPEAR_KEY, {})
    if cancel := callbacks.pop(entry.entry_id, None):
        cancel()
