"""
Configuration management utilities.

This module provides environment variable handling with type conversion,
database URL parsing and validation, logging configuration utilities,
and feature flag management system.
"""

import json
import logging
import logging.config
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
from urllib.parse import parse_qs, urlparse

T = TypeVar("T")


class ConfigError(Exception):
    """Exception raised for configuration-related errors."""

    pass


class LogLevel(Enum):
    """Enumeration for log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class DatabaseConfig:
    """Configuration for database connection."""

    host: str
    port: int
    database: str
    username: str
    password: str
    driver: str = "postgresql+asyncpg"
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False

    @property
    def url(self) -> str:
        """Generate database URL from configuration."""
        return f"{self.driver}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

    @classmethod
    def from_url(cls, url: str) -> "DatabaseConfig":
        """Create DatabaseConfig from database URL."""
        parsed = urlparse(url)

        if not parsed.scheme:
            raise ConfigError("Database URL must include a scheme")

        if not parsed.hostname:
            raise ConfigError("Database URL must include a hostname")

        # Parse query parameters for additional config
        query_params = parse_qs(parsed.query)

        return cls(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip("/") if parsed.path else "",
            username=parsed.username or "",
            password=parsed.password or "",
            driver=parsed.scheme,
            pool_size=int(query_params.get("pool_size", [5])[0]),
            max_overflow=int(query_params.get("max_overflow", [10])[0]),
            pool_timeout=int(query_params.get("pool_timeout", [30])[0]),
            pool_recycle=int(query_params.get("pool_recycle", [3600])[0]),
            echo=query_params.get("echo", ["false"])[0].lower() == "true",
        )


@dataclass
class FeatureFlag:
    """Represents a feature flag configuration."""

    name: str
    enabled: bool
    description: str = ""
    conditions: Dict[str, Any] = field(default_factory=dict)
    rollout_percentage: float = 100.0

    def is_enabled_for_user(
        self,
        user_id: Optional[str] = None,
        user_attributes: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Check if the feature is enabled for a specific user.

        Args:
            user_id: The user ID to check
            user_attributes: Additional user attributes for condition checking

        Returns:
            True if the feature is enabled for the user
        """
        if not self.enabled:
            return False

        # Simple rollout percentage check
        if self.rollout_percentage < 100.0:
            if user_id:
                # Use hash of user_id to determine if user is in rollout
                user_hash = hash(user_id) % 100
                if user_hash >= self.rollout_percentage:
                    return False

        # Check additional conditions if provided
        if self.conditions and user_attributes:
            for condition_key, condition_value in self.conditions.items():
                if condition_key in user_attributes:
                    if user_attributes[condition_key] != condition_value:
                        return False

        return True


