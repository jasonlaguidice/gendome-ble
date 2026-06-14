"""BLE packet reassembly, payload parsing, and command encoding."""
from __future__ import annotations

import struct
from .crypto import decrypt, encrypt

# Keys whose values are 16-bit bitmasks expanded to {key_N: bool} sub-fields
_MULTI_SPEC = {168, 170, 171, 172, 174, 176}


def _crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        for i in range(8):
            bit = (byte >> (7 - i)) & 1
            c15 = (crc >> 15) & 1
            crc = (crc << 1) & 0xFFFF
            if bit ^ c15:
                crc ^= 0x1021
    return crc & 0xFFFF


def parse_payload(hex_str: str) -> dict:
    """
    Parse decrypted ASCII hex payload into {key: value}.

    Format: [count 4H][key 4H][val 4H]...
    Multi-spec keys expand into {"168_1": bool, ...}.
    Negative values use 16-bit two's complement.
    """
    if not hex_str or len(hex_str) < 4:
        return {}
    groups = [hex_str[i : i + 4] for i in range(0, len(hex_str), 4)]
    result: dict = {}
    count = int(groups[0], 16)
    for i in range(1, min(2 * count + 1, len(groups) - 1), 2):
        key = int(groups[i], 16)
        if key == 0:
            continue
        raw = int(groups[i + 1], 16)
        if key in _MULTI_SPEC:
            for bit in range(16):
                result[f"{key}_{bit + 1}"] = bool((raw >> bit) & 1)
        elif raw >> 15:
            result[key] = -(((~raw) & 0x7FFF) + 1)
        else:
            result[key] = raw
    return result


class PacketReassembler:
    """
    Stateful reassembler for fragmented EE02 NOTIFY packets.

    Feed each raw 20-byte (or shorter) BLE packet via feed().
    Returns a parsed dict when a complete message is decoded, else None.

    Frame layout:
      SEQ=1 : [ID 2B][01][CRC 2B][LEN 2B][encrypted 13B]  (20B total)
      SEQ>1 : [ID 2B][SEQ][encrypted 17B]
      Last  : encrypted chunk < 17B → triggers reassembly
    """

    def __init__(self) -> None:
        self._chunks: list[bytes] = []
        self._expected_len: int | None = None

    def feed(self, data: bytes) -> dict | None:
        if len(data) < 3:
            return None
        seq = data[2]
        if seq == 1:
            self._chunks = []
            if len(data) < 7:
                return None
            self._expected_len = struct.unpack(">H", data[5:7])[0]
            self._chunks.append(data[7:])
            # Single-packet message (first packet shorter than max 20B)
            if len(data) < 20:
                return self._finish()
        else:
            if not self._chunks:
                return None
            chunk = data[3:]
            self._chunks.append(chunk)
            if len(chunk) < 17:
                return self._finish()
        return None

    def _finish(self) -> dict | None:
        if not self._chunks or self._expected_len is None:
            return None
        encrypted = b"".join(self._chunks)
        expected_len = self._expected_len
        self._chunks = []
        self._expected_len = None
        try:
            plaintext = decrypt(encrypted)[:expected_len]
            return parse_payload(plaintext.hex().upper())
        except Exception:
            return None


def encode_command(specs: list[tuple[int, int]], ble_id: int = 1) -> list[bytes]:
    """
    Encode key-value specs as a sequence of BLE write packets for EE03.

    Packet 1 (20B): [ID 2B BE][SEQ=1][CRC 2B][LEN 2B][encrypted[0:13]]
    Packet 2+     : [ID 2B BE][SEQ  ][encrypted chunk up to 17B]
    """
    count = len(specs)
    parts = [f"{count:04X}"]
    for key, val in specs:
        parts.append(f"{key:04X}")
        parts.append(f"{val & 0xFFFF:04X}")
    cmd_str = "".join(parts)
    plaintext = cmd_str.encode("ascii")
    crc = _crc16(plaintext)
    encrypted = encrypt(plaintext)

    packets: list[bytes] = []
    p1 = struct.pack(">HBH", ble_id, 1, crc) + struct.pack(">H", len(plaintext)) + encrypted[:13]
    packets.append(p1)

    remaining = encrypted[13:]
    seq = 2
    while remaining:
        chunk = remaining[:17]
        remaining = remaining[17:]
        packets.append(struct.pack(">HB", ble_id, seq) + chunk)
        seq += 1

    # If last encrypted chunk was exactly 17B, append empty terminator
    if len(encrypted[13:]) > 0 and len(encrypted[13:]) % 17 == 0:
        packets.append(struct.pack(">HB", ble_id, seq))

    return packets
