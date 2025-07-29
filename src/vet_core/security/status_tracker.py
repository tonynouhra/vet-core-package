"""
Vulnerability status tracking and progress monitoring module.

This module provides comprehensive tracking of vulnerability lifecycle,
status changes, and progress monitoring for remediation activities.

Requirements addressed:
- 3.3: Vulnerability prioritization with timeline recommendations
- 4.3: Compliance report generation with vulnerability management evidence
- 4.4: Evidence of proactive security management practices
"""

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .assessor import RiskAssessment
from .audit_trail import AuditEvent, AuditEventType, SecurityAuditTrail
from .models import SecurityReport, Vulnerability, VulnerabilitySeverity


class VulnerabilityStatus(Enum):
    """Vulnerability lifecycle status."""

    NEW = "new"
    DETECTED = "detected"
    ASSESSED = "assessed"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    RESOLVED = "resolved"
    VERIFIED = "verified"
    CLOSED = "closed"
    IGNORED = "ignored"
    DEFERRED = "deferred"
    FALSE_POSITIVE = "false_positive"


class ProgressStage(Enum):
    """Progress stages for vulnerability remediation."""

    DETECTION = "detection"
    ANALYSIS = "analysis"
    DISCOVERY = "discovery"
    ASSESSMENT = "assessment"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    VERIFICATION = "verification"
    CLOSURE = "closure"


@dataclass
class StatusChange:
    """Represents a status change event."""

    change_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vulnerability_id: str = ""
    old_status: Optional[VulnerabilityStatus] = None
    new_status: VulnerabilityStatus = VulnerabilityStatus.NEW
    changed_by: Optional[str] = None
    changed_at: datetime = field(default_factory=datetime.now)
    reason: str = ""
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert status change to dictionary representation."""
        return {
            "change_id": self.change_id,
            "vulnerability_id": self.vulnerability_id,
            "old_status": self.old_status.value if self.old_status else None,
            "new_status": self.new_status.value,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat(),
            "reason": self.reason,
            "notes": self.notes,
            "metadata": self.metadata,
        }


@dataclass
class ProgressMetrics:
    """Metrics for vulnerability progress tracking."""

    current_stage: ProgressStage
    completion_percentage: float  # 0.0 to 100.0
    time_in_current_stage: timedelta
    estimated_completion_time: timedelta
    stages_completed: List[ProgressStage] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    is_overdue: bool = False
    sla_deadline: Optional[datetime] = None
    progress_percentage: float = field(
        init=False
    )  # Alias for completion_percentage for backward compatibility

    def __post_init__(self) -> None:
        """Set progress_percentage as alias for completion_percentage."""
        self.progress_percentage = self.completion_percentage

    def to_dict(self) -> Dict[str, Any]:
        """Convert progress metrics to dictionary representation."""
        return {
            "current_stage": self.current_stage.value,
            "completion_percentage": self.completion_percentage,
            "time_in_current_stage": self.time_in_current_stage.total_seconds() / 3600,
            "estimated_completion_time": self.estimated_completion_time.total_seconds()
            / 3600,
            "stages_completed": [stage.value for stage in self.stages_completed],
            "blockers": self.blockers,
        }


@dataclass
class VulnerabilityTrackingRecord:
    """Complete tracking record for a vulnerability."""

    vulnerability_id: str
    package_name: str
    severity: VulnerabilitySeverity
    current_status: VulnerabilityStatus
    created_at: datetime
    updated_at: datetime
    assigned_to: Optional[str] = None
    priority_score: float = 0.0
    estimated_effort_hours: Optional[float] = None
    actual_effort_hours: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    status_history: List[StatusChange] = field(default_factory=list)
    progress_metrics: Optional[ProgressMetrics] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert tracking record to dictionary representation."""
        return {
            "vulnerability_id": self.vulnerability_id,
            "package_name": self.package_name,
            "severity": self.severity.name,
            "current_status": self.current_status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "assigned_to": self.assigned_to,
            "priority_score": self.priority_score,
            "estimated_effort_hours": self.estimated_effort_hours,
            "actual_effort_hours": self.actual_effort_hours,
            "tags": self.tags,
            "status_history": [change.to_dict() for change in self.status_history],
            "progress_metrics": (
                self.progress_metrics.to_dict() if self.progress_metrics else None
            ),
        }


