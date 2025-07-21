"""Alembic environment configuration for vet-core package."""

import asyncio
import os
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import all models to ensure they are registered with SQLAlchemy
from vet_core.models import (
    BaseModel,
    User, Pet, Appointment, Clinic, Veterinarian
)
from vet_core.utils.config import EnvironmentConfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = BaseModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url() -> str:
    """Get database URL from environment variables or config."""
    # Try to get from environment first
    database_url = EnvironmentConfig.get_str("DATABASE_URL")
    
    if not database_url:
        # Fall back to config file
        database_url = config.get_main_option("sqlalchemy.url")
    
    if not database_url:
        # Build from individual components
        host = EnvironmentConfig.get_str("DB_HOST", "localhost")
        port = EnvironmentConfig.get_int("DB_PORT", 5432)
        database = EnvironmentConfig.get_str("DB_NAME", "vetcore")
        username = EnvironmentConfig.get_str("DB_USER", "postgres")
        password = EnvironmentConfig.get_str("DB_PASSWORD", "")
        
        if password:
            database_url = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"
        else:
            database_url = f"postgresql+asyncpg://{username}@{host}:{port}/{database}"
    
    return database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get configuration section and override URL
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()