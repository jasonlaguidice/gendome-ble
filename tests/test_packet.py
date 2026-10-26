"""Replay captured notifications through PacketReassembler."""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "custom_components", "gendome_ble"))

from gendome.packet import PacketReassembler  # noqa: E402


def _frames():
    for f in sorted(glob.glob(os.path.join(ROOT, "dev", "captures", "*.json"))):
        for e in json.load(open(f)):
            if e["uuid"].startswith("0000ee02"):
                yield bytes.fromhex(e["data"])


def test_captures_decode_with_valid_crc():
    r = PacketReassembler()
    results = [x for x in (r.feed(d) for d in _frames()) if x]
    assert results
    assert all(0 <= v.get(80, 0) <= 100 for v in results)


def test_corrupted_frame_dropped():
    r = PacketReassembler()
    dropped = 0
    for d in _frames():
        if len(d) > 5 and d[2] == 1:
            d = d[:3] + bytes([d[3] ^ 0xFF]) + d[4:]  # break CRC
        if r.feed(d):
            dropped -= 100
    assert dropped == 0


def test_duplicate_notifications_are_ignored():
    from gendome.packet import encode_command

    specs = [(1, 500), (2, 1), (3, 60), (4, 7), (5, 9), (6, 11), (7, 13), (8, 15)]
    packets = encode_command(specs)
    assert len(packets) > 1

    single = PacketReassembler()
    expected = [r for r in (single.feed(p) for p in packets) if r]

    tripled = PacketReassembler()
    got = [r for p in packets for r in (tripled.feed(p) for _ in range(3)) if r]

    assert expected and got == expected
