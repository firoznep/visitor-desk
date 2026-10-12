"""baseline schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-29
"""
from alembic import op
import re

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA_SQL = "-- Run once by Postgres on first container start (docker-entrypoint-initdb.d).\n-- For an already-running database, apply this with Alembic instead (see backend/migrations).\n\nCREATE EXTENSION IF NOT EXISTS pgcrypto;\nCREATE EXTENSION IF NOT EXISTS pg_trgm;\n\nCREATE SEQUENCE IF NOT EXISTS badge_seq START 1;\n\nCREATE TABLE users (\n    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n    username             text UNIQUE NOT NULL,\n    full_name            text NOT NULL,\n    password_hash        text NOT NULL,\n    role                 text NOT NULL CHECK (role IN ('receptionist', 'admin')),\n    is_active            boolean NOT NULL DEFAULT true,\n    must_change_password boolean NOT NULL DEFAULT false,\n    failed_attempts      integer NOT NULL DEFAULT 0,\n    locked_until         timestamptz,\n    last_login_at        timestamptz,\n    created_at           timestamptz NOT NULL DEFAULT now(),\n    updated_at           timestamptz NOT NULL DEFAULT now()\n);\n\nCREATE TABLE sessions (\n    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n    user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,\n    token_hash    bytea UNIQUE NOT NULL,\n    csrf_token    text NOT NULL,\n    created_at    timestamptz NOT NULL DEFAULT now(),\n    last_seen_at  timestamptz NOT NULL DEFAULT now(),\n    expires_at    timestamptz NOT NULL,\n    revoked_at    timestamptz,\n    ip            text,\n    user_agent    text\n);\nCREATE INDEX idx_sessions_user ON sessions(user_id);\nCREATE INDEX idx_sessions_expiry ON sessions(expires_at) WHERE revoked_at IS NULL;\n\nCREATE TABLE visits (\n    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n    badge_no         text UNIQUE NOT NULL DEFAULT ('V-' || lpad(nextval('badge_seq')::text, 6, '0')),\n    visit_date       date NOT NULL,\n    full_name        text NOT NULL,\n    id_number_enc    text NOT NULL,       -- AES-256-GCM ciphertext, app-layer encrypted. See scripts/decrypt_export.py\n    id_number_hash   char(64) NOT NULL,   -- HMAC-SHA256 blind index: equality lookups without decrypting\n    id_last4         varchar(4) NOT NULL,\n    dob_enc          text NOT NULL,       -- AES-256-GCM ciphertext\n    nationality      text NOT NULL,\n    gender           text NOT NULL CHECK (gender IN ('Male', 'Female', 'Other')),\n    id_expiry        date NOT NULL,\n    id_expired       boolean NOT NULL,\n    floor            text NOT NULL,\n    purpose          text NOT NULL,\n    host_name        text NOT NULL,\n    department       text,\n    phone            text NOT NULL,\n    company          text,\n    vehicle_plate    text,\n    notes            text,\n    checked_in_at    timestamptz NOT NULL DEFAULT now(),\n    checked_out_at   timestamptz,\n    created_by       uuid NOT NULL REFERENCES users(id),\n    created_at       timestamptz NOT NULL DEFAULT now(),\n    deleted_at       timestamptz,         -- soft delete: hidden from normal views, never removed\n    deleted_by       text,\n    delete_reason    text\n);\nCREATE INDEX idx_visits_date ON visits(visit_date);\nCREATE INDEX idx_visits_id_hash ON visits(id_number_hash);\nCREATE INDEX idx_visits_open ON visits(visit_date) WHERE checked_out_at IS NULL AND deleted_at IS NULL;\nCREATE INDEX idx_visits_deleted ON visits(deleted_at) WHERE deleted_at IS NOT NULL;\nCREATE INDEX idx_visits_search ON visits USING gin (\n    (full_name || ' ' || coalesce(company, '') || ' ' || host_name || ' ' || badge_no) gin_trgm_ops\n);\n\nCREATE TABLE audit_logs (\n    id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,\n    at        timestamptz NOT NULL DEFAULT now(),\n    user_id   uuid,\n    username  text,\n    action    text NOT NULL,\n    target    text,\n    detail    text,\n    ip        text\n);\nCREATE INDEX idx_audit_at ON audit_logs(at DESC);\n\n-- Principle of least privilege: the API role can read/write the tables it needs and\n-- nothing else (no DDL, no other databases, no superuser). Rotate this password like any\n-- other secret; it lives only in the backend's environment, never in the frontend.\nDO $$\nBEGIN\n    EXECUTE format('GRANT CONNECT ON DATABASE %I TO visitor_app', current_database());\nEND $$;\nGRANT USAGE ON SCHEMA public TO visitor_app;\nGRANT SELECT, INSERT, UPDATE ON users, sessions, visits TO visitor_app;\nGRANT INSERT, SELECT ON audit_logs TO visitor_app;\nGRANT USAGE ON SEQUENCE badge_seq TO visitor_app;\nGRANT USAGE, SELECT ON SEQUENCE audit_logs_id_seq TO visitor_app;\n-- No DELETE grant anywhere: even a bug or a compromised API can only soft-delete (UPDATE deleted_at).\n"

GRANTS_SQL = """
GRANT USAGE ON SCHEMA public TO visitor_app;
GRANT SELECT, INSERT, UPDATE ON users, sessions, visits TO visitor_app;
GRANT INSERT, SELECT ON audit_logs TO visitor_app;
GRANT USAGE ON SEQUENCE badge_seq TO visitor_app;
GRANT USAGE, SELECT ON SEQUENCE audit_logs_id_seq TO visitor_app;
"""

ROLE_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'visitor_app') THEN
        RAISE EXCEPTION 'Role "visitor_app" does not exist. Create it first, e.g.: '
            'CREATE ROLE visitor_app LOGIN PASSWORD ''<see APP_DB_PASSWORD secret>'';';
    END IF;
END $$;
"""


def _statements(sql: str):
    """asyncpg cannot prepare a string with multiple statements, so split into individual
    statements on ';'. Comments are stripped first because a semicolon can appear inside a
    comment (e.g. 'this secret; that other thing') and would otherwise break the split.
    Dollar-quoted DO $$ ... $$ blocks are kept intact and split on their own '$$;' boundary."""
    no_comments = re.sub(r"--[^\n]*", "", sql)
    parts = re.split(r"(DO \$\$.*?\$\$;)", no_comments, flags=re.S)
    out = []
    for part in parts:
        if part.strip().startswith("DO $$"):
            out.append(part.strip())
        else:
            out.extend(stmt.strip() for stmt in part.split(";") if stmt.strip())
    return out


def upgrade():
    for stmt in _statements(ROLE_SQL):
        op.execute(stmt)
    for stmt in _statements(SCHEMA_SQL):
        op.execute(stmt)
    for stmt in _statements(GRANTS_SQL):
        op.execute(stmt)


def downgrade():
    op.execute("DROP TABLE IF EXISTS audit_logs, visits, sessions, users CASCADE")
    op.execute("DROP SEQUENCE IF EXISTS badge_seq")
