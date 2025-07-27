"""
Tests for security data models.
"""

import pytest
from datetime import datetime, timedelta
from vet_core.security.models import (
    Vulnerability,
    VulnerabilitySeverity,
    SecurityReport,
    RemediationAction,
    SecurityConfig,
)


class TestVulnerabilitySeverity:
    """Test VulnerabilitySeverity enum."""

    def test_from_cvss_score_critical(self):
        """Test CVSS score to severity conversion for critical."""
        assert (
            VulnerabilitySeverity.from_cvss_score(9.5) == VulnerabilitySeverity.CRITICAL
        )
        assert (
            VulnerabilitySeverity.from_cvss_score(10.0)
            == VulnerabilitySeverity.CRITICAL
        )

    def test_from_cvss_score_high(self):
        """Test CVSS score to severity conversion for high."""
        assert VulnerabilitySeverity.from_cvss_score(7.0) == VulnerabilitySeverity.HIGH
        assert VulnerabilitySeverity.from_cvss_score(8.9) == VulnerabilitySeverity.HIGH

    def test_from_cvss_score_medium(self):
        """Test CVSS score to severity conversion for medium."""
        assert (
            VulnerabilitySeverity.from_cvss_score(4.0) == VulnerabilitySeverity.MEDIUM
        )
        assert (
            VulnerabilitySeverity.from_cvss_score(6.9) == VulnerabilitySeverity.MEDIUM
        )

    def test_from_cvss_score_low(self):
        """Test CVSS score to severity conversion for low."""
        assert VulnerabilitySeverity.from_cvss_score(0.1) == VulnerabilitySeverity.LOW
        assert VulnerabilitySeverity.from_cvss_score(3.9) == VulnerabilitySeverity.LOW

    def test_from_cvss_score_none(self):
        """Test CVSS score to severity conversion for None."""
        assert (
            VulnerabilitySeverity.from_cvss_score(None) == VulnerabilitySeverity.UNKNOWN
        )


class TestVulnerability:
    """Test Vulnerability data model."""

    def test_vulnerability_creation(self):
        """Test basic vulnerability creation."""
        vuln = Vulnerability(
            id="PYSEC-2024-48",
            package_name="black",
            installed_version="23.12.1",
            fix_versions=["24.3.0"],
            severity=VulnerabilitySeverity.MEDIUM,
            cvss_score=5.5,
            description="Test vulnerability",
        )

        assert vuln.id == "PYSEC-2024-48"
        assert vuln.package_name == "black"
        assert vuln.installed_version == "23.12.1"
        assert vuln.fix_versions == ["24.3.0"]
        assert vuln.severity == VulnerabilitySeverity.MEDIUM
        assert vuln.cvss_score == 5.5
        assert vuln.description == "Test vulnerability"

    def test_vulnerability_auto_severity_from_cvss(self):
        """Test automatic severity derivation from CVSS score."""
        vuln = Vulnerability(
            id="TEST-001",
            package_name="test-package",
            installed_version="1.0.0",
            fix_versions=["1.1.0"],
            severity=VulnerabilitySeverity.UNKNOWN,
            cvss_score=8.5,
        )

        # Should auto-derive severity from CVSS score
        assert vuln.severity == VulnerabilitySeverity.HIGH

    def test_is_fixable_true(self):
        """Test is_fixable property when fix versions are available."""
        vuln = Vulnerability(
            id="TEST-001",
            package_name="test-package",
            installed_version="1.0.0",
            fix_versions=["1.1.0", "1.2.0"],
            severity=VulnerabilitySeverity.MEDIUM,
        )

        assert vuln.is_fixable is True

    def test_is_fixable_false(self):
        """Test is_fixable property when no fix versions are available."""
        vuln = Vulnerability(
            id="TEST-001",
            package_name="test-package",
            installed_version="1.0.0",
            fix_versions=[],
            severity=VulnerabilitySeverity.MEDIUM,
        )

        assert vuln.is_fixable is False

    def test_recommended_fix_version(self):
        """Test recommended fix version selection."""
        vuln = Vulnerability(
            id="TEST-001",
            package_name="test-package",
            installed_version="1.0.0",
            fix_versions=["1.1.0", "1.2.0", "1.3.0"],
            severity=VulnerabilitySeverity.MEDIUM,
        )

        # Should return the last (latest) version
        assert vuln.recommended_fix_version == "1.3.0"

    def test_recommended_fix_version_none(self):
        """Test recommended fix version when no fixes available."""
        vuln = Vulnerability(
            id="TEST-001",
            package_name="test-package",
            installed_version="1.0.0",
            fix_versions=[],
            severity=VulnerabilitySeverity.MEDIUM,
        )

        assert vuln.recommended_fix_version is None

    def test_to_dict(self):
        """Test vulnerability serialization to dictionary."""
        now = datetime.now()
        vuln = Vulnerability(
            id="TEST-001",
            package_name="test-package",
            installed_version="1.0.0",
            fix_versions=["1.1.0"],
            severity=VulnerabilitySeverity.HIGH,
            cvss_score=7.5,
            description="Test description",
            published_date=now,
            discovered_date=now,
        )

        result = vuln.to_dict()

        assert result["id"] == "TEST-001"
        assert result["package_name"] == "test-package"
        assert result["installed_version"] == "1.0.0"
        assert result["fix_versions"] == ["1.1.0"]
        assert result["severity"] == "high"
        assert result["cvss_score"] == 7.5
        assert result["description"] == "Test description"
        assert result["published_date"] == now.isoformat()
        assert result["discovered_date"] == now.isoformat()
        assert result["is_fixable"] is True
        assert result["recommended_fix_version"] == "1.1.0"


