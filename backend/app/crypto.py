"""Field encryption for personal data.

Format of an encrypted value:  "<key_id>.<base64url(nonce || ciphertext+tag)>"
Algorithm: AES-256-GCM, 96-bit random nonce, AAD binds the value to its table/field/row so
ciphertext cannot be moved to another row or field. This is a standard construction: any
AES-GCM library can decrypt it given the key, so backups never depend on this application
(see scripts/decrypt_export.py, which is a ~40 line standalone script for exactly that).
"""
import base64
import hashlib
import hmac
import os
import re
from functools import lru_cache

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def aad(field: str, row_id) -> bytes:
    return f"visits:{field}:{row_id}".encode()


def generate_key() -> str:
    return _b64e(os.urandom(32))


class DecryptError(Exception):
    pass


class Vault:
    def __init__(self, keys_spec: str, active_id: str, index_key_b64: str):
        self._keys: dict[str, bytes] = {}
        for part in keys_spec.split(","):
            kid, _, val = part.strip().partition(":")
            if not kid or "." in kid or not val:
                raise ValueError("ID_ENCRYPTION_KEYS must look like 'k1:<key>,k0:<key>'")
            key = _b64d(val)
            if len(key) != 32:
                raise ValueError(f"Key '{kid}' must be exactly 32 bytes")
            self._keys[kid] = key
        if active_id not in self._keys:
            raise ValueError("ID_ACTIVE_KEY_ID is not present in ID_ENCRYPTION_KEYS")
        self.active_id = active_id
        self._index_key = _b64d(index_key_b64)
        if len(self._index_key) < 32:
            raise ValueError("ID_INDEX_KEY must be at least 32 bytes")

    @staticmethod
    def normalize_id(value: str) -> str:
        return re.sub(r"[\s-]", "", value).upper()

    def blind_index(self, value: str) -> str:
        return hmac.new(self._index_key, self.normalize_id(value).encode(), hashlib.sha256).hexdigest()

    def encrypt(self, plaintext: str, aad_bytes: bytes) -> str:
        nonce = os.urandom(12)
        ct = AESGCM(self._keys[self.active_id]).encrypt(nonce, plaintext.encode(), aad_bytes)
        return f"{self.active_id}.{_b64e(nonce + ct)}"

    def decrypt(self, token: str, aad_bytes: bytes) -> str:
        kid, _, payload = token.partition(".")
        key = self._keys.get(kid)
        if key is None:
            raise DecryptError(f"Unknown key id '{kid}' (add the old key to ID_ENCRYPTION_KEYS)")
        try:
            raw = _b64d(payload)
            return AESGCM(key).decrypt(raw[:12], raw[12:], aad_bytes).decode()
        except (InvalidTag, ValueError) as exc:
            raise DecryptError("Ciphertext failed authentication (wrong key or tampered data)") from exc

    def needs_rotation(self, token: str) -> bool:
        return token.partition(".")[0] != self.active_id


@lru_cache
def get_vault() -> Vault:
    from .config import settings

    return Vault(
        settings.id_encryption_keys.get_secret_value(),
        settings.id_active_key_id,
        settings.id_index_key.get_secret_value(),
    )
