"""GendomeDevice — BLE connection, state, and control."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .packet import PacketReassembler, encode_command

_LOGGER = logging.getLogger(__name__)

NOTIFY_UUID = "0000ee02-0000-1000-8000-00805f9b34fb"
WRITE_UUID  = "0000ee03-0000-1000-8000-00805f9b34fb"

_KEY_MAP: dict[int, tuple[float | None, str]] = {
    # Controls (read-back from device settings)
    1:   (0.1,   "ac_charge_power"),
    3:   (None,  "ac_standby_time"),
    6:   (None,  "bms_protect_min"),
    7:   (None,  "buzzer"),
    8:   (None,  "screen_brightness"),
    9:   (None,  "device_standby_time"),
    10:  (None,  "screen_sleep_time"),
    13:  (None,  "low_battery_alert"),
    14:  (None,  "low_battery_prewarn"),
    23:  (None,  "bms_protect_max"),
    24:  (None,  "charge_status"),
    25:  (None,  "light_brightness"),
    # Inverter
    33:  (0.1,   "inverter_temp"),
    34:  (0.1,   "inverter_power"),
    35:  (0.01,  "inverter_voltage"),
    36:  (0.01,  "inverter_current"),
    42:  (0.1,   "ac_output_power"),
    # MPPT / Solar
    48:  (0.1,   "mppt_temp"),
    49:  (None,  "pv_charge_time"),
    50:  (0.01,  "pv_current"),
    51:  (0.01,  "pv_voltage"),
    52:  (0.1,   "pv_power"),
    53:  (0.1,   "pv_input_power"),
    # Wind input
    55:  (0.01,  "wind_current"),
    56:  (0.01,  "wind_voltage"),
    57:  (0.1,   "wind_power"),
    58:  (0.1,   "wind_input_power"),
    # Car/RV DC output
    59:  (0.1,   "car_rv_output_power"),
    # BMS host cell voltages — raw mV, keys 64–79
    **{64 + i: (None, f"cell_{i + 1}_voltage") for i in range(16)},
    # Battery
    80:  (None,  "soc"),
    81:  (0.1,   "battery_temp"),
    82:  (0.1,   "battery_power"),
    83:  (0.01,  "battery_voltage"),
    84:  (0.01,  "battery_current"),
    85:  (0.1,   "battery_usable_energy"),
    86:  (0.1,   "cell_temp_max"),
    87:  (0.1,   "cell_temp_min"),
    # Parallel expansion packs
    88:  (0.1,   "pack_a_power"),
    89:  (None,  "pack_a_soc"),
    90:  (0.1,   "pack_b_power"),
    91:  (None,  "pack_b_soc"),
    92:  (None,  "parallel_battery_count"),
    # Time estimates
    93:  (None,  "discharge_time_remain"),
    94:  (None,  "charge_time_remain"),
    # USB-A output ports, keys 99–102
    99:  (0.1,   "usb_a1_power"),
    100: (0.1,   "usb_a2_power"),
    101: (0.1,   "usb_a3_power"),
    102: (0.1,   "usb_a4_power"),
    # USB-C output ports
    103: (0.1,   "usb_c1_power"),
    104: (0.1,   "usb_c2_power"),
    # Wireless charging
    105: (0.1,   "wireless_charge_power"),
    # DC barrel / XT60 group total
    106: (0.1,   "dc_output_power"),
    # Pack A cell voltages — raw mV, keys 128–143
    **{128 + i: (None, f"pack_a_cell_{i + 1}_voltage") for i in range(16)},
    # Pack B cell voltages — raw mV, keys 144–159
    **{144 + i: (None, f"pack_b_cell_{i + 1}_voltage") for i in range(16)},
    # Environment / system
    163: (0.1,   "env_temp"),
    164: (0.1,   "dc_12v_output_power"),
    165: (0.1,   "input_total_power"),
    166: (0.1,   "output_total_power"),
    # Fault status — key 169 is raw int; 168/170–176 are bitmasks handled in _apply
    169: (None,  "fault_main_board_2"),
    # Switches / modes
    177: (None,  "dc_output_switch"),
    178: (None,  "ac_output_switch"),
    179: (None,  "mppt_charge_mode"),
    181: (None,  "top_light"),
    182: (None,  "bottom_light"),
    183: (None,  "device_status"),
    # Device hardware spec constants
    236: (None,  "spec_capacity"),
    239: (None,  "spec_cycle_count_1"),
    240: (None,  "spec_cycle_count_2"),
    247: (None,  "spec_ac_input_min_v"),
    248: (None,  "spec_ac_input_max_v"),
    252: (None,  "spec_ac_output_max_w"),
    255: (None,  "spec_dc_output_max_w"),
    # Input enable switches
    369: (None,  "ac_input_switch"),
    370: (None,  "mppt_input_switch"),
}

# Multi-spec bitmask keys: packet.py expands these to {"168_1": bool, ...} sub-fields
_FAULT_KEYS = {168, 170, 171, 172, 174, 176}

# Light color mode index (keys 181/182): 255=off, 0-7=color
LIGHT_COLOR_MODES: dict[str, int] = {
    "Off":    255,
    "White":  0,
    "Red":    1,
    "Orange": 2,
    "Yellow": 3,
    "Green":  4,
    "Teal":   5,
    "Blue":   6,
    "Purple": 7,
}
LIGHT_COLOR_INDEX: dict[int, str] = {v: k for k, v in LIGHT_COLOR_MODES.items()}

_FAULT_PROPS: dict[int, str] = {
    168: "fault_main_board",
    170: "fault_battery",
    171: "fault_inverter",
    172: "fault_pack_a",
    174: "fault_pack_b",
    176: "warn_battery",
}


class GendomeDevice:
    """Manages the BLE connection to a Gendome Home3000 and exposes its state."""

    def __init__(self, ble_device: BLEDevice, address: str) -> None:
        self._ble_device = ble_device
        self.address = address
        self.name: str = ble_device.name or f"Gendome {address[-5:]}"
        self._client: BleakClient | None = None
        self._is_connected = False
        self._state: dict[str, Any] = {}
        self._fault_bits: dict[int, dict[int, bool]] = {}
        self._callbacks: dict[str, list[Callable]] = {}
        self._disconnect_callbacks: list[Callable] = []
        self._reassembler = PacketReassembler()

    # ── Connection ────────────────────────────────────────────────────────────

    def update_ble_device(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device

    async def connect(self) -> None:
        _LOGGER.debug("Connecting to %s (%s)", self.name, self.address)
        self._client = await establish_connection(
            BleakClientWithServiceCache,
            self._ble_device,
            self.name,
            disconnected_callback=self._on_disconnected,
        )
        self._is_connected = True
        await self._client.start_notify(NOTIFY_UUID, self._on_notify)
        _LOGGER.debug("Subscribed to EE02, sending initial query")
        await self._send_command([(26, 1)])

    async def disconnect(self) -> None:
        self._is_connected = False
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None

    def on_disconnect(self, callback: Callable) -> Callable:
        self._disconnect_callbacks.append(callback)
        def cancel():
            try:
                self._disconnect_callbacks.remove(callback)
            except ValueError:
                pass
        return cancel

    def _on_disconnected(self, _client: BleakClient) -> None:
        _LOGGER.warning("Disconnected from %s", self.name)
        self._is_connected = False
        for cb in list(self._disconnect_callbacks):
            cb(None)

    # ── State access ──────────────────────────────────────────────────────────

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._state.get(name)
        except AttributeError:
            raise AttributeError(name)

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    # Switch properties need a bool cast (raw values are integers)
    @property
    def dc_output_switch(self) -> bool | None:
        val = self._state.get("dc_output_switch")
        return bool(val) if val is not None else None

    @property
    def ac_output_switch(self) -> bool | None:
        val = self._state.get("ac_output_switch")
        return bool(val) if val is not None else None

    @property
    def buzzer(self) -> bool | None:
        val = self._state.get("buzzer")
        return bool(val) if val is not None else None

    @property
    def ac_input_switch(self) -> bool | None:
        val = self._state.get("ac_input_switch")
        return bool(val) if val is not None else None

    @property
    def mppt_input_switch(self) -> bool | None:
        val = self._state.get("mppt_input_switch")
        return bool(val) if val is not None else None

    @property
    def mppt_charge_mode(self) -> bool | None:
        val = self._state.get("mppt_charge_mode")
        return bool(val) if val is not None else None

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def register_state_update_callback(self, callback: Callable, prop: str) -> None:
        self._callbacks.setdefault(prop, []).append(callback)

    def remove_state_update_callback(self, callback: Callable, prop: str) -> None:
        lst = self._callbacks.get(prop, [])
        try:
            lst.remove(callback)
        except ValueError:
            pass

    def _on_notify(self, _char: Any, data: bytes) -> None:
        parsed = self._reassembler.feed(data)
        if parsed:
            self._apply(parsed)

    def _apply(self, parsed: dict) -> None:
        fault_bits_seen: dict[int, dict[int, bool]] = {}

        for raw_key, raw_val in parsed.items():
            if isinstance(raw_key, int):
                if raw_key not in _KEY_MAP:
                    continue
                scale, prop = _KEY_MAP[raw_key]
                value = round(raw_val * scale, 2) if scale is not None else raw_val
                if self._state.get(prop) != value:
                    self._state[prop] = value
                    for cb in list(self._callbacks.get(prop, [])):
                        cb(value)
            elif isinstance(raw_key, str):
                # Multi-spec bitmask sub-field: "168_1", "168_2", etc.
                try:
                    base_str, bit_str = raw_key.split("_", 1)
                    base_key = int(base_str)
                    bit = int(bit_str)
                except (ValueError, AttributeError):
                    continue
                if base_key in _FAULT_KEYS:
                    fault_bits_seen.setdefault(base_key, {})[bit] = bool(raw_val)

        for base_key, bits in fault_bits_seen.items():
            self._fault_bits.setdefault(base_key, {}).update(bits)
            prop = _FAULT_PROPS[base_key]
            any_set = any(self._fault_bits[base_key].values())
            if self._state.get(prop) != any_set:
                self._state[prop] = any_set
                for cb in list(self._callbacks.get(prop, [])):
                    cb(any_set)
            raw_int = sum(1 << (b - 1) for b, v in self._fault_bits[base_key].items() if v)
            raw_prop = f"{prop}_raw"
            if self._state.get(raw_prop) != raw_int:
                self._state[raw_prop] = raw_int
                for cb in list(self._callbacks.get(raw_prop, [])):
                    cb(raw_int)

    # ── Commands ──────────────────────────────────────────────────────────────

    async def async_set_ac_switch(self, on: bool) -> None:
        await self._send_command([(178, 1 if on else 0)])

    async def async_set_dc_switch(self, on: bool) -> None:
        await self._send_command([(177, 1 if on else 0)])

    async def async_set_buzzer(self, on: bool) -> None:
        await self._send_command([(7, 1 if on else 0)])

    async def async_set_ac_input(self, on: bool) -> None:
        await self._send_command([(369, 1 if on else 0)])

    async def async_set_mppt_input(self, on: bool) -> None:
        await self._send_command([(370, 1 if on else 0)])

    async def async_set_light_color(self, color_name: str) -> None:
        idx = LIGHT_COLOR_MODES.get(color_name)
        if idx is None:
            return
        await self._send_command([(181, idx), (182, idx)])

    async def async_set_mppt_fast_charge(self, on: bool) -> None:
        await self._send_command([(179, 1 if on else 0)])

    async def async_set_ac_charge_power(self, watts: float) -> None:
        await self._send_command([(1, int(watts * 10))])

    async def async_set_bms_protect_min(self, pct: float) -> None:
        await self._send_command([(6, int(pct))])

    async def async_set_bms_protect_max(self, pct: float) -> None:
        await self._send_command([(23, int(pct))])

    async def async_set_light_brightness(self, level: float) -> None:
        await self._send_command([(25, int(level))])

    async def async_set_screen_brightness(self, level: float) -> None:
        await self._send_command([(8, int(level))])

    async def async_set_screen_sleep(self, minutes: float) -> None:
        await self._send_command([(10, int(minutes))])

    async def async_set_ac_timeout(self, minutes: float) -> None:
        await self._send_command([(3, int(minutes))])

    async def async_set_auto_shutdown(self, value: float) -> None:
        await self._send_command([(9, int(value))])

    async def async_set_low_battery_alert(self, pct: float) -> None:
        await self._send_command([(13, int(pct))])

    async def async_set_low_battery_prewarn(self, pct: float) -> None:
        await self._send_command([(14, int(pct))])

    async def _send_command(self, specs: list[tuple[int, int]]) -> None:
        if not self._client or not self._is_connected:
            _LOGGER.warning("Cannot send command: not connected")
            return
        pkts = encode_command(specs)
        for pkt in pkts:
            await self._client.write_gatt_char(WRITE_UUID, pkt, response=True)
            await asyncio.sleep(0.05)
