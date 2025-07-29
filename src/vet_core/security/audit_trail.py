"""
Security audit trail and compliance reporting module.

This module provides comprehensive logging and tracking of all vulnerability
detection and remediation actions, creating a complete audit trail for
compliance and security management purposes.

Requirements addressed:
- 4.1: Detailed logging of vulnerability detection and remediation actions
- 4.2: Audit trail functionality tracking timelines, actions, and outcomes
- 4.3: Compliance report generation with vulnerability management evidence
- 4.4: Evidence of proactive security management practices
"""

import json
import logging
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .assessor import RiskAssessment
from .models import (
    RemediationAction,
    SecurityReport,
    Vulnerability,
    VulnerabilitySeverity,
)


class AuditEventType(Enum):
    """Types of audit events that can be logged."""

    VULNERABILITY_DETECTED = "vulnerability_detected"
    VULNERABILITY_RESOLVED = "vulnerability_resolved"
    SCAN_INITIATED = "scan_initiated"
    SCAN_COMPLETED = "scan_completed"
    REMEDIATION_STARTED = "remediation_started"
    REMEDIATION_COMPLETED = "remediation_completed"
    REMEDIATION_FAILED = "remediation_failed"
    RISK_ASSESSMENT_PERFORMED = "risk_assessment_performed"
    COMPLIANCE_CHECK = "compliance_check"
    POLICY_VIOLATION = "policy_violation"
    MANUAL_OVERRIDE = "manual_override"
    FALSE_POSITIVE_REPORTED = "false_positive_reported"


@dataclass
class AuditEvent:
    """Represents a single audit event in the security management system."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: AuditEventType = AuditEventType.VULNERABILITY_DETECTED
    timestamp: datetime = field(default_factory=datetime.now)
    vulnerability_id: Optional[str] = None
    package_name: Optional[str] = None
    severity: Optional[VulnerabilitySeverity] = None
    action_taken: Optional[str] = None
    outcome: Optional[str] = None
    user_id: Optional[str] = None
    system_component: str = "vet-core-security"
    details: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary representation."""
        data = asdict(self)
        # Convert enum values to strings
        data["event_type"] = self.event_type.value
        if self.severity:
            data["severity"] = self.severity.value
        # Convert datetime to ISO format
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        """Create audit event from dictionary representation."""
        # Convert string values back to enums
        if "event_type" in data:
            data["event_type"] = AuditEventType(data["event_type"])
        if "severity" in data and data["severity"]:
            data["severity"] = VulnerabilitySeverity(data["severity"])
        # Convert ISO format back to datetime
        if "timestamp" in data:
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        return cls(**data)


