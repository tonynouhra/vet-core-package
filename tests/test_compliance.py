"""
Tests for security compliance reporting and management functionality.

This module tests the comprehensive compliance system including:
- Policy rule management
- Compliance checking and violation detection
- Framework-specific reporting
- Evidence generation
"""

import gc
import json
import os
import platform
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from vet_core.security.assessor import RiskAssessor
from vet_core.security.audit_trail import AuditEventType, SecurityAuditTrail
from vet_core.security.compliance import (
    ComplianceFramework,
    ComplianceViolation,
    PolicyRule,
    SecurityComplianceManager,
)
from vet_core.security.models import (
    SecurityReport,
    Vulnerability,
    VulnerabilitySeverity,
)


class TestSecurityComplianceManager:
    """Test cases for SecurityComplianceManager class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path for testing."""
        fd, temp_path = tempfile.mkstemp(suffix=".db")
        db_path = Path(temp_path)
        os.close(fd)

        yield db_path

        # Windows-safe cleanup
        gc.collect()
        if platform.system() == "Windows":
            for i in range(5):
                try:
                    if db_path.exists():
                        db_path.unlink()
                    break
                except PermissionError:
                    if i < 4:
                        time.sleep(0.2)
                    else:
                        print(f"Warning: Could not delete {db_path}")
        else:
            if db_path.exists():
                db_path.unlink()

    @pytest.fixture
    def audit_trail(self, temp_db_path):
        """Create SecurityAuditTrail instance for testing."""
        return SecurityAuditTrail(audit_db_path=temp_db_path)

    @pytest.fixture
    def risk_assessor(self):
        """Create RiskAssessor instance for testing."""
        return RiskAssessor()

    @pytest.fixture
    def compliance_manager(self, audit_trail, risk_assessor):
        """Create SecurityComplianceManager instance for testing."""
        return SecurityComplianceManager(
            audit_trail=audit_trail, risk_assessor=risk_assessor
        )

    @pytest.fixture
    def sample_vulnerability_critical(self):
        """Create sample critical vulnerability for testing."""
        return Vulnerability(
            id="CRITICAL-2024-001",
            package_name="setuptools",
            installed_version="65.5.0",
            fix_versions=["78.1.1"],
            severity=VulnerabilitySeverity.CRITICAL,
            cvss_score=9.8,
            description="Critical security vulnerability",
            published_date=datetime.now() - timedelta(days=2),
            discovered_date=datetime.now()
            - timedelta(hours=30),  # 30 hours old - violates 24h rule
        )

    @pytest.fixture
    def sample_vulnerability_high(self):
        """Create sample high severity vulnerability for testing."""
        return Vulnerability(
            id="HIGH-2024-002",
            package_name="requests",
            installed_version="2.28.0",
            fix_versions=["2.31.0"],
            severity=VulnerabilitySeverity.HIGH,
            cvss_score=7.5,
            description="High severity vulnerability",
            published_date=datetime.now() - timedelta(days=1),
            discovered_date=datetime.now()
            - timedelta(hours=80),  # 80 hours old - violates 72h rule
        )

    @pytest.fixture
    def sample_vulnerability_medium(self):
        """Create sample medium severity vulnerability for testing."""
        return Vulnerability(
            id="MEDIUM-2024-003",
            package_name="black",
            installed_version="23.12.1",
            fix_versions=["24.3.0"],
            severity=VulnerabilitySeverity.MEDIUM,
            cvss_score=5.5,
            description="Medium severity vulnerability",
            published_date=datetime.now() - timedelta(days=3),
            discovered_date=datetime.now()
            - timedelta(hours=2),  # 2 hours old - within limits
        )

    @pytest.fixture
    def sample_security_report(
        self,
        sample_vulnerability_critical,
        sample_vulnerability_high,
        sample_vulnerability_medium,
    ):
        """Create sample security report for testing."""
        return SecurityReport(
            scan_date=datetime.now(),
            vulnerabilities=[
                sample_vulnerability_critical,
                sample_vulnerability_high,
                sample_vulnerability_medium,
            ],
            total_packages_scanned=150,
            scan_duration=60.5,
            scanner_version="pip-audit 2.6.1",
            scan_command="pip-audit --format=json",
        )

    def test_initialization(self, audit_trail, risk_assessor):
        """Test SecurityComplianceManager initialization."""
        manager = SecurityComplianceManager(
            audit_trail=audit_trail, risk_assessor=risk_assessor
        )

        assert manager.audit_trail == audit_trail
        assert manager.risk_assessor == risk_assessor
        assert len(manager.policy_rules) == 4  # Default rules

        # Check default policy rules exist
        assert "CRITICAL_24H" in manager.policy_rules
        assert "HIGH_72H" in manager.policy_rules
        assert "MEDIUM_7D" in manager.policy_rules
        assert "DAILY_SCAN" in manager.policy_rules

    def test_custom_policy_rules(self, audit_trail):
        """Test initialization with custom policy rules."""
        custom_rule = PolicyRule(
            rule_id="CUSTOM_RULE",
            name="Custom Security Rule",
            description="Custom rule for testing",
            severity_threshold=VulnerabilitySeverity.LOW,
            max_resolution_time_hours=48,
            framework=ComplianceFramework.CUSTOM,
        )

        manager = SecurityComplianceManager(
            audit_trail=audit_trail, custom_policy_rules=[custom_rule]
        )

        assert "CUSTOM_RULE" in manager.policy_rules
        assert manager.policy_rules["CUSTOM_RULE"] == custom_rule

    def test_check_compliance_with_violations(
        self, compliance_manager, sample_security_report
    ):
        """Test compliance checking with policy violations."""
        violations, metrics = compliance_manager.check_compliance(
            sample_security_report
        )

        # Should find violations for critical and high severity vulnerabilities
        assert len(violations) >= 2

        # Check violation details
        violation_ids = [v.vulnerability_id for v in violations]
        assert "CRITICAL-2024-001" in violation_ids  # Critical vuln exceeds 24h
        assert "HIGH-2024-002" in violation_ids  # High vuln exceeds 72h

        # Check metrics
        assert metrics.total_vulnerabilities == 3
        assert metrics.critical_vulnerabilities == 1
        assert metrics.high_vulnerabilities == 1
        assert metrics.medium_vulnerabilities == 1
        assert metrics.compliance_score < 100.0  # Should be reduced due to violations

    def test_check_compliance_no_violations(self, compliance_manager):
        """Test compliance checking with no violations."""
        # Create report with recent vulnerabilities (within policy limits)
        recent_vuln = Vulnerability(
            id="RECENT-2024-001",
            package_name="test-package",
            installed_version="1.0.0",
            fix_versions=["1.0.1"],
            severity=VulnerabilitySeverity.MEDIUM,
            cvss_score=4.5,
            description="Recent vulnerability",
            discovered_date=datetime.now() - timedelta(hours=1),  # 1 hour old
        )

        report = SecurityReport(
            scan_date=datetime.now(),
            vulnerabilities=[recent_vuln],
            total_packages_scanned=100,
            scan_duration=30.0,
            scanner_version="pip-audit 2.6.1",
        )

        violations, metrics = compliance_manager.check_compliance(
            report, check_historical=False
        )

        # Should find no violations for recent vulnerability
        assert len(violations) == 0
        assert metrics.compliance_score > 80.0  # Should be high with no violations

    def test_scan_frequency_compliance(self, compliance_manager, audit_trail):
        """Test scan frequency compliance checking."""
        # Create a report with no vulnerabilities
        empty_report = SecurityReport(
            scan_date=datetime.now(),
            vulnerabilities=[],
            total_packages_scanned=100,
            scan_duration=30.0,
            scanner_version="pip-audit 2.6.1",
        )

        # Don't log any recent scans - should trigger scan frequency violation
        violations, metrics = compliance_manager.check_compliance(
            empty_report, check_historical=True
        )

        # Should find scan frequency violation
        scan_violations = [
            v for v in violations if v.violation_type == "scan_frequency"
        ]
        assert len(scan_violations) >= 1

        # Now log a recent scan and check again
        audit_trail.log_scan_completed("recent_scan", empty_report, 30.0)
        violations, metrics = compliance_manager.check_compliance(
            empty_report, check_historical=True
        )

        # Scan frequency violation should be resolved
        scan_violations = [
            v for v in violations if v.violation_type == "scan_frequency"
        ]
        assert len(scan_violations) == 0

    def test_policy_rule_applicability(self, compliance_manager):
        """Test policy rule applicability logic."""
        critical_rule = compliance_manager.policy_rules["CRITICAL_24H"]
        high_rule = compliance_manager.policy_rules["HIGH_72H"]
        medium_rule = compliance_manager.policy_rules["MEDIUM_7D"]

        # Test critical vulnerability
        critical_vuln = Vulnerability(
            id="TEST-CRITICAL",
            package_name="test",
            installed_version="1.0.0",
            fix_versions=["1.0.1"],
            severity=VulnerabilitySeverity.CRITICAL,
        )

        assert compliance_manager._is_rule_applicable(critical_rule, critical_vuln)
        assert compliance_manager._is_rule_applicable(
            high_rule, critical_vuln
        )  # Critical applies to high rule too
        assert compliance_manager._is_rule_applicable(
            medium_rule, critical_vuln
        )  # Critical applies to medium rule too

        # Test medium vulnerability
        medium_vuln = Vulnerability(
            id="TEST-MEDIUM",
            package_name="test",
            installed_version="1.0.0",
            fix_versions=["1.0.1"],
            severity=VulnerabilitySeverity.MEDIUM,
        )

        assert not compliance_manager._is_rule_applicable(critical_rule, medium_vuln)
        assert not compliance_manager._is_rule_applicable(high_rule, medium_vuln)
        assert compliance_manager._is_rule_applicable(medium_rule, medium_vuln)

    def test_generate_nist_csf_report(
        self, compliance_manager, audit_trail, sample_security_report
    ):
        """Test NIST CSF compliance report generation."""
        # Log some audit events to provide evidence
        audit_trail.log_scan_completed("scan_123", sample_security_report, 60.5)
        audit_trail.log_vulnerability_detected(
            sample_security_report.vulnerabilities[0]
        )

        report = compliance_manager.generate_compliance_report(
            framework=ComplianceFramework.NIST_CSF
        )

        assert report["report_metadata"]["framework"] == "nist_csf"
        assert "framework_requirements" in report
        assert "functions" in report["framework_requirements"]

        # Check NIST CSF functions
        functions = report["framework_requirements"]["functions"]
        assert "identify" in functions
        assert "protect" in functions
        assert "detect" in functions
        assert "respond" in functions
        assert "recover" in functions

        # Check evidence is provided
        for function_name, function_data in functions.items():
            assert "evidence" in function_data
            assert "compliance_status" in function_data

    def test_generate_iso27001_report(
        self, compliance_manager, audit_trail, sample_security_report
    ):
        """Test ISO 27001 compliance report generation."""
        # Log some audit events
        audit_trail.log_scan_completed("scan_456", sample_security_report, 45.0)

        report = compliance_manager.generate_compliance_report(
            framework=ComplianceFramework.ISO_27001
        )

        assert report["report_metadata"]["framework"] == "iso_27001"
        assert "framework_requirements" in report
        assert "controls" in report["framework_requirements"]

        # Check ISO 27001 controls
        controls = report["framework_requirements"]["controls"]
        assert "A.12.6.1" in controls  # Management of technical vulnerabilities
        assert "A.16.1.3" in controls  # Reporting information security weaknesses

        # Check control evidence
        for control_id, control_data in controls.items():
            assert "evidence" in control_data
            assert "compliance_status" in control_data

    def test_generate_soc2_report(
        self, compliance_manager, audit_trail, sample_security_report
    ):
        """Test SOC 2 compliance report generation."""
        audit_trail.log_scan_completed("scan_789", sample_security_report, 55.0)

        report = compliance_manager.generate_compliance_report(
            framework=ComplianceFramework.SOC2
        )

        assert report["report_metadata"]["framework"] == "soc2"
        assert "framework_requirements" in report
        assert "trust_criteria" in report["framework_requirements"]

        # Check SOC 2 trust criteria
        criteria = report["framework_requirements"]["trust_criteria"]
        assert "security" in criteria
        assert "availability" in criteria

        # Check criteria evidence
        for criterion_name, criterion_data in criteria.items():
            assert "evidence" in criterion_data
            assert "compliance_status" in criterion_data

    def test_generate_pci_dss_report(
        self, compliance_manager, audit_trail, sample_security_report
    ):
        """Test PCI DSS compliance report generation."""
        audit_trail.log_scan_completed("scan_101", sample_security_report, 40.0)

        report = compliance_manager.generate_compliance_report(
            framework=ComplianceFramework.PCI_DSS
        )

        assert report["report_metadata"]["framework"] == "pci_dss"
        assert "framework_requirements" in report
        assert "requirements" in report["framework_requirements"]

        # Check PCI DSS requirements
        requirements = report["framework_requirements"]["requirements"]
        assert "req_6" in requirements  # Secure systems and applications
        assert "req_11" in requirements  # Test security systems

        # Check requirement evidence
        for req_id, req_data in requirements.items():
            assert "sub_requirements" in req_data
            for sub_req_id, sub_req_data in req_data["sub_requirements"].items():
                assert "evidence" in sub_req_data
                assert "compliance_status" in sub_req_data

    def test_executive_summary_generation(
        self, compliance_manager, audit_trail, sample_security_report
    ):
        """Test executive summary generation."""
        # Log events and calculate metrics
        audit_trail.log_scan_completed("scan_summary", sample_security_report, 50.0)
        violations, metrics = compliance_manager.check_compliance(
            sample_security_report
        )

        report = compliance_manager.generate_compliance_report(
            framework=ComplianceFramework.NIST_CSF
        )

        summary = report["executive_summary"]

        assert "compliance_overview" in summary
        assert "security_posture" in summary
        assert "operational_metrics" in summary

        # Check compliance overview
        overview = summary["compliance_overview"]
        assert "overall_score" in overview
        assert "policy_violations" in overview
        assert "active_policy_rules" in overview

        # Check security posture
        posture = summary["security_posture"]
        assert "total_vulnerabilities" in posture
        assert "critical_vulnerabilities" in posture
        assert "vulnerabilities_resolved" in posture

    def test_evidence_documentation(
        self, compliance_manager, audit_trail, sample_security_report
    ):
        """Test evidence documentation generation."""
        audit_trail.log_scan_completed("evidence_scan", sample_security_report, 35.0)

        report = compliance_manager.generate_compliance_report(
            framework=ComplianceFramework.CUSTOM
        )

        evidence = report["evidence_documentation"]

        assert "audit_trail_evidence" in evidence
        assert "vulnerability_management_evidence" in evidence
        assert "documentation_evidence" in evidence

        # Check audit trail evidence
        audit_evidence = evidence["audit_trail_evidence"]
        assert "total_events_logged" in audit_evidence
        assert "event_types_tracked" in audit_evidence
        assert "data_retention_period" in audit_evidence

        # Check vulnerability management evidence
        vuln_evidence = evidence["vulnerability_management_evidence"]
        assert "detection_capabilities" in vuln_evidence
        assert "assessment_procedures" in vuln_evidence
        assert "remediation_tracking" in vuln_evidence

    def test_compliance_recommendations(
        self, compliance_manager, sample_security_report
    ):
        """Test compliance recommendations generation."""
        violations, metrics = compliance_manager.check_compliance(
            sample_security_report
        )

        report = compliance_manager.generate_compliance_report(
            framework=ComplianceFramework.NIST_CSF
        )

        recommendations = report["recommendations"]

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

        # Should include recommendations for critical vulnerabilities
        critical_recommendations = [
            r for r in recommendations if "critical" in r.lower()
        ]
        assert len(critical_recommendations) > 0

    def test_policy_rule_management(self, compliance_manager):
        """Test policy rule management operations."""
        # Test adding new policy rule
        new_rule = PolicyRule(
            rule_id="TEST_RULE",
            name="Test Rule",
            description="Test rule for unit testing",
            severity_threshold=VulnerabilitySeverity.LOW,
            max_resolution_time_hours=24,
            framework=ComplianceFramework.CUSTOM,
        )

        compliance_manager.add_policy_rule(new_rule)
        assert "TEST_RULE" in compliance_manager.policy_rules

        # Test getting policy rules by framework
        custom_rules = compliance_manager.get_policy_rules(ComplianceFramework.CUSTOM)
        assert len(custom_rules) >= 1
        assert any(rule.rule_id == "TEST_RULE" for rule in custom_rules)

        # Test removing policy rule
        success = compliance_manager.remove_policy_rule("TEST_RULE")
        assert success
        assert "TEST_RULE" not in compliance_manager.policy_rules

        # Test removing non-existent rule
        success = compliance_manager.remove_policy_rule("NON_EXISTENT")
        assert not success

    def test_compliance_violation_serialization(self):
        """Test ComplianceViolation serialization."""
        violation = ComplianceViolation(
            violation_id="TEST_VIOLATION",
            rule_id="CRITICAL_24H",
            vulnerability_id="PYSEC-2024-48",
            package_name="black",
            violation_type="resolution_time_exceeded",
            description="Test violation",
            severity="critical",
            detected_at=datetime.now(),
        )

        # Convert to dict
        violation_dict = violation.to_dict()

        # Verify dict structure
        assert violation_dict["violation_id"] == "TEST_VIOLATION"
        assert violation_dict["rule_id"] == "CRITICAL_24H"
        assert violation_dict["vulnerability_id"] == "PYSEC-2024-48"
        assert violation_dict["is_resolved"] is False
        assert "detected_at" in violation_dict

    def test_policy_rule_serialization(self):
        """Test PolicyRule serialization."""
        rule = PolicyRule(
            rule_id="TEST_SERIALIZATION",
            name="Test Serialization Rule",
            description="Rule for testing serialization",
            severity_threshold=VulnerabilitySeverity.HIGH,
            max_resolution_time_hours=48,
            framework=ComplianceFramework.NIST_CSF,
        )

        # Convert to dict
        rule_dict = rule.to_dict()

        # Verify dict structure
        assert rule_dict["rule_id"] == "TEST_SERIALIZATION"
        assert rule_dict["severity_threshold"] == "high"
        assert rule_dict["max_resolution_time_hours"] == 48
        assert rule_dict["framework"] == "nist_csf"
        assert rule_dict["is_active"] is True
        assert "created_at" in rule_dict

    def test_report_file_output(
        self, compliance_manager, audit_trail, sample_security_report
    ):
        """Test saving compliance report to file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_file = Path(f.name)

        try:
            # Generate and save report
            audit_trail.log_scan_completed("file_test", sample_security_report, 30.0)
            report = compliance_manager.generate_compliance_report(
                framework=ComplianceFramework.NIST_CSF, output_file=output_file
            )

            # Verify file was created
            assert output_file.exists()

            # Verify file content
            with open(output_file, "r") as f:
                saved_report = json.load(f)

            assert saved_report["report_metadata"]["framework"] == "nist_csf"
            assert "executive_summary" in saved_report

        finally:
            # Cleanup
            if output_file.exists():
                output_file.unlink()

    def test_overall_compliance_assessment(self, compliance_manager):
        """Test overall compliance status assessment."""
        # Mock audit report with different compliance scores
        mock_audit_report = {
            "compliance_metrics_history": [
                {"compliance_score": 98.0},  # Fully compliant
                {"compliance_score": 85.0},  # Substantially compliant
                {"compliance_score": 65.0},  # Partially compliant
                {"compliance_score": 45.0},  # Non-compliant
            ]
        }

        # Test different compliance levels
        assert (
            compliance_manager._assess_overall_compliance(mock_audit_report)
            == "fully_compliant"
        )

        mock_audit_report["compliance_metrics_history"] = [{"compliance_score": 85.0}]
        assert (
            compliance_manager._assess_overall_compliance(mock_audit_report)
            == "substantially_compliant"
        )

        mock_audit_report["compliance_metrics_history"] = [{"compliance_score": 65.0}]
        assert (
            compliance_manager._assess_overall_compliance(mock_audit_report)
            == "partially_compliant"
        )

        mock_audit_report["compliance_metrics_history"] = [{"compliance_score": 45.0}]
        assert (
            compliance_manager._assess_overall_compliance(mock_audit_report)
            == "non_compliant"
        )

        # Test unknown status with no metrics
        mock_audit_report["compliance_metrics_history"] = []
        assert (
            compliance_manager._assess_overall_compliance(mock_audit_report)
            == "unknown"
        )


if __name__ == "__main__":
    pytest.main([__file__])
