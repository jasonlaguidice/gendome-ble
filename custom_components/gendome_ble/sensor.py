"""Sensor entities for Gendome BLE."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GendomeConfigEntry
from .entity import GendomeEntity
from .gendome import GendomeDevice


@dataclass(frozen=True, kw_only=True)
class GendomeSensorDescription(SensorEntityDescription):
    prop: str = ""


def _power(key: str, prop: str, name: str, *, disabled: bool = False) -> GendomeSensorDescription:
    return GendomeSensorDescription(
        key=key, prop=prop, name=name,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        entity_registry_enabled_default=not disabled,
    )


def _current(key: str, prop: str, name: str, *, disabled: bool = False) -> GendomeSensorDescription:
    return GendomeSensorDescription(
        key=key, prop=prop, name=name,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
        entity_registry_enabled_default=not disabled,
    )


def _voltage(key: str, prop: str, name: str, *, disabled: bool = False) -> GendomeSensorDescription:
    return GendomeSensorDescription(
        key=key, prop=prop, name=name,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=2,
        entity_registry_enabled_default=not disabled,
    )


def _temp(key: str, prop: str, name: str, *, disabled: bool = False) -> GendomeSensorDescription:
    return GendomeSensorDescription(
        key=key, prop=prop, name=name,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_registry_enabled_default=not disabled,
    )


SENSORS: tuple[GendomeSensorDescription, ...] = (
    # ── Battery ───────────────────────────────────────────────────────────────
    GendomeSensorDescription(
        key="soc", prop="soc", name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    _power("battery_power", "battery_power", "Battery Power"),
    _voltage("battery_voltage", "battery_voltage", "Battery Voltage"),
    _current("battery_current", "battery_current", "Battery Current"),
    _temp("battery_temp", "battery_temp", "Battery Temperature"),
    GendomeSensorDescription(
        key="battery_usable_energy", prop="battery_usable_energy",
        name="Battery Usable Energy",
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_display_precision=0,
    ),
    # ── AC output ─────────────────────────────────────────────────────────────
    _power("ac_output_power", "ac_output_power", "AC Output Power"),
    # ── Solar / MPPT ──────────────────────────────────────────────────────────
    _power("pv_input_power", "pv_input_power", "Solar Input Power"),
    _voltage("pv_voltage", "pv_voltage", "Solar Voltage"),
    _current("pv_current", "pv_current", "Solar Current"),
    _temp("mppt_temp", "mppt_temp", "MPPT Temperature", disabled=True),
    GendomeSensorDescription(
        key="pv_charge_time", prop="pv_charge_time", name="Solar Charge Time",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        entity_registry_enabled_default=False,
    ),
    # ── Time estimates ────────────────────────────────────────────────────────
    GendomeSensorDescription(
        key="discharge_time_remain", prop="discharge_time_remain",
        name="Discharge Time Remaining",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    GendomeSensorDescription(
        key="charge_time_remain", prop="charge_time_remain",
        name="Charge Time Remaining",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    # ── Temperatures ──────────────────────────────────────────────────────────
    _temp("env_temp", "env_temp", "Environment Temperature"),
    _temp("inverter_temp", "inverter_temp", "Inverter Temperature", disabled=True),
    # ── Inverter detail ───────────────────────────────────────────────────────
    _power("inverter_power", "inverter_power", "Inverter Power", disabled=True),
    _voltage("inverter_voltage", "inverter_voltage", "Inverter DC Voltage", disabled=True),
    _current("inverter_current", "inverter_current", "Inverter DC Current", disabled=True),
    # ── DC per-port output ────────────────────────────────────────────────────
    _power("car_rv_output_power", "car_rv_output_power", "Car/RV Output Power"),
    _power("usb_a1_power", "usb_a1_power", "USB-A 1 Power"),
    _power("usb_a2_power", "usb_a2_power", "USB-A 2 Power"),
    _power("usb_a3_power", "usb_a3_power", "USB-A 3 Power"),
    _power("usb_a4_power", "usb_a4_power", "USB-A 4 Power"),
    _power("usb_c1_power", "usb_c1_power", "USB-C 1 Power"),
    _power("usb_c2_power", "usb_c2_power", "USB-C 2 Power"),
    _power("wireless_charge_power", "wireless_charge_power", "Wireless Charging Power"),
    _power("dc_output_power", "dc_output_power", "DC Output Power"),
    _power("dc_12v_output_power", "dc_12v_output_power", "12V DC Output Power"),
    # ── System aggregates ─────────────────────────────────────────────────────
    _power("input_total_power", "input_total_power", "Total Input Power"),
    _power("output_total_power", "output_total_power", "Total Output Power"),
    # ── Wind input ────────────────────────────────────────────────────────────
    _current("wind_current", "wind_current", "Wind Current", disabled=True),
    _voltage("wind_voltage", "wind_voltage", "Wind Voltage", disabled=True),
    _power("wind_power", "wind_power", "Wind Power", disabled=True),
    _power("wind_input_power", "wind_input_power", "Wind Input Power", disabled=True),
    # ── BMS cell temperatures ─────────────────────────────────────────────────
    _temp("cell_temp_max", "cell_temp_max", "Cell Temp Max", disabled=True),
    _temp("cell_temp_min", "cell_temp_min", "Cell Temp Min", disabled=True),
    # ── Parallel expansion packs ──────────────────────────────────────────────
    _power("pack_a_power", "pack_a_power", "Pack A Power", disabled=True),
    GendomeSensorDescription(
        key="pack_a_soc", prop="pack_a_soc", name="Pack A SOC",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_registry_enabled_default=False,
    ),
    _power("pack_b_power", "pack_b_power", "Pack B Power", disabled=True),
    GendomeSensorDescription(
        key="pack_b_soc", prop="pack_b_soc", name="Pack B SOC",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_registry_enabled_default=False,
    ),
    GendomeSensorDescription(
        key="parallel_battery_count", prop="parallel_battery_count",
        name="Parallel Battery Count",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    # ── Charge status (semantics TBD — observe across states) ─────────────────
    GendomeSensorDescription(
        key="charge_status", prop="charge_status", name="Charge Status",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # ── Device hardware spec constants ────────────────────────────────────────
    GendomeSensorDescription(
        key="spec_capacity", prop="spec_capacity", name="Battery Capacity",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeSensorDescription(
        key="spec_cycle_count_1", prop="spec_cycle_count_1", name="Charge Cycles 1",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeSensorDescription(
        key="spec_cycle_count_2", prop="spec_cycle_count_2", name="Charge Cycles 2",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeSensorDescription(
        key="spec_ac_input_min_v", prop="spec_ac_input_min_v", name="AC Input Min Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeSensorDescription(
        key="spec_ac_input_max_v", prop="spec_ac_input_max_v", name="AC Input Max Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeSensorDescription(
        key="spec_ac_output_max_w", prop="spec_ac_output_max_w", name="AC Output Max Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeSensorDescription(
        key="spec_dc_output_max_w", prop="spec_dc_output_max_w", name="DC Output Max Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    # ── Fault status raw bitmasks (diagnostic companions to binary_sensor) ─────
    GendomeSensorDescription(
        key="fault_main_board_raw", prop="fault_main_board_raw",
        name="Main Board Fault Status",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeSensorDescription(
        key="fault_battery_raw", prop="fault_battery_raw",
        name="Battery Fault Status",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeSensorDescription(
        key="fault_inverter_raw", prop="fault_inverter_raw",
        name="Inverter Fault Status",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeSensorDescription(
        key="fault_pack_a_raw", prop="fault_pack_a_raw",
        name="Pack A Fault Status",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeSensorDescription(
        key="fault_pack_b_raw", prop="fault_pack_b_raw",
        name="Pack B Fault Status",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeSensorDescription(
        key="warn_battery_raw", prop="warn_battery_raw",
        name="Battery Warning Status",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    GendomeSensorDescription(
        key="fault_main_board_2", prop="fault_main_board_2",
        name="Main Board Fault 2",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)

# BMS host cell voltages (raw mV)
SENSORS = SENSORS + tuple(
    GendomeSensorDescription(
        key=f"cell_{i + 1}_voltage",
        prop=f"cell_{i + 1}_voltage",
        name=f"Cell {i + 1} Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        entity_registry_enabled_default=False,
    )
    for i in range(16)
) + tuple(
    GendomeSensorDescription(
        key=f"pack_a_cell_{i + 1}_voltage",
        prop=f"pack_a_cell_{i + 1}_voltage",
        name=f"Pack A Cell {i + 1} Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        entity_registry_enabled_default=False,
    )
    for i in range(16)
) + tuple(
    GendomeSensorDescription(
        key=f"pack_b_cell_{i + 1}_voltage",
        prop=f"pack_b_cell_{i + 1}_voltage",
        name=f"Pack B Cell {i + 1} Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        entity_registry_enabled_default=False,
    )
    for i in range(16)
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GendomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    device: GendomeDevice = entry.runtime_data
    async_add_entities(GendomeSensor(device, desc) for desc in SENSORS)


class GendomeSensor(GendomeEntity, SensorEntity):
    def __init__(self, device: GendomeDevice, description: GendomeSensorDescription) -> None:
        super().__init__(device, description.prop)
        self.entity_description = description
        self._attr_unique_id = f"{device.address}_{description.key}"

    @property
    def native_value(self):
        return getattr(self._device, self._prop, None)
