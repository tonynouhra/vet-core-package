"""
Data models for vulnerability tracking and security management.

This module defines the core data structures used throughout the security
system for tracking vulnerabilities, assessments, and remediation actions.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class VulnerabilitySeverity(Enum):
    """Enumeration of vulnerability severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"

    @classmethod
    def from_cvss_score(cls, score: Optional[float]) -> "VulnerabilitySeverity":
        """Convert CVSS score to severity level."""
        if score is None:
            return cls.UNKNOWN

        if score >= 9.0:
            return cls.CRITICAL
        elif score >= 7.0:
            return cls.HIGH
        elif score >= 4.0:
            return cls.MEDIUM
        else:
            return cls.LOW


@dataclass
class Vulnerability:
    """Represents a security vulnerability in a package."""

    id: str  # e.g., "PYSEC-2024-48"
    package_name: str
    installed_version: str
    fix_versions: List[str]
    severity: VulnerabilitySeverity
    cvss_score: Optional[float] = None
    description: str = ""
    published_date: Optional[datetime] = None
    discovered_date: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Post-initialization processing."""
        # If severity is not set but CVSS score is available, derive severity
        if (
            self.severity == VulnerabilitySeverity.UNKNOWN
            and self.cvss_score is not None
        ):
            self.severity = VulnerabilitySeverity.from_cvss_score(self.cvss_score)

    @property
    def is_fixable(self) -> bool:
        """Check if the vulnerability has available fixes."""
        return len(self.fix_versions) > 0

    @property
    def recommended_fix_version(self) -> Optional[str]:
        """Get the recommended fix version (typically the latest)."""
        if not self.fix_versions:
            return None
        return self.fix_versions[-1]  # Assume last version is the latest

    def to_dict(self) -> Dict[str, Any]:
        """Convert vulnerability to dictionary representation."""
        return {
            "id": self.id,
            "package_name": self.package_name,
            "installed_version": self.installed_version,
            "fix_versions": self.fix_versions,
            "severity": self.severity.value,
            "cvss_score": self.cvss_score,
            "description": self.description,
            "published_date": (
                self.published_date.isoformat() if self.published_date else None
            ),
            "discovered_date": self.discovered_date.isoformat(),
            "is_fixable": self.is_fixable,
            "recommended_fix_version": self.recommended_fix_version,
        }


@dataclass
class SecurityReport:
    """Represents a complete security scan report."""

    scan_date: datetime
    vulnerabilities: List[Vulnerability]
    total_packages_scanned: int
    scan_duration: float  # in seconds
    scanner_version: str
    scan_command: str = ""

    @property
    def vulnerability_count(self) -> int:
        """Total number of vulnerabilities found."""
        return len(self.vulnerabilities)

    @property
    def critical_count(self) -> int:
        """Number of critical vulnerabilities."""
        return sum(
            1
            for v in self.vulnerabilities
            if v.severity == VulnerabilitySeverity.CRITICAL
        )

    @property
    def high_count(self) -> int:
        """Number of high severity vulnerabilities."""
        return sum(
            1 for v in self.vulnerabilities if v.severity == VulnerabilitySeverity.HIGH
        )

    @property
    def medium_count(self) -> int:
        """Number of medium severity vulnerabilities."""
        return sum(
            1
            for v in self.vulnerabilities
            if v.severity == VulnerabilitySeverity.MEDIUM
        )

    @property
    def low_count(self) -> int:
        """Number of low severity vulnerabilities."""
        return sum(
            1 for v in self.vulnerabilities if v.severity == VulnerabilitySeverity.LOW
        )

    @property
    def fixable_count(self) -> int:
        """Number of vulnerabilities that have available fixes."""
        return sum(1 for v in self.vulnerabilities if v.is_fixable)

    def get_vulnerabilities_by_severity(
        self, severity: VulnerabilitySeverity
    ) -> List[Vulnerability]:
        """Get all vulnerabilities of a specific severity level."""
        return [v for v in self.vulnerabilities if v.severity == severity]

    def get_vulnerabilities_by_package(self, package_name: str) -> List[Vulnerability]:
        """Get all vulnerabilities for a specific package."""
        return [v for v in self.vulnerabilities if v.package_name == package_name]

    def to_dict(self) -> Dict[str, Any]:
        """Convert security report to dictionary representation."""
        return {
            "scan_date": self.scan_date.isoformat(),
            "total_packages_scanned": self.total_packages_scanned,
            "scan_duration": self.scan_duration,
            "scanner_version": self.scanner_version,
            "scan_command": self.scan_command,
            "summary": {
                "total_vulnerabilities": self.vulnerability_count,
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "fixable": self.fixable_count,
            },
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
        }


@dataclass
class RemediationAction:
    """Represents an action taken to remediate a vulnerability."""

    vulnerability_id: str
    action_type: str  # "upgrade", "patch", "workaround", "ignore"
    target_version: str = ""
    status: str = "planned"  # "planned", "in_progress", "completed", "failed"
    started_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    notes: str = ""

    def mark_started(self) -> None:
        """Mark the remediation action as started."""
        self.status = "in_progress"
        self.started_date = datetime.now()

    def mark_completed(self, notes: str = "") -> None:
        """Mark the remediation action as completed."""
        self.status = "completed"
        self.completed_date = datetime.now()
        if notes:
            self.notes = notes

    def mark_failed(self, notes: str = "") -> None:
        """Mark the remediation action as failed."""
        self.status = "failed"
        if notes:
            self.notes = notes

    def to_dict(self) -> Dict[str, Any]:
        """Convert remediation action to dictionary representation."""
        return {
            "vulnerability_id": self.vulnerability_id,
            "action_type": self.action_type,
            "target_version": self.target_version,
            "status": self.status,
            "started_date": (
                self.started_date.isoformat() if self.started_date else None
            ),
            "completed_date": (
                self.completed_date.isoformat() if self.completed_date else None
            ),
            "notes": self.notes,
        }


@dataclass
class SecurityConfig:
    """Configuration settings for security scanning and management."""

    scan_schedule: str = "0 6 * * *"  # Daily at 6 AM UTC
    severity_thresholds: Dict[str, int] = field(default_factory=dict)
    notification_channels: List[str] = field(default_factory=list)
    auto_fix_enabled: bool = False
    max_auto_fix_severity: VulnerabilitySeverity = VulnerabilitySeverity.MEDIUM
    scanner_timeout: int = 300  # 5 minutes

    def __post_init__(self) -> None:
        """Set default severity thresholds if not provided."""
        if not self.severity_thresholds:
            self.severity_thresholds = {
                "critical": 24,  # hours
                "high": 72,  # 3 days
                "medium": 168,  # 1 week
                "low": 720,  # 1 month
            }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "SecurityConfig":
        """Create SecurityConfig from dictionary."""
        # Handle severity enum conversion
        max_severity = config_dict.get("max_auto_fix_severity", "medium")
        if isinstance(max_severity, str):
            max_severity = VulnerabilitySeverity(max_severity)

        return cls(
            scan_schedule=config_dict.get("scan_schedule", "0 6 * * *"),
            severity_thresholds=config_dict.get("severity_thresholds", {}),
            notification_channels=config_dict.get("notification_channels", []),
            auto_fix_enabled=config_dict.get("auto_fix_enabled", False),
            max_auto_fix_severity=max_severity,
            scanner_timeout=config_dict.get("scanner_timeout", 300),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert security config to dictionary representation."""
        return {
            "scan_schedule": self.scan_schedule,
            "severity_thresholds": self.severity_thresholds,
            "notification_channels": self.notification_channels,
            "auto_fix_enabled": self.auto_fix_enabled,
            "max_auto_fix_severity": self.max_auto_fix_severity.value,
            "scanner_timeout": self.scanner_timeout,
        }
