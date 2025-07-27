"""
Tests for security configuration management.

This module contains comprehensive tests for the security configuration system,
including validation, environment-specific settings, and configuration management.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from vet_core.security.config import (
    AutoFixConfig,
    ComplianceConfig,
    ConfigurationError,
    Environment,
    EnvironmentSecurityConfig,
    NotificationConfig,
    ScannerConfig,
    SecurityConfigManager,
    get_config,
    validate_config,
)
from vet_core.security.models import SecurityConfig, VulnerabilitySeverity


class TestNotificationConfig:
    """Test notification configuration validation."""

    def test_valid_notification_config(self):
        """Test valid notification configuration."""
        config = NotificationConfig(
            email=["test@example.com", "admin@example.com"],
            slack_webhook="https://hooks.slack.com/services/test",
            console=True,
        )

        errors = config.validate()
        assert len(errors) == 0

    def test_invalid_email_addresses(self):
        """Test validation of invalid email addresses."""
        config = NotificationConfig(email=["invalid-email", "another@invalid"])

        errors = config.validate()
        assert len(errors) == 2
        assert "Invalid email address: invalid-email" in errors
        assert "Invalid email address: another@invalid" in errors

    def test_invalid_slack_webhook(self):
        """Test validation of invalid Slack webhook."""
        config = NotificationConfig(slack_webhook="https://invalid-webhook.com")

        errors = config.validate()
        assert len(errors) == 1
        assert "Invalid Slack webhook URL" in errors[0]

    def test_invalid_teams_webhook(self):
        """Test validation of invalid Teams webhook."""
        config = NotificationConfig(teams_webhook="invalid-url")

        errors = config.validate()
        assert len(errors) == 1
        assert "Invalid Teams webhook URL" in errors[0]


class TestScannerConfig:
    """Test scanner configuration validation."""

    def test_valid_scanner_config(self):
        """Test valid scanner configuration."""
        config = ScannerConfig(
            primary_scanner="pip-audit",
            backup_scanners=["safety"],
            timeout=300,
            retry_attempts=3,
        )

        errors = config.validate()
        assert len(errors) == 0

    def test_invalid_primary_scanner(self):
        """Test validation of invalid primary scanner."""
        config = ScannerConfig(primary_scanner="invalid-scanner")

        errors = config.validate()
        assert len(errors) == 1
        assert "Unsupported primary scanner: invalid-scanner" in errors[0]

    def test_invalid_backup_scanner(self):
        """Test validation of invalid backup scanner."""
        config = ScannerConfig(backup_scanners=["invalid-scanner"])

        errors = config.validate()
        assert len(errors) == 1
        assert "Unsupported backup scanner: invalid-scanner" in errors[0]

    def test_invalid_timeout(self):
        """Test validation of invalid timeout."""
        config = ScannerConfig(timeout=-1)

        errors = config.validate()
        assert len(errors) == 1
        assert "Scanner timeout must be positive" in errors[0]

    def test_invalid_retry_attempts(self):
        """Test validation of invalid retry attempts."""
        config = ScannerConfig(retry_attempts=-1)

        errors = config.validate()
        assert len(errors) == 1
        assert "Retry attempts cannot be negative" in errors[0]

    def test_invalid_output_format(self):
        """Test validation of invalid output format."""
        config = ScannerConfig(output_format="invalid-format")

        errors = config.validate()
        assert len(errors) == 1
        assert "Unsupported output format: invalid-format" in errors[0]


class TestAutoFixConfig:
    """Test auto-fix configuration validation."""

    def test_valid_auto_fix_config(self):
        """Test valid auto-fix configuration."""
        config = AutoFixConfig(
            enabled=True,
            max_severity=VulnerabilitySeverity.MEDIUM,
            require_approval=True,
        )

        errors = config.validate()
        assert len(errors) == 0

    def test_unsafe_auto_fix_config(self):
        """Test validation of unsafe auto-fix configuration."""
        config = AutoFixConfig(enabled=True, dry_run=False, require_approval=False)

        errors = config.validate()
        assert len(errors) == 1
        assert "Auto-fix without dry-run or approval is not recommended" in errors[0]


class TestComplianceConfig:
    """Test compliance configuration validation."""

    def test_valid_compliance_config(self):
        """Test valid compliance configuration."""
        config = ComplianceConfig(
            audit_retention_days=365, compliance_standards=["SOC2", "ISO27001"]
        )

        errors = config.validate()
        assert len(errors) == 0

    def test_invalid_retention_days(self):
        """Test validation of invalid retention days."""
        config = ComplianceConfig(audit_retention_days=-1)

        errors = config.validate()
        assert len(errors) == 1
        assert "Audit retention days must be positive" in errors[0]

    def test_invalid_compliance_standard(self):
        """Test validation of invalid compliance standard."""
        config = ComplianceConfig(compliance_standards=["INVALID-STANDARD"])

        errors = config.validate()
        assert len(errors) == 1
        assert "Unsupported compliance standard: INVALID-STANDARD" in errors[0]

    def test_invalid_export_format(self):
        """Test validation of invalid export format."""
        config = ComplianceConfig(export_format="invalid-format")

        errors = config.validate()
        assert len(errors) == 1
        assert "Unsupported export format: invalid-format" in errors[0]


class TestEnvironmentSecurityConfig:
    """Test environment-specific security configuration."""

    def test_valid_environment_config(self):
        """Test valid environment configuration."""
        base_config = SecurityConfig()
        config = EnvironmentSecurityConfig(
            environment=Environment.DEVELOPMENT, base_config=base_config
        )

        errors = config.validate()
        assert len(errors) == 0

    def test_production_validation_rules(self):
        """Test production-specific validation rules."""
        base_config = SecurityConfig()
        auto_fix = AutoFixConfig(enabled=True, require_approval=False)
        notifications = NotificationConfig()  # No notification channels

        config = EnvironmentSecurityConfig(
            environment=Environment.PRODUCTION,
            base_config=base_config,
            auto_fix=auto_fix,
            notifications=notifications,
        )

        errors = config.validate()
        assert len(errors) >= 2
        assert any(
            "Production auto-fix must require approval" in error for error in errors
        )
        assert any(
            "Production environment must have notification channels" in error
            for error in errors
        )

    def test_missing_severity_thresholds(self):
        """Test validation when severity thresholds are missing."""
        # Create a SecurityConfig and manually clear thresholds after initialization
        base_config = SecurityConfig()
        base_config.severity_thresholds = {}  # Clear after __post_init__ has run

        config = EnvironmentSecurityConfig(
            environment=Environment.DEVELOPMENT, base_config=base_config
        )

        errors = config.validate()
        assert len(errors) == 1
        assert "Severity thresholds must be defined" in errors[0]


class TestSecurityConfigManager:
    """Test security configuration manager."""

    def test_init_with_custom_config_dir(self):
        """Test initialization with custom config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "custom_config"
            manager = SecurityConfigManager(config_dir)

            assert manager.config_dir == config_dir
            assert config_dir.exists()

    def test_create_default_config(self):
        """Test creation of default configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SecurityConfigManager(Path(temp_dir))

            config = manager._create_default_config(Environment.DEVELOPMENT)

            assert config.environment == Environment.DEVELOPMENT
            assert isinstance(config.base_config, SecurityConfig)
            assert config.notifications.console is True
            assert config.auto_fix.enabled is True

    def test_production_default_config(self):
        """Test production-specific default configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SecurityConfigManager(Path(temp_dir))

            config = manager._create_default_config(Environment.PRODUCTION)

            assert config.environment == Environment.PRODUCTION
            assert config.auto_fix.enabled is False
            assert config.auto_fix.require_approval is True
            assert "security@company.com" in config.notifications.email

    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SecurityConfigManager(Path(temp_dir))

            # Create and save config
            original_config = manager._create_default_config(Environment.DEVELOPMENT)
            original_config.base_config.scan_schedule = "0 8 * * *"
            manager.save_config(original_config)

            # Load config
            loaded_config = manager.load_config(Environment.DEVELOPMENT)

            assert loaded_config.environment == Environment.DEVELOPMENT
            assert loaded_config.base_config.scan_schedule == "0 8 * * *"

    def test_get_current_environment(self):
        """Test getting current environment from environment variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SecurityConfigManager(Path(temp_dir))

            # Test default environment
            env = manager.get_current_environment()
            assert env == Environment.DEVELOPMENT

            # Test with environment variable
            with patch.dict("os.environ", {"SECURITY_ENVIRONMENT": "production"}):
                env = manager.get_current_environment()
                assert env == Environment.PRODUCTION

            # Test with invalid environment variable
            with patch.dict("os.environ", {"SECURITY_ENVIRONMENT": "invalid"}):
                env = manager.get_current_environment()
                assert env == Environment.DEVELOPMENT

    def test_validate_config(self):
        """Test configuration validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SecurityConfigManager(Path(temp_dir))

            # Valid config
            valid_config = manager._create_default_config(Environment.DEVELOPMENT)
            errors = manager.validate_config(valid_config)
            assert len(errors) == 0

            # Invalid config
            invalid_config = manager._create_default_config(Environment.PRODUCTION)
            invalid_config.notifications = (
                NotificationConfig()
            )  # No notification channels
            invalid_config.auto_fix.enabled = True
            invalid_config.auto_fix.require_approval = False

            errors = manager.validate_config(invalid_config)
            assert len(errors) > 0

    def test_list_environments(self):
        """Test listing configured environments."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SecurityConfigManager(Path(temp_dir))

            # Initially no environments
            environments = manager.list_environments()
            assert len(environments) == 0

            # Create configurations
            dev_config = manager._create_default_config(Environment.DEVELOPMENT)
            prod_config = manager._create_default_config(Environment.PRODUCTION)

            manager.save_config(dev_config)
            manager.save_config(prod_config)

            # Should now list both environments
            environments = manager.list_environments()
            assert len(environments) == 2
            assert Environment.DEVELOPMENT in environments
            assert Environment.PRODUCTION in environments

    def test_export_config(self):
        """Test exporting configuration to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SecurityConfigManager(Path(temp_dir))

            # Create and save config
            config = manager._create_default_config(Environment.DEVELOPMENT)
            manager.save_config(config)

            # Export to JSON
            export_file = Path(temp_dir) / "export.json"
            manager.export_config(Environment.DEVELOPMENT, export_file)

            assert export_file.exists()

            # Verify exported content
            with open(export_file, "r") as f:
                exported_data = json.load(f)

            assert exported_data["environment"] == "development"
            assert "base_config" in exported_data

    def test_import_config(self):
        """Test importing configuration from file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SecurityConfigManager(Path(temp_dir))

            # Create a config file to import
            config_data = {
                "environment": "testing",
                "base_config": {
                    "scan_schedule": "0 12 * * *",
                    "severity_thresholds": {
                        "critical": 12,
                        "high": 48,
                        "medium": 168,
                        "low": 720,
                    },
                    "auto_fix_enabled": False,
                    "max_auto_fix_severity": "low",
                    "scanner_timeout": 600,
                },
                "notifications": {"email": ["test@example.com"], "console": True},
                "scanner": {"primary_scanner": "pip-audit", "timeout": 600},
                "auto_fix": {"enabled": False, "max_severity": "low"},
                "compliance": {"audit_retention_days": 180},
            }

            import_file = Path(temp_dir) / "import.yaml"
            import yaml

            with open(import_file, "w") as f:
                yaml.dump(config_data, f)

            # Import configuration
            manager.import_config(import_file, Environment.TESTING)

            # Verify imported config
            loaded_config = manager.load_config(Environment.TESTING)
            assert loaded_config.environment == Environment.TESTING
            assert loaded_config.base_config.scan_schedule == "0 12 * * *"
            assert loaded_config.notifications.email == ["test@example.com"]

    def test_import_invalid_config(self):
        """Test importing invalid configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SecurityConfigManager(Path(temp_dir))

            # Create invalid config file
            invalid_config_data = {
                "environment": "testing",
                "base_config": {
                    "severity_thresholds": {}  # Empty thresholds (invalid)
                },
                "notifications": {},
                "scanner": {"primary_scanner": "invalid-scanner"},  # Invalid scanner
                "auto_fix": {
                    "enabled": True,
                    "dry_run": False,
                    "require_approval": False,  # Unsafe config
                },
                "compliance": {"audit_retention_days": -1},  # Invalid retention
            }

            import_file = Path(temp_dir) / "invalid.yaml"
            import yaml

            with open(import_file, "w") as f:
                yaml.dump(invalid_config_data, f)

            # Import should fail with validation errors
            with pytest.raises(ConfigurationError) as exc_info:
                manager.import_config(import_file, Environment.TESTING)

            assert "Configuration validation failed" in str(exc_info.value)


