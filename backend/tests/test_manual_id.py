from datetime import date

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.routers.visits import manual_id
from app.schemas import ManualIdIn
from app.security import read_scan_token


class EmptyQueryResult:
    def first(self):
        return None


class EmptyDatabase:
    async def execute(self, _query):
        return EmptyQueryResult()


def test_manual_id_normalizes_id_number():
    entry = ManualIdIn(
        full_name="  Amina Hassan  ",
        id_number="123-456 789",
        date_of_birth=date(1990, 2, 3),
        nationality="Qatari",
        gender="Female",
        id_expiry=date(2030, 2, 3),
    )

    assert entry.full_name == "Amina Hassan"
    assert entry.id_number == "123456789"


@pytest.mark.parametrize(
    "overrides",
    [
        {"id_number": "12!"},
        {"full_name": "A"},
        {"gender": "Unknown"},
    ],
)
def test_manual_id_rejects_invalid_required_details(overrides):
    details = {
        "full_name": "Amina Hassan",
        "id_number": "12345678901",
        "date_of_birth": date(1990, 2, 3),
        "nationality": "Qatari",
        "gender": "Female",
        "id_expiry": date(2030, 2, 3),
    }
    details.update(overrides)

    with pytest.raises(ValidationError):
        ManualIdIn(**details)


@pytest.mark.asyncio
async def test_manual_id_returns_signed_scan_token():
    entry = ManualIdIn(
        full_name="Amina Hassan",
        id_number="12345678901",
        date_of_birth=date(1990, 2, 3),
        nationality="Qatari",
        gender="Female",
        id_expiry=date(2030, 2, 3),
    )

    result = await manual_id(entry, EmptyDatabase(), None)

    assert result.full_name == entry.full_name
    assert result.id_last4 == "8901"
    assert result.already_checked_in is False
    assert read_scan_token(result.scan_token) == {
        "id_number": "12345678901",
        "full_name": "Amina Hassan",
        "dob": "1990-02-03",
        "nationality": "Qatari",
        "gender": "Female",
        "id_expiry": "2030-02-03",
    }


@pytest.mark.asyncio
async def test_manual_id_rejects_future_date_of_birth():
    from app.timeutil import local_today

    entry = ManualIdIn(
        full_name="Amina Hassan",
        id_number="12345678901",
        date_of_birth=date.fromordinal(local_today().toordinal() + 1),
        nationality="Qatari",
        gender="Female",
        id_expiry=date(2030, 2, 3),
    )

    with pytest.raises(HTTPException) as exc:
        await manual_id(entry, EmptyDatabase(), None)

    assert exc.value.status_code == 422
