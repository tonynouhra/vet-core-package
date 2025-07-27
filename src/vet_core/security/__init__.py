"""
Security module for vulnerability scanning and management.

This module provides functionality for:
- Vulnerability detection and scanning
- Risk assessment and prioritization
- Security report generation
- Audit trail management
- Compliance reporting and monitoring
"""

from .models import (
    Vulnerability,
    VulnerabilitySeverity,
    SecurityReport,
    RemediationAction,
    SecurityConfig,
)
from .scanner import VulnerabilityScanner
from .reporter import SecurityReporter
from .assessor import RiskAssessor
from .upgrade_validator import (
    UpgradeValidator,
    UpgradeResult,
    EnvironmentBackup,
    DependencyConflictError,
    TestFailureError,
    validate_vulnerability_fixes,
)
from .audit_trail import (
    SecurityAuditTrail,
    AuditEvent,
    AuditEventType,
    ComplianceMetrics,
)
from .compliance import (
    SecurityComplianceManager,
    ComplianceFramework,
    PolicyRule,
    ComplianceViolation,
)
from .config import (
    SecurityConfigManager,
    Environment,
    EnvironmentSecurityConfig,
    NotificationConfig,
    ScannerConfig,
    AutoFixConfig,
    ComplianceConfig,
    ConfigurationError,
    get_config,
    validate_config,
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
