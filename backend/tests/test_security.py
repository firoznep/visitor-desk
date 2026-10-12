import pytest

from app.security import password_problem


@pytest.mark.parametrize("pw,username", [
    ("short", ""),
    ("administrator123", "administrator"),  # contains username
    ("password1234", ""),                    # common
])
def test_weak_passwords_rejected(pw, username):
    assert password_problem(pw, username) is not None


def test_strong_password_accepted():
    assert password_problem("Tr0ub4dor&Zebra!Fence", "reception") is None
