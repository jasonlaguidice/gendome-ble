"""Number (slider/box) entities for Gendome BLE."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Awaitable, Callable

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GendomeConfigEntry
from .entity import GendomeEntity
from .gendome import GendomeDevice


@dataclass(frozen=True, kw_only=True)
class GendomeNumberDescription(NumberEntityDescription):
    prop: str = ""
    set_fn: Callable[[GendomeDevice, float], Awaitable[None]] = lambda d, v: None


NUMBERS: tuple[GendomeNumberDescription, ...] = (
    GendomeNumberDescription(
        key="ac_charge_power",
        prop="ac_charge_power",
        name="AC Charge Power",
        device_class=NumberDeviceClass.POWER,
        native_min_value=500,
        native_max_value=1800,
        native_step=100,
        native_unit_of_measurement=UnitOfPower.WATT,
        mode=NumberMode.SLIDER,
        set_fn=lambda d, v: d.async_set_ac_charge_power(v),
    ),
    GendomeNumberDescription(
        key="bms_protect_min",
        prop="bms_protect_min",
        name="Battery Discharge Floor",
        native_min_value=0,
        native_max_value=30,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        set_fn=lambda d, v: d.async_set_bms_protect_min(v),
    ),
    GendomeNumberDescription(
        key="bms_protect_max",
        prop="bms_protect_max",
        name="Battery Charge Ceiling",
        native_min_value=70,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        set_fn=lambda d, v: d.async_set_bms_protect_max(v),
    ),
    GendomeNumberDescription(
        key="light_brightness",
        prop="light_brightness",
        name="Light Brightness",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        set_fn=lambda d, v: d.async_set_light_brightness(v),
    ),
    GendomeNumberDescription(
        key="screen_brightness",
        prop="screen_brightness",
        name="Screen Brightness",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        set_fn=lambda d, v: d.async_set_screen_brightness(v),
    ),
    GendomeNumberDescription(
        key="screen_sleep_time",
        prop="screen_sleep_time",
        name="Screen Sleep Time",
        device_class=NumberDeviceClass.DURATION,
        native_min_value=0,
        native_max_value=60,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        mode=NumberMode.BOX,
        set_fn=lambda d, v: d.async_set_screen_sleep(v),
    ),
    GendomeNumberDescription(
        key="ac_standby_time",
        prop="ac_standby_time",
        name="AC Timeout",
        device_class=NumberDeviceClass.DURATION,
        native_min_value=0,
        native_max_value=720,
        native_step=5,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        mode=NumberMode.BOX,
        set_fn=lambda d, v: d.async_set_ac_timeout(v),
    ),
    GendomeNumberDescription(
        key="device_standby_time",
        prop="device_standby_time",
        name="Auto Shutdown",
        device_class=NumberDeviceClass.DURATION,
        native_min_value=0,
        native_max_value=720,
        native_step=5,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        mode=NumberMode.BOX,
        set_fn=lambda d, v: d.async_set_auto_shutdown(v),
    ),
    GendomeNumberDescription(
        key="low_battery_alert",
        prop="low_battery_alert",
        name="Low Battery Alert",
        native_min_value=0,
        native_max_value=50,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        set_fn=lambda d, v: d.async_set_low_battery_alert(v),
    ),
    GendomeNumberDescription(
        key="low_battery_prewarn",
        prop="low_battery_prewarn",
        name="Low Battery Pre-warning",
        native_min_value=0,
        native_max_value=50,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        set_fn=lambda d, v: d.async_set_low_battery_prewarn(v),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GendomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    device: GendomeDevice = entry.runtime_data
    async_add_entities(GendomeNumber(device, desc) for desc in NUMBERS)


class GendomeNumber(GendomeEntity, NumberEntity):
    def __init__(self, device: GendomeDevice, description: GendomeNumberDescription) -> None:
        super().__init__(device, description.prop)
        self.entity_description = description
        self._attr_unique_id = f"{device.address}_{description.key}"
        self._set_fn = description.set_fn

    @property
    def native_value(self) -> float | None:
        return getattr(self._device, self._prop, None)

    async def async_set_native_value(self, value: float) -> None:
        await self._set_fn(self._device, value)
