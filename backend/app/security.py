import asyncio
import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from itsdangerous import BadSignature, URLSafeTimedSerializer

from .config import settings

# Argon2id (argon2-cffi default type). ~64 MiB, 3 passes: tune on your hardware, target ~100-250 ms.
_ph = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=4)
DUMMY_HASH = _ph.hash("timing-equaliser-not-a-real-password")

_COMMON = {"password1234", "123456789012", "qwertyuiop12", "administrator", "welcome12345", "letmein12345"}


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_ph.hash, password)


async def verify_password(hashed: str, password: str) -> bool:
    def _run() -> bool:
        try:
            return _ph.verify(hashed, password)
        except (VerificationError, InvalidHashError):
            return False

    return await asyncio.to_thread(_run)


def needs_rehash(hashed: str) -> bool:
    return _ph.check_needs_rehash(hashed)


def password_problem(password: str, username: str = "") -> str | None:
    if len(password) < 12:
        return "Password must be at least 12 characters."
    if len(password) > 128:
        return "Password must be at most 128 characters."
    if username and username.lower() in password.lower():
        return "Password must not contain the username."
    if password.lower() in _COMMON or len(set(password)) < 5:
        return "Password is too easy to guess."
    return None


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def _scan_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.scan_token_secret.get_secret_value(), salt="visitor-desk.scan.v1")


def make_scan_token(payload: dict) -> str:
    return _scan_serializer().dumps(payload)


def read_scan_token(token: str) -> dict:
    try:
        data = _scan_serializer().loads(token, max_age=settings.scan_token_ttl_seconds)
    except BadSignature as exc:  # includes SignatureExpired
        raise ValueError("invalid scan token") from exc
    if not isinstance(data, dict):
        raise ValueError("invalid scan token")
    return data
