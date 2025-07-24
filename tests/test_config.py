"""
Test configuration for the vet-core package.

This module provides configuration settings and utilities for different
testing environments and scenarios.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class TestEnvironment(Enum):
    """Test environment types."""
    UNIT = "unit"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    CI = "ci"


@dataclass
class DatabaseTestConfig:
    """Configuration for test database connections."""
    url: str
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    use_null_pool: bool = True
    connect_timeout: int = 10
    
    @classmethod
    def from_environment(cls) -> "DatabaseTestConfig":
        """Create config from environment variables."""
        return cls(
            url=os.getenv(
                "TEST_DATABASE_URL",
                "postgresql+asyncpg://postgres:postgres@localhost:5432/vet_core_test"
            ),
            echo=os.getenv("TEST_DB_ECHO", "false").lower() == "true",
            pool_size=int(os.getenv("TEST_DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("TEST_DB_MAX_OVERFLOW", "10")),
            use_null_pool=os.getenv("TEST_DB_USE_NULL_POOL", "true").lower() == "true",
            connect_timeout=int(os.getenv("TEST_DB_CONNECT_TIMEOUT", "10")),
        )


@dataclass
class TestConfig:
    """Main test configuration."""
    environment: TestEnvironment
    database: DatabaseTestConfig
    parallel_workers: int = 1
    timeout_seconds: int = 30
    cleanup_after_tests: bool = True
    generate_coverage: bool = True
    verbose_logging: bool = False
    
    @classmethod
    def from_environment(cls) -> "TestConfig":
        """Create config from environment variables."""
        env_name = os.getenv("TEST_ENVIRONMENT", "unit").lower()
        try:
            environment = TestEnvironment(env_name)
        except ValueError:
            environment = TestEnvironment.UNIT
        
        return cls(
            environment=environment,
            database=DatabaseTestConfig.from_environment(),
            parallel_workers=int(os.getenv("TEST_PARALLEL_WORKERS", "1")),
            timeout_seconds=int(os.getenv("TEST_TIMEOUT_SECONDS", "30")),
            cleanup_after_tests=os.getenv("TEST_CLEANUP", "true").lower() == "true",
            generate_coverage=os.getenv("TEST_COVERAGE", "true").lower() == "true",
            verbose_logging=os.getenv("TEST_VERBOSE", "false").lower() == "true",
        )


# Environment-specific configurations
UNIT_TEST_CONFIG = {
    "database_url": "sqlite+aiosqlite:///:memory:",
    "echo": False,
    "use_null_pool": True,
    "timeout": 10,
    "cleanup": True,
}

INTEGRATION_TEST_CONFIG = {
    "database_url": os.getenv(
        "INTEGRATION_TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/vet_core_integration_test"
    ),
    "echo": False,
    "use_null_pool": False,
    "timeout": 60,
    "cleanup": True,
}

PERFORMANCE_TEST_CONFIG = {
    "database_url": os.getenv(
        "PERFORMANCE_TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/vet_core_performance_test"
    ),
    "echo": False,
    "use_null_pool": False,
    "timeout": 300,
    "cleanup": False,  # Keep data for analysis
}

CI_TEST_CONFIG = {
    "database_url": os.getenv(
        "CI_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/vet_core_ci_test"
    ),
    "echo": False,
    "use_null_pool": True,
    "timeout": 120,
    "cleanup": True,
}


def get_test_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """
    Get test configuration for the specified environment.
    
    Args:
        environment: Test environment name (unit, integration, performance, ci)
        
    Returns:
        Configuration dictionary for the environment
    """
    if environment is None:
        environment = os.getenv("TEST_ENVIRONMENT", "unit").lower()
    
    config_map = {
        "unit": UNIT_TEST_CONFIG,
        "integration": INTEGRATION_TEST_CONFIG,
        "performance": PERFORMANCE_TEST_CONFIG,
        "ci": CI_TEST_CONFIG,
    }
    
    return config_map.get(environment, UNIT_TEST_CONFIG)


def is_postgresql_available() -> bool:
    """
    Check if PostgreSQL is available for testing.
    
    Returns:
        True if PostgreSQL is available, False otherwise
    """
    try:
        import asyncpg
        import asyncio
        
        async def check_connection():
            try:
                config = DatabaseTestConfig.from_environment()
                # Parse URL to get connection parameters
                from urllib.parse import urlparse
                parsed = urlparse(config.url)
                
                conn = await asyncpg.connect(
                    host=parsed.hostname,
                    port=parsed.port or 5432,
                    user=parsed.username,
                    password=parsed.password,
                    database=parsed.path.lstrip('/') if parsed.path else 'postgres',
                    timeout=5
                )
                await conn.close()
                return True
            except Exception:
                return False
        
        return asyncio.run(check_connection())
    except ImportError:
        return False


def should_use_postgresql() -> bool:
    """
    Determine if tests should use PostgreSQL or fall back to SQLite.
    
    Returns:
        True if PostgreSQL should be used, False for SQLite fallback
    """
    # Force SQLite for unit tests unless explicitly requested
    if os.getenv("TEST_ENVIRONMENT", "unit").lower() == "unit":
        return os.getenv("FORCE_POSTGRESQL", "false").lower() == "true"
    
    # Use PostgreSQL for integration and performance tests if available
    return is_postgresql_available()


def get_database_url_for_tests() -> str:
    """
    Get the appropriate database URL for the current test environment.
    
    Returns:
        Database URL string
    """
    if should_use_postgresql():
        config = get_test_config()
        return config["database_url"]
    else:
        return "sqlite+aiosqlite:///:memory:"


# Test markers configuration
TEST_MARKERS = {
    "unit": "Unit tests that don't require external dependencies",
    "integration": "Integration tests that require database and external services",
    "slow": "Tests that take more than 1 second to run",
    "database": "Tests that require database access",
    "performance": "Performance and load tests",
    "flaky": "Tests that may fail intermittently",
    "skip_ci": "Tests to skip in CI environment",
}


# Performance test thresholds
PERFORMANCE_THRESHOLDS = {
    "database_connection": 0.1,  # seconds
    "simple_query": 0.05,  # seconds
    "complex_query": 0.5,  # seconds
    "transaction": 0.1,  # seconds
    "bulk_insert": 1.0,  # seconds per 100 records
}


def get_performance_threshold(operation: str) -> float:
    """
    Get performance threshold for an operation.
    
    Args:
        operation: Operation name
        
    Returns:
        Threshold in seconds
    """
    return PERFORMANCE_THRESHOLDS.get(operation, 1.0)


# Test data limits
TEST_DATA_LIMITS = {
    "max_users": 1000,
    "max_pets_per_user": 10,
    "max_appointments_per_pet": 50,
    "max_clinics": 100,
    "max_veterinarians_per_clinic": 20,
}


def get_test_data_limit(entity: str) -> int:
    """
    Get test data limit for an entity type.
    
    Args:
        entity: Entity name
        
    Returns:
        Maximum number of entities to create in tests
    """
    return TEST_DATA_LIMITS.get(entity, 100)


# Logging configuration for tests
def configure_test_logging():
    """Configure logging for tests."""
    import logging
    
    # Set log level based on environment
    if os.getenv("TEST_VERBOSE", "false").lower() == "true":
        log_level = logging.DEBUG
    else:
        log_level = logging.WARNING
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    
    # Suppress noisy loggers in tests
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)


# Test isolation settings
ISOLATION_SETTINGS = {
    "use_transactions": True,  # Use transaction rollback for isolation
    "truncate_tables": False,  # Alternative: truncate tables between tests
    "reset_sequences": False,  # Reset auto-increment sequences
    "clear_cache": True,  # Clear any caches between tests
}


def get_isolation_setting(setting: str) -> bool:
    """
    Get test isolation setting.
    
    Args:
        setting: Setting name
        
    Returns:
        Setting value
    """
    env_var = f"TEST_ISOLATION_{setting.upper()}"
    env_value = os.getenv(env_var)
    
    if env_value is not None:
        return env_value.lower() == "true"
    
    return ISOLATION_SETTINGS.get(setting, True)


# Global test configuration instance
_test_config: Optional[TestConfig] = None


def get_global_test_config() -> TestConfig:
    """Get the global test configuration instance."""
    global _test_config
    if _test_config is None:
        _test_config = TestConfig.from_environment()
    return _test_config


def set_global_test_config(config: TestConfig) -> None:
    """Set the global test configuration instance."""
    global _test_config
    _test_config = config