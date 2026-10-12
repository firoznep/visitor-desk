import pytest
from pydantic import ValidationError

from app.schemas import VisitCreateIn


def make_visit(**overrides):
    data = {
        "scan_token": "signed-token",
        "floor": "99",
        "purpose": "Meeting",
    }
    data.update(overrides)
    return VisitCreateIn(**data)


def test_visit_details_allow_floor_99_and_optional_host_and_phone():
    visit = make_visit()

    assert visit.floor == "99"
    assert visit.host_name is None
    assert visit.phone is None


@pytest.mark.parametrize("floor", ["0", "100", "Basement"])
def test_visit_details_reject_floors_outside_ground_through_99(floor):
    with pytest.raises(ValidationError):
        make_visit(floor=floor)


def test_visit_details_normalize_blank_optional_fields():
    visit = make_visit(host_name="  ", phone="  ")

    assert visit.host_name is None
    assert visit.phone is None
