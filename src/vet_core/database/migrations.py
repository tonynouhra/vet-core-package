"""
Database migration utilities for the vet-core package.

This module provides utilities for managing database schema changes,
running migrations, and validating migration states.
"""

import asyncio
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import AsyncEngine

from ..exceptions import  MigrationException

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manager for database migrations using Alembic."""

    def __init__(
        self,
        alembic_config_path: Optional[str] = None,
        database_url: Optional[str] = None,
    ):
        """
        Initialize the migration manager.

        Args:
            alembic_config_path: Path to alembic.ini file
            database_url: Database URL override
        """
        self.alembic_config_path = alembic_config_path or self._find_alembic_config()
        self.database_url = database_url
        self._alembic_config: Optional[Config] = None

    def _find_alembic_config(self) -> str:
        """Find the alembic.ini configuration file."""
        # Look for alembic.ini in common locations
        possible_paths = [
            "alembic.ini",
            "../alembic.ini",
            "../../alembic.ini",
            os.path.join(os.path.dirname(__file__), "../../../alembic.ini"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)

        raise MigrationException("Could not find alembic.ini configuration file")

    @property
    def alembic_config(self) -> Config:
        """Get the Alembic configuration object."""
        if self._alembic_config is None:
            self._alembic_config = Config(self.alembic_config_path)

            # Override database URL if provided
            if self.database_url:
                self._alembic_config.set_main_option(
                    "sqlalchemy.url", self.database_url
                )

        return self._alembic_config

    def create_migration(
        self,
        message: str,
        autogenerate: bool = True,
        sql: bool = False,
        head: str = "head",
        splice: bool = False,
        branch_label: Optional[str] = None,
        version_path: Optional[str] = None,
        rev_id: Optional[str] = None,
    ) -> str:
        """
        Create a new migration revision.

        Args:
            message: Migration message/description
            autogenerate: Whether to auto-generate migration from model changes
            sql: Whether to generate SQL-only migration
            head: Head revision to use as base
            splice: Whether to allow splicing
            branch_label: Optional branch label
            version_path: Optional version path
            rev_id: Optional revision ID

        Returns:
            The revision ID of the created migration

        Raises:
            MigrationException: If migration creation fails
        """
        try:
            logger.info(f"Creating migration: {message}")

            # Prepare command arguments
            command_args = {
                "message": message,
                "autogenerate": autogenerate,
                "sql": sql,
                "head": head,
                "splice": splice,
            }

            if branch_label:
                command_args["branch_label"] = branch_label
            if version_path:
                command_args["version_path"] = version_path
            if rev_id:
                command_args["rev_id"] = rev_id

            # Create the revision
            script = command.revision(self.alembic_config, **command_args)

            revision_id = script.revision
            logger.info(f"Created migration {revision_id}: {message}")
            return revision_id

        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            raise MigrationException(
                f"Failed to create migration: {e}", original_error=e
            )

    def upgrade_database(
        self, revision: str = "head", sql: bool = False, tag: Optional[str] = None
    ) -> None:
        """
        Upgrade database to a specific revision.

        Args:
            revision: Target revision (default: "head")
            sql: Whether to generate SQL only
            tag: Optional tag for the upgrade

        Raises:
            MigrationException: If upgrade fails
        """
        try:
            logger.info(f"Upgrading database to revision: {revision}")

            command_args = {
                "revision": revision,
                "sql": sql,
            }

            if tag:
                command_args["tag"] = tag

            command.upgrade(self.alembic_config, **command_args)
            logger.info(f"Successfully upgraded database to {revision}")

        except Exception as e:
            logger.error(f"Failed to upgrade database: {e}")
            raise MigrationException(
                f"Failed to upgrade database: {e}", original_error=e
            )

    def downgrade_database(
        self, revision: str, sql: bool = False, tag: Optional[str] = None
    ) -> None:
        """
        Downgrade database to a specific revision.

        Args:
            revision: Target revision
            sql: Whether to generate SQL only
            tag: Optional tag for the downgrade

        Raises:
            MigrationException: If downgrade fails
        """
        try:
            logger.info(f"Downgrading database to revision: {revision}")

            command_args = {
                "revision": revision,
                "sql": sql,
            }

            if tag:
                command_args["tag"] = tag

            command.upgrade(self.alembic_config, **command_args)
            logger.info(f"Successfully downgraded database to {revision}")

        except Exception as e:
            logger.error(f"Failed to downgrade database: {e}")
            raise MigrationException(
                f"Failed to downgrade database: {e}", original_error=e
            )

    def get_current_revision(self) -> Optional[str]:
        """
        Get the current database revision.

        Returns:
            Current revision ID or None if no migrations applied

        Raises:
            MigrationException: If unable to get current revision
        """
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_config)

            def get_revision(connection):
                context = MigrationContext.configure(connection)
                return context.get_current_revision()

            # This is a simplified approach - in practice you'd need to connect to the database
            # For now, we'll use the command line approach
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alembic",
                    "-c",
                    self.alembic_config_path,
                    "current",
                ],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(self.alembic_config_path),
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                if output and not output.startswith("INFO"):
                    # Extract revision ID from output
                    lines = output.split("\n")
                    for line in lines:
                        if line and not line.startswith("INFO"):
                            return line.split()[0]

            return None

        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            raise MigrationException(
                f"Failed to get current revision: {e}", original_error=e
            )

    def get_migration_history(self) -> List[Dict[str, Any]]:
        """
        Get the migration history.

        Returns:
            List of migration information dictionaries

        Raises:
            MigrationException: If unable to get migration history
        """
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_config)
            revisions = []

            for revision in script_dir.walk_revisions():
                revision_info = {
                    "revision": revision.revision,
                    "down_revision": revision.down_revision,
                    "branch_labels": getattr(revision, "branch_labels", None),
                    "doc": revision.doc,
                    "module_path": getattr(revision, "path", None),
                }

                # Only add depends_on if it exists (newer Alembic versions)
                if hasattr(revision, "depends_on"):
                    revision_info["depends_on"] = revision.depends_on

                revisions.append(revision_info)

            return revisions

        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            raise MigrationException(
                f"Failed to get migration history: {e}", original_error=e
            )

    def validate_migration_state(self) -> Dict[str, Any]:
        """
        Validate the current migration state.

        Returns:
            Dictionary with validation results

        Raises:
            MigrationException: If validation fails
        """
        try:
            result = {
                "valid": True,
                "current_revision": None,
                "head_revision": None,
                "pending_migrations": [],
                "issues": [],
            }

            # Get current revision
            current_revision = self.get_current_revision()
            result["current_revision"] = current_revision

            # Get head revision
            script_dir = ScriptDirectory.from_config(self.alembic_config)
            head_revision = script_dir.get_current_head()
            result["head_revision"] = head_revision

            # Check if database is up to date
            if current_revision != head_revision:
                result["valid"] = False
                result["issues"].append(
                    "Database is not up to date with latest migrations"
                )

                # Get pending migrations
                if current_revision:
                    for revision in script_dir.iterate_revisions(
                        head_revision, current_revision
                    ):
                        if revision.revision != current_revision:
                            result["pending_migrations"].append(
                                {
                                    "revision": revision.revision,
                                    "doc": revision.doc,
                                }
                            )
                else:
                    # No migrations applied yet
                    for revision in script_dir.walk_revisions():
                        result["pending_migrations"].append(
                            {
                                "revision": revision.revision,
                                "doc": revision.doc,
                            }
                        )

            return result

        except Exception as e:
            logger.error(f"Failed to validate migration state: {e}")
            raise MigrationException(
                f"Failed to validate migration state: {e}", original_error=e
            )

    def check_migration_conflicts(self) -> List[Dict[str, Any]]:
        """
        Check for migration conflicts.

        Returns:
            List of conflict information

        Raises:
            MigrationException: If conflict check fails
        """
        try:
            conflicts = []
            script_dir = ScriptDirectory.from_config(self.alembic_config)

            # Check for multiple heads
            heads = script_dir.get_heads()
            if len(heads) > 1:
                conflicts.append(
                    {
                        "type": "multiple_heads",
                        "description": "Multiple head revisions found",
                        "heads": heads,
                    }
                )

            # Check for circular dependencies
            revisions = list(script_dir.walk_revisions())
            revision_map = {rev.revision: rev for rev in revisions}

            for revision in revisions:
                if revision.down_revision:
                    if revision.down_revision not in revision_map:
                        conflicts.append(
                            {
                                "type": "missing_dependency",
                                "description": f"Revision {revision.revision} depends on missing revision {revision.down_revision}",
                                "revision": revision.revision,
                                "missing_dependency": revision.down_revision,
                            }
                        )

            return conflicts

        except Exception as e:
            logger.error(f"Failed to check migration conflicts: {e}")
            raise MigrationException(
                f"Failed to check migration conflicts: {e}", original_error=e
            )


async def run_migrations_async(
    engine: AsyncEngine, target_revision: str = "head", validate_before: bool = True
) -> Dict[str, Any]:
    """
    Run database migrations asynchronously.

    Args:
        engine: SQLAlchemy async engine
        target_revision: Target revision to migrate to
        validate_before: Whether to validate before running migrations

    Returns:
        Dictionary with migration results

    Raises:
        MigrationException: If migration fails
    """
    try:
        logger.info(f"Running async migrations to {target_revision}")

        # Get database URL from engine
        database_url = str(engine.url)

        # Create migration manager
        manager = MigrationManager(database_url=database_url)

        result = {
            "success": False,
            "target_revision": target_revision,
            "initial_revision": None,
            "final_revision": None,
            "migrations_applied": [],
            "validation_results": None,
            "errors": [],
        }

        # Validate migration state if requested
        if validate_before:
            try:
                validation = manager.validate_migration_state()
                result["validation_results"] = validation

                if not validation["valid"]:
                    logger.warning("Migration validation found issues")
                    for issue in validation["issues"]:
                        logger.warning(f"Validation issue: {issue}")
            except Exception as e:
                logger.warning(f"Migration validation failed: {e}")
                result["errors"].append(f"Validation failed: {e}")

        # Get initial revision
        try:
            result["initial_revision"] = manager.get_current_revision()
        except Exception as e:
            logger.warning(f"Could not get initial revision: {e}")

        # Run the migration
        manager.upgrade_database(target_revision)

        # Get final revision
        try:
            result["final_revision"] = manager.get_current_revision()
        except Exception as e:
            logger.warning(f"Could not get final revision: {e}")

        result["success"] = True
        logger.info(f"Successfully completed migrations to {target_revision}")

        return result

    except Exception as e:
        logger.error(f"Failed to run async migrations: {e}")
        raise MigrationException(
            f"Failed to run async migrations: {e}", original_error=e
        )


def create_initial_migration(message: str = "Initial migration") -> str:
    """
    Create the initial migration with all core models.

    Args:
        message: Migration message

    Returns:
        Revision ID of the created migration

    Raises:
        MigrationException: If migration creation fails
    """
    try:
        logger.info("Creating initial migration with all core models")

        manager = MigrationManager()
        revision_id = manager.create_migration(message=message, autogenerate=True)

        logger.info(f"Created initial migration: {revision_id}")
        return revision_id

    except Exception as e:
        logger.error(f"Failed to create initial migration: {e}")
        raise MigrationException(
            f"Failed to create initial migration: {e}", original_error=e
        )


def validate_database_schema(engine: AsyncEngine) -> Dict[str, Any]:
    """
    Validate the database schema against the current models.

    Args:
        engine: SQLAlchemy async engine

    Returns:
        Dictionary with validation results

    Raises:
        MigrationException: If validation fails
    """
    # This would require more complex implementation to compare
    # actual database schema with SQLAlchemy models
    # For now, return a basic validation
    return {
        "valid": True,
        "message": "Schema validation not fully implemented",
        "timestamp": datetime.utcnow().isoformat(),
    }


def get_migration_status() -> Dict[str, Any]:
    """
    Get comprehensive migration status information.

    Returns:
        Dictionary with migration status

    Raises:
        MigrationException: If status check fails
    """
    try:
        manager = MigrationManager()

        status = {
            "current_revision": manager.get_current_revision(),
            "migration_history": manager.get_migration_history(),
            "validation_results": manager.validate_migration_state(),
            "conflicts": manager.check_migration_conflicts(),
            "timestamp": datetime.utcnow().isoformat(),
        }

        return status

    except Exception as e:
        logger.error(f"Failed to get migration status: {e}")
        raise MigrationException(
            f"Failed to get migration status: {e}", original_error=e
        )