class VulnerabilityStatusTracker:
    """
    Comprehensive vulnerability status tracking and progress monitoring system.

    This class provides detailed tracking of vulnerability lifecycle, status changes,
    and progress monitoring for remediation activities.
    """

    # Status progression mapping
    STATUS_PROGRESSION = {
        VulnerabilityStatus.NEW: [
            VulnerabilityStatus.DETECTED,
            VulnerabilityStatus.IN_PROGRESS,
            VulnerabilityStatus.ASSESSED,
            VulnerabilityStatus.ASSIGNED,
            VulnerabilityStatus.RESOLVED,
        ],
        VulnerabilityStatus.DETECTED: [
            VulnerabilityStatus.ASSESSED,
            VulnerabilityStatus.IGNORED,
            VulnerabilityStatus.ASSIGNED,
            VulnerabilityStatus.IN_PROGRESS,
        ],
        VulnerabilityStatus.ASSESSED: [
            VulnerabilityStatus.ASSIGNED,
            VulnerabilityStatus.DEFERRED,
            VulnerabilityStatus.IN_PROGRESS,
        ],
        VulnerabilityStatus.ASSIGNED: [
            VulnerabilityStatus.IN_PROGRESS,
            VulnerabilityStatus.ASSESSED,
        ],
        VulnerabilityStatus.IN_PROGRESS: [
            VulnerabilityStatus.TESTING,
            VulnerabilityStatus.RESOLVED,
            VulnerabilityStatus.ASSIGNED,
        ],
        VulnerabilityStatus.TESTING: [
            VulnerabilityStatus.RESOLVED,
            VulnerabilityStatus.IN_PROGRESS,
        ],
        VulnerabilityStatus.RESOLVED: [
            VulnerabilityStatus.VERIFIED,
            VulnerabilityStatus.IN_PROGRESS,
            VulnerabilityStatus.CLOSED,
        ],
        VulnerabilityStatus.VERIFIED: [VulnerabilityStatus.CLOSED],
        VulnerabilityStatus.CLOSED: [],
        VulnerabilityStatus.IGNORED: [],
        VulnerabilityStatus.DEFERRED: [VulnerabilityStatus.ASSESSED],
    }

    # Progress stage mapping
    STAGE_PROGRESS_MAP = {
        ProgressStage.DISCOVERY: 10.0,
        ProgressStage.ASSESSMENT: 20.0,
        ProgressStage.PLANNING: 30.0,
        ProgressStage.IMPLEMENTATION: 60.0,
        ProgressStage.TESTING: 80.0,
        ProgressStage.DEPLOYMENT: 90.0,
        ProgressStage.VERIFICATION: 95.0,
        ProgressStage.CLOSURE: 100.0,
    }

    # SLA timelines by severity (in hours)
    SLA_TIMELINES = {
        VulnerabilitySeverity.CRITICAL: 24,
        VulnerabilitySeverity.HIGH: 72,
        VulnerabilitySeverity.MEDIUM: 168,  # 1 week
        VulnerabilitySeverity.LOW: 720,  # 1 month
    }

    def __init__(
        self,
        audit_trail: SecurityAuditTrail,
        tracking_db_path: Optional[Path] = None,
    ) -> None:
        """
        Initialize the vulnerability status tracker.

        Args:
            audit_trail: Security audit trail system
            tracking_db_path: Path to tracking database
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.audit_trail = audit_trail

        # Set up tracking database
        if tracking_db_path is None:
            tracking_db_path = Path.cwd() / "vulnerability-tracking.db"
        self.tracking_db_path = tracking_db_path

        # Initialize database
        self._init_tracking_database()

        # In-memory cache for active tracking records
        self.tracking_cache: Dict[str, VulnerabilityTrackingRecord] = {}

        self.logger.info(
            f"Initialized VulnerabilityStatusTracker with database: {self.tracking_db_path}"
        )

    def cleanup(self) -> None:
        """
        Clean up resources and ensure database connections are properly closed.
        This is especially important on Windows to prevent file locking issues.
        """
        import gc
        import time
        import platform

        # Clear the tracking cache
        self.tracking_cache.clear()

        # Force garbage collection to ensure any lingering database connections are closed
        gc.collect()

        # On Windows, add a small delay to ensure file handles are released
        if platform.system() == "Windows":
            time.sleep(0.1)

        self.logger.debug("VulnerabilityStatusTracker cleanup completed")

    def _init_tracking_database(self) -> None:
        """Initialize the tracking database."""
        try:
            self.tracking_db_path.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(self.tracking_db_path) as conn:
                cursor = conn.cursor()

                # Create tracking records table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tracking_records (
                        vulnerability_id TEXT PRIMARY KEY,
                        package_name TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        current_status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        assigned_to TEXT,
                        priority_score REAL DEFAULT 0.0,
                        estimated_effort_hours REAL,
                        actual_effort_hours REAL,
                        tags TEXT,  -- JSON array
                        metadata TEXT  -- JSON object
                    )
                """
                )

                # Create status changes table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS status_changes (
                        change_id TEXT PRIMARY KEY,
                        vulnerability_id TEXT NOT NULL,
                        old_status TEXT,
                        new_status TEXT NOT NULL,
                        changed_by TEXT,
                        changed_at TEXT NOT NULL,
                        reason TEXT,
                        notes TEXT,
                        metadata TEXT,  -- JSON object
                        FOREIGN KEY (vulnerability_id) REFERENCES tracking_records (vulnerability_id)
                    )
                """
                )

                # Create progress metrics table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS progress_metrics (
                        vulnerability_id TEXT PRIMARY KEY,
                        current_stage TEXT NOT NULL,
                        progress_percentage REAL NOT NULL,
                        estimated_completion_time TEXT,
                        sla_deadline TEXT,
                        completion_confidence REAL DEFAULT 0.5,
                        calculated_at TEXT NOT NULL,
                        FOREIGN KEY (vulnerability_id) REFERENCES tracking_records (vulnerability_id)
                    )
                """
                )

                # Create indexes
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tracking_status ON tracking_records(current_status)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tracking_severity ON tracking_records(severity)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tracking_updated ON tracking_records(updated_at)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_status_changes_vuln ON status_changes(vulnerability_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_status_changes_time ON status_changes(changed_at)"
                )

                conn.commit()

        except Exception as e:
            self.logger.error(f"Failed to initialize tracking database: {e}")
            raise

    def track_vulnerability(
        self,
        vulnerability: Vulnerability,
        initial_status: VulnerabilityStatus = VulnerabilityStatus.NEW,
        assigned_to: Optional[str] = None,
        priority_score: float = 0.0,
        tags: Optional[List[str]] = None,
    ) -> VulnerabilityTrackingRecord:
        """
        Start tracking a vulnerability.

        Args:
            vulnerability: Vulnerability to track
            initial_status: Initial status
            assigned_to: Person assigned to handle the vulnerability
            priority_score: Priority score for the vulnerability
            tags: Optional tags for categorization

        Returns:
            VulnerabilityTrackingRecord for the vulnerability
        """
        # Check if already tracking
        existing_record = self.get_tracking_record(vulnerability.id)
        if existing_record:
            self.logger.info(f"Vulnerability {vulnerability.id} already being tracked")
            return existing_record

        # Create new tracking record
        now = datetime.now()
        record = VulnerabilityTrackingRecord(
            vulnerability_id=vulnerability.id,
            package_name=vulnerability.package_name,
            severity=vulnerability.severity,
            current_status=initial_status,
            created_at=now,
            updated_at=now,
            assigned_to=assigned_to,
            priority_score=priority_score,
            tags=tags or [],
        )

        # Create initial status change
        initial_change = StatusChange(
            vulnerability_id=vulnerability.id,
            old_status=None,
            new_status=initial_status,
            changed_by="system",
            reason="Initial tracking",
            notes=f"Started tracking vulnerability in {vulnerability.package_name}",
        )

        record.status_history.append(initial_change)

        # Calculate initial progress metrics
        record.progress_metrics = self._calculate_progress_metrics(record)

        # Save to database
        self._save_tracking_record(record)
        self._save_status_change(initial_change)

        # Cache the record
        self.tracking_cache[vulnerability.id] = record

        # Log to audit trail
        audit_event = AuditEvent(
            event_type=AuditEventType.VULNERABILITY_DETECTED,
            vulnerability_id=vulnerability.id,
            package_name=vulnerability.package_name,
            severity=vulnerability.severity,
            action_taken="vulnerability_tracking_started",
            outcome="tracking_initiated",
            details={
                "description": f"Started tracking vulnerability in {vulnerability.package_name}",
                "initial_status": initial_status.value,
                "assigned_to": assigned_to,
                "priority_score": priority_score,
                "tags": tags or [],
            },
        )
        self.audit_trail.log_event(audit_event)

        self.logger.info(f"Started tracking vulnerability: {vulnerability.id}")
        return record

    def update_status(
        self,
        vulnerability_id: str,
        new_status: VulnerabilityStatus,
        changed_by: Optional[str] = None,
        reason: str = "",
        notes: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[VulnerabilityTrackingRecord]:
        """
        Update vulnerability status.

        Args:
            vulnerability_id: ID of the vulnerability
            new_status: New status to set
            changed_by: Person making the change
            reason: Reason for the status change
            notes: Additional notes
            metadata: Additional metadata

        Returns:
            Updated VulnerabilityTrackingRecord if successful, None otherwise
        """
        record = self.get_tracking_record(vulnerability_id)
        if not record:
            self.logger.error(
                f"Vulnerability {vulnerability_id} not found for status update"
            )
            return None

        # Validate status transition
        if not self._is_valid_status_transition(record.current_status, new_status):
            self.logger.warning(
                f"Invalid status transition for {vulnerability_id}: "
                f"{record.current_status.value} -> {new_status.value}"
            )
            return None

        # Create status change record
        status_change = StatusChange(
            vulnerability_id=vulnerability_id,
            old_status=record.current_status,
            new_status=new_status,
            changed_by=changed_by or "system",
            reason=reason,
            notes=notes,
            metadata=metadata or {},
        )

        # Update tracking record
        record.current_status = new_status
        record.updated_at = datetime.now()
        record.status_history.append(status_change)

        # Recalculate progress metrics
        record.progress_metrics = self._calculate_progress_metrics(record)

        # Save changes
        self._save_tracking_record(record)
        self._save_status_change(status_change)

        # Update cache
        self.tracking_cache[vulnerability_id] = record

        # Log appropriate audit event
        if new_status == VulnerabilityStatus.RESOLVED:
            self.audit_trail.log_vulnerability_resolved(
                vulnerability_id=vulnerability_id,
                package_name=record.package_name,
                resolution_method=reason or "status_update",
            )

        self.logger.info(
            f"Updated status for {vulnerability_id}: "
            f"{status_change.old_status.value if status_change.old_status else 'None'} -> {new_status.value}"
        )

        return record

    def get_tracking_record(
        self, vulnerability_id: str
    ) -> Optional[VulnerabilityTrackingRecord]:
        """
        Get tracking record for a vulnerability.

        Args:
            vulnerability_id: ID of the vulnerability

        Returns:
            VulnerabilityTrackingRecord if found, None otherwise
        """
        # Check cache first
        if vulnerability_id in self.tracking_cache:
            return self.tracking_cache[vulnerability_id]

        # Load from database
        record = self._load_tracking_record(vulnerability_id)
        if record:
            self.tracking_cache[vulnerability_id] = record

        return record

    def get_all_tracking_records(
        self,
        status_filter: Optional[VulnerabilityStatus] = None,
        severity_filter: Optional[VulnerabilitySeverity] = None,
        assigned_to_filter: Optional[str] = None,
    ) -> List[VulnerabilityTrackingRecord]:
        """
        Get all tracking records with optional filters.

        Args:
            status_filter: Filter by status
            severity_filter: Filter by severity
            assigned_to_filter: Filter by assignee

        Returns:
            List of matching tracking records
        """
        try:
            with sqlite3.connect(self.tracking_db_path) as conn:
                cursor = conn.cursor()

                query = "SELECT vulnerability_id FROM tracking_records WHERE 1=1"
                params = []

                if status_filter:
                    query += " AND current_status = ?"
                    params.append(status_filter.value)

                if severity_filter:
                    query += " AND severity = ?"
                    params.append(severity_filter.value)

                if assigned_to_filter:
                    query += " AND assigned_to = ?"
                    params.append(assigned_to_filter)

                query += " ORDER BY updated_at DESC"

                cursor.execute(query, params)
                vulnerability_ids = [row[0] for row in cursor.fetchall()]

                # Load full records
                records = []
                for vuln_id in vulnerability_ids:
                    record = self.get_tracking_record(vuln_id)
                    if record:
                        records.append(record)

                return records

        except Exception as e:
            self.logger.error(f"Failed to get tracking records: {e}")
            return []

    def get_progress_summary(self) -> Dict[str, Any]:
        """
        Get overall progress summary.

        Returns:
            Dictionary with progress summary statistics
        """
        all_records = self.get_all_tracking_records()

        # Status distribution
        status_counts = {}
        for status in VulnerabilityStatus:
            status_counts[status.value] = 0

        # Severity distribution
        severity_counts = {}
        for severity in VulnerabilitySeverity:
            severity_counts[severity.value] = 0

        # Progress metrics
        total_progress = 0.0
        overdue_count = 0
        completed_count = 0

        for record in all_records:
            status_counts[record.current_status.value] += 1
            severity_counts[record.severity.value] += 1

            if record.progress_metrics:
                total_progress += record.progress_metrics.progress_percentage
                if record.progress_metrics.is_overdue:
                    overdue_count += 1
                if record.progress_metrics.progress_percentage >= 100.0:
                    completed_count += 1

        average_progress = total_progress / len(all_records) if all_records else 0.0

        return {
            "total_vulnerabilities": len(all_records),
            "status_distribution": status_counts,
            "severity_distribution": severity_counts,
            "progress_metrics": {
                "average_progress_percentage": average_progress,
                "completed_count": completed_count,
                "overdue_count": overdue_count,
                "completion_rate": (
                    (completed_count / len(all_records) * 100) if all_records else 0.0
                ),
            },
            "generated_at": datetime.now().isoformat(),
        }

    def get_overdue_vulnerabilities(self) -> List[VulnerabilityTrackingRecord]:
        """
        Get vulnerabilities that are overdue based on SLA.

        Returns:
            List of overdue vulnerability tracking records
        """
        all_records = self.get_all_tracking_records()
        overdue_records = []

        for record in all_records:
            if record.progress_metrics and record.progress_metrics.is_overdue:
                overdue_records.append(record)

        # Sort by how overdue they are (most overdue first)
        overdue_records.sort(
            key=lambda r: (
                r.progress_metrics.sla_deadline
                if r.progress_metrics and r.progress_metrics.sla_deadline
                else datetime.now()
            ),
            reverse=False,
        )

        return overdue_records

    def _is_valid_status_transition(
        self, current_status: VulnerabilityStatus, new_status: VulnerabilityStatus
    ) -> bool:
        """Check if a status transition is valid."""
        allowed_transitions = self.STATUS_PROGRESSION.get(current_status, [])
        return new_status in allowed_transitions or new_status == current_status

    def _calculate_progress_metrics(
        self, record: VulnerabilityTrackingRecord
    ) -> ProgressMetrics:
        """Calculate progress metrics for a vulnerability."""
        now = datetime.now()

        # Determine current stage based on status
        stage_map = {
            VulnerabilityStatus.NEW: ProgressStage.DISCOVERY,
            VulnerabilityStatus.DETECTED: ProgressStage.DISCOVERY,
            VulnerabilityStatus.ASSESSED: ProgressStage.ASSESSMENT,
            VulnerabilityStatus.ASSIGNED: ProgressStage.PLANNING,
            VulnerabilityStatus.IN_PROGRESS: ProgressStage.IMPLEMENTATION,
            VulnerabilityStatus.TESTING: ProgressStage.TESTING,
            VulnerabilityStatus.RESOLVED: ProgressStage.DEPLOYMENT,
            VulnerabilityStatus.VERIFIED: ProgressStage.VERIFICATION,
            VulnerabilityStatus.CLOSED: ProgressStage.CLOSURE,
            VulnerabilityStatus.IGNORED: ProgressStage.CLOSURE,
            VulnerabilityStatus.DEFERRED: ProgressStage.ASSESSMENT,
        }

        current_stage = stage_map.get(record.current_status, ProgressStage.DISCOVERY)
        progress_percentage = self.STAGE_PROGRESS_MAP.get(current_stage, 0.0)

        # Calculate time metrics
        total_time_since_detection = now - record.created_at

        # Find time in current status
        time_in_current_status = timedelta()
        if record.status_history:
            # Find the most recent status change to current status
            for change in reversed(record.status_history):
                if change.new_status == record.current_status:
                    time_in_current_status = now - change.changed_at
                    break

        # Calculate SLA deadline
        sla_hours = self.SLA_TIMELINES.get(record.severity, 720)  # Default to 1 month
        sla_deadline = record.created_at + timedelta(hours=sla_hours)
        is_overdue = now > sla_deadline and record.current_status not in [
            VulnerabilityStatus.CLOSED,
            VulnerabilityStatus.IGNORED,
        ]

        # Estimate completion time (simplified heuristic)
        estimated_completion_time = None
        if record.current_status not in [
            VulnerabilityStatus.CLOSED,
            VulnerabilityStatus.IGNORED,
        ]:
            remaining_progress = 100.0 - progress_percentage
            if remaining_progress > 0:
                # Estimate based on average time per progress unit
                avg_time_per_percent = total_time_since_detection.total_seconds() / max(
                    progress_percentage, 1.0
                )
                remaining_seconds = remaining_progress * avg_time_per_percent
                estimated_completion_time = now + timedelta(seconds=remaining_seconds)

        # Calculate completion confidence (simplified)
        completion_confidence = 0.5
        if record.current_status == VulnerabilityStatus.CLOSED:
            completion_confidence = 1.0
        elif record.current_status in [
            VulnerabilityStatus.RESOLVED,
            VulnerabilityStatus.VERIFIED,
        ]:
            completion_confidence = 0.9
        elif record.current_status == VulnerabilityStatus.IN_PROGRESS:
            completion_confidence = 0.7
        elif is_overdue:
            completion_confidence = 0.3

        # Determine completed stages based on current status
        stages_completed = []
        stage_order = [
            ProgressStage.DETECTION,
            ProgressStage.ANALYSIS,
            ProgressStage.DISCOVERY,
            ProgressStage.ASSESSMENT,
            ProgressStage.PLANNING,
            ProgressStage.IMPLEMENTATION,
            ProgressStage.TESTING,
            ProgressStage.DEPLOYMENT,
            ProgressStage.VERIFICATION,
            ProgressStage.CLOSURE,
        ]

        current_stage_index = (
            stage_order.index(current_stage) if current_stage in stage_order else 0
        )
        stages_completed = stage_order[:current_stage_index]

        # Determine blockers (simplified)
        blockers = []
        if is_overdue:
            blockers.append("SLA deadline exceeded")
        if record.current_status == VulnerabilityStatus.DEFERRED:
            blockers.append("Deferred for later resolution")

        # Convert estimated_completion_time to timedelta if it exists
        estimated_completion_timedelta = timedelta()
        if estimated_completion_time:
            estimated_completion_timedelta = estimated_completion_time - now

        return ProgressMetrics(
            current_stage=current_stage,
            completion_percentage=progress_percentage,
            time_in_current_stage=time_in_current_status,
            estimated_completion_time=estimated_completion_timedelta,
            stages_completed=stages_completed,
            blockers=blockers,
            is_overdue=is_overdue,
            sla_deadline=sla_deadline,
        )

    def _save_tracking_record(self, record: VulnerabilityTrackingRecord) -> None:
        """Save tracking record to database."""
        try:
            with sqlite3.connect(self.tracking_db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO tracking_records (
                        vulnerability_id, package_name, severity, current_status,
                        created_at, updated_at, assigned_to, priority_score,
                        estimated_effort_hours, actual_effort_hours, tags, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        record.vulnerability_id,
                        record.package_name,
                        record.severity.value,
                        record.current_status.value,
                        record.created_at.isoformat(),
                        record.updated_at.isoformat(),
                        record.assigned_to,
                        record.priority_score,
                        record.estimated_effort_hours,
                        record.actual_effort_hours,
                        json.dumps(record.tags),
                        json.dumps({}),  # metadata placeholder
                    ),
                )

                # Save progress metrics
                if record.progress_metrics:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO progress_metrics (
                            vulnerability_id, current_stage, progress_percentage,
                            estimated_completion_time, sla_deadline, completion_confidence,
                            calculated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            record.vulnerability_id,
                            record.progress_metrics.current_stage.value,
                            record.progress_metrics.completion_percentage,
                            (
                                str(
                                    record.progress_metrics.estimated_completion_time.total_seconds()
                                )
                                if record.progress_metrics.estimated_completion_time
                                else None
                            ),
                            (
                                record.progress_metrics.sla_deadline.isoformat()
                                if record.progress_metrics.sla_deadline
                                else None
                            ),
                            0.5,  # completion_confidence not available, use default
                            datetime.now().isoformat(),
                        ),
                    )

                conn.commit()

        except Exception as e:
            self.logger.error(
                f"Failed to save tracking record {record.vulnerability_id}: {e}"
            )
            raise

    def _save_status_change(self, change: StatusChange) -> None:
        """Save status change to database."""
        try:
            with sqlite3.connect(self.tracking_db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO status_changes (
                        change_id, vulnerability_id, old_status, new_status,
                        changed_by, changed_at, reason, notes, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        change.change_id,
                        change.vulnerability_id,
                        change.old_status.value if change.old_status else None,
                        change.new_status.value,
                        change.changed_by,
                        change.changed_at.isoformat(),
                        change.reason,
                        change.notes,
                        json.dumps(change.metadata),
                    ),
                )

                conn.commit()

        except Exception as e:
            self.logger.error(f"Failed to save status change {change.change_id}: {e}")
            raise

    def _load_tracking_record(
        self, vulnerability_id: str
    ) -> Optional[VulnerabilityTrackingRecord]:
        """Load tracking record from database."""
        try:
            with sqlite3.connect(self.tracking_db_path) as conn:
                cursor = conn.cursor()

                # Load main record
                cursor.execute(
                    """
                    SELECT vulnerability_id, package_name, severity, current_status,
                           created_at, updated_at, assigned_to, priority_score,
                           estimated_effort_hours, actual_effort_hours, tags
                    FROM tracking_records
                    WHERE vulnerability_id = ?
                """,
                    (vulnerability_id,),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                # Create record
                record = VulnerabilityTrackingRecord(
                    vulnerability_id=row[0],
                    package_name=row[1],
                    severity=VulnerabilitySeverity(row[2]),
                    current_status=VulnerabilityStatus(row[3]),
                    created_at=datetime.fromisoformat(row[4]),
                    updated_at=datetime.fromisoformat(row[5]),
                    assigned_to=row[6],
                    priority_score=row[7] or 0.0,
                    estimated_effort_hours=row[8],
                    actual_effort_hours=row[9],
                    tags=json.loads(row[10]) if row[10] else [],
                )

                # Load status history
                cursor.execute(
                    """
                    SELECT change_id, old_status, new_status, changed_by,
                           changed_at, reason, notes, metadata
                    FROM status_changes
                    WHERE vulnerability_id = ?
                    ORDER BY changed_at ASC
                """,
                    (vulnerability_id,),
                )

                for change_row in cursor.fetchall():
                    change = StatusChange(
                        change_id=change_row[0],
                        vulnerability_id=vulnerability_id,
                        old_status=(
                            VulnerabilityStatus(change_row[1])
                            if change_row[1]
                            else None
                        ),
                        new_status=VulnerabilityStatus(change_row[2]),
                        changed_by=change_row[3],
                        changed_at=datetime.fromisoformat(change_row[4]),
                        reason=change_row[5] or "",
                        notes=change_row[6] or "",
                        metadata=json.loads(change_row[7]) if change_row[7] else {},
                    )
                    record.status_history.append(change)

                # Load progress metrics
                cursor.execute(
                    """
                    SELECT current_stage, progress_percentage, estimated_completion_time,
                           sla_deadline, completion_confidence
                    FROM progress_metrics
                    WHERE vulnerability_id = ?
                """,
                    (vulnerability_id,),
                )

                metrics_row = cursor.fetchone()
                if metrics_row:
                    record.progress_metrics = self._calculate_progress_metrics(record)

                return record

        except Exception as e:
            self.logger.error(f"Failed to load tracking record {vulnerability_id}: {e}")
            return None
