# ha-gendome-ble

Unofficial Home Assistant integration for the **Gendome Home3000** portable power station, communicating locally over Bluetooth LE.

No cloud account, no internet connection, no MQTT broker required. Data is pushed directly from the device to HA every ~10 seconds.

---

## Features

- **Local-only** — communicates directly with the device over BLE
- **Works with HA Bluetooth proxies** — use an ESPHome BLE proxy if the station is out of range of your HA host
- **Real-time push** — device sends telemetry automatically; no polling
- **Bidirectional** — read sensor data and control outputs, lights, and settings from HA

---

## Supported Devices

| Device | Status |
|--------|--------|
| Gendome Home3000 | ✅ |

Other Gendome models using the same app (`com.guoxuansource`) may work but are untested.

---

## Requirements

- Home Assistant 2024.1 or later (Python 3.12+)
- The [Bluetooth integration](https://www.home-assistant.io/integrations/bluetooth/) enabled in HA
- A Bluetooth adapter within range of the power station, or an [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html)

---

## Installation

### HACS (recommended)

1. In HACS, go to **Integrations → ⋮ → Custom repositories**
2. Add `https://github.com/jasonlaguidice/ha-gendome-ble` as an **Integration**
3. Search for **Gendome BLE** and install it
4. Restart Home Assistant

### Manual

Copy the `custom_components/gendome_ble/` directory into your HA config's `custom_components/` folder and restart Home Assistant.

---

## Configuration

Once installed, make sure your power station is powered on and within Bluetooth range.

Home Assistant will automatically discover the device and show a notification:

> **New device discovered: Gendome_XXXX** — click to add

Alternatively, go to **Settings → Devices & Services → Add Integration** and search for **Gendome BLE**.

---

## Entities

### Sensors

| Entity | Unit | Notes |
|--------|------|-------|
| Battery | % | State of charge |
| Battery Power | W | Positive = discharging |
| Battery Voltage | V | Pack voltage |
| Battery Current | A | Positive = discharging |
| Battery Temperature | °C | BMS temperature |
| Battery Usable Energy | Wh | |
| AC Output Power | W | Total AC load |
| Solar Input Power | W | MPPT input |
| Solar Voltage | V | |
| Solar Current | A | |
| Car/RV Output Power | W | Barrel/XT60 rail |
| DC Output Power | W | Barrel/XT60 group total |
| 12V DC Output Power | W | Separate 12V rail |
| USB-A 1–4 Power | W | Per-port |
| USB-C 1–2 Power | W | Per-port |
| Wireless Charging Power | W | |
| Total Input Power | W | All charging sources combined |
| Total Output Power | W | All outputs combined |
| Discharge Time Remaining | min | Estimated at current load |
| Charge Time Remaining | min | Estimated at current charge rate |
| Environment Temperature | °C | Ambient sensor inside unit |
| Charge Status | — | Raw device charge state (diagnostic) |

The following sensors are created but **disabled by default**. Enable them in the entity registry if needed:

| Entity | Unit | Notes |
|--------|------|-------|
| Inverter Temperature | °C | |
| Inverter Power | W | |
| Inverter DC Voltage | V | |
| Inverter DC Current | A | |
| MPPT Temperature | °C | |
| Solar Charge Time | min | Lifetime accumulator |
| Cell Temp Max / Min | °C | BMS cell temperature range |
| Cell 1–16 Voltage | mV | Individual BMS cell voltages |
| Pack A / B Power | W | Expansion pack (if connected) |
| Pack A / B SOC | % | Expansion pack (if connected) |
| Pack A / B Cell 1–16 Voltage | mV | Expansion pack cells |
| Parallel Battery Count | — | |
| Wind Current / Voltage / Power | A / V / W | Wind turbine input (if connected) |
| Wind Input Power | W | |
| Battery Capacity | Wh | Hardware spec constant |
| Charge Cycles 1 / 2 | — | Hardware spec constant |
| AC Input Min / Max Voltage | V | Hardware spec constant |
| AC / DC Output Max Power | W | Hardware spec constant |
| Main Board / Battery / Inverter Fault Status | — | Raw bitmask (diagnostic) |
| Pack A / B Fault Status | — | Raw bitmask (diagnostic) |
| Battery Warning Status | — | Raw bitmask (diagnostic) |
| Main Board Fault 2 | — | Raw integer (diagnostic) |

### Switches

| Entity | Notes |
|--------|-------|
| AC Output | Enable/disable AC inverter output |
| DC Output | Enable/disable DC/USB outputs |
| AC Input | Enable/disable AC charging input |
| Solar Input | Enable/disable MPPT/solar charging |
| Buzzer | Audible alerts on/off |
| MPPT Fast Charge | Fast vs standard MPPT charge mode |

### Select

| Entity | Options | Notes |
|--------|---------|-------|
| Light Color | Off, White, Red, Orange, Yellow, Green, Teal, Blue, Purple | Controls both top and bottom mood lights |

### Numbers

| Entity | Range | Unit | Notes |
|--------|-------|------|-------|
| AC Charge Power | 500–1800 | W | Slider; limits AC charging rate |
| Battery Discharge Floor | 0–30 | % | Low-SOC cutoff |
| Battery Charge Ceiling | 70–100 | % | Charge limit |
| Light Brightness | 0–100 | % | Overall mood light intensity |
| Screen Brightness | 0–100 | % | Display panel brightness |
| Screen Sleep Time | 0–60 | min | 0 = never sleep |
| AC Timeout | 0–720 | min | Auto-off when AC load is 0; 0 = disabled |
| Auto Shutdown | 0–720 | min | Device auto-off when idle; 0 = disabled |
| Low Battery Alert | 0–50 | % | SOC alert threshold |
| Low Battery Pre-warning | 0–50 | % | SOC early-warning threshold |

### Binary Sensors (diagnostic, disabled by default)

| Entity | Notes |
|--------|-------|
| Main Board Fault | True if any main board fault bit is set |
| Battery Fault | True if any BMS fault bit is set |
| Inverter Fault | True if any inverter fault bit is set |
| Pack A Fault | True if any expansion pack A fault bit is set |
| Pack B Fault | True if any expansion pack B fault bit is set |
| Battery Warning | True if any BMS warning bit is set |

---

## Notes

- The device BLE name follows the pattern `Gendome_XXXX` where `XXXX` is derived from the last bytes of the MAC address
- When using an ESPHome BLE proxy, ensure the proxy is not exclusively owned by another integration (the Bluetooth integration's scanner must be shared)
- Battery current and power show positive values when discharging, negative when charging from AC
- AC Timeout and Auto Shutdown are in minutes; the device app displays them in hours
- Scheduled charging is cloud-only (via AWS) and cannot be implemented locally
