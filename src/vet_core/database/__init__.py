"""
Database connection and session management utilities.

This module provides async SQLAlchemy engine configuration, session management,
and database utilities for the veterinary clinic platform.
"""

from .connection import (
    DatabaseConfig,
    create_engine,
    get_database_url,
    test_connection,
    close_engine,
    wait_for_database,
    check_database_exists,
    get_database_info,
    create_database_if_not_exists,
)
from .session import (
    SessionManager,
    initialize_session_manager,
    get_session_manager,
    get_session,
    get_transaction,
    execute_with_retry,
    health_check,
    initialize_database,
    cleanup_database,
    get_pool_status,
    AsyncSessionLocal,
)

__all__ = [
    # Connection utilities
    "DatabaseConfig",
    "create_engine",
    "get_database_url",
    "test_connection",
    "close_engine",
    "wait_for_database",
    "check_database_exists",
    "get_database_info",
    "create_database_if_not_exists",
    # Session management
    "SessionManager",
    "initialize_session_manager",
    "get_session_manager",
    "get_session",
    "get_transaction",
    "execute_with_retry",
    "health_check",
    "initialize_database",
    "cleanup_database",
    "get_pool_status",
    "AsyncSessionLocal",
]