"""Switch entities for Gendome BLE."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Awaitable, Callable
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GendomeConfigEntry
from .entity import GendomeEntity
from .gendome import GendomeDevice


@dataclass(frozen=True, kw_only=True)
class GendomeSwitchDescription(SwitchEntityDescription):
    prop: str = ""
    set_fn: Callable[[GendomeDevice, bool], Awaitable[None]] = lambda d, v: None


SWITCHES: tuple[GendomeSwitchDescription, ...] = (
    GendomeSwitchDescription(
        key="ac_output_switch",
        prop="ac_output_switch",
        name="AC Output",
        device_class=SwitchDeviceClass.OUTLET,
        set_fn=lambda d, v: d.async_set_ac_switch(v),
    ),
    GendomeSwitchDescription(
        key="dc_output_switch",
        prop="dc_output_switch",
        name="DC Output",
        device_class=SwitchDeviceClass.OUTLET,
        set_fn=lambda d, v: d.async_set_dc_switch(v),
    ),
    GendomeSwitchDescription(
        key="ac_input_switch",
        prop="ac_input_switch",
        name="AC Input",
        device_class=SwitchDeviceClass.SWITCH,
        set_fn=lambda d, v: d.async_set_ac_input(v),
    ),
    GendomeSwitchDescription(
        key="mppt_input_switch",
        prop="mppt_input_switch",
        name="Solar Input",
        device_class=SwitchDeviceClass.SWITCH,
        set_fn=lambda d, v: d.async_set_mppt_input(v),
    ),
    GendomeSwitchDescription(
        key="buzzer",
        prop="buzzer",
        name="Buzzer",
        device_class=SwitchDeviceClass.SWITCH,
        set_fn=lambda d, v: d.async_set_buzzer(v),
    ),
    GendomeSwitchDescription(
        key="mppt_charge_mode",
        prop="mppt_charge_mode",
        name="MPPT Fast Charge",
        device_class=SwitchDeviceClass.SWITCH,
        set_fn=lambda d, v: d.async_set_mppt_fast_charge(v),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GendomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    device: GendomeDevice = entry.runtime_data
    async_add_entities(GendomeSwitch(device, desc) for desc in SWITCHES)


class GendomeSwitch(GendomeEntity, SwitchEntity):
    def __init__(self, device: GendomeDevice, description: GendomeSwitchDescription) -> None:
        super().__init__(device, description.prop)
        self.entity_description = description
        self._attr_unique_id = f"{device.address}_{description.key}"
        self._set_fn = description.set_fn

    @property
    def is_on(self) -> bool | None:
        return getattr(self._device, self._prop, None)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_fn(self._device, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_fn(self._device, False)