@dataclass
class ComplianceMetrics:
    """Represents compliance metrics for security management."""

    assessment_date: datetime
    total_vulnerabilities: int
    critical_vulnerabilities: int
    high_vulnerabilities: int
    medium_vulnerabilities: int
    low_vulnerabilities: int
    unresolved_critical: int
    unresolved_high: int
    mean_time_to_detection: Optional[float] = None  # hours
    mean_time_to_remediation: Optional[float] = None  # hours
    compliance_score: float = 0.0  # 0.0 to 100.0
    policy_violations: int = 0
    overdue_remediations: int = 0
    scan_frequency_compliance: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert compliance metrics to dictionary representation."""
        data = asdict(self)
        data["assessment_date"] = self.assessment_date.isoformat()
        return data


class SecurityAuditTrail:
    """
    Comprehensive audit trail system for security vulnerability management.

    This class provides complete logging and tracking of all security-related
    activities, creating a detailed audit trail for compliance and governance
    purposes.
    """

    def __init__(
        self,
        audit_db_path: Optional[Path] = None,
        log_file_path: Optional[Path] = None,
        retention_days: int = 365,
    ) -> None:
        """
        Initialize the security audit trail system.

        Args:
            audit_db_path: Path to SQLite database for audit events
            log_file_path: Path to log file for audit events
            retention_days: Number of days to retain audit events
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Set up database path
        if audit_db_path is None:
            audit_db_path = Path.cwd() / "security-audit.db"
        self.audit_db_path = audit_db_path

        # Set up log file path
        if log_file_path is None:
            log_file_path = Path.cwd() / "security-audit.log"
        self.log_file_path = log_file_path

        self.retention_days = retention_days

        # Track initialization status
        self._database_initialized = False
        self._file_logging_initialized = False

        # Try to initialize database and file logging
        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize database and file logging components with error handling."""
        # Initialize database
        try:
            self._init_database()
            self._database_initialized = True
        except Exception as e:
            self.logger.warning(f"Database initialization failed: {e}")
            # Don't re-raise the exception - this is expected behavior

        # Set up file logging
        try:
            self._setup_file_logging()
            self._file_logging_initialized = True
        except Exception as e:
            self.logger.warning(f"File logging initialization failed: {e}")

        if self._database_initialized:
            self.logger.info(
                f"Initialized SecurityAuditTrail with database: {self.audit_db_path}"
            )
        else:
            self.logger.warning(
                f"SecurityAuditTrail initialized with limited functionality - database unavailable"
            )

    def _init_database(self) -> None:
        """Initialize the SQLite database for audit events."""
        try:
            # Create directory if it doesn't exist
            self.audit_db_path.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(self.audit_db_path) as conn:
                cursor = conn.cursor()

                # Create audit events table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_events (
                        event_id TEXT PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        vulnerability_id TEXT,
                        package_name TEXT,
                        severity TEXT,
                        action_taken TEXT,
                        outcome TEXT,
                        user_id TEXT,
                        system_component TEXT,
                        details TEXT,
                        metadata TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create compliance metrics table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS compliance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        assessment_date TEXT NOT NULL,
                        total_vulnerabilities INTEGER,
                        critical_vulnerabilities INTEGER,
                        high_vulnerabilities INTEGER,
                        medium_vulnerabilities INTEGER,
                        low_vulnerabilities INTEGER,
                        unresolved_critical INTEGER,
                        unresolved_high INTEGER,
                        mean_time_to_detection REAL,
                        mean_time_to_remediation REAL,
                        compliance_score REAL,
                        policy_violations INTEGER,
                        overdue_remediations INTEGER,
                        scan_frequency_compliance INTEGER,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create indexes for better query performance
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp 
                    ON audit_events(timestamp)
                """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_audit_events_type 
                    ON audit_events(event_type)
                """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_audit_events_vulnerability 
                    ON audit_events(vulnerability_id)
                """
                )

                conn.commit()

        except (OSError, PermissionError) as e:
            # Handle file system errors gracefully
            self.logger.error(
                f"Failed to initialize audit database due to file system error: {e}"
            )
            raise
        except sqlite3.Error as e:
            # Handle SQLite-specific errors
            self.logger.error(
                f"Failed to initialize audit database due to SQLite error: {e}"
            )
            raise
        except Exception as e:
            # Handle any other unexpected errors
            self.logger.error(f"Failed to initialize audit database: {e}")
            raise

    def _setup_file_logging(self) -> None:
        """Set up file-based logging for audit events."""
        try:
            # Create directory if it doesn't exist
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create a dedicated logger for audit events
            self.audit_logger = logging.getLogger("security_audit")
            self.audit_logger.setLevel(logging.INFO)

            # Remove existing handlers to avoid duplicates
            for handler in self.audit_logger.handlers[:]:
                self.audit_logger.removeHandler(handler)

            # Create file handler
            file_handler = logging.FileHandler(self.log_file_path)
            file_handler.setLevel(logging.INFO)

            # Create formatter
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(formatter)

            # Add handler to logger
            self.audit_logger.addHandler(file_handler)

            # Prevent propagation to root logger
            self.audit_logger.propagate = False

        except (OSError, PermissionError) as e:
            # Handle file system errors gracefully
            self.logger.error(
                f"Failed to setup file logging due to file system error: {e}"
            )
            raise
        except Exception as e:
            # Handle any other unexpected errors
            self.logger.error(f"Failed to setup file logging: {e}")
            raise

    def log_event(self, event: AuditEvent) -> None:
        """
        Log an audit event to both database and file.

        Args:
            event: The audit event to log
        """
        logged_successfully = False

        try:
            # Log to database if available
            if self._database_initialized:
                self._log_to_database(event)
                logged_successfully = True
            else:
                self.logger.warning(
                    f"Database not available, skipping database logging for event: {event.event_id}"
                )

            # Log to file if available
            if self._file_logging_initialized:
                self._log_to_file(event)
                logged_successfully = True
            else:
                self.logger.warning(
                    f"File logging not available, skipping file logging for event: {event.event_id}"
                )

            if logged_successfully:
                self.logger.debug(f"Logged audit event: {event.event_id}")
            else:
                self.logger.error(
                    f"Failed to log audit event {event.event_id}: No logging mechanisms available"
                )

        except Exception as e:
            self.logger.error(f"Failed to log audit event {event.event_id}: {e}")
            raise

    def _log_to_database(self, event: AuditEvent) -> None:
        """Log audit event to SQLite database."""
        with sqlite3.connect(self.audit_db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO audit_events (
                    event_id, event_type, timestamp, vulnerability_id, package_name,
                    severity, action_taken, outcome, user_id, system_component,
                    details, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event.event_id,
                    event.event_type.value,
                    event.timestamp.isoformat(),
                    event.vulnerability_id,
                    event.package_name,
                    event.severity.value if event.severity else None,
                    event.action_taken,
                    event.outcome,
                    event.user_id,
                    event.system_component,
                    json.dumps(event.details),
                    json.dumps(event.metadata),
                ),
            )

            conn.commit()

    def _log_to_file(self, event: AuditEvent) -> None:
        """Log audit event to file."""
        log_message = (
            f"EVENT_ID={event.event_id} "
            f"TYPE={event.event_type.value} "
            f"VULN_ID={event.vulnerability_id or 'N/A'} "
            f"PACKAGE={event.package_name or 'N/A'} "
            f"SEVERITY={event.severity.value if event.severity else 'N/A'} "
            f"ACTION={event.action_taken or 'N/A'} "
            f"OUTCOME={event.outcome or 'N/A'} "
            f"DETAILS={json.dumps(event.details)}"
        )

        self.audit_logger.info(log_message)

    def log_vulnerability_detected(
        self, vulnerability: Vulnerability, scan_id: Optional[str] = None
    ) -> None:
        """
        Log detection of a new vulnerability.

        Args:
            vulnerability: The detected vulnerability
            scan_id: Optional scan identifier
        """
        event = AuditEvent(
            event_type=AuditEventType.VULNERABILITY_DETECTED,
            vulnerability_id=vulnerability.id,
            package_name=vulnerability.package_name,
            severity=vulnerability.severity,
            action_taken="vulnerability_detected",
            outcome="pending_assessment",
            details={
                "installed_version": vulnerability.installed_version,
                "fix_versions": vulnerability.fix_versions,
                "cvss_score": vulnerability.cvss_score,
                "description": vulnerability.description,
                "scan_id": scan_id,
            },
        )

        self.log_event(event)

    def log_vulnerability_resolved(
        self,
        vulnerability_id: str,
        package_name: str,
        resolution_method: str,
        new_version: Optional[str] = None,
    ) -> None:
        """
        Log resolution of a vulnerability.

        Args:
            vulnerability_id: ID of the resolved vulnerability
            package_name: Name of the affected package
            resolution_method: How the vulnerability was resolved
            new_version: New version if upgraded
        """
        event = AuditEvent(
            event_type=AuditEventType.VULNERABILITY_RESOLVED,
            vulnerability_id=vulnerability_id,
            package_name=package_name,
            action_taken=resolution_method,
            outcome="resolved",
            details={
                "new_version": new_version,
                "resolution_method": resolution_method,
            },
        )

        self.log_event(event)

    def log_scan_initiated(
        self,
        scan_id: str,
        scan_type: str = "pip-audit",
        scan_command: Optional[str] = None,
    ) -> None:
        """
        Log initiation of a security scan.

        Args:
            scan_id: Unique identifier for the scan
            scan_type: Type of scan being performed
            scan_command: Command used for scanning
        """
        event = AuditEvent(
            event_type=AuditEventType.SCAN_INITIATED,
            action_taken="security_scan_started",
            outcome="in_progress",
            details={
                "scan_id": scan_id,
                "scan_type": scan_type,
                "scan_command": scan_command,
            },
        )

        self.log_event(event)

    def log_scan_completed(
        self, scan_id: str, report: SecurityReport, duration: float
    ) -> None:
        """
        Log completion of a security scan.

        Args:
            scan_id: Unique identifier for the scan
            report: The generated security report
            duration: Scan duration in seconds
        """
        event = AuditEvent(
            event_type=AuditEventType.SCAN_COMPLETED,
            action_taken="security_scan_completed",
            outcome="completed",
            details={
                "scan_id": scan_id,
                "total_vulnerabilities": report.vulnerability_count,
                "critical_count": report.critical_count,
                "high_count": report.high_count,
                "medium_count": report.medium_count,
                "low_count": report.low_count,
                "packages_scanned": report.total_packages_scanned,
                "scan_duration": duration,
                "scanner_version": report.scanner_version,
            },
        )

        self.log_event(event)

    def log_remediation_action(
        self, remediation: RemediationAction, event_type: AuditEventType
    ) -> None:
        """
        Log a remediation action (started, completed, or failed).

        Args:
            remediation: The remediation action
            event_type: Type of remediation event
        """
        event = AuditEvent(
            event_type=event_type,
            vulnerability_id=remediation.vulnerability_id,
            action_taken=remediation.action_type,
            outcome=remediation.status,
            details={
                "target_version": remediation.target_version,
                "started_date": (
                    remediation.started_date.isoformat()
                    if remediation.started_date
                    else None
                ),
                "completed_date": (
                    remediation.completed_date.isoformat()
                    if remediation.completed_date
                    else None
                ),
                "notes": remediation.notes,
            },
        )

        self.log_event(event)

    def log_risk_assessment(
        self, vulnerability_id: str, assessment: RiskAssessment
    ) -> None:
        """
        Log completion of a risk assessment.

        Args:
            vulnerability_id: ID of the assessed vulnerability
            assessment: The risk assessment results
        """
        event = AuditEvent(
            event_type=AuditEventType.RISK_ASSESSMENT_PERFORMED,
            vulnerability_id=vulnerability_id,
            action_taken="risk_assessment",
            outcome="completed",
            details={
                "risk_score": assessment.risk_score,
                "priority_level": assessment.priority_level,
                "recommended_timeline_hours": int(
                    assessment.recommended_timeline.total_seconds() / 3600
                ),
                "confidence_score": assessment.confidence_score,
                "remediation_complexity": assessment.remediation_complexity,
                "business_impact": assessment.business_impact,
                "impact_factors": assessment.impact_factors,
            },
        )

        self.log_event(event)

    def log_compliance_check(
        self, metrics: ComplianceMetrics, policy_violations: Optional[List[str]] = None
    ) -> None:
        """
        Log a compliance check and its results.

        Args:
            metrics: Compliance metrics
            policy_violations: List of policy violations found
        """
        event = AuditEvent(
            event_type=AuditEventType.COMPLIANCE_CHECK,
            action_taken="compliance_assessment",
            outcome="completed",
            details={
                "compliance_score": metrics.compliance_score,
                "total_vulnerabilities": metrics.total_vulnerabilities,
                "critical_vulnerabilities": metrics.critical_vulnerabilities,
                "policy_violations": policy_violations or [],
                "overdue_remediations": metrics.overdue_remediations,
                "scan_frequency_compliance": metrics.scan_frequency_compliance,
            },
        )

        self.log_event(event)

    def log_policy_violation(
        self,
        violation_type: str,
        description: str,
        vulnerability_id: Optional[str] = None,
    ) -> None:
        """
        Log a security policy violation.

        Args:
            violation_type: Type of policy violation
            description: Description of the violation
            vulnerability_id: Associated vulnerability ID if applicable
        """
        event = AuditEvent(
            event_type=AuditEventType.POLICY_VIOLATION,
            vulnerability_id=vulnerability_id,
            action_taken="policy_violation_detected",
            outcome="requires_attention",
            details={"violation_type": violation_type, "description": description},
        )

        self.log_event(event)

    def get_audit_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[AuditEventType] = None,
        vulnerability_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        """
        Retrieve audit events based on filters.

        Args:
            start_date: Start date for filtering events
            end_date: End date for filtering events
            event_type: Filter by event type
            vulnerability_id: Filter by vulnerability ID
            limit: Maximum number of events to return

        Returns:
            List of matching audit events
        """
        if not self._database_initialized:
            self.logger.warning(
                "Database not initialized, returning empty audit events list"
            )
            return []

        try:
            with sqlite3.connect(self.audit_db_path) as conn:
                cursor = conn.cursor()

                # Build query with filters
                query = "SELECT * FROM audit_events WHERE 1=1"
                params = []

                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date.isoformat())

                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date.isoformat())

                if event_type:
                    query += " AND event_type = ?"
                    params.append(event_type.value)

                if vulnerability_id:
                    query += " AND vulnerability_id = ?"
                    params.append(vulnerability_id)

                query += " ORDER BY timestamp DESC"

                if limit:
                    query += " LIMIT ?"
                    params.append(str(limit))

                cursor.execute(query, params)
                rows = cursor.fetchall()

                # Convert rows to AuditEvent objects
                events = []
                for row in rows:
                    event_data = {
                        "event_id": row[0],
                        "event_type": row[1],
                        "timestamp": row[2],
                        "vulnerability_id": row[3],
                        "package_name": row[4],
                        "severity": row[5],
                        "action_taken": row[6],
                        "outcome": row[7],
                        "user_id": row[8],
                        "system_component": row[9],
                        "details": json.loads(row[10]) if row[10] else {},
                        "metadata": json.loads(row[11]) if row[11] else {},
                    }

                    events.append(AuditEvent.from_dict(event_data))

                return events

        except Exception as e:
            self.logger.error(f"Failed to retrieve audit events: {e}")
            raise

    def get_vulnerability_timeline(self, vulnerability_id: str) -> List[AuditEvent]:
        """
        Get complete timeline for a specific vulnerability.

        Args:
            vulnerability_id: ID of the vulnerability

        Returns:
            List of audit events for the vulnerability, ordered by timestamp
        """
        return self.get_audit_events(vulnerability_id=vulnerability_id)

    def calculate_compliance_metrics(
        self,
        current_report: SecurityReport,
        historical_reports: Optional[List[SecurityReport]] = None,
    ) -> ComplianceMetrics:
        """
        Calculate comprehensive compliance metrics.

        Args:
            current_report: Latest security report
            historical_reports: Historical reports for trend analysis

        Returns:
            Calculated compliance metrics
        """
        # Get recent audit events for timing analysis
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_events = self.get_audit_events(start_date=thirty_days_ago)

        # Calculate mean time to detection (time between vulnerability publication and detection)
        detection_times: List[float] = []
        for event in recent_events:
            if event.event_type == AuditEventType.VULNERABILITY_DETECTED:
                # This would require vulnerability publication dates from external sources
                # For now, we'll use a placeholder calculation
                pass

        # Calculate mean time to remediation
        remediation_times = []
        vulnerability_timelines: Dict[str, List[AuditEvent]] = {}

        for event in recent_events:
            if event.vulnerability_id:
                if event.vulnerability_id not in vulnerability_timelines:
                    vulnerability_timelines[event.vulnerability_id] = []
                vulnerability_timelines[event.vulnerability_id].append(event)

        for vuln_id, events in vulnerability_timelines.items():
            events.sort(key=lambda e: e.timestamp)

            detected_time = None
            resolved_time = None

            for event in events:
                if event.event_type == AuditEventType.VULNERABILITY_DETECTED:
                    detected_time = event.timestamp
                elif event.event_type == AuditEventType.VULNERABILITY_RESOLVED:
                    resolved_time = event.timestamp
                    break

            if detected_time and resolved_time:
                remediation_time = (
                    resolved_time - detected_time
                ).total_seconds() / 3600
                remediation_times.append(remediation_time)

        # Calculate policy violations
        policy_violations = len(
            [
                e
                for e in recent_events
                if e.event_type == AuditEventType.POLICY_VIOLATION
            ]
        )

        # Calculate overdue remediations (based on policy thresholds)
        # Count vulnerabilities that exceeded policy thresholds, regardless of resolution status
        overdue_count = 0
        for vuln in current_report.vulnerabilities:
            if vuln.severity in [
                VulnerabilitySeverity.CRITICAL,
                VulnerabilitySeverity.HIGH,
            ]:
                # Check if it's overdue based on policy thresholds
                hours_old = (
                    datetime.now() - vuln.discovered_date
                ).total_seconds() / 3600

                # Consider critical/high vulnerabilities as overdue if they exceed policy thresholds
                if (
                    vuln.severity == VulnerabilitySeverity.CRITICAL and hours_old > 24
                ) or (vuln.severity == VulnerabilitySeverity.HIGH and hours_old > 72):
                    overdue_count += 1

        # Calculate compliance score (0-100)
        compliance_score = 100.0

        # Deduct points for unresolved critical/high vulnerabilities
        compliance_score -= current_report.critical_count * 20
        compliance_score -= current_report.high_count * 10
        compliance_score -= policy_violations * 5
        compliance_score -= overdue_count * 15

        compliance_score = max(0.0, compliance_score)

        # Check scan frequency compliance (daily scans expected)
        scan_events = [
            e for e in recent_events if e.event_type == AuditEventType.SCAN_COMPLETED
        ]
        scan_frequency_compliance = (
            len(scan_events) >= 25
        )  # At least 25 scans in 30 days

        metrics = ComplianceMetrics(
            assessment_date=datetime.now(),
            total_vulnerabilities=current_report.vulnerability_count,
            critical_vulnerabilities=current_report.critical_count,
            high_vulnerabilities=current_report.high_count,
            medium_vulnerabilities=current_report.medium_count,
            low_vulnerabilities=current_report.low_count,
            unresolved_critical=current_report.critical_count,
            unresolved_high=current_report.high_count,
            mean_time_to_detection=(
                sum(detection_times) / len(detection_times) if detection_times else None
            ),
            mean_time_to_remediation=(
                sum(remediation_times) / len(remediation_times)
                if remediation_times
                else None
            ),
            compliance_score=compliance_score,
            policy_violations=policy_violations,
            overdue_remediations=overdue_count,
            scan_frequency_compliance=scan_frequency_compliance,
        )

        # Store metrics in database
        self._store_compliance_metrics(metrics)

        # Log compliance check
        self.log_compliance_check(metrics)

        return metrics

    def _store_compliance_metrics(self, metrics: ComplianceMetrics) -> None:
        """Store compliance metrics in database."""
        if not self._database_initialized:
            self.logger.warning(
                "Database not initialized, skipping compliance metrics storage"
            )
            return

        try:
            with sqlite3.connect(self.audit_db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO compliance_metrics (
                        assessment_date, total_vulnerabilities, critical_vulnerabilities,
                        high_vulnerabilities, medium_vulnerabilities, low_vulnerabilities,
                        unresolved_critical, unresolved_high, mean_time_to_detection,
                        mean_time_to_remediation, compliance_score, policy_violations,
                        overdue_remediations, scan_frequency_compliance
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        metrics.assessment_date.isoformat(),
                        metrics.total_vulnerabilities,
                        metrics.critical_vulnerabilities,
                        metrics.high_vulnerabilities,
                        metrics.medium_vulnerabilities,
                        metrics.low_vulnerabilities,
                        metrics.unresolved_critical,
                        metrics.unresolved_high,
                        metrics.mean_time_to_detection,
                        metrics.mean_time_to_remediation,
                        metrics.compliance_score,
                        metrics.policy_violations,
                        metrics.overdue_remediations,
                        1 if metrics.scan_frequency_compliance else 0,
                    ),
                )

                conn.commit()

        except Exception as e:
            self.logger.error(f"Failed to store compliance metrics: {e}")
            raise

    def generate_compliance_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        output_file: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive compliance report.

        Args:
            start_date: Start date for report period
            end_date: End date for report period
            output_file: Optional file to save the report

        Returns:
            Dictionary containing compliance report data
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Get audit events for the period
        events = self.get_audit_events(start_date=start_date, end_date=end_date)

        # Get compliance metrics for the period
        metrics_rows = []
        if self._database_initialized:
            try:
                with sqlite3.connect(self.audit_db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT * FROM compliance_metrics 
                        WHERE assessment_date >= ? AND assessment_date <= ?
                        ORDER BY assessment_date DESC
                    """,
                        (start_date.isoformat(), end_date.isoformat()),
                    )

                    metrics_rows = cursor.fetchall()
            except Exception as e:
                self.logger.error(f"Failed to retrieve compliance metrics: {e}")
                metrics_rows = []
        else:
            self.logger.warning(
                "Database not initialized, compliance metrics history will be empty"
            )

        # Analyze events by type
        event_summary = {}
        for event_type in AuditEventType:
            event_summary[event_type.value] = len(
                [e for e in events if e.event_type == event_type]
            )

        # Calculate vulnerability lifecycle metrics
        vulnerability_lifecycles = self._analyze_vulnerability_lifecycles(events)

        # Generate report
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "total_events": len(events),
                "generator": "vet-core-security-audit-trail",
                "version": "1.0.0",
            },
            "executive_summary": {
                "total_audit_events": len(events),
                "vulnerabilities_detected": event_summary.get(
                    "vulnerability_detected", 0
                ),
                "vulnerabilities_resolved": event_summary.get(
                    "vulnerability_resolved", 0
                ),
                "scans_completed": event_summary.get("scan_completed", 0),
                "policy_violations": event_summary.get("policy_violation", 0),
                "compliance_checks": event_summary.get("compliance_check", 0),
            },
            "event_summary": event_summary,
            "vulnerability_lifecycle_analysis": vulnerability_lifecycles,
            "compliance_metrics_history": [
                {
                    "assessment_date": row[1],
                    "total_vulnerabilities": row[2],
                    "critical_vulnerabilities": row[3],
                    "compliance_score": row[12],
                    "policy_violations": row[13],
                    "overdue_remediations": row[14],
                }
                for row in metrics_rows
            ],
            "audit_trail": [
                event.to_dict() for event in events[-100:]
            ],  # Last 100 events
        }

        # Save to file if requested
        if output_file:
            self._save_compliance_report(report, output_file)

        return report

    def _analyze_vulnerability_lifecycles(
        self, events: List[AuditEvent]
    ) -> Dict[str, Any]:
        """Analyze vulnerability lifecycles from audit events."""
        vulnerability_data: Dict[str, Dict[str, Any]] = {}

        for event in events:
            if event.vulnerability_id:
                if event.vulnerability_id not in vulnerability_data:
                    vulnerability_data[event.vulnerability_id] = {
                        "events": [],
                        "package_name": event.package_name,
                        "severity": event.severity.value if event.severity else None,
                    }
                vulnerability_data[event.vulnerability_id]["events"].append(event)

        # Analyze lifecycles
        lifecycle_analysis: Dict[str, Any] = {
            "total_vulnerabilities_tracked": len(vulnerability_data),
            "resolved_vulnerabilities": 0,
            "unresolved_vulnerabilities": 0,
            "mean_resolution_time_hours": 0,
            "vulnerability_details": [],
        }

        resolution_times = []

        for vuln_id, data in vulnerability_data.items():
            events = sorted(data["events"], key=lambda e: e.timestamp)

            detected_time = None
            resolved_time = None

            for event in events:
                if event.event_type == AuditEventType.VULNERABILITY_DETECTED:
                    detected_time = event.timestamp
                elif event.event_type == AuditEventType.VULNERABILITY_RESOLVED:
                    resolved_time = event.timestamp

            is_resolved = resolved_time is not None
            resolution_time = None

            if detected_time and resolved_time:
                resolution_time = (resolved_time - detected_time).total_seconds() / 3600
                resolution_times.append(resolution_time)

            if is_resolved:
                lifecycle_analysis["resolved_vulnerabilities"] += 1
            else:
                lifecycle_analysis["unresolved_vulnerabilities"] += 1

            lifecycle_analysis["vulnerability_details"].append(
                {
                    "vulnerability_id": vuln_id,
                    "package_name": data["package_name"],
                    "severity": data["severity"],
                    "detected_at": detected_time.isoformat() if detected_time else None,
                    "resolved_at": resolved_time.isoformat() if resolved_time else None,
                    "resolution_time_hours": resolution_time,
                    "is_resolved": is_resolved,
                    "total_events": len(events),
                }
            )

        if resolution_times:
            lifecycle_analysis["mean_resolution_time_hours"] = sum(
                resolution_times
            ) / len(resolution_times)

        return lifecycle_analysis

    def _save_compliance_report(
        self, report: Dict[str, Any], output_file: Path
    ) -> None:
        """Save compliance report to file."""
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2, default=str)
            self.logger.info(f"Compliance report saved to {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save compliance report: {e}")
            raise

    def cleanup_old_events(self) -> int:
        """
        Clean up audit events older than retention period.

        Returns:
            Number of events deleted
        """
        if not self._database_initialized:
            self.logger.warning(
                "Database not initialized, skipping cleanup of old events"
            )
            return 0

        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        try:
            with sqlite3.connect(self.audit_db_path) as conn:
                cursor = conn.cursor()

                # Count events to be deleted
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM audit_events 
                    WHERE timestamp < ?
                """,
                    (cutoff_date.isoformat(),),
                )

                count: int = cursor.fetchone()[0]

                # Delete old events
                cursor.execute(
                    """
                    DELETE FROM audit_events 
                    WHERE timestamp < ?
                """,
                    (cutoff_date.isoformat(),),
                )

                conn.commit()

                self.logger.info(f"Cleaned up {count} old audit events")
                return count

        except Exception as e:
            self.logger.error(f"Failed to cleanup old events: {e}")
            raise
