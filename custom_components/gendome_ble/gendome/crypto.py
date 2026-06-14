"""DES/CBC/NoPadding crypto — key and IV are both b"gwin0801"."""
import struct

try:
    from Crypto.Cipher import DES
except ImportError:
    from Cryptodome.Cipher import DES

_KEY = b"gwin0801"


def decrypt(data: bytes) -> bytes:
    padded = data + b"\x00" * ((-len(data)) % 8)
    return DES.new(_KEY, DES.MODE_CBC, iv=_KEY).decrypt(padded)


def encrypt(data: bytes) -> bytes:
    padded = data + b"\x00" * ((-len(data)) % 8)
    return DES.new(_KEY, DES.MODE_CBC, iv=_KEY).encrypt(padded)
