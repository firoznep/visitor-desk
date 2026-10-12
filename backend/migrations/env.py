import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.db import Base
from app.models import *  # noqa: F401,F403  (registers all tables on Base.metadata)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _db_url() -> str:
    # Migrations need schema-owner privileges (CREATE TABLE, GRANT, ...). The running API
    # uses the restricted `visitor_app` role instead (see db/init/001_schema.sql), which
    # cannot alter schema even if the API is compromised. Point MIGRATION_DATABASE_URL at a
    # superuser/owner connection; DATABASE_URL is kept as a fallback for local dev only.
    return os.environ.get("MIGRATION_DATABASE_URL") or os.environ["DATABASE_URL"]


def run_migrations_offline():
    context.configure(url=_db_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    engine = create_async_engine(_db_url())
    async with engine.connect() as connection:
        await connection.run_sync(
            lambda conn: context.configure(connection=conn, target_metadata=target_metadata)
        )
        async with connection.begin():
            await connection.run_sync(lambda conn: context.run_migrations())
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
