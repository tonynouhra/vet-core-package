"""
Security module for vulnerability scanning and management.

This module provides functionality for:
- Vulnerability detection and scanning
- Risk assessment and prioritization
- Security report generation
- Audit trail management
- Compliance reporting and monitoring
"""

from .assessor import RiskAssessor
from .audit_trail import (
    AuditEvent,
    AuditEventType,
    ComplianceMetrics,
    SecurityAuditTrail,
)
from .compliance import (
    ComplianceFramework,
    ComplianceViolation,
    PolicyRule,
    SecurityComplianceManager,
)
from .config import (
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
from .models import (
    RemediationAction,
    SecurityConfig,
    SecurityReport,
    Vulnerability,
    VulnerabilitySeverity,
)
from .reporter import SecurityReporter
from .scanner import VulnerabilityScanner
from .upgrade_validator import (
    DependencyConflictError,
    EnvironmentBackup,
    TestFailureError,
    UpgradeResult,
    UpgradeValidator,
    validate_vulnerability_fixes,
)

__all__ = [
    "Vulnerability",
    "VulnerabilitySeverity",
    "SecurityReport",
    "RemediationAction",
    "SecurityConfig",
    "VulnerabilityScanner",
    "SecurityReporter",
    "RiskAssessor",
    "UpgradeValidator",
    "UpgradeResult",
    "EnvironmentBackup",
    "DependencyConflictError",
    "TestFailureError",
    "validate_vulnerability_fixes",
    "SecurityAuditTrail",
    "AuditEvent",
    "AuditEventType",
    "ComplianceMetrics",
    "SecurityComplianceManager",
    "ComplianceFramework",
    "PolicyRule",
    "ComplianceViolation",
    "SecurityConfigManager",
    "Environment",
    "EnvironmentSecurityConfig",
    "NotificationConfig",
    "ScannerConfig",
    "AutoFixConfig",
    "ComplianceConfig",
    "ConfigurationError",
    "get_config",
    "validate_config",
]