class TestSecurityReport:
    """Test SecurityReport data model."""

    def test_security_report_creation(self):
        """Test basic security report creation."""
        now = datetime.now()
        vulnerabilities = [
            Vulnerability(
                id="TEST-001",
                package_name="test-package",
                installed_version="1.0.0",
                fix_versions=["1.1.0"],
                severity=VulnerabilitySeverity.HIGH,
            )
        ]

        report = SecurityReport(
            scan_date=now,
            vulnerabilities=vulnerabilities,
            total_packages_scanned=10,
            scan_duration=30.5,
            scanner_version="pip-audit 2.6.0",
        )

        assert report.scan_date == now
        assert len(report.vulnerabilities) == 1
        assert report.total_packages_scanned == 10
        assert report.scan_duration == 30.5
        assert report.scanner_version == "pip-audit 2.6.0"

    def test_vulnerability_counts(self):
        """Test vulnerability count properties."""
        vulnerabilities = [
            Vulnerability(
                id="CRIT-001",
                package_name="pkg1",
                installed_version="1.0.0",
                fix_versions=["1.1.0"],
                severity=VulnerabilitySeverity.CRITICAL,
            ),
            Vulnerability(
                id="HIGH-001",
                package_name="pkg2",
                installed_version="1.0.0",
                fix_versions=["1.1.0"],
                severity=VulnerabilitySeverity.HIGH,
            ),
            Vulnerability(
                id="MED-001",
                package_name="pkg3",
                installed_version="1.0.0",
                fix_versions=[],
                severity=VulnerabilitySeverity.MEDIUM,
            ),
            Vulnerability(
                id="LOW-001",
                package_name="pkg4",
                installed_version="1.0.0",
                fix_versions=["1.1.0"],
                severity=VulnerabilitySeverity.LOW,
            ),
        ]

        report = SecurityReport(
            scan_date=datetime.now(),
            vulnerabilities=vulnerabilities,
            total_packages_scanned=10,
            scan_duration=30.0,
            scanner_version="test",
        )

        assert report.vulnerability_count == 4
        assert report.critical_count == 1
        assert report.high_count == 1
        assert report.medium_count == 1
        assert report.low_count == 1
        assert report.fixable_count == 3  # All except MED-001

    def test_get_vulnerabilities_by_severity(self):
        """Test filtering vulnerabilities by severity."""
        vulnerabilities = [
            Vulnerability(
                id="HIGH-001",
                package_name="pkg1",
                installed_version="1.0.0",
                fix_versions=["1.1.0"],
                severity=VulnerabilitySeverity.HIGH,
            ),
            Vulnerability(
                id="HIGH-002",
                package_name="pkg2",
                installed_version="1.0.0",
                fix_versions=["1.1.0"],
                severity=VulnerabilitySeverity.HIGH,
            ),
            Vulnerability(
                id="MED-001",
                package_name="pkg3",
                installed_version="1.0.0",
                fix_versions=[],
                severity=VulnerabilitySeverity.MEDIUM,
            ),
        ]

        report = SecurityReport(
            scan_date=datetime.now(),
            vulnerabilities=vulnerabilities,
            total_packages_scanned=10,
            scan_duration=30.0,
            scanner_version="test",
        )

        high_vulns = report.get_vulnerabilities_by_severity(VulnerabilitySeverity.HIGH)
        assert len(high_vulns) == 2
        assert all(v.severity == VulnerabilitySeverity.HIGH for v in high_vulns)

        medium_vulns = report.get_vulnerabilities_by_severity(
            VulnerabilitySeverity.MEDIUM
        )
        assert len(medium_vulns) == 1
        assert medium_vulns[0].id == "MED-001"

    def test_get_vulnerabilities_by_package(self):
        """Test filtering vulnerabilities by package."""
        vulnerabilities = [
            Vulnerability(
                id="PKG1-001",
                package_name="package1",
                installed_version="1.0.0",
                fix_versions=["1.1.0"],
                severity=VulnerabilitySeverity.HIGH,
            ),
            Vulnerability(
                id="PKG1-002",
                package_name="package1",
                installed_version="1.0.0",
                fix_versions=["1.1.0"],
                severity=VulnerabilitySeverity.MEDIUM,
            ),
            Vulnerability(
                id="PKG2-001",
                package_name="package2",
                installed_version="1.0.0",
                fix_versions=[],
                severity=VulnerabilitySeverity.LOW,
            ),
        ]

        report = SecurityReport(
            scan_date=datetime.now(),
            vulnerabilities=vulnerabilities,
            total_packages_scanned=10,
            scan_duration=30.0,
            scanner_version="test",
        )

        pkg1_vulns = report.get_vulnerabilities_by_package("package1")
        assert len(pkg1_vulns) == 2
        assert all(v.package_name == "package1" for v in pkg1_vulns)

        pkg2_vulns = report.get_vulnerabilities_by_package("package2")
        assert len(pkg2_vulns) == 1
        assert pkg2_vulns[0].id == "PKG2-001"


