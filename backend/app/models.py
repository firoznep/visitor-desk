import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Identity, Index, Integer, LargeBinary, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

TS = DateTime(timezone=True)
NOW = text("now()")


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(Text)
    full_name: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(TS)
    last_login_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=NOW)
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=NOW)


class UserSession(Base):
    __tablename__ = "sessions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    csrf_token: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=NOW)
    last_seen_at: Mapped[datetime] = mapped_column(TS, server_default=NOW)
    expires_at: Mapped[datetime] = mapped_column(TS)
    revoked_at: Mapped[datetime | None] = mapped_column(TS)
    ip: Mapped[str | None] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(Text)


class Visit(Base):
    __tablename__ = "visits"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    badge_no: Mapped[str] = mapped_column(
        Text, unique=True, server_default=text("'V-' || lpad(nextval('badge_seq')::text, 6, '0')")
    )
    visit_date: Mapped[date] = mapped_column(Date)
    full_name: Mapped[str] = mapped_column(Text)
    id_number_enc: Mapped[str] = mapped_column(Text)          # AES-256-GCM, never plaintext
    id_number_hash: Mapped[str] = mapped_column(String(64))   # HMAC-SHA256 blind index (duplicate checks)
    id_last4: Mapped[str] = mapped_column(String(4))
    dob_enc: Mapped[str] = mapped_column(Text)                # AES-256-GCM
    nationality: Mapped[str] = mapped_column(Text)
    gender: Mapped[str] = mapped_column(Text)
    id_expiry: Mapped[date] = mapped_column(Date)
    id_expired: Mapped[bool] = mapped_column(Boolean)
    floor: Mapped[str] = mapped_column(Text)
    purpose: Mapped[str] = mapped_column(Text)
    host_name: Mapped[str | None] = mapped_column(Text)
    department: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(Text)
    vehicle_plate: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    checked_in_at: Mapped[datetime] = mapped_column(TS, server_default=NOW)
    checked_out_at: Mapped[datetime | None] = mapped_column(TS)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=NOW)
    deleted_at: Mapped[datetime | None] = mapped_column(TS)
    deleted_by: Mapped[str | None] = mapped_column(Text)
    delete_reason: Mapped[str | None] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    at: Mapped[datetime] = mapped_column(TS, server_default=NOW)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    username: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    target: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(Text)


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (Index("uq_departments_name_lower", text("lower(name)"), unique=True),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True)


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (Index("uq_companies_name_lower", text("lower(name)"), unique=True),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
