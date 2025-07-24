#!/usr/bin/env python3
"""
Simple test script to verify session management functionality.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from vet_core.database import (
    SessionManager,
    get_session_manager,
    initialize_session_manager,
)


async def test_session_manager():
    """Test basic SessionManager functionality."""
    print("Testing SessionManager...")

    # Create mock engine
    mock_engine = AsyncMock()
    mock_engine.url = MagicMock()
    mock_engine.url.password = "test_password"

    # Mock pool
    pool = MagicMock()
    pool.size.return_value = 10
    pool.checkedin.return_value = 8
    pool.checkedout.return_value = 2
    pool.overflow.return_value = 0
    pool.invalid.return_value = 0
    pool.__class__.__name__ = "QueuePool"
    mock_engine.pool = pool

    # Test SessionManager creation
    manager = SessionManager(mock_engine)
    assert manager.engine == mock_engine
    assert not manager.is_initialized
    print("✓ SessionManager creation successful")

    # Test global session manager
    global_manager = initialize_session_manager(mock_engine)
    assert isinstance(global_manager, SessionManager)
    assert get_session_manager() == global_manager
    print("✓ Global session manager initialization successful")

    # Test pool status
    pool_status = await manager.get_pool_status()
    assert "pool_class" in pool_status
    assert "url" in pool_status
    assert pool_status["pool_class"] == "QueuePool"
    print("✓ Pool status retrieval successful")

    print("All tests passed! ✅")


if __name__ == "__main__":
    asyncio.run(test_session_manager())
