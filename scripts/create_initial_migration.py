#!/usr/bin/env python3
"""
Script to create the initial migration with all core models.

This script creates the initial Alembic migration without requiring
a database connection, using offline mode.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path so we can import vet_core
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging

from alembic import command
from alembic.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_initial_migration():
    """Create the initial migration with all core models."""
    try:
        # Get the path to alembic.ini
        alembic_ini_path = Path(__file__).parent.parent / "alembic.ini"

        if not alembic_ini_path.exists():
            raise FileNotFoundError(f"alembic.ini not found at {alembic_ini_path}")

        # Create Alembic config
        alembic_cfg = Config(str(alembic_ini_path))

        # Set a dummy database URL to avoid connection issues during migration creation
        alembic_cfg.set_main_option(
            "sqlalchemy.url", "postgresql+asyncpg://dummy:dummy@localhost/dummy"
        )

        logger.info("Creating initial migration with all core models...")

        # Create the migration
        command.revision(
            alembic_cfg,
            message="Initial migration with all core models",
            autogenerate=True,
        )

        logger.info("Initial migration created successfully!")

    except Exception as e:
        logger.error(f"Failed to create initial migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_initial_migration()
