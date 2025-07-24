#!/usr/bin/env python3
"""
Example demonstrating enhanced database session management features.

This example shows how to use the vet-core package's database session
management capabilities including:
- Async session factory with proper lifecycle management
- Transaction context managers for atomic operations
- Connection pooling configuration and health checks
- Database initialization and cleanup utilities
"""

import asyncio
import os

from sqlalchemy import Column, Integer, MetaData, String, Table, text

from vet_core.database import (
    cleanup_database,
    create_engine,
    execute_with_retry,
    get_pool_status,
    get_session,
    get_transaction,
    health_check,
    initialize_database,
    initialize_session_manager,
)


async def demonstrate_session_management():
    """Demonstrate session management features."""
    print("🏥 Vet Core Package - Session Management Demo")
    print("=" * 50)

    # 1. Create database engine with enhanced configuration
    print("\n1. Creating database engine...")
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:password@localhost:5432/vet_clinic_dev",
    )

    engine = create_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
        echo=False,  # Set to True for SQL logging
    )
    print("✓ Database engine created with connection pooling")

    # 2. Initialize session manager
    print("\n2. Initializing session manager...")
    session_manager = initialize_session_manager(engine)
    print("✓ Session manager initialized")

    # 3. Perform health check
    print("\n3. Performing database health check...")
    try:
        health_status = await health_check(force=True)
        print(f"✓ Health status: {health_status['status']}")

        if health_status["status"] == "healthy":
            for check_name, check_result in health_status["checks"].items():
                print(
                    f"  - {check_name}: {check_result['status']} "
                    f"({check_result.get('response_time', 0)}ms)"
                )

        # Show pool information
        if "pool_info" in health_status:
            pool_info = health_status["pool_info"]
            print(
                f"  - Pool: {pool_info.get('checked_out', 0)}/{pool_info.get('size', 0)} connections in use"
            )

    except Exception as e:
        print(f"⚠️  Health check failed: {e}")
        print("This is expected if no database is running")

    # 4. Get detailed pool status
    print("\n4. Getting connection pool status...")
    try:
        pool_status = await get_pool_status()
        print(f"✓ Pool class: {pool_status['pool_class']}")
        print(f"✓ Pool size: {pool_status.get('size', 'N/A')}")
        print(f"✓ Active connections: {pool_status.get('checked_out', 'N/A')}")
        print(f"✓ Available connections: {pool_status.get('checked_in', 'N/A')}")
    except Exception as e:
        print(f"⚠️  Pool status check failed: {e}")

    # 5. Demonstrate session usage patterns
    print("\n5. Demonstrating session usage patterns...")

    # Basic session usage
    print("   a) Basic session usage:")
    try:
        async with get_session() as session:
            result = await session.execute(text("SELECT 1 as test_value"))
            value = result.scalar()
            print(f"      ✓ Basic query result: {value}")
    except Exception as e:
        print(f"      ⚠️  Basic session failed: {e}")

    # Transaction usage
    print("   b) Transaction usage:")
    try:
        async with get_transaction() as session:
            # All operations in this block are part of one transaction
            result = await session.execute(text("SELECT 'Transaction Test' as message"))
            message = result.scalar()
            print(f"      ✓ Transaction query result: {message}")
            # Transaction is automatically committed on success
    except Exception as e:
        print(f"      ⚠️  Transaction failed: {e}")

    # 6. Demonstrate retry mechanism
    print("\n6. Demonstrating retry mechanism...")

    async def sample_database_operation(session):
        """Sample operation that might need retry logic."""
        result = await session.execute(text("SELECT 'Retry Test Success' as message"))
        return result.scalar()

    try:
        result = await execute_with_retry(
            sample_database_operation,
            max_retries=3,
            retry_delay=0.1,
            exponential_backoff=True,
        )
        print(f"✓ Retry operation result: {result}")
    except Exception as e:
        print(f"⚠️  Retry operation failed: {e}")

    # 7. Database initialization example
    print("\n7. Demonstrating database initialization...")

    # Create sample metadata for demonstration
    metadata = MetaData()
    sample_table = Table(
        "demo_table",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(50)),
        Column("description", String(200)),
    )

    try:
        # Note: This would create tables in a real database
        # For demo purposes, we'll skip actual table creation
        print("✓ Database initialization prepared (skipped for demo)")
        # result = await initialize_database(metadata)
        # print(f"✓ Database initialization: {'Success' if result else 'Failed'}")
    except Exception as e:
        print(f"⚠️  Database initialization failed: {e}")

    # 8. Cleanup
    print("\n8. Cleaning up resources...")
    try:
        await cleanup_database()
        print("✓ Database cleanup completed")
    except Exception as e:
        print(f"⚠️  Cleanup failed: {e}")

    # Close engine
    await engine.dispose()
    print("✓ Database engine disposed")

    print("\n" + "=" * 50)
    print("🎉 Session management demonstration completed!")
    print("\nKey Features Demonstrated:")
    print("• Async session factory with lifecycle management")
    print("• Transaction context managers for atomic operations")
    print("• Connection pooling with health monitoring")
    print("• Retry mechanisms for transient failures")
    print("• Database initialization and cleanup utilities")
    print("• Comprehensive health checks and monitoring")


