"""
Database connection, session management, and migration utilities.

This module provides async SQLAlchemy engine configuration, session management,
migration utilities, and database utilities for the veterinary clinic platform.
"""

from .connection import (
    DatabaseConfig,
    check_connection,
    check_database_exists,
    close_engine,
    create_database_if_not_exists,
    create_engine,
    get_database_info,
    get_database_url,
    wait_for_database,
)
from .migrations import (
    MigrationManager,
    create_initial_migration,
    get_migration_status,
    run_migrations_async,
    validate_database_schema,
)
from .session import (
    AsyncSessionLocal,
    SessionManager,
    cleanup_database,
    execute_with_retry,
    get_engine,
    get_pool_status,
    get_session,
    get_session_manager,
    get_transaction,
    health_check,
    initialize_database,
    initialize_session_manager,
)

__all__ = [
    # Connection utilities
    "DatabaseConfig",
    "create_engine",
    "get_database_url",
    "check_connection",
    "close_engine",
    "wait_for_database",
    "check_database_exists",
    "get_database_info",
    "create_database_if_not_exists",
    # Session management
    "SessionManager",
    "initialize_session_manager",
    "get_session_manager",
    "get_engine",
    "get_session",
    "get_transaction",
    "execute_with_retry",
    "health_check",
    "initialize_database",
    "cleanup_database",
    "get_pool_status",
    "AsyncSessionLocal",
    # Migration utilities
    "MigrationManager",
    "run_migrations_async",
    "create_initial_migration",
    "validate_database_schema",
    "get_migration_status",
]
