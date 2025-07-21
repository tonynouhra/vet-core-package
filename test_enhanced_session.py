#!/usr/bin/env python3
"""
Test script to verify enhanced session management functionality.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from vet_core.database import (
    SessionManager,
    initialize_session_manager,
    health_check,
    execute_with_retry,
    initialize_database,
    cleanup_database,
    get_pool_status,
)
from vet_core.exceptions import DatabaseException


async def test_enhanced_session_features():
    """Test enhanced session management features."""
    print("Testing enhanced session management features...")
    
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
    
    # Mock URL with password
    mock_engine.url.__str__ = lambda self: "postgresql+asyncpg://user:test_password@localhost:5432/test"
    
    # Initialize session manager
    manager = initialize_session_manager(mock_engine)
    
    # Test 1: Health check functionality
    print("Testing health check...")
    mock_session = AsyncMock()
    
    with patch.object(manager, 'get_session') as mock_get_session:
        mock_get_session.return_value.__aenter__.return_value = mock_session
        with patch.object(manager, 'get_transaction') as mock_get_transaction:
            mock_get_transaction.return_value.__aenter__.return_value = mock_session
            
            health_result = await health_check(force=True)
            
            assert health_result["status"] == "healthy"
            assert "checks" in health_result
            assert "pool_info" in health_result
            assert health_result["checks"]["basic_query"]["status"] == "pass"
            assert health_result["checks"]["transaction"]["status"] == "pass"
            print("✓ Health check successful")
    
    # Test 2: Database initialization
    print("Testing database initialization...")
    with patch.object(manager, 'health_check') as mock_health:
        mock_health.return_value = {"status": "healthy"}
        
        with patch.object(manager.engine, 'begin') as mock_begin:
            mock_conn = AsyncMock()
            mock_begin.return_value.__aenter__.return_value = mock_conn
            
            with patch.object(manager, 'get_session') as mock_get_session:
                mock_get_session.return_value.__aenter__.return_value = mock_session
                
                result = await initialize_database()
                
                assert result is True
                print("✓ Database initialization successful")
    
    # Test 3: Execute with retry
    print("Testing execute with retry...")
    call_count = 0
    
    async def test_operation(session):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            from sqlalchemy.exc import DisconnectionError
            raise DisconnectionError("Connection lost")
        return "success_after_retry"
    
    with patch.object(manager, 'get_transaction') as mock_get_transaction:
        mock_get_transaction.return_value.__aenter__.return_value = mock_session
        
        result = await execute_with_retry(test_operation, max_retries=3, retry_delay=0.01)
        
        assert result == "success_after_retry"
        assert call_count == 2
        print("✓ Execute with retry successful")
    
    # Test 4: Pool status
    print("Testing pool status...")
    pool_status = await get_pool_status()
    
    assert "pool_class" in pool_status
    assert "url" in pool_status
    assert "size" in pool_status
    assert pool_status["pool_class"] == "QueuePool"
    assert "***" in pool_status["url"]  # Password should be masked
    print("✓ Pool status retrieval successful")
    
    # Test 5: Database cleanup
    print("Testing database cleanup...")
    with patch.object(manager.engine, 'begin') as mock_begin:
        mock_conn = AsyncMock()
        mock_begin.return_value.__aenter__.return_value = mock_conn
        
        with patch.object(manager, 'close_all_sessions') as mock_close:
            result = await cleanup_database()
            
            assert result is True
            mock_close.assert_called_once()
            print("✓ Database cleanup successful")
    
    # Test 6: Session configuration
    print("Testing custom session configuration...")
    custom_config = {
        "expire_on_commit": True,
        "autoflush": False,
    }
    
    custom_manager = SessionManager(mock_engine, session_config=custom_config)
    assert custom_manager.engine == mock_engine
    print("✓ Custom session configuration successful")
    
    print("All enhanced features tested successfully! ✅")


if __name__ == "__main__":
    asyncio.run(test_enhanced_session_features())