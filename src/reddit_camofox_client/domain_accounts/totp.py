"""TOTP helper."""
import base64
import hashlib
import hmac
import struct
import time


def current_totp(secret: str, digits: int = 6, period: int = 30) -> str:
    key = base64.b32decode(secret.upper())
    counter = int(time.time() // period)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10**digits)).zfill(digits)