class TestGlobalFunctions:
    """Test global configuration functions."""

    def test_get_config(self):
        """Test global get_config function."""
        with patch("vet_core.security.config.config_manager") as mock_manager:
            mock_config = EnvironmentSecurityConfig(
                environment=Environment.DEVELOPMENT, base_config=SecurityConfig()
            )
            mock_manager.get_config.return_value = mock_config

            config = get_config(Environment.DEVELOPMENT)

            assert config == mock_config
            mock_manager.get_config.assert_called_once_with(Environment.DEVELOPMENT)

    def test_validate_config_function(self):
        """Test global validate_config function."""
        with patch("vet_core.security.config.config_manager") as mock_manager:
            mock_config = EnvironmentSecurityConfig(
                environment=Environment.DEVELOPMENT, base_config=SecurityConfig()
            )
            mock_manager.validate_config.return_value = []

            errors = validate_config(mock_config)

            assert errors == []
            mock_manager.validate_config.assert_called_once_with(mock_config)


class TestConfigurationIntegration:
    """Integration tests for configuration management."""

    def test_full_configuration_workflow(self):
        """Test complete configuration management workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SecurityConfigManager(Path(temp_dir))

            # 1. Create default configuration
            config = manager._create_default_config(Environment.DEVELOPMENT)

            # 2. Customize configuration
            config.base_config.scan_schedule = "0 9 * * *"
            config.notifications.email = ["dev@example.com"]
            config.auto_fix.enabled = True
            config.auto_fix.max_severity = VulnerabilitySeverity.HIGH

            # 3. Validate configuration
            errors = manager.validate_config(config)
            assert len(errors) == 0

            # 4. Save configuration
            manager.save_config(config)

            # 5. Load configuration
            loaded_config = manager.load_config(Environment.DEVELOPMENT)

            # 6. Verify all settings
            assert loaded_config.base_config.scan_schedule == "0 9 * * *"
            assert loaded_config.notifications.email == ["dev@example.com"]
            assert loaded_config.auto_fix.enabled is True
            assert loaded_config.auto_fix.max_severity == VulnerabilitySeverity.HIGH

            # 7. Export configuration
            export_file = Path(temp_dir) / "exported.json"
            manager.export_config(Environment.DEVELOPMENT, export_file)
            assert export_file.exists()

            # 8. List environments
            environments = manager.list_environments()
            assert Environment.DEVELOPMENT in environments
