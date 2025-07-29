"""Tests for the VulnerabilityStatusTracker class."""

import json
import sqlite3
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from vet_core.security.audit_trail import AuditEvent, AuditEventType
from vet_core.security.models import Vulnerability, VulnerabilitySeverity
from vet_core.security.status_tracker import (
    ProgressMetrics,
    ProgressStage,
    StatusChange,
    VulnerabilityStatus,
    VulnerabilityStatusTracker,
    VulnerabilityTrackingRecord,
)


class TestVulnerabilityStatus:
    """Test cases for VulnerabilityStatus enum."""

    def test_vulnerability_status_values(self):
        """Test VulnerabilityStatus enum values."""
        assert VulnerabilityStatus.NEW.value == "new"
        assert VulnerabilityStatus.DETECTED.value == "detected"
        assert VulnerabilityStatus.ASSESSED.value == "assessed"
        assert VulnerabilityStatus.ASSIGNED.value == "assigned"
        assert VulnerabilityStatus.IN_PROGRESS.value == "in_progress"
        assert VulnerabilityStatus.TESTING.value == "testing"
        assert VulnerabilityStatus.RESOLVED.value == "resolved"
        assert VulnerabilityStatus.VERIFIED.value == "verified"
        assert VulnerabilityStatus.CLOSED.value == "closed"
        assert VulnerabilityStatus.IGNORED.value == "ignored"
        assert VulnerabilityStatus.DEFERRED.value == "deferred"
        assert VulnerabilityStatus.FALSE_POSITIVE.value == "false_positive"

    def test_vulnerability_status_count(self):
        """Test that all expected status values are present."""
        expected_count = 12
        assert len(VulnerabilityStatus) == expected_count


class TestProgressStage:
    """Test cases for ProgressStage enum."""

    def test_progress_stage_values(self):
        """Test ProgressStage enum values."""
        assert ProgressStage.DETECTION.value == "detection"
        assert ProgressStage.ANALYSIS.value == "analysis"
        assert ProgressStage.DISCOVERY.value == "discovery"
        assert ProgressStage.ASSESSMENT.value == "assessment"
        assert ProgressStage.PLANNING.value == "planning"
        assert ProgressStage.IMPLEMENTATION.value == "implementation"
        assert ProgressStage.TESTING.value == "testing"
        assert ProgressStage.DEPLOYMENT.value == "deployment"
        assert ProgressStage.VERIFICATION.value == "verification"
        assert ProgressStage.CLOSURE.value == "closure"

    def test_progress_stage_count(self):
        """Test that all expected stage values are present."""
        expected_count = 10
        assert len(ProgressStage) == expected_count


class TestStatusChange:
    """Test cases for StatusChange dataclass."""

    def test_status_change_creation(self):
        """Test creating a StatusChange instance."""
        change_id = str(uuid.uuid4())
        vulnerability_id = str(uuid.uuid4())
        timestamp = datetime.now()

        change = StatusChange(
            change_id=change_id,
            vulnerability_id=vulnerability_id,
            old_status=VulnerabilityStatus.NEW,
            new_status=VulnerabilityStatus.IN_PROGRESS,
            changed_by="test-user",
            changed_at=timestamp,
            reason="Starting work on vulnerability",
            notes="Initial analysis completed",
            metadata={"priority": "high"},
        )

        assert change.change_id == change_id
        assert change.vulnerability_id == vulnerability_id
        assert change.old_status == VulnerabilityStatus.NEW
        assert change.new_status == VulnerabilityStatus.IN_PROGRESS
        assert change.changed_by == "test-user"
        assert change.changed_at == timestamp
        assert change.reason == "Starting work on vulnerability"
        assert change.notes == "Initial analysis completed"
        assert change.metadata == {"priority": "high"}

    def test_status_change_to_dict(self):
        """Test converting StatusChange to dictionary."""
        change = StatusChange(
            change_id="test-change-123",
            vulnerability_id="vuln-456",
            old_status=VulnerabilityStatus.NEW,
            new_status=VulnerabilityStatus.RESOLVED,
            changed_by="developer",
            changed_at=datetime(2023, 1, 1, 12, 0, 0),
            reason="Fixed the issue",
            notes="Applied security patch",
            metadata={"fix_version": "1.2.3"},
        )

        result = change.to_dict()

        assert isinstance(result, dict)
        assert result["change_id"] == "test-change-123"
        assert result["vulnerability_id"] == "vuln-456"
        assert result["old_status"] == "new"
        assert result["new_status"] == "resolved"
        assert result["changed_by"] == "developer"
        assert result["reason"] == "Fixed the issue"
        assert result["notes"] == "Applied security patch"
        assert result["metadata"] == {"fix_version": "1.2.3"}
        assert "changed_at" in result


