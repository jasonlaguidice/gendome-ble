"""Binary sensor entities for Gendome BLE (fault and warning status)."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GendomeConfigEntry
from .entity import GendomeEntity
from .gendome import GendomeDevice


@dataclass(frozen=True, kw_only=True)
class GendomeBinarySensorDescription(BinarySensorEntityDescription):
    prop: str = ""


BINARY_SENSORS: tuple[GendomeBinarySensorDescription, ...] = (
    GendomeBinarySensorDescription(
        key="fault_main_board",
        prop="fault_main_board",
        name="Main Board Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeBinarySensorDescription(
        key="fault_battery",
        prop="fault_battery",
        name="Battery Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeBinarySensorDescription(
        key="fault_inverter",
        prop="fault_inverter",
        name="Inverter Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeBinarySensorDescription(
        key="fault_pack_a",
        prop="fault_pack_a",
        name="Pack A Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeBinarySensorDescription(
        key="fault_pack_b",
        prop="fault_pack_b",
        name="Pack B Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeBinarySensorDescription(
        key="warn_battery",
        prop="warn_battery",
        name="Battery Warning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GendomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    device: GendomeDevice = entry.runtime_data
    async_add_entities(GendomeBinarySensor(device, desc) for desc in BINARY_SENSORS)


class GendomeBinarySensor(GendomeEntity, BinarySensorEntity):
    def __init__(self, device: GendomeDevice, description: GendomeBinarySensorDescription) -> None:
        super().__init__(device, description.prop)
        self.entity_description = description
        self._attr_unique_id = f"{device.address}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        return getattr(self._device, self._prop, None)