async def demonstrate_advanced_patterns():
    """Demonstrate advanced session management patterns."""
    print("\n🔧 Advanced Session Management Patterns")
    print("=" * 50)

    # Custom session configuration
    print("\n1. Custom session configuration...")
    database_url = "postgresql+asyncpg://user:pass@localhost:5432/test"

    engine = create_engine(database_url, use_null_pool=True)  # For demo

    from vet_core.database import SessionManager

    # Custom session settings
    custom_session_config = {
        "expire_on_commit": False,
        "autoflush": True,
        "autocommit": False,
    }

    custom_manager = SessionManager(engine, session_config=custom_session_config)
    print("✓ Custom session manager created")

    # Demonstrate batch operations pattern
    print("\n2. Batch operations pattern...")

    async def batch_operation_example():
        """Example of handling batch operations efficiently."""
        try:
            async with custom_manager.get_transaction() as session:
                # Simulate batch operations
                operations = [
                    "INSERT INTO users (name) VALUES ('User 1')",
                    "INSERT INTO users (name) VALUES ('User 2')",
                    "INSERT INTO users (name) VALUES ('User 3')",
                ]

                for i, op in enumerate(operations, 1):
                    # In real scenario, these would be actual SQL operations
                    print(f"   ✓ Batch operation {i} prepared")

                print("   ✓ All batch operations would be committed together")
                return len(operations)
        except Exception as e:
            print(f"   ⚠️  Batch operation failed: {e}")
            return 0

    batch_count = await batch_operation_example()
    print(f"✓ Batch operations pattern demonstrated ({batch_count} operations)")

    # Connection pool monitoring
    print("\n3. Connection pool monitoring...")

    async def monitor_pool():
        """Monitor connection pool status."""
        try:
            status = await custom_manager.get_pool_status()
            print(f"   • Pool type: {status['pool_class']}")
            print(
                f"   • URL: {status['url'][:50]}..."
                if len(status["url"]) > 50
                else f"   • URL: {status['url']}"
            )

            if "size" in status:
                print(f"   • Pool size: {status['size']}")
                print(f"   • Checked out: {status['checked_out']}")
                print(f"   • Checked in: {status['checked_in']}")
        except Exception as e:
            print(f"   ⚠️  Pool monitoring failed: {e}")

    await monitor_pool()
    print("✓ Pool monitoring demonstrated")

    await engine.dispose()
    print("✓ Advanced patterns demonstration completed")


if __name__ == "__main__":
    print("Starting vet-core session management demonstration...")
    print("Note: Some features require a running PostgreSQL database")
    print("Set DATABASE_URL environment variable to connect to your database")
    print()

    asyncio.run(demonstrate_session_management())
    asyncio.run(demonstrate_advanced_patterns())