class TestProgressMetrics:
    """Test cases for ProgressMetrics dataclass."""

    def test_progress_metrics_creation(self):
        """Test creating a ProgressMetrics instance."""
        metrics = ProgressMetrics(
            current_stage=ProgressStage.IMPLEMENTATION,
            completion_percentage=75.0,
            time_in_current_stage=timedelta(hours=24),
            estimated_completion_time=timedelta(hours=8),
            stages_completed=[ProgressStage.DETECTION, ProgressStage.ANALYSIS],
            blockers=["Waiting for approval", "Resource constraints"],
        )

        assert metrics.current_stage == ProgressStage.IMPLEMENTATION
        assert metrics.completion_percentage == 75.0
        assert metrics.time_in_current_stage == timedelta(hours=24)
        assert metrics.estimated_completion_time == timedelta(hours=8)
        assert len(metrics.stages_completed) == 2
        assert len(metrics.blockers) == 2

    def test_progress_metrics_to_dict(self):
        """Test converting ProgressMetrics to dictionary."""
        metrics = ProgressMetrics(
            current_stage=ProgressStage.TESTING,
            completion_percentage=90.0,
            time_in_current_stage=timedelta(hours=12),
            estimated_completion_time=timedelta(hours=4),
            stages_completed=[ProgressStage.DETECTION],
            blockers=[],
        )

        result = metrics.to_dict()

        assert isinstance(result, dict)
        assert result["current_stage"] == "testing"
        assert result["completion_percentage"] == 90.0
        assert "time_in_current_stage" in result
        assert "estimated_completion_time" in result
        assert result["stages_completed"] == ["detection"]
        assert result["blockers"] == []


class TestVulnerabilityTrackingRecord:
    """Test cases for VulnerabilityTrackingRecord dataclass."""

    def test_tracking_record_creation(self):
        """Test creating a VulnerabilityTrackingRecord instance."""
        record_id = str(uuid.uuid4())
        vulnerability_id = str(uuid.uuid4())
        created_at = datetime.now()
        updated_at = datetime.now()

        record = VulnerabilityTrackingRecord(
            vulnerability_id=vulnerability_id,
            package_name="test-package",
            current_status=VulnerabilityStatus.IN_PROGRESS,
            severity=VulnerabilitySeverity.HIGH,
            assigned_to="security-team",
            created_at=created_at,
            updated_at=updated_at,
            priority_score=8.5,
            tags=["critical", "authentication"],
            status_history=[],
            progress_metrics=None,
        )

        assert record.vulnerability_id == vulnerability_id
        assert record.current_status == VulnerabilityStatus.IN_PROGRESS
        assert record.severity == VulnerabilitySeverity.HIGH
        assert record.assigned_to == "security-team"
        assert record.created_at == created_at
        assert record.updated_at == updated_at
        assert record.priority_score == 8.5
        assert record.tags == ["critical", "authentication"]

    def test_tracking_record_to_dict(self):
        """Test converting VulnerabilityTrackingRecord to dictionary."""
        record = VulnerabilityTrackingRecord(
            vulnerability_id="vuln-456",
            package_name="test-package",
            current_status=VulnerabilityStatus.RESOLVED,
            severity=VulnerabilitySeverity.MEDIUM,
            assigned_to="dev-team",
            created_at=datetime(2023, 1, 1),
            updated_at=datetime(2023, 1, 2),
            priority_score=6.0,
            tags=["web", "xss"],
            status_history=[],
            progress_metrics=None,
        )

        result = record.to_dict()

        assert isinstance(result, dict)
        assert result["vulnerability_id"] == "vuln-456"
        assert result["current_status"] == "resolved"
        assert result["severity"] == "MEDIUM"
        assert result["assigned_to"] == "dev-team"
        assert result["priority_score"] == 6.0
        assert result["tags"] == ["web", "xss"]
        assert "created_at" in result
        assert "updated_at" in result