class TestRemediationAction:
    """Test RemediationAction data model."""

    def test_remediation_action_creation(self):
        """Test basic remediation action creation."""
        action = RemediationAction(
            vulnerability_id="TEST-001", action_type="upgrade", target_version="1.1.0"
        )

        assert action.vulnerability_id == "TEST-001"
        assert action.action_type == "upgrade"
        assert action.target_version == "1.1.0"
        assert action.status == "planned"
        assert action.started_date is None
        assert action.completed_date is None

    def test_mark_started(self):
        """Test marking remediation action as started."""
        action = RemediationAction(vulnerability_id="TEST-001", action_type="upgrade")

        action.mark_started()

        assert action.status == "in_progress"
        assert action.started_date is not None
        assert isinstance(action.started_date, datetime)

    def test_mark_completed(self):
        """Test marking remediation action as completed."""
        action = RemediationAction(vulnerability_id="TEST-001", action_type="upgrade")

        action.mark_completed("Successfully upgraded package")

        assert action.status == "completed"
        assert action.completed_date is not None
        assert isinstance(action.completed_date, datetime)
        assert action.notes == "Successfully upgraded package"

    def test_mark_failed(self):
        """Test marking remediation action as failed."""
        action = RemediationAction(vulnerability_id="TEST-001", action_type="upgrade")

        action.mark_failed("Upgrade caused test failures")

        assert action.status == "failed"
        assert action.notes == "Upgrade caused test failures"


class TestSecurityConfig:
    """Test SecurityConfig data model."""

    def test_security_config_defaults(self):
        """Test security config with default values."""
        config = SecurityConfig()

        assert config.scan_schedule == "0 6 * * *"
        assert config.auto_fix_enabled is False
        assert config.max_auto_fix_severity == VulnerabilitySeverity.MEDIUM
        assert config.scanner_timeout == 300
        assert "critical" in config.severity_thresholds
        assert config.severity_thresholds["critical"] == 24

    def test_security_config_custom_values(self):
        """Test security config with custom values."""
        custom_thresholds = {"critical": 12, "high": 48}

        config = SecurityConfig(
            scan_schedule="0 12 * * *",
            severity_thresholds=custom_thresholds,
            auto_fix_enabled=True,
            max_auto_fix_severity=VulnerabilitySeverity.HIGH,
        )

        assert config.scan_schedule == "0 12 * * *"
        assert config.severity_thresholds == custom_thresholds
        assert config.auto_fix_enabled is True
        assert config.max_auto_fix_severity == VulnerabilitySeverity.HIGH

    def test_from_dict(self):
        """Test creating security config from dictionary."""
        config_dict = {
            "scan_schedule": "0 8 * * *",
            "auto_fix_enabled": True,
            "max_auto_fix_severity": "high",
            "scanner_timeout": 600,
        }

        config = SecurityConfig.from_dict(config_dict)

        assert config.scan_schedule == "0 8 * * *"
        assert config.auto_fix_enabled is True
        assert config.max_auto_fix_severity == VulnerabilitySeverity.HIGH
        assert config.scanner_timeout == 600

    def test_to_dict(self):
        """Test converting security config to dictionary."""
        config = SecurityConfig(
            scan_schedule="0 9 * * *",
            auto_fix_enabled=True,
            max_auto_fix_severity=VulnerabilitySeverity.CRITICAL,
        )

        result = config.to_dict()

        assert result["scan_schedule"] == "0 9 * * *"
        assert result["auto_fix_enabled"] is True
        assert result["max_auto_fix_severity"] == "critical"
        assert "severity_thresholds" in result
