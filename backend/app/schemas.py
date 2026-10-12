import re
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

FLOORS = {"Ground", *(str(floor) for floor in range(1, 100))}
PURPOSES = {"Meeting", "Interview", "Delivery", "Maintenance", "Contractor work", "Personal visit", "Other"}


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class MeOut(BaseModel):
    username: str
    full_name: str
    role: str
    must_change_password: bool


class ChangePasswordIn(BaseModel):
    current_password: str = Field(max_length=256)
    new_password: str = Field(min_length=12, max_length=128)


class ScanIn(BaseModel):
    raw: str = Field(min_length=1, max_length=512)


class ManualIdIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(min_length=2, max_length=120)
    id_number: str = Field(min_length=4, max_length=64)
    date_of_birth: date
    nationality: str = Field(min_length=2, max_length=60)
    gender: Literal["Male", "Female", "Other"]
    id_expiry: date

    @field_validator("id_number")
    @classmethod
    def _id_number(cls, value: str) -> str:
        normalized = re.sub(r"[\s-]", "", value).upper()
        if not re.fullmatch(r"[A-Z0-9]{4,32}", normalized):
            raise ValueError("Enter a valid ID number")
        return normalized


class ScanOut(BaseModel):
    scan_token: str
    full_name: str
    id_last4: str
    nationality: str
    gender: str
    date_of_birth: date
    id_expiry: date
    id_expired: bool
    already_checked_in: bool


class VisitCreateIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    scan_token: str = Field(max_length=2048)
    floor: str
    purpose: str
    host_name: str | None = Field(default=None, min_length=2, max_length=80)
    department: str | None = Field(default=None, max_length=60)
    phone: str | None = Field(default=None, max_length=20)
    company: str | None = Field(default=None, max_length=80)
    vehicle_plate: str | None = Field(default=None, max_length=15)
    notes: str | None = Field(default=None, max_length=200)

    @field_validator("floor")
    @classmethod
    def _floor(cls, v: str) -> str:
        if v not in FLOORS:
            raise ValueError("Unknown floor")
        return v

    @field_validator("purpose")
    @classmethod
    def _purpose(cls, v: str) -> str:
        if v not in PURPOSES:
            raise ValueError("Unknown purpose")
        return v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not re.fullmatch(r"\+?[0-9 ]{7,15}", v.strip()):
            raise ValueError("Enter a valid phone number")
        return v.strip()

    @field_validator("host_name", "phone", "company", "department", "vehicle_plate", "notes", mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        return v.strip() or None if isinstance(v, str) else v


class VisitOut(BaseModel):
    id: uuid.UUID
    badge_no: str
    visit_date: date
    full_name: str
    id_last4: str
    nationality: str
    gender: str
    id_expiry: date
    id_expired: bool
    floor: str
    purpose: str
    host_name: str | None
    department: str | None
    phone: str | None
    company: str | None
    vehicle_plate: str | None
    notes: str | None
    checked_in_at: datetime
    checked_out_at: datetime | None
    is_deleted: bool = False
    deleted_by: str | None = None


class VisitListOut(BaseModel):
    items: list[VisitOut]
    total: int
    inside_count: int


class VisitStatsOut(BaseModel):
    today_total: int
    today_inside: int
    this_week_total: int
    this_month_total: int
    last_month_total: int


class NameOptionCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)

    @field_validator("name")
    @classmethod
    def _trim_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Department name must contain at least 2 characters.")
        return value


class DeleteVisitIn(BaseModel):
    reason: str = Field(min_length=3, max_length=200)


class AuditOut(BaseModel):
    at: datetime
    username: str | None
    action: str
    target: str | None
    detail: str | None


class ErrorOut(BaseModel):
    detail: str
