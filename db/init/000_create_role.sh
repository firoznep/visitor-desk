#!/usr/bin/env bash
# Runs before 001_schema.sql (docker-entrypoint-initdb.d executes files in name order).
# Creates the least-privilege application role using the password from the environment,
# so the password is never written into a .sql file or into version control.
set -euo pipefail
: "${APP_DB_PASSWORD:?APP_DB_PASSWORD must be set (see .env.db.example)}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'visitor_app') THEN
            CREATE ROLE visitor_app LOGIN PASSWORD '$APP_DB_PASSWORD';
        END IF;
    END \$\$;
SQL
