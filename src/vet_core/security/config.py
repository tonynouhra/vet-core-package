"""
Configuration management for security settings.

This module provides a comprehensive configuration management system for security
settings, including validation, environment-specific configurations, and
customizable thresholds.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml
from enum import Enum

from .models import SecurityConfig, VulnerabilitySeverity


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""

    pass


class Environment(Enum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class NotificationConfig:
    """Configuration for notification channels."""

    email: List[str] = field(default_factory=list)
    slack_webhook: Optional[str] = None
    teams_webhook: Optional[str] = None
    github_issues: bool = False
    console: bool = True

    def validate(self) -> List[str]:
        """Validate notification configuration."""
        errors = []

        # Validate email addresses
        for email in self.email:
            if "@" not in email or "." not in email:
                errors.append(f"Invalid email address: {email}")

        # Validate webhook URLs
        if self.slack_webhook and not self.slack_webhook.startswith(
            "https://hooks.slack.com"
        ):
            errors.append("Invalid Slack webhook URL")

        if self.teams_webhook and not self.teams_webhook.startswith("https://"):
            errors.append("Invalid Teams webhook URL")

        return errors


@dataclass
class ScannerConfig:
    """Configuration for vulnerability scanners."""

    primary_scanner: str = "pip-audit"
    backup_scanners: List[str] = field(default_factory=lambda: ["safety"])
    timeout: int = 300  # 5 minutes
    retry_attempts: int = 3
    retry_delay: int = 30  # seconds
    output_format: str = "json"
    include_dev_dependencies: bool = True

    def validate(self) -> List[str]:
        """Validate scanner configuration."""
        errors = []

        supported_scanners = ["pip-audit", "safety", "bandit"]
        if self.primary_scanner not in supported_scanners:
            errors.append(f"Unsupported primary scanner: {self.primary_scanner}")

        for scanner in self.backup_scanners:
            if scanner not in supported_scanners:
                errors.append(f"Unsupported backup scanner: {scanner}")

        if self.timeout <= 0:
            errors.append("Scanner timeout must be positive")

        if self.retry_attempts < 0:
            errors.append("Retry attempts cannot be negative")

        if self.retry_delay <= 0:
            errors.append("Retry delay must be positive")

        supported_formats = ["json", "yaml", "text"]
        if self.output_format not in supported_formats:
            errors.append(f"Unsupported output format: {self.output_format}")

        return errors


@dataclass
class AutoFixConfig:
    """Configuration for automatic vulnerability fixes."""

    enabled: bool = False
    max_severity: VulnerabilitySeverity = VulnerabilitySeverity.MEDIUM
    dry_run: bool = True
    require_approval: bool = True
    backup_before_fix: bool = True
    rollback_on_failure: bool = True
    test_after_fix: bool = True
    excluded_packages: List[str] = field(default_factory=list)

    def validate(self) -> List[str]:
        """Validate auto-fix configuration."""
        errors = []

        # If auto-fix is enabled, ensure safety measures are in place
        if self.enabled and not self.dry_run and not self.require_approval:
            errors.append("Auto-fix without dry-run or approval is not recommended")

        return errors


@dataclass
class ComplianceConfig:
    """Configuration for compliance and audit requirements."""

    audit_retention_days: int = 365
    compliance_standards: List[str] = field(
        default_factory=lambda: ["SOC2", "ISO27001"]
    )
    generate_reports: bool = True
    report_schedule: str = "0 0 1 * *"  # Monthly
    export_format: str = "json"
    include_remediation_evidence: bool = True

    def validate(self) -> List[str]:
        """Validate compliance configuration."""
        errors = []

        if self.audit_retention_days <= 0:
            errors.append("Audit retention days must be positive")

        supported_standards = ["SOC2", "ISO27001", "PCI-DSS", "HIPAA"]
        for standard in self.compliance_standards:
            if standard not in supported_standards:
                errors.append(f"Unsupported compliance standard: {standard}")

        supported_formats = ["json", "yaml", "pdf", "csv"]
        if self.export_format not in supported_formats:
            errors.append(f"Unsupported export format: {self.export_format}")

        return errors


@dataclass
class EnvironmentSecurityConfig:
    """Environment-specific security configuration."""

    environment: Environment
    base_config: SecurityConfig
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    scanner: ScannerConfig = field(default_factory=ScannerConfig)
    auto_fix: AutoFixConfig = field(default_factory=AutoFixConfig)
    compliance: ComplianceConfig = field(default_factory=ComplianceConfig)

    def validate(self) -> List[str]:
        """Validate the entire environment configuration."""
        errors = []

        # Validate base config
        if not self.base_config.severity_thresholds:
            errors.append("Severity thresholds must be defined")

        # Validate sub-configurations
        errors.extend(self.notifications.validate())
        errors.extend(self.scanner.validate())
        errors.extend(self.auto_fix.validate())
        errors.extend(self.compliance.validate())

        # Environment-specific validations
        if self.environment == Environment.PRODUCTION:
            if self.auto_fix.enabled and not self.auto_fix.require_approval:
                errors.append("Production auto-fix must require approval")

            if not self.notifications.email and not self.notifications.slack_webhook:
                errors.append("Production environment must have notification channels")

        return errors


class SecurityConfigManager:
    """Manages security configuration across different environments."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize the configuration manager."""
        self.config_dir = config_dir or Path.cwd() / ".security"
        self.config_dir.mkdir(exist_ok=True)
        self._configs: Dict[Environment, EnvironmentSecurityConfig] = {}

    def load_config(self, environment: Environment) -> EnvironmentSecurityConfig:
        """Load configuration for a specific environment."""
        if environment in self._configs:
            return self._configs[environment]

        config_file = self.config_dir / f"{environment.value}.yaml"

        if config_file.exists():
            config = self._load_from_file(config_file, environment)
        else:
            config = self._create_default_config(environment)
            self.save_config(config)

        self._configs[environment] = config
        return config

    def save_config(self, config: EnvironmentSecurityConfig) -> None:
        """Save configuration to file."""
        config_file = self.config_dir / f"{config.environment.value}.yaml"

        config_dict = {
            "environment": config.environment.value,
            "base_config": config.base_config.to_dict(),
            "notifications": {
                "email": config.notifications.email,
                "slack_webhook": config.notifications.slack_webhook,
                "teams_webhook": config.notifications.teams_webhook,
                "github_issues": config.notifications.github_issues,
                "console": config.notifications.console,
            },
            "scanner": {
                "primary_scanner": config.scanner.primary_scanner,
                "backup_scanners": config.scanner.backup_scanners,
                "timeout": config.scanner.timeout,
                "retry_attempts": config.scanner.retry_attempts,
                "retry_delay": config.scanner.retry_delay,
                "output_format": config.scanner.output_format,
                "include_dev_dependencies": config.scanner.include_dev_dependencies,
            },
            "auto_fix": {
                "enabled": config.auto_fix.enabled,
                "max_severity": config.auto_fix.max_severity.value,
                "dry_run": config.auto_fix.dry_run,
                "require_approval": config.auto_fix.require_approval,
                "backup_before_fix": config.auto_fix.backup_before_fix,
                "rollback_on_failure": config.auto_fix.rollback_on_failure,
                "test_after_fix": config.auto_fix.test_after_fix,
                "excluded_packages": config.auto_fix.excluded_packages,
            },
            "compliance": {
                "audit_retention_days": config.compliance.audit_retention_days,
                "compliance_standards": config.compliance.compliance_standards,
                "generate_reports": config.compliance.generate_reports,
                "report_schedule": config.compliance.report_schedule,
                "export_format": config.compliance.export_format,
                "include_remediation_evidence": config.compliance.include_remediation_evidence,
            },
        }

        with open(config_file, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)

    def validate_config(self, config: EnvironmentSecurityConfig) -> List[str]:
        """Validate a configuration and return any errors."""
        return config.validate()

    def get_current_environment(self) -> Environment:
        """Determine the current environment from environment variables."""
        env_name = os.getenv("SECURITY_ENVIRONMENT", "development").lower()

        try:
            return Environment(env_name)
        except ValueError:
            return Environment.DEVELOPMENT

    def get_config(
        self, environment: Optional[Environment] = None
    ) -> EnvironmentSecurityConfig:
        """Get configuration for the specified or current environment."""
        if environment is None:
            environment = self.get_current_environment()

        return self.load_config(environment)

    def _load_from_file(
        self, config_file: Path, environment: Environment
    ) -> EnvironmentSecurityConfig:
        """Load configuration from YAML file."""
        try:
            with open(config_file, "r") as f:
                config_dict = yaml.safe_load(f)

            return self._dict_to_config(config_dict, environment)

        except Exception as e:
            raise ConfigurationError(f"Failed to load config from {config_file}: {e}")

    def _dict_to_config(
        self, config_dict: Dict[str, Any], environment: Environment
    ) -> EnvironmentSecurityConfig:
        """Convert dictionary to EnvironmentSecurityConfig."""
        base_config = SecurityConfig.from_dict(config_dict.get("base_config", {}))

        notifications_dict = config_dict.get("notifications", {})
        notifications = NotificationConfig(
            email=notifications_dict.get("email", []),
            slack_webhook=notifications_dict.get("slack_webhook"),
            teams_webhook=notifications_dict.get("teams_webhook"),
            github_issues=notifications_dict.get("github_issues", False),
            console=notifications_dict.get("console", True),
        )

        scanner_dict = config_dict.get("scanner", {})
        scanner = ScannerConfig(
            primary_scanner=scanner_dict.get("primary_scanner", "pip-audit"),
            backup_scanners=scanner_dict.get("backup_scanners", ["safety"]),
            timeout=scanner_dict.get("timeout", 300),
            retry_attempts=scanner_dict.get("retry_attempts", 3),
            retry_delay=scanner_dict.get("retry_delay", 30),
            output_format=scanner_dict.get("output_format", "json"),
            include_dev_dependencies=scanner_dict.get("include_dev_dependencies", True),
        )

        auto_fix_dict = config_dict.get("auto_fix", {})
        auto_fix = AutoFixConfig(
            enabled=auto_fix_dict.get("enabled", False),
            max_severity=VulnerabilitySeverity(
                auto_fix_dict.get("max_severity", "medium")
            ),
            dry_run=auto_fix_dict.get("dry_run", True),
            require_approval=auto_fix_dict.get("require_approval", True),
            backup_before_fix=auto_fix_dict.get("backup_before_fix", True),
            rollback_on_failure=auto_fix_dict.get("rollback_on_failure", True),
            test_after_fix=auto_fix_dict.get("test_after_fix", True),
            excluded_packages=auto_fix_dict.get("excluded_packages", []),
        )

        compliance_dict = config_dict.get("compliance", {})
        compliance = ComplianceConfig(
            audit_retention_days=compliance_dict.get("audit_retention_days", 365),
            compliance_standards=compliance_dict.get(
                "compliance_standards", ["SOC2", "ISO27001"]
            ),
            generate_reports=compliance_dict.get("generate_reports", True),
            report_schedule=compliance_dict.get("report_schedule", "0 0 1 * *"),
            export_format=compliance_dict.get("export_format", "json"),
            include_remediation_evidence=compliance_dict.get(
                "include_remediation_evidence", True
            ),
        )

        return EnvironmentSecurityConfig(
            environment=environment,
            base_config=base_config,
            notifications=notifications,
            scanner=scanner,
            auto_fix=auto_fix,
            compliance=compliance,
        )

    def _create_default_config(
        self, environment: Environment
    ) -> EnvironmentSecurityConfig:
        """Create default configuration for an environment."""
        base_config = SecurityConfig()

        # Environment-specific defaults
        if environment == Environment.PRODUCTION:
            notifications = NotificationConfig(
                email=["security@company.com"],
                console=True,
            )
            auto_fix = AutoFixConfig(
                enabled=False,
                require_approval=True,
                dry_run=True,
            )
        elif environment == Environment.STAGING:
            notifications = NotificationConfig(
                email=["dev-team@company.com"],
                console=True,
            )
            auto_fix = AutoFixConfig(
                enabled=True,
                max_severity=VulnerabilitySeverity.MEDIUM,
                require_approval=True,
            )
        else:  # Development/Testing
            notifications = NotificationConfig(console=True)
            auto_fix = AutoFixConfig(
                enabled=True,
                max_severity=VulnerabilitySeverity.HIGH,
                require_approval=False,
                dry_run=True,
            )

        return EnvironmentSecurityConfig(
            environment=environment,
            base_config=base_config,
            notifications=notifications,
            scanner=ScannerConfig(),
            auto_fix=auto_fix,
            compliance=ComplianceConfig(),
        )

    def list_environments(self) -> List[Environment]:
        """List all configured environments."""
        config_files = list(self.config_dir.glob("*.yaml"))
        environments = []

        for config_file in config_files:
            env_name = config_file.stem
            try:
                environments.append(Environment(env_name))
            except ValueError:
                continue  # Skip invalid environment names

        return environments

    def export_config(self, environment: Environment, output_file: Path) -> None:
        """Export configuration to a file."""
        config = self.load_config(environment)

        if output_file.suffix.lower() == ".json":
            config_dict = {
                "environment": config.environment.value,
                "base_config": config.base_config.to_dict(),
                # Add other config sections as needed
            }
            with open(output_file, "w") as f:
                json.dump(config_dict, f, indent=2)
        else:
            # Default to YAML
            self.save_config(config)

    def import_config(self, config_file: Path, environment: Environment) -> None:
        """Import configuration from a file."""
        if not config_file.exists():
            raise ConfigurationError(f"Config file not found: {config_file}")

        config = self._load_from_file(config_file, environment)

        # Validate before saving
        errors = self.validate_config(config)
        if errors:
            raise ConfigurationError(f"Configuration validation failed: {errors}")

        self.save_config(config)
        self._configs[environment] = config


# Global configuration manager instance
config_manager = SecurityConfigManager()


def get_config(environment: Optional[Environment] = None) -> EnvironmentSecurityConfig:
    """Get security configuration for the specified or current environment."""
    return config_manager.get_config(environment)


def validate_config(config: EnvironmentSecurityConfig) -> List[str]:
    """Validate a security configuration."""
    return config_manager.validate_config(config)
