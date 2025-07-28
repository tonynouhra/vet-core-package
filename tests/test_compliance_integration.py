"""
Integration tests for compliance reporting and audit trail functionality.

This module tests the complete compliance reporting workflow including
audit trail generation, policy enforcement, and framework-specific
compliance reporting.

Requirements addressed:
- 4.1: Audit trail and compliance reporting functionality validation
- 4.2: Complete audit trail tracking and evidence generation
- 4.3: Compliance report generation with vulnerability management evidence
- 4.4: Evidence of proactive security management practices
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from vet_core.security.assessor import RiskAssessment, RiskAssessor
from vet_core.security.audit_trail import (
    AuditEvent,
    AuditEventType,
    ComplianceMetrics,
    SecurityAuditTrail,
)
from vet_core.security.compliance import (
    ComplianceFramework,
    ComplianceViolation,
    PolicyRule,
    SecurityComplianceManager,
)
from vet_core.security.models import (
    RemediationAction,
    SecurityReport,
    Vulnerability,
    VulnerabilitySeverity,
)
from vet_core.security.scanner import VulnerabilityScanner


class TestComplianceIntegration:
    """Integration tests for compliance reporting system."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            yield workspace

    @pytest.fixture
    def audit_trail_system(self, temp_workspace):
        """Create audit trail system for testing."""
        audit_db_path = temp_workspace / "compliance-audit.db"
        audit_log_path = temp_workspace / "compliance-audit.log"

        return SecurityAuditTrail(
            audit_db_path=audit_db_path,
            log_file_path=audit_log_path,
            retention_days=90,
        )

    @pytest.fixture
    def compliance_system(self, audit_trail_system):
        """Create complete compliance system for testing."""
        risk_assessor = RiskAssessor()
        compliance_manager = SecurityComplianceManager(
            audit_trail=audit_trail_system,
            risk_assessor=risk_assessor,
        )

        return {
            "audit_trail": audit_trail_system,
            "compliance_manager": compliance_manager,
            "risk_assessor": risk_assessor,
        }

    @pytest.fixture
    def sample_vulnerabilities(self):
        """Create sample vulnerabilities for testing."""
        return [
            Vulnerability(
                id="CRITICAL-001",
                package_name="critical-package",
                installed_version="1.0.0",
                fix_versions=["1.1.0"],
                severity=VulnerabilitySeverity.CRITICAL,
                cvss_score=9.5,
                description="Critical security vulnerability requiring immediate attention",
                published_date=datetime.now() - timedelta(days=2),
                discovered_date=datetime.now() - timedelta(hours=25),  # Over 24h old
            ),
            Vulnerability(
                id="HIGH-001",
                package_name="high-package",
                installed_version="2.0.0",
                fix_versions=["2.1.0", "2.2.0"],
                severity=VulnerabilitySeverity.HIGH,
                cvss_score=7.8,
                description="High severity vulnerability in authentication module",
                published_date=datetime.now() - timedelta(days=1),
                discovered_date=datetime.now() - timedelta(hours=80),  # Over 72h old
            ),
            Vulnerability(
                id="MEDIUM-001",
                package_name="medium-package",
                installed_version="3.0.0",
                fix_versions=["3.1.0"],
                severity=VulnerabilitySeverity.MEDIUM,
                cvss_score=5.5,
                description="Medium severity vulnerability in data processing",
                published_date=datetime.now() - timedelta(hours=12),
                discovered_date=datetime.now() - timedelta(hours=6),
            ),
        ]

    @pytest.fixture
    def sample_security_report(self, sample_vulnerabilities):
        """Create sample security report for testing."""
        return SecurityReport(
            scan_date=datetime.now(),
            vulnerabilities=sample_vulnerabilities,
            total_packages_scanned=150,
            scan_duration=67.3,
            scanner_version="pip-audit 2.6.1",
            scan_command="pip-audit --format=json --desc",
        )

    def test_complete_audit_trail_workflow(
        self, compliance_system, sample_security_report
    ):
        """Test complete audit trail workflow from scan to compliance."""
        audit_trail = compliance_system["audit_trail"]
        compliance_manager = compliance_system["compliance_manager"]

        # Phase 1: Log scan lifecycle
        scan_id = "compliance_test_scan_001"

        # Log scan initiation
        audit_trail.log_scan_initiated(scan_id, "pip-audit")

        # Log scan completion
        audit_trail.log_scan_completed(scan_id, sample_security_report, 67.3)

        # Phase 2: Log vulnerability detection
        for vulnerability in sample_security_report.vulnerabilities:
            audit_trail.log_vulnerability_detected(vulnerability, scan_id)

        # Phase 3: Log risk assessments
        risk_assessor = compliance_system["risk_assessor"]
        assessments = risk_assessor.assess_report(sample_security_report)

        for assessment in assessments:
            audit_trail.log_risk_assessment(assessment.vulnerability_id, assessment)

        # Phase 4: Check compliance and log violations
        violations, metrics = compliance_manager.check_compliance(
            sample_security_report
        )

        # Verify violations were found (critical and high vulns are overdue)
        assert len(violations) >= 2  # At least critical and high violations

        # Verify violation types
        violation_types = [v.violation_type for v in violations]
        assert "resolution_time_exceeded" in violation_types

        # Phase 5: Log remediation actions
        remediation_actions = []
        for vulnerability in sample_security_report.vulnerabilities:
            if vulnerability.is_fixable:
                remediation = RemediationAction(
                    vulnerability_id=vulnerability.id,
                    action_type="upgrade",
                    target_version=vulnerability.recommended_fix_version,
                    status="planned",
                    notes=f"Remediation for {vulnerability.severity.value} vulnerability",
                )
                remediation.mark_started()
                remediation_actions.append(remediation)

                audit_trail.log_remediation_action(
                    remediation, AuditEventType.REMEDIATION_STARTED
                )

        # Phase 6: Complete some remediations
        for i, remediation in enumerate(remediation_actions[:2]):  # Complete first 2
            remediation.mark_completed("Successfully upgraded package")
            audit_trail.log_remediation_action(
                remediation, AuditEventType.REMEDIATION_COMPLETED
            )

            # Log vulnerability resolution
            vulnerability = sample_security_report.vulnerabilities[i]
            audit_trail.log_vulnerability_resolved(
                vulnerability.id,
                vulnerability.package_name,
                "package_upgrade",
                remediation.target_version,
            )

        # Phase 7: Verify complete audit trail
        all_events = audit_trail.get_audit_events()

        # Verify all expected event types are present
        event_types = [event.event_type for event in all_events]
        expected_types = [
            AuditEventType.SCAN_INITIATED,
            AuditEventType.SCAN_COMPLETED,
            AuditEventType.VULNERABILITY_DETECTED,
            AuditEventType.RISK_ASSESSMENT_PERFORMED,
            AuditEventType.POLICY_VIOLATION,
            AuditEventType.REMEDIATION_STARTED,
            AuditEventType.REMEDIATION_COMPLETED,
            AuditEventType.VULNERABILITY_RESOLVED,
        ]

        for expected_type in expected_types:
            assert expected_type in event_types, f"Missing event type: {expected_type}"

        # Verify event counts
        assert (
            len(
                [
                    e
                    for e in all_events
                    if e.event_type == AuditEventType.VULNERABILITY_DETECTED
                ]
            )
            == 3
        )
        assert (
            len(
                [
                    e
                    for e in all_events
                    if e.event_type == AuditEventType.VULNERABILITY_RESOLVED
                ]
            )
            == 2
        )

        # Phase 8: Generate compliance metrics
        final_metrics = audit_trail.calculate_compliance_metrics(sample_security_report)

        # Verify metrics
        assert final_metrics.total_vulnerabilities == 3
        assert final_metrics.critical_vulnerabilities == 1
        assert final_metrics.high_vulnerabilities == 1
        assert final_metrics.medium_vulnerabilities == 1
        assert final_metrics.policy_violations >= 2
        assert 0 <= final_metrics.compliance_score <= 100

    def test_nist_csf_compliance_reporting(
        self, compliance_system, sample_security_report, temp_workspace
    ):
        """Test NIST Cybersecurity Framework compliance reporting."""
        audit_trail = compliance_system["audit_trail"]
        compliance_manager = compliance_system["compliance_manager"]

        # Create audit history
        self._create_audit_history(audit_trail, sample_security_report)

        # Generate NIST CSF compliance report
        output_file = temp_workspace / "nist-csf-compliance.json"
        nist_report = compliance_manager.generate_compliance_report(
            framework=ComplianceFramework.NIST_CSF,
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            output_file=output_file,
        )

        # Verify report structure
        assert "report_metadata" in nist_report
        assert "executive_summary" in nist_report
        assert "framework_requirements" in nist_report
        assert "policy_compliance" in nist_report
        assert "evidence_documentation" in nist_report
        assert "recommendations" in nist_report

        # Verify NIST CSF specific content
        framework_content = nist_report["framework_requirements"]
        assert framework_content["framework"] == "NIST Cybersecurity Framework"
        assert "functions" in framework_content

        # Verify all 5 NIST functions are covered
        functions = framework_content["functions"]
        expected_functions = ["identify", "protect", "detect", "respond", "recover"]
        for function in expected_functions:
            assert function in functions
            assert "description" in functions[function]
            assert "evidence" in functions[function]
            assert "compliance_status" in functions[function]

        # Verify executive summary
        exec_summary = nist_report["executive_summary"]
        assert "compliance_overview" in exec_summary
        assert "security_posture" in exec_summary
        assert "operational_metrics" in exec_summary

        # Verify evidence documentation
        evidence = nist_report["evidence_documentation"]
        assert "audit_trail_evidence" in evidence
        assert "vulnerability_management_evidence" in evidence
        assert "documentation_evidence" in evidence

        # Verify file was created
        assert output_file.exists()

        # Verify file content matches report
        with open(output_file) as f:
            file_content = json.load(f)
        assert file_content["report_metadata"]["framework"] == "nist_csf"

    def test_iso27001_compliance_reporting(
        self, compliance_system, sample_security_report, temp_workspace
    ):
        """Test ISO 27001 compliance reporting."""
        audit_trail = compliance_system["audit_trail"]
        compliance_manager = compliance_system["compliance_manager"]

        # Create audit history
        self._create_audit_history(audit_trail, sample_security_report)

        # Generate ISO 27001 compliance report
        output_file = temp_workspace / "iso27001-compliance.json"
        iso_report = compliance_manager.generate_compliance_report(
            framework=ComplianceFramework.ISO_27001,
            output_file=output_file,
        )

        # Verify ISO 27001 specific content
        framework_content = iso_report["framework_requirements"]
        assert framework_content["framework"] == "ISO 27001:2013"
        assert "controls" in framework_content

        # Verify specific ISO controls
        controls = framework_content["controls"]
        expected_controls = [
            "A.12.6.1",
            "A.16.1.3",
        ]  # Technical vulnerabilities, reporting

        for control in expected_controls:
            assert control in controls
            assert "title" in controls[control]
            assert "description" in controls[control]
            assert "evidence" in controls[control]
            assert "compliance_status" in controls[control]

        # Verify A.12.6.1 (Management of technical vulnerabilities)
        vuln_control = controls["A.12.6.1"]
        assert "technical vulnerabilities" in vuln_control["title"].lower()
        assert vuln_control["compliance_status"] == "implemented"

        # Verify file was created
        assert output_file.exists()

    def test_soc2_compliance_reporting(
        self, compliance_system, sample_security_report, temp_workspace
    ):
        """Test SOC 2 compliance reporting."""
        audit_trail = compliance_system["audit_trail"]
        compliance_manager = compliance_system["compliance_manager"]

        # Create audit history
        self._create_audit_history(audit_trail, sample_security_report)

        # Generate SOC 2 compliance report
        output_file = temp_workspace / "soc2-compliance.json"
        soc2_report = compliance_manager.generate_compliance_report(
            framework=ComplianceFramework.SOC2,
            output_file=output_file,
        )

        # Verify SOC 2 specific content
        framework_content = soc2_report["framework_requirements"]
        assert framework_content["framework"] == "SOC 2 Type II"
        assert "trust_criteria" in framework_content

        # Verify trust criteria
        trust_criteria = framework_content["trust_criteria"]
        expected_criteria = ["security", "availability"]

        for criterion in expected_criteria:
            assert criterion in trust_criteria
            assert "description" in trust_criteria[criterion]
            assert "controls" in trust_criteria[criterion]
            assert "evidence" in trust_criteria[criterion]
            assert "compliance_status" in trust_criteria[criterion]

        # Verify security criterion
        security = trust_criteria["security"]
        assert "protected against unauthorized access" in security["description"]
        assert security["compliance_status"] == "effective"

        # Verify file was created
        assert output_file.exists()

    def test_policy_violation_detection_and_tracking(
        self, compliance_system, sample_security_report
    ):
        """Test policy violation detection and tracking."""
        audit_trail = compliance_system["audit_trail"]
        compliance_manager = compliance_system["compliance_manager"]

        # Log vulnerabilities with different ages
        for vulnerability in sample_security_report.vulnerabilities:
            audit_trail.log_vulnerability_detected(vulnerability)

        # Check compliance (should detect violations)
        violations, metrics = compliance_manager.check_compliance(
            sample_security_report
        )

        # Verify violations were detected
        assert len(violations) > 0

        # Verify critical vulnerability violation
        critical_violations = [
            v
            for v in violations
            if v.vulnerability_id == "CRITICAL-001"
            and v.violation_type == "resolution_time_exceeded"
        ]
        assert len(critical_violations) == 1

        critical_violation = critical_violations[0]
        assert critical_violation.rule_id == "CRITICAL_24H"
        assert "exceeded 24h resolution time limit" in critical_violation.description

        # Verify high vulnerability violation
        high_violations = [
            v
            for v in violations
            if v.vulnerability_id == "HIGH-001"
            and v.violation_type == "resolution_time_exceeded"
        ]
        assert len(high_violations) == 1

        high_violation = high_violations[0]
        assert high_violation.rule_id == "HIGH_72H"
        assert "exceeded 72h resolution time limit" in high_violation.description

        # Verify medium vulnerability should not violate (within 7 days)
        medium_violations = [
            v for v in violations if v.vulnerability_id == "MEDIUM-001"
        ]
        assert len(medium_violations) == 0  # Should be within time limit

        # Verify policy violations were logged in audit trail
        violation_events = audit_trail.get_audit_events(
            event_type=AuditEventType.POLICY_VIOLATION
        )
        assert len(violation_events) >= 2

    def test_compliance_metrics_calculation(
        self, compliance_system, sample_security_report
    ):
        """Test comprehensive compliance metrics calculation."""
        audit_trail = compliance_system["audit_trail"]
        compliance_manager = compliance_system["compliance_manager"]

        # Create comprehensive audit history
        self._create_comprehensive_audit_history(audit_trail, sample_security_report)

        # Run compliance check to generate policy violations
        violations, _ = compliance_manager.check_compliance(sample_security_report)

        # Calculate compliance metrics after violations are logged
        metrics = audit_trail.calculate_compliance_metrics(sample_security_report)

        # Verify basic metrics
        assert metrics.total_vulnerabilities == 3
        assert metrics.critical_vulnerabilities == 1
        assert metrics.high_vulnerabilities == 1
        assert metrics.medium_vulnerabilities == 1
        assert metrics.low_vulnerabilities == 0

        # Verify compliance score calculation
        assert 0 <= metrics.compliance_score <= 100

        # With critical and high vulnerabilities, score should be reduced
        assert metrics.compliance_score < 100

        # Verify policy violations
        assert metrics.policy_violations >= 2

        # Verify overdue remediations
        assert metrics.overdue_remediations >= 2  # Critical and high are overdue

        # Verify scan frequency compliance
        # Should be True if we have recent scans
        assert isinstance(metrics.scan_frequency_compliance, bool)

    def test_vulnerability_lifecycle_tracking(
        self, compliance_system, sample_security_report
    ):
        """Test complete vulnerability lifecycle tracking."""
        audit_trail = compliance_system["audit_trail"]

        # Track lifecycle for critical vulnerability
        critical_vuln = sample_security_report.vulnerabilities[0]  # CRITICAL-001

        # Phase 1: Detection
        audit_trail.log_vulnerability_detected(critical_vuln, "scan_001")

        # Phase 2: Risk Assessment
        mock_assessment = Mock(spec=RiskAssessment)
        mock_assessment.risk_score = 9.2
        mock_assessment.priority_level = "immediate"
        mock_assessment.recommended_timeline = timedelta(hours=24)
        mock_assessment.confidence_score = 0.95
        mock_assessment.remediation_complexity = "low"
        mock_assessment.business_impact = "critical"
        mock_assessment.impact_factors = {"severity": 0.95, "exposure": 0.8}

        audit_trail.log_risk_assessment(critical_vuln.id, mock_assessment)

        # Phase 3: Remediation Planning
        remediation = RemediationAction(
            vulnerability_id=critical_vuln.id,
            action_type="upgrade",
            target_version="1.1.0",
            status="planned",
            notes="Critical vulnerability requires immediate upgrade",
        )

        # Phase 4: Remediation Execution
        remediation.mark_started()
        audit_trail.log_remediation_action(
            remediation, AuditEventType.REMEDIATION_STARTED
        )

        # Simulate some time passing
        import time

        time.sleep(0.1)

        remediation.mark_completed("Package successfully upgraded to 1.1.0")
        audit_trail.log_remediation_action(
            remediation, AuditEventType.REMEDIATION_COMPLETED
        )

        # Phase 5: Resolution
        audit_trail.log_vulnerability_resolved(
            critical_vuln.id,
            critical_vuln.package_name,
            "package_upgrade",
            "1.1.0",
        )

        # Verify complete timeline
        timeline = audit_trail.get_vulnerability_timeline(critical_vuln.id)

        # Verify timeline completeness
        timeline_types = [event.event_type for event in timeline]
        expected_timeline = [
            AuditEventType.VULNERABILITY_DETECTED,
            AuditEventType.RISK_ASSESSMENT_PERFORMED,
            AuditEventType.REMEDIATION_STARTED,
            AuditEventType.REMEDIATION_COMPLETED,
            AuditEventType.VULNERABILITY_RESOLVED,
        ]

        for expected_event in expected_timeline:
            assert expected_event in timeline_types

        # Verify chronological order
        timeline.sort(key=lambda e: e.timestamp)
        assert timeline[0].event_type == AuditEventType.VULNERABILITY_DETECTED
        assert timeline[-1].event_type == AuditEventType.VULNERABILITY_RESOLVED

        # Verify event details
        detection_event = next(
            e for e in timeline if e.event_type == AuditEventType.VULNERABILITY_DETECTED
        )
        assert detection_event.vulnerability_id == critical_vuln.id
        assert detection_event.package_name == critical_vuln.package_name

        resolution_event = next(
            e for e in timeline if e.event_type == AuditEventType.VULNERABILITY_RESOLVED
        )
        assert resolution_event.vulnerability_id == critical_vuln.id
        assert resolution_event.details["new_version"] == "1.1.0"

    def test_comprehensive_compliance_report_generation(
        self, compliance_system, sample_security_report, temp_workspace
    ):
        """Test comprehensive compliance report generation."""
        audit_trail = compliance_system["audit_trail"]

        # Create rich audit history
        self._create_comprehensive_audit_history(audit_trail, sample_security_report)

        # Generate comprehensive audit report
        audit_report = audit_trail.generate_compliance_report(
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
        )

        # Verify report structure
        assert "report_metadata" in audit_report
        assert "executive_summary" in audit_report
        assert "event_summary" in audit_report
        assert "vulnerability_lifecycle_analysis" in audit_report
        assert "compliance_metrics_history" in audit_report
        assert "audit_trail" in audit_report

        # Verify report metadata
        metadata = audit_report["report_metadata"]
        assert metadata["generator"] == "vet-core-security-audit-trail"
        assert "generated_at" in metadata
        assert "report_period" in metadata

        # Verify executive summary
        exec_summary = audit_report["executive_summary"]
        assert exec_summary["total_audit_events"] > 0
        assert exec_summary["vulnerabilities_detected"] >= 3
        assert exec_summary["vulnerabilities_resolved"] >= 0

        # Verify event summary
        event_summary = audit_report["event_summary"]
        assert AuditEventType.VULNERABILITY_DETECTED.value in event_summary
        assert AuditEventType.SCAN_COMPLETED.value in event_summary

        # Verify vulnerability lifecycle analysis
        lifecycle = audit_report["vulnerability_lifecycle_analysis"]
        assert "total_vulnerabilities_tracked" in lifecycle
        assert lifecycle["total_vulnerabilities_tracked"] >= 3

    def _create_audit_history(self, audit_trail, security_report):
        """Create basic audit history for testing."""
        # Log scan
        scan_id = "test_scan_001"
        audit_trail.log_scan_initiated(scan_id, "pip-audit")
        audit_trail.log_scan_completed(scan_id, security_report, 45.2)

        # Log vulnerabilities
        for vulnerability in security_report.vulnerabilities:
            audit_trail.log_vulnerability_detected(vulnerability, scan_id)

    def _create_comprehensive_audit_history(self, audit_trail, security_report):
        """Create comprehensive audit history for testing."""
        # Basic history
        self._create_audit_history(audit_trail, security_report)

        # Add risk assessments
        for vulnerability in security_report.vulnerabilities:
            mock_assessment = Mock(spec=RiskAssessment)
            mock_assessment.risk_score = 7.5
            mock_assessment.priority_level = "urgent"
            mock_assessment.recommended_timeline = timedelta(hours=72)
            mock_assessment.confidence_score = 0.8
            mock_assessment.remediation_complexity = "medium"
            mock_assessment.business_impact = "high"
            mock_assessment.impact_factors = {"severity": 0.7, "exposure": 0.6}

            audit_trail.log_risk_assessment(vulnerability.id, mock_assessment)

        # Add some remediation actions
        for i, vulnerability in enumerate(security_report.vulnerabilities[:2]):
            remediation = RemediationAction(
                vulnerability_id=vulnerability.id,
                action_type="upgrade",
                target_version=vulnerability.recommended_fix_version,
                status="completed",
                notes=f"Remediation for {vulnerability.package_name}",
            )
            remediation.mark_started()
            remediation.mark_completed("Successfully resolved")

            audit_trail.log_remediation_action(
                remediation, AuditEventType.REMEDIATION_STARTED
            )
            audit_trail.log_remediation_action(
                remediation, AuditEventType.REMEDIATION_COMPLETED
            )

            audit_trail.log_vulnerability_resolved(
                vulnerability.id,
                vulnerability.package_name,
                "package_upgrade",
                vulnerability.recommended_fix_version,
            )

        # Add compliance check
        audit_trail.log_compliance_check(
            ComplianceMetrics(
                assessment_date=datetime.now(),
                total_vulnerabilities=3,
                critical_vulnerabilities=1,
                high_vulnerabilities=1,
                medium_vulnerabilities=1,
                low_vulnerabilities=0,
                unresolved_critical=0,
                unresolved_high=0,
                compliance_score=85.5,
                policy_violations=1,
                overdue_remediations=0,
                scan_frequency_compliance=True,
            )
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
