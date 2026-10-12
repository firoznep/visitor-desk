import pytest

from app.crypto import Vault, generate_key


def make_vault() -> Vault:
    return Vault(f"k1:{generate_key()},k0:{generate_key()}", "k1", generate_key())


def test_roundtrip():
    v = make_vault()
    token = v.encrypt("29850123456", b"aad")
    assert v.decrypt(token, b"aad") == "29850123456"


def test_wrong_aad_fails():
    v = make_vault()
    token = v.encrypt("secret", b"row:1")
    from app.crypto import DecryptError
    with pytest.raises(DecryptError):
        v.decrypt(token, b"row:2")


def test_blind_index_stable_and_normalizes():
    v = make_vault()
    assert v.blind_index("298-501-23456") == v.blind_index("29850123456")
    assert v.blind_index("abc123") != v.blind_index("abc124")


def test_unknown_key_id_raises():
    v = make_vault()
    from app.crypto import DecryptError
    with pytest.raises(DecryptError):
        v.decrypt("kX." + "AAAA", b"aad")