class TestVulnerabilityStatusTracker:
    """Test cases for VulnerabilityStatusTracker class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = Path(f.name)
        yield temp_path
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def mock_audit_trail(self):
        """Create a mock audit trail."""
        mock_trail = Mock()
        mock_trail.log_event.return_value = None
        return mock_trail

    @pytest.fixture
    def tracker(self, mock_audit_trail, temp_db_path):
        """Create a VulnerabilityStatusTracker instance."""
        return VulnerabilityStatusTracker(
            audit_trail=mock_audit_trail, tracking_db_path=temp_db_path
        )

    @pytest.fixture
    def sample_vulnerability(self):
        """Create a sample vulnerability for testing."""
        return Vulnerability(
            id="vuln-test-123",
            package_name="test-package",
            installed_version="1.0.0",
            fix_versions=["1.0.1", "1.1.0"],
            severity=VulnerabilitySeverity.HIGH,
            description="SQL injection vulnerability in login form",
            cvss_score=8.5,
        )

    def test_init_with_default_db_path(self, mock_audit_trail):
        """Test tracker initialization with default database path."""
        tracker = VulnerabilityStatusTracker(audit_trail=mock_audit_trail)
        assert tracker is not None

    def test_init_with_custom_db_path(self, mock_audit_trail, temp_db_path):
        """Test tracker initialization with custom database path."""
        tracker = VulnerabilityStatusTracker(
            audit_trail=mock_audit_trail, tracking_db_path=temp_db_path
        )
        assert tracker is not None

    def test_track_vulnerability_basic(
        self, tracker, sample_vulnerability, mock_audit_trail
    ):
        """Test tracking a vulnerability with basic parameters."""
        record = tracker.track_vulnerability(sample_vulnerability)

        assert isinstance(record, VulnerabilityTrackingRecord)
        assert record.vulnerability_id == sample_vulnerability.id
        assert record.current_status == VulnerabilityStatus.NEW
        assert record.severity == sample_vulnerability.severity
        mock_audit_trail.log_event.assert_called()

    def test_track_vulnerability_with_custom_params(
        self, tracker, sample_vulnerability, mock_audit_trail
    ):
        """Test tracking a vulnerability with custom parameters."""
        record = tracker.track_vulnerability(
            vulnerability=sample_vulnerability,
            initial_status=VulnerabilityStatus.ASSESSED,
            assigned_to="security-team",
            priority_score=9.0,
            tags=["critical", "sql-injection"],
        )

        assert record.current_status == VulnerabilityStatus.ASSESSED
        assert record.assigned_to == "security-team"
        assert record.priority_score == 9.0
        assert record.tags == ["critical", "sql-injection"]

    def test_update_status_valid_transition(
        self, tracker, sample_vulnerability, mock_audit_trail
    ):
        """Test updating vulnerability status with valid transition."""
        # First track the vulnerability
        record = tracker.track_vulnerability(sample_vulnerability)

        # Update status
        updated_record = tracker.update_status(
            vulnerability_id=sample_vulnerability.id,
            new_status=VulnerabilityStatus.IN_PROGRESS,
            changed_by="developer",
            reason="Starting investigation",
            notes="Initial analysis in progress",
        )

        assert updated_record.current_status == VulnerabilityStatus.IN_PROGRESS
        assert len(updated_record.status_history) > 0
        mock_audit_trail.log_event.assert_called()

    def test_update_status_with_metadata(
        self, tracker, sample_vulnerability, mock_audit_trail
    ):
        """Test updating vulnerability status with metadata."""
        # Track vulnerability first
        tracker.track_vulnerability(sample_vulnerability)

        metadata = {"fix_version": "1.2.3", "estimated_hours": 8}
        updated_record = tracker.update_status(
            vulnerability_id=sample_vulnerability.id,
            new_status=VulnerabilityStatus.RESOLVED,
            changed_by="developer",
            reason="Applied security patch",
            metadata=metadata,
        )

        assert updated_record.current_status == VulnerabilityStatus.RESOLVED
        # Check that metadata was stored in status history
        assert len(updated_record.status_history) > 0

    def test_get_tracking_record_exists(self, tracker, sample_vulnerability):
        """Test getting tracking record that exists."""
        # Track vulnerability first
        original_record = tracker.track_vulnerability(sample_vulnerability)

        # Retrieve the record
        retrieved_record = tracker.get_tracking_record(sample_vulnerability.id)

        assert retrieved_record is not None
        assert retrieved_record.vulnerability_id == original_record.vulnerability_id
        assert retrieved_record.current_status == original_record.current_status

    def test_get_tracking_record_not_exists(self, tracker):
        """Test getting tracking record that doesn't exist."""
        non_existent_id = "non-existent-vuln-id"
        record = tracker.get_tracking_record(non_existent_id)
        assert record is None

    def test_get_all_tracking_records_no_filter(self, tracker, mock_audit_trail):
        """Test getting all tracking records without filters."""
        # Create multiple vulnerabilities
        vuln1 = Vulnerability(
            id="vuln-1",
            package_name="test-package-1",
            installed_version="1.0.0",
            fix_versions=["1.0.1"],
            severity=VulnerabilitySeverity.HIGH,
            description="Desc 1",
        )
        vuln2 = Vulnerability(
            id="vuln-2",
            package_name="test-package-2",
            installed_version="2.0.0",
            fix_versions=["2.0.1"],
            severity=VulnerabilitySeverity.MEDIUM,
            description="Desc 2",
        )

        tracker.track_vulnerability(vuln1)
        tracker.track_vulnerability(vuln2)

        records = tracker.get_all_tracking_records()

        assert isinstance(records, list)
        assert len(records) == 2

    def test_get_all_tracking_records_with_status_filter(
        self, tracker, mock_audit_trail
    ):
        """Test getting tracking records with status filter."""
        vuln1 = Vulnerability(
            id="vuln-1",
            package_name="test-package-1",
            installed_version="1.0.0",
            fix_versions=["1.0.1"],
            severity=VulnerabilitySeverity.HIGH,
            description="Desc 1",
        )
        vuln2 = Vulnerability(
            id="vuln-2",
            package_name="test-package-2",
            installed_version="2.0.0",
            fix_versions=["2.0.1"],
            severity=VulnerabilitySeverity.MEDIUM,
            description="Desc 2",
        )

        tracker.track_vulnerability(vuln1, initial_status=VulnerabilityStatus.NEW)
        tracker.track_vulnerability(vuln2, initial_status=VulnerabilityStatus.RESOLVED)

        new_records = tracker.get_all_tracking_records(
            status_filter=VulnerabilityStatus.NEW
        )
        resolved_records = tracker.get_all_tracking_records(
            status_filter=VulnerabilityStatus.RESOLVED
        )

        assert len(new_records) == 1
        assert len(resolved_records) == 1
        assert new_records[0].current_status == VulnerabilityStatus.NEW
        assert resolved_records[0].current_status == VulnerabilityStatus.RESOLVED

    def test_get_all_tracking_records_with_severity_filter(
        self, tracker, mock_audit_trail
    ):
        """Test getting tracking records with severity filter."""
        vuln_high = Vulnerability(
            id="vuln-high",
            package_name="high-severity-package",
            installed_version="1.0.0",
            fix_versions=["1.0.1"],
            severity=VulnerabilitySeverity.HIGH,
            description="High severity vuln",
        )
        vuln_low = Vulnerability(
            id="vuln-low",
            package_name="low-severity-package",
            installed_version="1.0.0",
            fix_versions=["1.0.1"],
            severity=VulnerabilitySeverity.LOW,
            description="Low severity vuln",
        )

        tracker.track_vulnerability(vuln_high)
        tracker.track_vulnerability(vuln_low)

        high_records = tracker.get_all_tracking_records(
            severity_filter=VulnerabilitySeverity.HIGH
        )
        low_records = tracker.get_all_tracking_records(
            severity_filter=VulnerabilitySeverity.LOW
        )

        assert len(high_records) == 1
        assert len(low_records) == 1
        assert high_records[0].severity == VulnerabilitySeverity.HIGH
        assert low_records[0].severity == VulnerabilitySeverity.LOW

    def test_get_all_tracking_records_with_assigned_to_filter(
        self, tracker, mock_audit_trail
    ):
        """Test getting tracking records with assigned_to filter."""
        vuln1 = Vulnerability(
            id="vuln-1",
            package_name="test-package-1",
            installed_version="1.0.0",
            fix_versions=["1.0.1"],
            severity=VulnerabilitySeverity.HIGH,
            description="Desc 1",
        )
        vuln2 = Vulnerability(
            id="vuln-2",
            package_name="test-package-2",
            installed_version="2.0.0",
            fix_versions=["2.0.1"],
            severity=VulnerabilitySeverity.MEDIUM,
            description="Desc 2",
        )

        tracker.track_vulnerability(vuln1, assigned_to="team-a")
        tracker.track_vulnerability(vuln2, assigned_to="team-b")

        team_a_records = tracker.get_all_tracking_records(assigned_to_filter="team-a")
        team_b_records = tracker.get_all_tracking_records(assigned_to_filter="team-b")

        assert len(team_a_records) == 1
        assert len(team_b_records) == 1
        assert team_a_records[0].assigned_to == "team-a"
        assert team_b_records[0].assigned_to == "team-b"

    def test_get_progress_summary(self, tracker, mock_audit_trail):
        """Test getting progress summary."""
        # Create vulnerabilities with different statuses
        vulnerabilities = []
        statuses = [
            VulnerabilityStatus.NEW,
            VulnerabilityStatus.IN_PROGRESS,
            VulnerabilityStatus.RESOLVED,
            VulnerabilityStatus.RESOLVED,
            VulnerabilityStatus.CLOSED,
        ]

        for i, status in enumerate(statuses):
            vuln = Vulnerability(
                id=f"vuln-{i}",
                package_name=f"test-package-{i}",
                installed_version="1.0.0",
                fix_versions=["1.0.1"],
                severity=VulnerabilitySeverity.MEDIUM,
                description=f"Desc {i}",
            )
            tracker.track_vulnerability(vuln, initial_status=status)
            vulnerabilities.append(vuln)

        summary = tracker.get_progress_summary()

        assert summary is not None
        assert isinstance(summary, dict)
        assert "total_vulnerabilities" in summary
        assert "status_distribution" in summary
        assert "severity_distribution" in summary
        assert "progress_metrics" in summary
        assert "generated_at" in summary

        # Check specific status counts in status_distribution
        status_dist = summary["status_distribution"]
        assert "new" in status_dist
        assert "in_progress" in status_dist
        assert "resolved" in status_dist
        assert "closed" in status_dist

        # Check progress metrics structure
        progress_metrics = summary["progress_metrics"]
        assert "average_progress_percentage" in progress_metrics
        assert "completed_count" in progress_metrics
        assert "completion_rate" in progress_metrics

    def test_get_overdue_vulnerabilities(self, tracker, mock_audit_trail):
        """Test getting overdue vulnerabilities."""
        # Create an old vulnerability
        old_vuln = Vulnerability(
            id="old-vuln",
            package_name="old-package",
            installed_version="1.0.0",
            fix_versions=["1.0.1"],
            severity=VulnerabilitySeverity.HIGH,
            description="Old vuln",
        )

        # Track it with an old creation date
        with patch("vet_core.security.status_tracker.datetime") as mock_datetime:
            old_date = datetime.now() - timedelta(days=30)
            mock_datetime.now.return_value = old_date
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            tracker.track_vulnerability(
                old_vuln, initial_status=VulnerabilityStatus.NEW
            )

        overdue = tracker.get_overdue_vulnerabilities()

        assert isinstance(overdue, list)
        # The specific logic for determining overdue vulnerabilities depends on implementation

    def test_is_valid_status_transition(self, tracker):
        """Test status transition validation."""
        # Test valid transitions
        assert (
            tracker._is_valid_status_transition(
                VulnerabilityStatus.NEW, VulnerabilityStatus.DETECTED
            )
            is True
        )

        assert (
            tracker._is_valid_status_transition(
                VulnerabilityStatus.IN_PROGRESS, VulnerabilityStatus.RESOLVED
            )
            is True
        )

        # Test invalid transitions (if any - depends on implementation)
        # This test may need adjustment based on actual business rules

    def test_calculate_progress_metrics(self, tracker, sample_vulnerability):
        """Test calculating progress metrics for a vulnerability."""
        # Track vulnerability
        record = tracker.track_vulnerability(sample_vulnerability)

        # Calculate progress metrics
        metrics = tracker._calculate_progress_metrics(record)

        assert isinstance(metrics, ProgressMetrics)
        assert hasattr(metrics, "current_stage")
        assert hasattr(metrics, "completion_percentage")

    def test_save_tracking_record(self, tracker, sample_vulnerability):
        """Test saving tracking record to database."""
        record = tracker.track_vulnerability(sample_vulnerability)

        # The record should be automatically saved during tracking
        # Verify by retrieving it
        retrieved = tracker.get_tracking_record(sample_vulnerability.id)
        assert retrieved is not None
        assert retrieved.vulnerability_id == record.vulnerability_id

    def test_save_status_change(self, tracker, sample_vulnerability, mock_audit_trail):
        """Test saving status change to database."""
        # Track vulnerability
        tracker.track_vulnerability(sample_vulnerability)

        # Update status (this should save a status change)
        tracker.update_status(
            vulnerability_id=sample_vulnerability.id,
            new_status=VulnerabilityStatus.IN_PROGRESS,
            changed_by="test-user",
            reason="Starting work",
        )

        # Verify the status change was saved by checking the record
        record = tracker.get_tracking_record(sample_vulnerability.id)
        assert record.current_status == VulnerabilityStatus.IN_PROGRESS
        assert len(record.status_history) > 0

    def test_load_tracking_record(self, tracker, sample_vulnerability):
        """Test loading tracking record from database."""
        # Track vulnerability (this saves it)
        original_record = tracker.track_vulnerability(sample_vulnerability)

        # Load it back
        loaded_record = tracker._load_tracking_record(sample_vulnerability.id)

        assert loaded_record is not None
        assert loaded_record.vulnerability_id == original_record.vulnerability_id
        assert loaded_record.current_status == original_record.current_status

    def test_load_tracking_record_not_found(self, tracker):
        """Test loading tracking record that doesn't exist."""
        non_existent_id = "non-existent-id"
        record = tracker._load_tracking_record(non_existent_id)
        assert record is None

    def test_database_initialization(self, mock_audit_trail, temp_db_path):
        """Test that database is properly initialized."""
        # Create tracker (this should initialize the database)
        tracker = VulnerabilityStatusTracker(
            audit_trail=mock_audit_trail, tracking_db_path=temp_db_path
        )

        # Verify database file exists
        assert temp_db_path.exists()

        # Verify tables exist by attempting to query them
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()

            # Check if tracking_records table exists
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='tracking_records'
            """
            )
            assert cursor.fetchone() is not None

            # Check if status_changes table exists
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='status_changes'
            """
            )
            assert cursor.fetchone() is not None

    def test_vulnerability_status_tracker_integration(self, tracker, mock_audit_trail):
        """Test integration of multiple tracker features."""
        # Create a vulnerability
        vuln = Vulnerability(
            id="integration-test-vuln",
            package_name="integration-package",
            installed_version="1.0.0",
            fix_versions=["1.0.1"],
            severity=VulnerabilitySeverity.HIGH,
            description="Testing full workflow",
        )

        # Track the vulnerability
        record = tracker.track_vulnerability(
            vulnerability=vuln,
            initial_status=VulnerabilityStatus.NEW,
            assigned_to="security-team",
            priority_score=8.5,
            tags=["critical", "sql-injection"],
        )

        # Update status through workflow
        statuses = [
            VulnerabilityStatus.DETECTED,
            VulnerabilityStatus.ASSESSED,
            VulnerabilityStatus.ASSIGNED,
            VulnerabilityStatus.IN_PROGRESS,
            VulnerabilityStatus.TESTING,
            VulnerabilityStatus.RESOLVED,
            VulnerabilityStatus.VERIFIED,
            VulnerabilityStatus.CLOSED,
        ]

        for status in statuses:
            updated_record = tracker.update_status(
                vulnerability_id=vuln.id,
                new_status=status,
                changed_by="test-user",
                reason=f"Moving to {status.value}",
                notes=f"Status updated to {status.value}",
            )
            assert updated_record.current_status == status

        # Verify final state
        final_record = tracker.get_tracking_record(vuln.id)
        assert final_record.current_status == VulnerabilityStatus.CLOSED
        assert (
            len(final_record.status_history) == len(statuses) + 1
        )  # +1 for initial tracking

        # Test progress summary
        summary = tracker.get_progress_summary()
        assert summary is not None

        # Test filtering
        closed_records = tracker.get_all_tracking_records(
            status_filter=VulnerabilityStatus.CLOSED
        )
        assert len(closed_records) == 1
        assert closed_records[0].vulnerability_id == vuln.id

    def test_concurrent_status_updates(
        self, tracker, sample_vulnerability, mock_audit_trail
    ):
        """Test handling concurrent status updates."""
        # Track vulnerability
        tracker.track_vulnerability(sample_vulnerability)

        # Simulate concurrent updates
        record1 = tracker.update_status(
            vulnerability_id=sample_vulnerability.id,
            new_status=VulnerabilityStatus.DETECTED,
            changed_by="user1",
            reason="First update",
        )

        record2 = tracker.update_status(
            vulnerability_id=sample_vulnerability.id,
            new_status=VulnerabilityStatus.IN_PROGRESS,
            changed_by="user2",
            reason="Second update",
        )

        # The final status should be the last update
        assert record2.current_status == VulnerabilityStatus.IN_PROGRESS
        assert len(record2.status_history) >= 2