class EnvironmentConfig:
    """Utility class for handling environment variables with type conversion."""

    @staticmethod
    def get_str(
        key: str, default: Optional[str] = None, required: bool = False
    ) -> Optional[str]:
        """
        Get a string environment variable.

        Args:
            key: Environment variable key
            default: Default value if not found
            required: Whether the variable is required

        Returns:
            String value or default

        Raises:
            ConfigError: If required variable is missing
        """
        value = os.getenv(key, default)

        if required and value is None:
            raise ConfigError(f"Required environment variable '{key}' is not set")

        return value

    @staticmethod
    def get_int(
        key: str, default: Optional[int] = None, required: bool = False
    ) -> Optional[int]:
        """
        Get an integer environment variable.

        Args:
            key: Environment variable key
            default: Default value if not found
            required: Whether the variable is required

        Returns:
            Integer value or default

        Raises:
            ConfigError: If required variable is missing or invalid
        """
        value = os.getenv(key)

        if value is None:
            if required:
                raise ConfigError(f"Required environment variable '{key}' is not set")
            return default

        try:
            return int(value)
        except ValueError:
            raise ConfigError(
                f"Environment variable '{key}' must be an integer, got: {value}"
            )

    @staticmethod
    def get_float(
        key: str, default: Optional[float] = None, required: bool = False
    ) -> Optional[float]:
        """
        Get a float environment variable.

        Args:
            key: Environment variable key
            default: Default value if not found
            required: Whether the variable is required

        Returns:
            Float value or default

        Raises:
            ConfigError: If required variable is missing or invalid
        """
        value = os.getenv(key)

        if value is None:
            if required:
                raise ConfigError(f"Required environment variable '{key}' is not set")
            return default

        try:
            return float(value)
        except ValueError:
            raise ConfigError(
                f"Environment variable '{key}' must be a float, got: {value}"
            )

    @staticmethod
    def get_bool(
        key: str, default: Optional[bool] = None, required: bool = False
    ) -> Optional[bool]:
        """
        Get a boolean environment variable.

        Args:
            key: Environment variable key
            default: Default value if not found
            required: Whether the variable is required

        Returns:
            Boolean value or default

        Raises:
            ConfigError: If required variable is missing
        """
        value = os.getenv(key)

        if value is None:
            if required:
                raise ConfigError(f"Required environment variable '{key}' is not set")
            return default

        return value.lower() in ("true", "1", "yes", "on", "enabled")

    @staticmethod
    def get_list(
        key: str,
        separator: str = ",",
        default: Optional[List[str]] = None,
        required: bool = False,
    ) -> Optional[List[str]]:
        """
        Get a list environment variable.

        Args:
            key: Environment variable key
            separator: Separator character for list items
            default: Default value if not found
            required: Whether the variable is required

        Returns:
            List of strings or default

        Raises:
            ConfigError: If required variable is missing
        """
        value = os.getenv(key)

        if value is None:
            if required:
                raise ConfigError(f"Required environment variable '{key}' is not set")
            return default or []

        return [item.strip() for item in value.split(separator) if item.strip()]

    @staticmethod
    def get_json(
        key: str, default: Optional[Dict[str, Any]] = None, required: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get a JSON environment variable.

        Args:
            key: Environment variable key
            default: Default value if not found
            required: Whether the variable is required

        Returns:
            Parsed JSON object or default

        Raises:
            ConfigError: If required variable is missing or invalid JSON
        """
        value = os.getenv(key)

        if value is None:
            if required:
                raise ConfigError(f"Required environment variable '{key}' is not set")
            return default

        try:
            result = json.loads(value)
            if isinstance(result, dict):
                return result
            else:
                raise ConfigError(f"Environment variable '{key}' must be a JSON object")
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"Environment variable '{key}' contains invalid JSON: {e}"
            )


class DatabaseURLValidator:
    """Utility class for validating database URLs."""

    SUPPORTED_DRIVERS = {
        "postgresql": ["postgresql", "postgresql+asyncpg", "postgresql+psycopg2"],
        "mysql": ["mysql", "mysql+pymysql", "mysql+aiomysql"],
        "sqlite": ["sqlite", "sqlite+aiosqlite"],
    }

    @classmethod
    def validate_url(cls, url: str) -> Dict[str, Any]:
        """
        Validate a database URL and return parsed components.

        Args:
            url: Database URL to validate

        Returns:
            Dictionary with validation results and parsed components

        Raises:
            ConfigError: If URL is invalid
        """
        if not url:
            raise ConfigError("Database URL cannot be empty")

        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ConfigError(f"Invalid URL format: {e}")

        # Validate scheme
        if not parsed.scheme:
            raise ConfigError(
                "Database URL must include a scheme (e.g., postgresql://)"
            )

        # Check if driver is supported
        driver_supported = False
        for db_type, drivers in cls.SUPPORTED_DRIVERS.items():
            if parsed.scheme in drivers:
                driver_supported = True
                break

        if not driver_supported:
            supported_list = []
            for drivers in cls.SUPPORTED_DRIVERS.values():
                supported_list.extend(drivers)
            raise ConfigError(
                f"Unsupported database driver '{parsed.scheme}'. Supported: {', '.join(supported_list)}"
            )

        # Validate required components
        if not parsed.hostname and parsed.scheme != "sqlite":
            raise ConfigError("Database URL must include a hostname")

        if parsed.scheme != "sqlite" and not parsed.path.lstrip("/"):
            raise ConfigError("Database URL must include a database name")

        return {
            "valid": True,
            "scheme": parsed.scheme,
            "hostname": parsed.hostname,
            "port": parsed.port,
            "database": parsed.path.lstrip("/") if parsed.path else "",
            "username": parsed.username,
            "password": parsed.password,
            "query": dict(parse_qs(parsed.query)),
        }


class LoggingConfigurator:
    """Utility class for configuring logging."""

    DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @staticmethod
    def configure_basic_logging(
        level: Union[str, LogLevel] = LogLevel.INFO,
        format_string: Optional[str] = None,
        log_file: Optional[str] = None,
    ) -> None:
        """
        Configure basic logging for the application.

        Args:
            level: Logging level
            format_string: Custom format string
            log_file: Optional log file path
        """
        if isinstance(level, LogLevel):
            level = level.value

        format_string = format_string or LoggingConfigurator.DEFAULT_FORMAT

        # Basic configuration
        logging_config = {
            "level": level,
            "format": format_string,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }

        if log_file:
            logging_config["filename"] = log_file
            logging_config["filemode"] = "a"

        # Configure logging with proper type handling
        basic_config_args: Dict[str, Any] = {}
        if "level" in logging_config:
            basic_config_args["level"] = logging_config["level"]
        if "format" in logging_config:
            basic_config_args["format"] = logging_config["format"]
        if "datefmt" in logging_config:
            basic_config_args["datefmt"] = logging_config["datefmt"]
        if "filename" in logging_config:
            basic_config_args["filename"] = logging_config["filename"]
        if "filemode" in logging_config:
            basic_config_args["filemode"] = logging_config["filemode"]

        logging.basicConfig(**basic_config_args)

    @staticmethod
    def configure_structured_logging(
        config_dict: Optional[Dict[str, Any]] = None, config_file: Optional[str] = None
    ) -> None:
        """
        Configure structured logging using a dictionary or file.

        Args:
            config_dict: Logging configuration dictionary
            config_file: Path to logging configuration file
        """
        if config_file and Path(config_file).exists():
            logging.config.fileConfig(config_file)
        elif config_dict:
            logging.config.dictConfig(config_dict)
        else:
            # Default structured configuration
            default_config = {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "standard": {"format": LoggingConfigurator.DEFAULT_FORMAT},
                    "detailed": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s"
                    },
                },
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "level": "INFO",
                        "formatter": "standard",
                        "stream": "ext://sys.stdout",
                    }
                },
                "loggers": {
                    "vet_core": {
                        "level": "INFO",
                        "handlers": ["console"],
                        "propagate": False,
                    }
                },
                "root": {"level": "WARNING", "handlers": ["console"]},
            }
            logging.config.dictConfig(default_config)


class FeatureFlagManager:
    """Manager for feature flags."""

    def __init__(self, config_source: Optional[Union[str, Dict[str, Any]]] = None):
        """
        Initialize the feature flag manager.

        Args:
            config_source: Path to config file or dictionary of flags
        """
        self._flags: Dict[str, FeatureFlag] = {}

        if isinstance(config_source, str):
            self._load_from_file(config_source)
        elif isinstance(config_source, dict):
            self._load_from_dict(config_source)
        else:
            self._load_from_environment()

    def _load_from_file(self, file_path: str) -> None:
        """Load feature flags from a JSON file."""
        try:
            with open(file_path, "r") as f:
                config = json.load(f)
            self._load_from_dict(config)
        except FileNotFoundError:
            # File doesn't exist, use environment variables
            self._load_from_environment()
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in feature flag config file: {e}")

    def _load_from_dict(self, config: Dict[str, Any]) -> None:
        """Load feature flags from a dictionary."""
        for flag_name, flag_config in config.items():
            if isinstance(flag_config, bool):
                # Simple boolean flag
                self._flags[flag_name] = FeatureFlag(
                    name=flag_name, enabled=flag_config
                )
            elif isinstance(flag_config, dict):
                # Complex flag configuration
                self._flags[flag_name] = FeatureFlag(
                    name=flag_name,
                    enabled=flag_config.get("enabled", False),
                    description=flag_config.get("description", ""),
                    conditions=flag_config.get("conditions", {}),
                    rollout_percentage=flag_config.get("rollout_percentage", 100.0),
                )

    def _load_from_environment(self) -> None:
        """Load feature flags from environment variables."""
        # Look for environment variables with FEATURE_FLAG_ prefix
        for key, value in os.environ.items():
            if key.startswith("FEATURE_FLAG_"):
                flag_name = key[13:].lower()  # Remove FEATURE_FLAG_ prefix
                self._flags[flag_name] = FeatureFlag(
                    name=flag_name,
                    enabled=value.lower() in ("true", "1", "yes", "on", "enabled"),
                )

    def is_enabled(
        self,
        flag_name: str,
        user_id: Optional[str] = None,
        user_attributes: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            flag_name: Name of the feature flag
            user_id: Optional user ID for user-specific checks
            user_attributes: Optional user attributes for condition checking

        Returns:
            True if the feature is enabled
        """
        if flag_name not in self._flags:
            return False

        return self._flags[flag_name].is_enabled_for_user(user_id, user_attributes)

    def get_flag(self, flag_name: str) -> Optional[FeatureFlag]:
        """Get a feature flag by name."""
        return self._flags.get(flag_name)

    def add_flag(self, flag: FeatureFlag) -> None:
        """Add or update a feature flag."""
        self._flags[flag.name] = flag

    def remove_flag(self, flag_name: str) -> bool:
        """Remove a feature flag."""
        if flag_name in self._flags:
            del self._flags[flag_name]
            return True
        return False

    def list_flags(self) -> List[FeatureFlag]:
        """Get a list of all feature flags."""
        return list(self._flags.values())


# Global feature flag manager instance
_feature_flag_manager: Optional[FeatureFlagManager] = None


def get_feature_flag_manager() -> FeatureFlagManager:
    """Get the global feature flag manager instance."""
    global _feature_flag_manager
    if _feature_flag_manager is None:
        _feature_flag_manager = FeatureFlagManager()
    return _feature_flag_manager


def is_feature_enabled(
    flag_name: str,
    user_id: Optional[str] = None,
    user_attributes: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Check if a feature flag is enabled.

    Args:
        flag_name: Name of the feature flag
        user_id: Optional user ID for user-specific checks
        user_attributes: Optional user attributes for condition checking

    Returns:
        True if the feature is enabled
    """
    return get_feature_flag_manager().is_enabled(flag_name, user_id, user_attributes)
