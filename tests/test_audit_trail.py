"""
Tests for security audit trail and compliance reporting functionality.

This module tests the comprehensive audit trail system including:
- Event logging and tracking
- Compliance metrics calculation
- Audit trail generation
- Database operations
"""

import json
import sqlite3
import tempfile
import os
import gc
import time
import platform
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from vet_core.security.assessor import RiskAssessment
from vet_core.security.audit_trail import (
    AuditEvent,
    AuditEventType,
    ComplianceMetrics,
    SecurityAuditTrail,
)
from vet_core.security.models import (
    RemediationAction,
    SecurityReport,
    Vulnerability,
    VulnerabilitySeverity,
)


class TestSecurityAuditTrail:
    """Test cases for SecurityAuditTrail class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path for testing."""
        # Create temporary file and get the path
        fd, temp_path = tempfile.mkstemp(suffix=".db")
        db_path = Path(temp_path)

        # Close the file descriptor immediately since we just need the path
        os.close(fd)

        yield db_path

        # Windows-safe cleanup
        try:
            # Force garbage collection to close any open handles
            gc.collect()

            # Additional cleanup for SQLite connections
            if hasattr(sqlite3, "sqlite_version_info"):
                # Force close any lingering SQLite connections
                sqlite3.sqlite_version_info

            if platform.system() == "Windows":
                # Retry logic for Windows file locking issues
                for attempt in range(10):  # Try up to 10 times
                    try:
                        if db_path.exists():
                            db_path.unlink()
                        break
                    except PermissionError:
                        if attempt < 9:  # Don't sleep on last attempt
                            time.sleep(0.2)  # Wait 200ms before retry
                        else:
                            # If all retries fail, log warning instead of raising
                            print(
                                f"Warning: Could not delete temporary database file {db_path}"
                            )
            else:
                # Unix systems - simple deletion
                if db_path.exists():
                    db_path.unlink()
        except (PermissionError, OSError) as e:
            # On Windows, sometimes files can't be deleted immediately
            # This is acceptable for temporary test files
            print(f"Warning: Could not clean up temporary database file {db_path}: {e}")

    @pytest.fixture
    def temp_log_path(self):
        """Create temporary log file path for testing."""
        # Create temporary file and get the path
        fd, temp_path = tempfile.mkstemp(suffix=".log")
        log_path = Path(temp_path)

        # Close the file descriptor immediately
        os.close(fd)

        yield log_path

        # Windows-safe cleanup
        try:
            # Force garbage collection to close any open handles
            gc.collect()

            if platform.system() == "Windows":
                # Retry logic for Windows file locking issues
                for attempt in range(10):
                    try:
                        if log_path.exists():
                            log_path.unlink()
                        break
                    except PermissionError:
                        if attempt < 9:
                            time.sleep(0.2)
                        else:
                            print(
                                f"Warning: Could not delete temporary log file {log_path}"
                            )
            else:
                if log_path.exists():
                    log_path.unlink()
        except (PermissionError, OSError) as e:
            print(f"Warning: Could not clean up temporary log file {log_path}: {e}")

    @pytest.fixture
    def audit_trail(self, temp_db_path, temp_log_path):
        """Create SecurityAuditTrail instance for testing."""
        trail = SecurityAuditTrail(
            audit_db_path=temp_db_path, log_file_path=temp_log_path, retention_days=30
        )

        yield trail

        # Explicit cleanup to ensure database connections are closed
        try:
            # Close any open database connections
            if hasattr(trail, "_db_connection"):
                trail._db_connection.close()

            # Force garbage collection
            gc.collect()
        except Exception as e:
            print(f"Warning during audit trail cleanup: {e}")

    @pytest.fixture
    def sample_vulnerability(self):
        """Create sample vulnerability for testing."""
        return Vulnerability(
            id="PYSEC-2024-48",
            package_name="black",
            installed_version="23.12.1",
            fix_versions=["24.3.0"],
            severity=VulnerabilitySeverity.MEDIUM,
            cvss_score=5.5,
            description="Code formatting vulnerability",
            published_date=datetime.now() - timedelta(days=5),
            discovered_date=datetime.now() - timedelta(hours=2),
        )

    @pytest.fixture
    def sample_security_report(self, sample_vulnerability):
        """Create sample security report for testing."""
        return SecurityReport(
            scan_date=datetime.now(),
            vulnerabilities=[sample_vulnerability],
            total_packages_scanned=100,
            scan_duration=45.2,
            scanner_version="pip-audit 2.6.1",
            scan_command="pip-audit --format=json",
        )

    def test_initialization(self, temp_db_path, temp_log_path):
        """Test SecurityAuditTrail initialization."""
        audit_trail = SecurityAuditTrail(
            audit_db_path=temp_db_path, log_file_path=temp_log_path
        )

        assert audit_trail.audit_db_path == temp_db_path
        assert audit_trail.log_file_path == temp_log_path
        assert audit_trail.retention_days == 365  # default

        # Check database was created
        assert temp_db_path.exists()

        # Check tables were created
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            assert "audit_events" in tables
            assert "compliance_metrics" in tables

    def test_log_event(self, audit_trail):
        """Test logging audit events."""
        event = AuditEvent(
            event_type=AuditEventType.VULNERABILITY_DETECTED,
            vulnerability_id="PYSEC-2024-48",
            package_name="black",
            severity=VulnerabilitySeverity.MEDIUM,
            action_taken="vulnerability_detected",
            outcome="pending_assessment",
            details={"test": "data"},
        )

        # Log the event
        audit_trail.log_event(event)

        # Verify event was stored in database
        with sqlite3.connect(audit_trail.audit_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM audit_events WHERE event_id = ?", (event.event_id,)
            )
            row = cursor.fetchone()

            assert row is not None
            assert row[1] == event.event_type.value
            assert row[3] == event.vulnerability_id
            assert row[4] == event.package_name

    def test_log_vulnerability_detected(self, audit_trail, sample_vulnerability):
        """Test logging vulnerability detection."""
        scan_id = "scan_123"

        audit_trail.log_vulnerability_detected(sample_vulnerability, scan_id)

        # Verify event was logged
        events = audit_trail.get_audit_events(
            event_type=AuditEventType.VULNERABILITY_DETECTED
        )

        assert len(events) == 1
        event = events[0]
        assert event.vulnerability_id == sample_vulnerability.id
        assert event.package_name == sample_vulnerability.package_name
        assert event.severity == sample_vulnerability.severity
        assert event.details["scan_id"] == scan_id

    def test_log_vulnerability_resolved(self, audit_trail):
        """Test logging vulnerability resolution."""
        vulnerability_id = "PYSEC-2024-48"
        package_name = "black"
        resolution_method = "package_upgrade"
        new_version = "24.3.0"

        audit_trail.log_vulnerability_resolved(
            vulnerability_id, package_name, resolution_method, new_version
        )

        # Verify event was logged
        events = audit_trail.get_audit_events(
            event_type=AuditEventType.VULNERABILITY_RESOLVED
        )

        assert len(events) == 1
        event = events[0]
        assert event.vulnerability_id == vulnerability_id
        assert event.package_name == package_name
        assert event.action_taken == resolution_method
        assert event.details["new_version"] == new_version

    def test_log_scan_lifecycle(self, audit_trail, sample_security_report):
        """Test logging complete scan lifecycle."""
        scan_id = "scan_456"
        scan_command = "pip-audit --format=json"
        duration = 45.2

        # Log scan initiation
        audit_trail.log_scan_initiated(scan_id, "pip-audit", scan_command)

        # Log scan completion
        audit_trail.log_scan_completed(scan_id, sample_security_report, duration)

        # Verify both events were logged
        events = audit_trail.get_audit_events()
        assert len(events) == 2

        # Check scan initiated event
        initiated_events = [
            e for e in events if e.event_type == AuditEventType.SCAN_INITIATED
        ]
        assert len(initiated_events) == 1
        assert initiated_events[0].details["scan_id"] == scan_id

        # Check scan completed event
        completed_events = [
            e for e in events if e.event_type == AuditEventType.SCAN_COMPLETED
        ]
        assert len(completed_events) == 1
        assert completed_events[0].details["scan_duration"] == duration

    def test_log_remediation_action(self, audit_trail):
        """Test logging remediation actions."""
        remediation = RemediationAction(
            vulnerability_id="PYSEC-2024-48",
            action_type="upgrade",
            target_version="24.3.0",
            status="completed",
            notes="Successfully upgraded package",
        )
        remediation.mark_started()
        remediation.mark_completed("Upgrade successful")

        audit_trail.log_remediation_action(
            remediation, AuditEventType.REMEDIATION_COMPLETED
        )

        # Verify event was logged
        events = audit_trail.get_audit_events(
            event_type=AuditEventType.REMEDIATION_COMPLETED
        )

        assert len(events) == 1
        event = events[0]
        assert event.vulnerability_id == remediation.vulnerability_id
        assert event.action_taken == remediation.action_type
        assert event.outcome == remediation.status

    def test_log_risk_assessment(self, audit_trail):
        """Test logging risk assessments."""
        vulnerability_id = "PYSEC-2024-48"
        assessment = Mock(spec=RiskAssessment)
        assessment.risk_score = 7.5
        assessment.priority_level = "urgent"
        assessment.recommended_timeline = timedelta(hours=72)
        assessment.confidence_score = 0.85
        assessment.remediation_complexity = "medium"
        assessment.business_impact = "high"
        assessment.impact_factors = {"severity": 0.8, "exposure": 0.6}

        audit_trail.log_risk_assessment(vulnerability_id, assessment)

        # Verify event was logged
        events = audit_trail.get_audit_events(
            event_type=AuditEventType.RISK_ASSESSMENT_PERFORMED
        )

        assert len(events) == 1
        event = events[0]
        assert event.vulnerability_id == vulnerability_id
        assert event.details["risk_score"] == 7.5
        assert event.details["priority_level"] == "urgent"

    def test_get_audit_events_filtering(self, audit_trail, sample_vulnerability):
        """Test filtering audit events by various criteria."""
        # Log multiple events
        audit_trail.log_vulnerability_detected(sample_vulnerability)
        audit_trail.log_vulnerability_resolved(
            sample_vulnerability.id, sample_vulnerability.package_name, "upgrade"
        )
        audit_trail.log_scan_initiated("scan_123")

        # Test filtering by event type
        vuln_events = audit_trail.get_audit_events(
            event_type=AuditEventType.VULNERABILITY_DETECTED
        )
        assert len(vuln_events) == 1

        # Test filtering by vulnerability ID
        vuln_specific_events = audit_trail.get_audit_events(
            vulnerability_id=sample_vulnerability.id
        )
        assert len(vuln_specific_events) == 2  # detected and resolved

        # Test filtering by date range
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_events = audit_trail.get_audit_events(start_date=one_hour_ago)
        assert len(recent_events) == 3  # All events are recent

        # Test limit
        limited_events = audit_trail.get_audit_events(limit=2)
        assert len(limited_events) == 2

    def test_get_vulnerability_timeline(self, audit_trail, sample_vulnerability):
        """Test getting complete vulnerability timeline."""
        # Log vulnerability lifecycle events
        audit_trail.log_vulnerability_detected(sample_vulnerability)
        audit_trail.log_vulnerability_resolved(
            sample_vulnerability.id, sample_vulnerability.package_name, "upgrade"
        )

        # Get timeline
        timeline = audit_trail.get_vulnerability_timeline(sample_vulnerability.id)

        assert len(timeline) == 2
        event_types = [event.event_type for event in timeline]
        assert AuditEventType.VULNERABILITY_DETECTED in event_types
        assert AuditEventType.VULNERABILITY_RESOLVED in event_types

    def test_calculate_compliance_metrics(self, audit_trail, sample_security_report):
        """Test compliance metrics calculation."""
        # Log some events to create history
        audit_trail.log_vulnerability_detected(
            sample_security_report.vulnerabilities[0]
        )
        audit_trail.log_scan_completed("scan_123", sample_security_report, 45.2)

        # Calculate metrics
        metrics = audit_trail.calculate_compliance_metrics(sample_security_report)

        assert isinstance(metrics, ComplianceMetrics)
        assert (
            metrics.total_vulnerabilities == sample_security_report.vulnerability_count
        )
        assert metrics.medium_vulnerabilities == sample_security_report.medium_count
        assert metrics.compliance_score >= 0.0
        assert metrics.compliance_score <= 100.0

        # Verify metrics were stored in database
        with sqlite3.connect(audit_trail.audit_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM compliance_metrics")
            count = cursor.fetchone()[0]
            assert count == 1

    def test_generate_compliance_report(self, audit_trail, sample_security_report):
        """Test compliance report generation."""
        # Log some events
        audit_trail.log_vulnerability_detected(
            sample_security_report.vulnerabilities[0]
        )
        audit_trail.log_scan_completed("scan_123", sample_security_report, 45.2)

        # Generate report
        report = audit_trail.generate_compliance_report()

        assert "report_metadata" in report
        assert "executive_summary" in report
        assert "event_summary" in report
        assert "vulnerability_lifecycle_analysis" in report
        assert "compliance_metrics_history" in report
        assert "audit_trail" in report

        # Check report metadata
        assert report["report_metadata"]["generator"] == "vet-core-security-audit-trail"
        assert "generated_at" in report["report_metadata"]

        # Check executive summary
        assert report["executive_summary"]["total_audit_events"] >= 2
        assert report["executive_summary"]["vulnerabilities_detected"] >= 1
        assert report["executive_summary"]["scans_completed"] >= 1

    def test_cleanup_old_events(self, audit_trail):
        """Test cleanup of old audit events."""
        # Create old event (simulate by directly inserting into database)
        old_date = datetime.now() - timedelta(days=400)  # Older than retention period
        old_event = AuditEvent(
            event_type=AuditEventType.VULNERABILITY_DETECTED,
            timestamp=old_date,
            vulnerability_id="OLD-VULN-123",
        )

        # Create recent event
        recent_event = AuditEvent(
            event_type=AuditEventType.VULNERABILITY_DETECTED,
            vulnerability_id="RECENT-VULN-456",
        )

        # Log both events
        audit_trail.log_event(old_event)
        audit_trail.log_event(recent_event)

        # Verify both events exist
        all_events = audit_trail.get_audit_events()
        assert len(all_events) == 2

        # Cleanup old events
        deleted_count = audit_trail.cleanup_old_events()

        # Verify old event was deleted
        assert deleted_count == 1
        remaining_events = audit_trail.get_audit_events()
        assert len(remaining_events) == 1
        assert remaining_events[0].vulnerability_id == "RECENT-VULN-456"

    def test_audit_event_serialization(self):
        """Test AuditEvent serialization and deserialization."""
        original_event = AuditEvent(
            event_type=AuditEventType.VULNERABILITY_DETECTED,
            vulnerability_id="PYSEC-2024-48",
            package_name="black",
            severity=VulnerabilitySeverity.HIGH,
            action_taken="detected",
            outcome="pending",
            details={"test": "data"},
            metadata={"source": "test"},
        )

        # Convert to dict
        event_dict = original_event.to_dict()

        # Verify dict structure
        assert event_dict["event_type"] == "vulnerability_detected"
        assert event_dict["severity"] == "high"
        assert "timestamp" in event_dict

        # Convert back to object
        restored_event = AuditEvent.from_dict(event_dict)

        # Verify restoration
        assert restored_event.event_type == original_event.event_type
        assert restored_event.vulnerability_id == original_event.vulnerability_id
        assert restored_event.severity == original_event.severity
        assert restored_event.details == original_event.details

    def test_compliance_metrics_serialization(self):
        """Test ComplianceMetrics serialization."""
        metrics = ComplianceMetrics(
            assessment_date=datetime.now(),
            total_vulnerabilities=5,
            critical_vulnerabilities=1,
            high_vulnerabilities=2,
            medium_vulnerabilities=2,
            low_vulnerabilities=0,
            unresolved_critical=1,
            unresolved_high=1,
            mean_time_to_detection=2.5,
            mean_time_to_remediation=24.0,
            compliance_score=85.5,
            policy_violations=2,
            overdue_remediations=1,
            scan_frequency_compliance=True,
        )

        # Convert to dict
        metrics_dict = metrics.to_dict()

        # Verify dict structure
        assert metrics_dict["total_vulnerabilities"] == 5
        assert metrics_dict["compliance_score"] == 85.5
        assert metrics_dict["scan_frequency_compliance"] is True
        assert "assessment_date" in metrics_dict

    def test_error_handling(self, audit_trail):
        """Test error handling in audit trail operations."""
        # Test with invalid database path
        invalid_audit_trail = SecurityAuditTrail(
            audit_db_path=Path("/invalid/path/audit.db")
        )

        # This should raise an exception during initialization
        with pytest.raises(Exception):
            invalid_audit_trail._init_database()

    def test_concurrent_access(self, audit_trail):
        """Test concurrent access to audit trail (basic test)."""
        import threading
        import time

        def log_events():
            for i in range(10):
                event = AuditEvent(
                    event_type=AuditEventType.VULNERABILITY_DETECTED,
                    vulnerability_id=f"VULN-{i}",
                    package_name=f"package-{i}",
                )
                audit_trail.log_event(event)
                time.sleep(0.01)  # Small delay

        # Start multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=log_events)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all events were logged
        events = audit_trail.get_audit_events()
        assert len(events) == 30  # 3 threads * 10 events each


if __name__ == "__main__":
    pytest.main([__file__])
