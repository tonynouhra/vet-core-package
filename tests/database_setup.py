"""
Database setup utilities for testing.

This module provides utilities for creating, managing, and cleaning up
test databases across different environments.
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy import text, MetaData
from sqlalchemy.exc import SQLAlchemyError

from vet_core.database.connection import create_engine, get_database_url
from vet_core.database.session import SessionManager
from vet_core.models.base import Base

logger = logging.getLogger(__name__)


class TestDatabaseManager:
    """Manages test database lifecycle and operations."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine: Optional[AsyncEngine] = None
        self.session_manager: Optional[SessionManager] = None
        self._is_postgresql = database_url.startswith("postgresql")
        self._is_sqlite = database_url.startswith("sqlite")
        
    async def create_engine(self, **kwargs) -> AsyncEngine:
        """Create and configure the test database engine."""
        engine_kwargs = {
            "use_null_pool": True,  # Don't pool connections in tests
            "echo": False,
            **kwargs
        }
        
        self.engine = create_engine(self.database_url, **engine_kwargs)
        return self.engine
    
    async def create_session_manager(self) -> SessionManager:
        """Create and configure the session manager."""
        if self.engine is None:
            await self.create_engine()
        
        self.session_manager = SessionManager(self.engine)
        return self.session_manager
    
    async def create_database_if_not_exists(self) -> bool:
        """
        Create the test database if it doesn't exist.
        
        Returns:
            True if database was created or already exists, False on error
        """
        if self._is_sqlite:
            # SQLite databases are created automatically
            return True
        
        if not self._is_postgresql:
            logger.warning(f"Database creation not supported for {self.database_url}")
            return False
        
        try:
            # Parse database URL to get connection info
            parsed = urlparse(self.database_url)
            database_name = parsed.path.lstrip('/')
            
            # Create admin connection URL (connect to postgres database)
            admin_url = self.database_url.replace(f"/{database_name}", "/postgres")
            
            # Create admin engine
            admin_engine = create_engine(admin_url, use_null_pool=True)
            
            try:
                # Check if database exists
                async with admin_engine.begin() as conn:
                    result = await conn.execute(
                        text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                        {"db_name": database_name}
                    )
                    
                    if result.fetchone() is None:
                        # Database doesn't exist, create it
                        await conn.execute(text("COMMIT"))  # End transaction
                        await conn.execute(text(f'CREATE DATABASE "{database_name}"'))
                        logger.info(f"Created test database: {database_name}")
                    else:
                        logger.info(f"Test database already exists: {database_name}")
                
                return True
                
            finally:
                await admin_engine.dispose()
                
        except Exception as e:
            logger.error(f"Failed to create test database: {e}")
            return False
    
    async def drop_database_if_exists(self) -> bool:
        """
        Drop the test database if it exists.
        
        Returns:
            True if database was dropped or didn't exist, False on error
        """
        if self._is_sqlite:
            # SQLite in-memory databases are automatically cleaned up
            return True
        
        if not self._is_postgresql:
            logger.warning(f"Database dropping not supported for {self.database_url}")
            return False
        
        try:
            # Parse database URL to get connection info
            parsed = urlparse(self.database_url)
            database_name = parsed.path.lstrip('/')
            
            # Create admin connection URL
            admin_url = self.database_url.replace(f"/{database_name}", "/postgres")
            
            # Create admin engine
            admin_engine = create_engine(admin_url, use_null_pool=True)
            
            try:
                async with admin_engine.begin() as conn:
                    # Terminate active connections to the database
                    await conn.execute(
                        text("""
                            SELECT pg_terminate_backend(pid)
                            FROM pg_stat_activity
                            WHERE datname = :db_name AND pid <> pg_backend_pid()
                        """),
                        {"db_name": database_name}
                    )
                    
                    # Drop database if it exists
                    await conn.execute(text("COMMIT"))  # End transaction
                    await conn.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
                    logger.info(f"Dropped test database: {database_name}")
                
                return True
                
            finally:
                await admin_engine.dispose()
                
        except Exception as e:
            logger.error(f"Failed to drop test database: {e}")
            return False
    
    async def create_schema(self, metadata: Optional[MetaData] = None) -> bool:
        """
        Create database schema from metadata.
        
        Args:
            metadata: SQLAlchemy metadata object, defaults to Base.metadata
            
        Returns:
            True if schema was created successfully, False on error
        """
        if metadata is None:
            metadata = Base.metadata
        
        if self.engine is None:
            await self.create_engine()
        
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(metadata.create_all)
            
            logger.info("Created database schema successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create database schema: {e}")
            return False
    
    async def drop_schema(self, metadata: Optional[MetaData] = None) -> bool:
        """
        Drop database schema.
        
        Args:
            metadata: SQLAlchemy metadata object, defaults to Base.metadata
            
        Returns:
            True if schema was dropped successfully, False on error
        """
        if metadata is None:
            metadata = Base.metadata
        
        if self.engine is None:
            await self.create_engine()
        
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(metadata.drop_all)
            
            logger.info("Dropped database schema successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to drop database schema: {e}")
            return False
    
    async def truncate_all_tables(self) -> bool:
        """
        Truncate all tables in the database.
        
        Returns:
            True if tables were truncated successfully, False on error
        """
        if self.engine is None:
            await self.create_engine()
        
        try:
            if self._is_postgresql:
                # Get all table names
                async with self.engine.begin() as conn:
                    result = await conn.execute(
                        text("""
                            SELECT tablename FROM pg_tables 
                            WHERE schemaname = 'public' 
                            AND tablename NOT LIKE 'alembic_%'
                        """)
                    )
                    table_names = [row[0] for row in result.fetchall()]
                    
                    if table_names:
                        # Truncate all tables with CASCADE to handle foreign keys
                        tables_str = ', '.join(f'"{name}"' for name in table_names)
                        await conn.execute(text(f"TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE"))
                        
            elif self._is_sqlite:
                # For SQLite, delete from all tables
                async with self.engine.begin() as conn:
                    result = await conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                    )
                    table_names = [row[0] for row in result.fetchall()]
                    
                    for table_name in table_names:
                        await conn.execute(text(f"DELETE FROM {table_name}"))
            
            logger.info("Truncated all tables successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to truncate tables: {e}")
            return False
    
    async def get_table_counts(self) -> Dict[str, int]:
        """
        Get record counts for all tables.
        
        Returns:
            Dictionary mapping table names to record counts
        """
        if self.engine is None:
            await self.create_engine()
        
        counts = {}
        
        try:
            if self._is_postgresql:
                async with self.engine.begin() as conn:
                    result = await conn.execute(
                        text("""
                            SELECT tablename FROM pg_tables 
                            WHERE schemaname = 'public' 
                            AND tablename NOT LIKE 'alembic_%'
                        """)
                    )
                    table_names = [row[0] for row in result.fetchall()]
                    
                    for table_name in table_names:
                        count_result = await conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                        counts[table_name] = count_result.scalar()
                        
            elif self._is_sqlite:
                async with self.engine.begin() as conn:
                    result = await conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                    )
                    table_names = [row[0] for row in result.fetchall()]
                    
                    for table_name in table_names:
                        count_result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                        counts[table_name] = count_result.scalar()
            
        except Exception as e:
            logger.error(f"Failed to get table counts: {e}")
        
        return counts
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the test database.
        
        Returns:
            Dictionary with health check results
        """
        if self.engine is None:
            await self.create_engine()
        
        health_info = {
            "database_url": self.database_url,
            "engine_created": self.engine is not None,
            "connection_test": False,
            "schema_exists": False,
            "table_counts": {},
            "error": None
        }
        
        try:
            # Test basic connection
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                health_info["connection_test"] = True
                
                # Check if main tables exist
                if self._is_postgresql:
                    result = await conn.execute(
                        text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
                    )
                    table_count = result.scalar()
                    health_info["schema_exists"] = table_count > 0
                    
                elif self._is_sqlite:
                    result = await conn.execute(
                        text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                    )
                    table_count = result.scalar()
                    health_info["schema_exists"] = table_count > 0
                
                # Get table counts
                health_info["table_counts"] = await self.get_table_counts()
                
        except Exception as e:
            health_info["error"] = str(e)
            logger.error(f"Database health check failed: {e}")
        
        return health_info
    
    async def cleanup(self) -> None:
        """Clean up database resources."""
        if self.session_manager:
            await self.session_manager.close_all_sessions()
        
        if self.engine:
            await self.engine.dispose()
        
        logger.info("Database cleanup completed")


# Global test database manager instance
_test_db_manager: Optional[TestDatabaseManager] = None


def get_test_database_manager(database_url: Optional[str] = None) -> TestDatabaseManager:
    """
    Get or create the global test database manager.
    
    Args:
        database_url: Database URL, uses TEST_DATABASE_URL env var if not provided
        
    Returns:
        TestDatabaseManager instance
    """
    global _test_db_manager
    
    if database_url is None:
        database_url = os.getenv(
            "TEST_DATABASE_URL",
            "sqlite+aiosqlite:///:memory:"
        )
    
    if _test_db_manager is None or _test_db_manager.database_url != database_url:
        _test_db_manager = TestDatabaseManager(database_url)
    
    return _test_db_manager


async def setup_test_database(database_url: Optional[str] = None) -> TestDatabaseManager:
    """
    Set up a test database with schema.
    
    Args:
        database_url: Database URL, uses TEST_DATABASE_URL env var if not provided
        
    Returns:
        Configured TestDatabaseManager instance
    """
    manager = get_test_database_manager(database_url)
    
    # Create database if needed
    await manager.create_database_if_not_exists()
    
    # Create engine and session manager
    await manager.create_engine()
    await manager.create_session_manager()
    
    # Create schema
    await manager.create_schema()
    
    logger.info(f"Test database setup completed: {manager.database_url}")
    return manager


async def teardown_test_database(manager: Optional[TestDatabaseManager] = None) -> None:
    """
    Tear down test database and clean up resources.
    
    Args:
        manager: TestDatabaseManager instance, uses global if not provided
    """
    if manager is None:
        manager = get_test_database_manager()
    
    await manager.cleanup()
    
    # Optionally drop the database (useful for integration tests)
    if os.getenv("TEST_DROP_DATABASE", "false").lower() == "true":
        await manager.drop_database_if_exists()
    
    logger.info("Test database teardown completed")


async def reset_test_database(manager: Optional[TestDatabaseManager] = None) -> None:
    """
    Reset test database to clean state.
    
    Args:
        manager: TestDatabaseManager instance, uses global if not provided
    """
    if manager is None:
        manager = get_test_database_manager()
    
    # Truncate all tables
    await manager.truncate_all_tables()
    
    logger.info("Test database reset completed")


# Convenience functions for pytest fixtures
async def pytest_setup_database():
    """Set up database for pytest session."""
    return await setup_test_database()


async def pytest_teardown_database():
    """Tear down database after pytest session."""
    await teardown_test_database()


async def pytest_reset_database():
    """Reset database between pytest tests."""
    await reset_test_database()