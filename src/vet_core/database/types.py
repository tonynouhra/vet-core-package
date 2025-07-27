"""
Database-agnostic column types for vet-core.

This module provides column types that work across different database backends,
particularly for handling JSON data in both PostgreSQL and SQLite.
"""

from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB


class JSONType(TypeDecorator):
    """
    Database-agnostic JSON column type.

    Uses JSONB for PostgreSQL and JSON for other databases (like SQLite).
    This ensures compatibility across different database backends while
    maintaining optimal performance for each.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Load the appropriate JSON type based on the database dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())
