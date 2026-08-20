"""Alembic environment for FreightPipe."""
from alembic import context
import asyncio
import asyncpg
import os

config = context.config

def run_migrations_offline():
    url = os.environ.get("NEON_DATABASE_URL", "")
    context.configure(url=url, target_metadata=None, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    dsn = os.environ.get("NEON_DATABASE_URL", "")
    async with asyncpg.connect(dsn) as connection:
        await connection.run_sync(do_run_migrations)

def run_migrations_online():
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
