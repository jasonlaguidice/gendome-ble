"""Select entities for Gendome BLE (light color mode)."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Awaitable, Callable

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GendomeConfigEntry
from .entity import GendomeEntity
from .gendome import GendomeDevice
from .gendome.device import LIGHT_COLOR_INDEX, LIGHT_COLOR_MODES


@dataclass(frozen=True, kw_only=True)
class GendomeSelectDescription(SelectEntityDescription):
    prop: str = ""
    set_fn: Callable[[GendomeDevice, str], Awaitable[None]] = lambda d, v: None


SELECTS: tuple[GendomeSelectDescription, ...] = (
    GendomeSelectDescription(
        key="light_color",
        prop="top_light",
        name="Light Color",
        options=list(LIGHT_COLOR_MODES.keys()),
        set_fn=lambda d, v: d.async_set_light_color(v),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GendomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    device: GendomeDevice = entry.runtime_data
    async_add_entities(GendomeSelect(device, desc) for desc in SELECTS)


class GendomeSelect(GendomeEntity, SelectEntity):
    def __init__(self, device: GendomeDevice, description: GendomeSelectDescription) -> None:
        super().__init__(device, description.prop)
        self.entity_description = description
        self._attr_unique_id = f"{device.address}_{description.key}"
        self._attr_options = list(description.options or [])
        self._set_fn = description.set_fn

    @property
    def current_option(self) -> str | None:
        raw = getattr(self._device, self._prop, None)
        if raw is None:
            return None
        return LIGHT_COLOR_INDEX.get(raw)

    async def async_select_option(self, option: str) -> None:
        await self._set_fn(self._device, option)
