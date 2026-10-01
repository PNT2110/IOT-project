"""Sealed envelopes for the Pi -> PC device channel.

Contract: contracts/v1/DEVICE_FLIGHT_CONTRACT.md. The Pi keeps a byte-for-byte
compatible copy at edge/pi5/pi5/web/device_crypto.py; both are pinned by the
same test vector.
"""
from __future__ import annotations

import base64
import json
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class DeviceAuthError(Exception):
    """The envelope is malformed, stale, or does not authenticate."""


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def seal(key: bytes, device_id: str, payload: dict, now: int, *, nonce: bytes | None = None) -> dict:
    nonce = nonce or secrets.token_bytes(12)
    plaintext = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode()
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, f"{device_id}|{now}".encode())
    return {"device_id": device_id, "ts": now, "nonce": _b64(nonce), "ciphertext": _b64(ciphertext)}


def open_sealed(key: bytes, envelope: dict, now: int, max_skew: int = 300) -> dict:
    try:
        device_id = envelope["device_id"]
        ts = envelope["ts"]
        if not isinstance(device_id, str) or not isinstance(ts, int) or isinstance(ts, bool):
            raise DeviceAuthError("malformed envelope")
        if abs(now - ts) > max_skew:
            raise DeviceAuthError("stale envelope")
        nonce = _unb64(envelope["nonce"])
        if len(nonce) != 12:
            raise DeviceAuthError("malformed nonce")
        plaintext = AESGCM(key).decrypt(nonce, _unb64(envelope["ciphertext"]), f"{device_id}|{ts}".encode())
        payload = json.loads(plaintext)
    except DeviceAuthError:
        raise
    except (InvalidTag, KeyError, TypeError, ValueError) as exc:
        raise DeviceAuthError("envelope does not authenticate") from exc
    if not isinstance(payload, dict):
        raise DeviceAuthError("payload must be an object")
    return payload
