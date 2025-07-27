"""
Security metrics and trends analysis module.

This module provides comprehensive analysis of security metrics, trends,
and performance indicators for vulnerability management reporting.

Requirements addressed:
- 3.3: Vulnerability prioritization with timeline recommendations
- 4.3: Compliance report generation with vulnerability management evidence
- 4.4: Evidence of proactive security management practices
"""

import json
import logging
import sqlite3
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .audit_trail import AuditEvent, AuditEventType, SecurityAuditTrail
from .models import SecurityReport, VulnerabilitySeverity
from .status_tracker import (
    ProgressStage,
    VulnerabilityStatus,
    VulnerabilityStatusTracker,
)


@dataclass
class MetricPoint:
    """Represents a single metric data point."""

    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric point to dictionary representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "metadata": self.metadata,
        }


@dataclass
class TrendAnalysis:
    """Represents trend analysis results."""

    metric_name: str
    time_period: str
    data_points: List[MetricPoint]
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_strength: float  # 0.0 to 1.0
    average_value: float
    min_value: float
    max_value: float
    variance: float
    growth_rate: float  # percentage change

    def to_dict(self) -> Dict[str, Any]:
        """Convert trend analysis to dictionary representation."""
        return {
            "metric_name": self.metric_name,
            "time_period": self.time_period,
            "data_points": [point.to_dict() for point in self.data_points],
            "trend_direction": self.trend_direction,
            "trend_strength": self.trend_strength,
            "statistics": {
                "average_value": self.average_value,
                "min_value": self.min_value,
                "max_value": self.max_value,
                "variance": self.variance,
                "growth_rate": self.growth_rate,
            },
        }


@dataclass
class SecurityMetrics:
    """Comprehensive security metrics."""

    # Vulnerability metrics
    total_vulnerabilities: int = 0
    critical_vulnerabilities: int = 0
    high_vulnerabilities: int = 0
    medium_vulnerabilities: int = 0
    low_vulnerabilities: int = 0
    resolved_vulnerabilities: int = 0

    # Time-based metrics
    mean_time_to_detection: Optional[float] = None  # hours
    mean_time_to_assessment: Optional[float] = None  # hours
    mean_time_to_resolution: Optional[float] = None  # hours
    mean_time_to_verification: Optional[float] = None  # hours

    # Performance metrics
    scan_frequency: float = 0.0  # scans per day
    detection_rate: float = 0.0  # vulnerabilities per scan
    resolution_rate: float = 0.0  # percentage
    false_positive_rate: float = 0.0  # percentage

    # Compliance metrics
    sla_compliance_rate: float = 0.0  # percentage
    overdue_vulnerabilities: int = 0
    policy_violations: int = 0

    # Trend indicators
    vulnerability_trend: str = "stable"  # "increasing", "decreasing", "stable"
    resolution_trend: str = "stable"
    performance_trend: str = "stable"

    # Metadata
    calculated_at: datetime = field(default_factory=datetime.now)
    calculation_period: str = "30_days"

    def to_dict(self) -> Dict[str, Any]:
        """Convert security metrics to dictionary representation."""
        return {
            "vulnerability_metrics": {
                "total_vulnerabilities": self.total_vulnerabilities,
                "critical_vulnerabilities": self.critical_vulnerabilities,
                "high_vulnerabilities": self.high_vulnerabilities,
                "medium_vulnerabilities": self.medium_vulnerabilities,
                "low_vulnerabilities": self.low_vulnerabilities,
                "resolved_vulnerabilities": self.resolved_vulnerabilities,
            },
            "time_based_metrics": {
                "mean_time_to_detection": self.mean_time_to_detection,
                "mean_time_to_assessment": self.mean_time_to_assessment,
                "mean_time_to_resolution": self.mean_time_to_resolution,
                "mean_time_to_verification": self.mean_time_to_verification,
            },
            "performance_metrics": {
                "scan_frequency": self.scan_frequency,
                "detection_rate": self.detection_rate,
                "resolution_rate": self.resolution_rate,
                "false_positive_rate": self.false_positive_rate,
            },
            "compliance_metrics": {
                "sla_compliance_rate": self.sla_compliance_rate,
                "overdue_vulnerabilities": self.overdue_vulnerabilities,
                "policy_violations": self.policy_violations,
            },
            "trend_indicators": {
                "vulnerability_trend": self.vulnerability_trend,
                "resolution_trend": self.resolution_trend,
                "performance_trend": self.performance_trend,
            },
            "metadata": {
                "calculated_at": self.calculated_at.isoformat(),
                "calculation_period": self.calculation_period,
            },
        }


class SecurityMetricsAnalyzer:
    """
    Comprehensive security metrics and trends analysis system.

    This class provides detailed analysis of security metrics, trends,
    and performance indicators for vulnerability management reporting.
    """

    def __init__(
        self,
        audit_trail: SecurityAuditTrail,
        status_tracker: VulnerabilityStatusTracker,
        metrics_db_path: Optional[Path] = None,
    ) -> None:
        """
        Initialize the security metrics analyzer.

        Args:
            audit_trail: Security audit trail system
            status_tracker: Vulnerability status tracker
            metrics_db_path: Path to metrics database
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.audit_trail = audit_trail
        self.status_tracker = status_tracker

        # Set up metrics database
        if metrics_db_path is None:
            metrics_db_path = Path.cwd() / "security-metrics.db"
        self.metrics_db_path = metrics_db_path

        # Initialize database
        self._init_metrics_database()

        self.logger.info(
            f"Initialized SecurityMetricsAnalyzer with database: {self.metrics_db_path}"
        )

    def _init_metrics_database(self) -> None:
        """Initialize the metrics database."""
        try:
            self.metrics_db_path.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(self.metrics_db_path) as conn:
                cursor = conn.cursor()

                # Create metrics snapshots table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS metrics_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        snapshot_date TEXT NOT NULL,
                        metrics_data TEXT NOT NULL,  -- JSON
                        calculation_period TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create trend data table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trend_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        value REAL NOT NULL,
                        metadata TEXT,  -- JSON
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create indexes
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_snapshots_date ON metrics_snapshots(snapshot_date)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_trend_metric ON trend_data(metric_name)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_trend_timestamp ON trend_data(timestamp)"
                )

                conn.commit()

        except Exception as e:
            self.logger.error(f"Failed to initialize metrics database: {e}")
            raise

    def calculate_current_metrics(
        self, period_days: int = 30, include_trends: bool = True
    ) -> SecurityMetrics:
        """
        Calculate current security metrics.

        Args:
            period_days: Number of days to analyze
            include_trends: Whether to calculate trend indicators

        Returns:
            SecurityMetrics with current calculations
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)

        self.logger.info(
            f"Calculating security metrics for period: {start_date} to {end_date}"
        )

        # Get audit events for the period
        events = self.audit_trail.get_audit_events(
            start_date=start_date, end_date=end_date
        )

        # Get current tracking records
        tracking_records = self.status_tracker.get_all_tracking_records()

        # Calculate vulnerability metrics
        vulnerability_metrics = self._calculate_vulnerability_metrics(
            events, tracking_records
        )

        # Calculate time-based metrics
        time_metrics = self._calculate_time_based_metrics(events, tracking_records)

        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(
            events, tracking_records, period_days
        )

        # Calculate compliance metrics
        compliance_metrics = self._calculate_compliance_metrics(tracking_records)

        # Calculate trend indicators if requested
        trend_indicators = {}
        if include_trends:
            trend_indicators = self._calculate_trend_indicators(period_days)

        # Create comprehensive metrics object
        metrics = SecurityMetrics(
            # Vulnerability metrics
            total_vulnerabilities=vulnerability_metrics["total"],
            critical_vulnerabilities=vulnerability_metrics["critical"],
            high_vulnerabilities=vulnerability_metrics["high"],
            medium_vulnerabilities=vulnerability_metrics["medium"],
            low_vulnerabilities=vulnerability_metrics["low"],
            resolved_vulnerabilities=vulnerability_metrics["resolved"],
            # Time-based metrics
            mean_time_to_detection=time_metrics.get("detection"),
            mean_time_to_assessment=time_metrics.get("assessment"),
            mean_time_to_resolution=time_metrics.get("resolution"),
            mean_time_to_verification=time_metrics.get("verification"),
            # Performance metrics
            scan_frequency=performance_metrics["scan_frequency"],
            detection_rate=performance_metrics["detection_rate"],
            resolution_rate=performance_metrics["resolution_rate"],
            false_positive_rate=performance_metrics.get("false_positive_rate", 0.0),
            # Compliance metrics
            sla_compliance_rate=compliance_metrics["sla_compliance_rate"],
            overdue_vulnerabilities=compliance_metrics["overdue_count"],
            policy_violations=compliance_metrics["policy_violations"],
            # Trend indicators
            vulnerability_trend=trend_indicators.get("vulnerability_trend", "stable"),
            resolution_trend=trend_indicators.get("resolution_trend", "stable"),
            performance_trend=trend_indicators.get("performance_trend", "stable"),
            # Metadata
            calculated_at=datetime.now(),
            calculation_period=f"{period_days}_days",
        )

        # Save metrics snapshot
        self._save_metrics_snapshot(metrics)

        self.logger.info("Security metrics calculation completed")
        return metrics

    def _calculate_vulnerability_metrics(
        self, events: List[AuditEvent], tracking_records: List
    ) -> Dict[str, int]:
        """Calculate vulnerability-related metrics."""
        # Count vulnerabilities by severity from tracking records
        severity_counts = {
            "total": len(tracking_records),
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "resolved": 0,
        }

        for record in tracking_records:
            severity_key = record.severity.value.lower()
            if severity_key in severity_counts:
                severity_counts[severity_key] += 1

            if record.current_status in [
                VulnerabilityStatus.RESOLVED,
                VulnerabilityStatus.CLOSED,
            ]:
                severity_counts["resolved"] += 1

        return severity_counts

    def _calculate_time_based_metrics(
        self, events: List[AuditEvent], tracking_records: List
    ) -> Dict[str, Optional[float]]:
        """Calculate time-based metrics."""
        # Group events by vulnerability
        vulnerability_timelines = defaultdict(list)
        for event in events:
            if event.vulnerability_id:
                vulnerability_timelines[event.vulnerability_id].append(event)

        # Calculate time intervals
        detection_times = []
        assessment_times = []
        resolution_times = []
        verification_times = []

        for vuln_id, vuln_events in vulnerability_timelines.items():
            vuln_events.sort(key=lambda e: e.timestamp)

            # Find key timestamps
            detected_time = None
            assessed_time = None
            resolved_time = None
            verified_time = None

            for event in vuln_events:
                if event.event_type == AuditEventType.VULNERABILITY_DETECTED:
                    detected_time = event.timestamp
                elif event.event_type == AuditEventType.RISK_ASSESSMENT_PERFORMED:
                    assessed_time = event.timestamp
                elif event.event_type == AuditEventType.VULNERABILITY_RESOLVED:
                    resolved_time = event.timestamp
                # Add verification event type if available

            # Calculate intervals
            if detected_time and assessed_time:
                assessment_times.append(
                    (assessed_time - detected_time).total_seconds() / 3600
                )

            if detected_time and resolved_time:
                resolution_times.append(
                    (resolved_time - detected_time).total_seconds() / 3600
                )

        # Calculate means
        return {
            "detection": None,  # Would need external data source
            "assessment": (
                statistics.mean(assessment_times) if assessment_times else None
            ),
            "resolution": (
                statistics.mean(resolution_times) if resolution_times else None
            ),
            "verification": (
                statistics.mean(verification_times) if verification_times else None
            ),
        }

    def _calculate_performance_metrics(
        self, events: List[AuditEvent], tracking_records: List, period_days: int
    ) -> Dict[str, float]:
        """Calculate performance metrics."""
        # Count scans
        scan_events = [
            e for e in events if e.event_type == AuditEventType.SCAN_COMPLETED
        ]
        scan_frequency = len(scan_events) / period_days if period_days > 0 else 0.0

        # Calculate detection rate
        vulnerability_events = [
            e for e in events if e.event_type == AuditEventType.VULNERABILITY_DETECTED
        ]
        detection_rate = (
            len(vulnerability_events) / len(scan_events) if scan_events else 0.0
        )

        # Calculate resolution rate
        resolved_count = sum(
            1
            for record in tracking_records
            if record.current_status
            in [VulnerabilityStatus.RESOLVED, VulnerabilityStatus.CLOSED]
        )
        resolution_rate = (
            (resolved_count / len(tracking_records) * 100) if tracking_records else 0.0
        )

        return {
            "scan_frequency": scan_frequency,
            "detection_rate": detection_rate,
            "resolution_rate": resolution_rate,
        }

    def _calculate_compliance_metrics(self, tracking_records: List) -> Dict[str, Any]:
        """Calculate compliance metrics."""
        if not tracking_records:
            return {
                "sla_compliance_rate": 100.0,
                "overdue_count": 0,
                "policy_violations": 0,
            }

        # Count overdue vulnerabilities
        overdue_count = 0
        for record in tracking_records:
            if record.progress_metrics and record.progress_metrics.is_overdue:
                overdue_count += 1

        # Calculate SLA compliance rate
        sla_compliance_rate = (
            (len(tracking_records) - overdue_count) / len(tracking_records) * 100
        )

        # Get policy violations from recent events
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_events = self.audit_trail.get_audit_events(start_date=thirty_days_ago)
        policy_violations = len(
            [
                e
                for e in recent_events
                if e.event_type == AuditEventType.POLICY_VIOLATION
            ]
        )

        return {
            "sla_compliance_rate": sla_compliance_rate,
            "overdue_count": overdue_count,
            "policy_violations": policy_violations,
        }

    def _calculate_trend_indicators(self, period_days: int) -> Dict[str, str]:
        """Calculate trend indicators."""
        # Get historical metrics for comparison
        historical_metrics = self._get_historical_metrics(
            period_days * 2
        )  # Double period for comparison

        if len(historical_metrics) < 2:
            return {
                "vulnerability_trend": "stable",
                "resolution_trend": "stable",
                "performance_trend": "stable",
            }

        # Compare recent vs older metrics
        recent_metrics = historical_metrics[-period_days // 2 :]  # Recent half
        older_metrics = historical_metrics[: period_days // 2]  # Older half

        # Calculate trends (simplified)
        trends = {}

        # Vulnerability trend
        recent_vuln_avg = statistics.mean(
            [m.total_vulnerabilities for m in recent_metrics]
        )
        older_vuln_avg = statistics.mean(
            [m.total_vulnerabilities for m in older_metrics]
        )

        if recent_vuln_avg > older_vuln_avg * 1.1:
            trends["vulnerability_trend"] = "increasing"
        elif recent_vuln_avg < older_vuln_avg * 0.9:
            trends["vulnerability_trend"] = "decreasing"
        else:
            trends["vulnerability_trend"] = "stable"

        # Resolution trend
        recent_res_avg = statistics.mean([m.resolution_rate for m in recent_metrics])
        older_res_avg = statistics.mean([m.resolution_rate for m in older_metrics])

        if recent_res_avg > older_res_avg * 1.1:
            trends["resolution_trend"] = "increasing"
        elif recent_res_avg < older_res_avg * 0.9:
            trends["resolution_trend"] = "decreasing"
        else:
            trends["resolution_trend"] = "stable"

        # Performance trend (based on scan frequency)
        recent_perf_avg = statistics.mean([m.scan_frequency for m in recent_metrics])
        older_perf_avg = statistics.mean([m.scan_frequency for m in older_metrics])

        if recent_perf_avg > older_perf_avg * 1.1:
            trends["performance_trend"] = "increasing"
        elif recent_perf_avg < older_perf_avg * 0.9:
            trends["performance_trend"] = "decreasing"
        else:
            trends["performance_trend"] = "stable"

        return trends

    def analyze_trends(
        self, metric_names: List[str], period_days: int = 30, granularity: str = "daily"
    ) -> List[TrendAnalysis]:
        """
        Analyze trends for specific metrics.

        Args:
            metric_names: List of metric names to analyze
            period_days: Number of days to analyze
            granularity: Time granularity ("daily", "weekly", "monthly")

        Returns:
            List of TrendAnalysis objects
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)

        trend_analyses = []

        for metric_name in metric_names:
            # Get trend data for the metric
            trend_data = self._get_trend_data(metric_name, start_date, end_date)

            if not trend_data:
                self.logger.warning(f"No trend data found for metric: {metric_name}")
                continue

            # Aggregate data by granularity
            aggregated_data = self._aggregate_trend_data(trend_data, granularity)

            # Calculate trend statistics
            values = [point.value for point in aggregated_data]

            if len(values) < 2:
                continue

            # Calculate trend direction and strength
            trend_direction, trend_strength = self._calculate_trend_direction(values)

            # Calculate statistics
            avg_value = statistics.mean(values)
            min_value = min(values)
            max_value = max(values)
            variance = statistics.variance(values) if len(values) > 1 else 0.0

            # Calculate growth rate
            growth_rate = (
                ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0.0
            )

            trend_analysis = TrendAnalysis(
                metric_name=metric_name,
                time_period=f"{period_days}_days_{granularity}",
                data_points=aggregated_data,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                average_value=avg_value,
                min_value=min_value,
                max_value=max_value,
                variance=variance,
                growth_rate=growth_rate,
            )

            trend_analyses.append(trend_analysis)

        return trend_analyses

    def generate_metrics_report(
        self,
        include_trends: bool = True,
        include_historical: bool = True,
        period_days: int = 30,
        output_file: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive metrics report.

        Args:
            include_trends: Whether to include trend analysis
            include_historical: Whether to include historical data
            period_days: Analysis period in days
            output_file: Optional file to save the report

        Returns:
            Dictionary containing the metrics report
        """
        self.logger.info("Generating comprehensive metrics report")

        # Calculate current metrics
        current_metrics = self.calculate_current_metrics(period_days, include_trends)

        # Build report
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "analysis_period_days": period_days,
                "report_type": "comprehensive_security_metrics",
                "version": "1.0.0",
            },
            "current_metrics": current_metrics.to_dict(),
        }

        # Add trend analysis if requested
        if include_trends:
            trend_metrics = [
                "total_vulnerabilities",
                "resolution_rate",
                "scan_frequency",
                "sla_compliance_rate",
            ]
            trends = self.analyze_trends(trend_metrics, period_days)
            report["trend_analysis"] = [trend.to_dict() for trend in trends]

        # Add historical data if requested
        if include_historical:
            historical_metrics = self._get_historical_metrics(
                period_days * 3
            )  # 3x period for context
            report["historical_data"] = [
                metrics.to_dict() for metrics in historical_metrics[-30:]
            ]  # Last 30 snapshots

        # Add insights and recommendations
        report["insights"] = self._generate_insights(
            current_metrics, report.get("trend_analysis", [])
        )
        report["recommendations"] = self._generate_recommendations(current_metrics)

        # Save to file if requested
        if output_file:
            self._save_report(report, output_file)

        self.logger.info("Metrics report generation completed")
        return report

    def _get_trend_data(
        self, metric_name: str, start_date: datetime, end_date: datetime
    ) -> List[MetricPoint]:
        """Get trend data for a specific metric."""
        try:
            with sqlite3.connect(self.metrics_db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT timestamp, value, metadata
                    FROM trend_data
                    WHERE metric_name = ? AND timestamp BETWEEN ? AND ?
                    ORDER BY timestamp ASC
                """,
                    (metric_name, start_date.isoformat(), end_date.isoformat()),
                )

                trend_data = []
                for row in cursor.fetchall():
                    point = MetricPoint(
                        timestamp=datetime.fromisoformat(row[0]),
                        value=row[1],
                        metadata=json.loads(row[2]) if row[2] else {},
                    )
                    trend_data.append(point)

                return trend_data

        except Exception as e:
            self.logger.error(f"Failed to get trend data for {metric_name}: {e}")
            return []

    def _aggregate_trend_data(
        self, trend_data: List[MetricPoint], granularity: str
    ) -> List[MetricPoint]:
        """Aggregate trend data by time granularity."""
        if not trend_data:
            return []

        # Group data points by time period
        grouped_data = defaultdict(list)

        for point in trend_data:
            if granularity == "daily":
                key = point.timestamp.date()
            elif granularity == "weekly":
                # Get Monday of the week
                key = point.timestamp.date() - timedelta(days=point.timestamp.weekday())
            elif granularity == "monthly":
                key = point.timestamp.replace(day=1).date()
            else:
                key = point.timestamp.date()  # Default to daily

            grouped_data[key].append(point)

        # Aggregate each group
        aggregated_data = []
        for date_key, points in sorted(grouped_data.items()):
            avg_value = statistics.mean([p.value for p in points])

            # Use the latest timestamp in the group
            latest_timestamp = max([p.timestamp for p in points])

            aggregated_point = MetricPoint(
                timestamp=latest_timestamp,
                value=avg_value,
                metadata={"aggregated_from": len(points), "granularity": granularity},
            )
            aggregated_data.append(aggregated_point)

        return aggregated_data

    def _calculate_trend_direction(self, values: List[float]) -> Tuple[str, float]:
        """Calculate trend direction and strength."""
        if len(values) < 2:
            return "stable", 0.0

        # Simple linear regression to determine trend
        n = len(values)
        x_values = list(range(n))

        # Calculate slope
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(values)

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        if denominator == 0:
            return "stable", 0.0

        slope = numerator / denominator

        # Determine direction
        if slope > 0.1:
            direction = "increasing"
        elif slope < -0.1:
            direction = "decreasing"
        else:
            direction = "stable"

        # Calculate strength (normalized absolute slope)
        strength = min(abs(slope) / max(values) if max(values) > 0 else 0, 1.0)

        return direction, strength

    def _get_historical_metrics(self, days: int) -> List[SecurityMetrics]:
        """Get historical metrics snapshots."""
        try:
            with sqlite3.connect(self.metrics_db_path) as conn:
                cursor = conn.cursor()

                start_date = (datetime.now() - timedelta(days=days)).isoformat()

                cursor.execute(
                    """
                    SELECT metrics_data
                    FROM metrics_snapshots
                    WHERE snapshot_date >= ?
                    ORDER BY snapshot_date ASC
                """,
                    (start_date,),
                )

                historical_metrics = []
                for row in cursor.fetchall():
                    metrics_data = json.loads(row[0])
                    # Create a simplified SecurityMetrics object from the data
                    # For trend analysis, we only need basic fields
                    metrics = SecurityMetrics(
                        total_vulnerabilities=metrics_data.get(
                            "vulnerability_metrics", {}
                        ).get("total_vulnerabilities", 0),
                        critical_vulnerabilities=metrics_data.get(
                            "vulnerability_metrics", {}
                        ).get("critical_vulnerabilities", 0),
                        high_vulnerabilities=metrics_data.get(
                            "vulnerability_metrics", {}
                        ).get("high_vulnerabilities", 0),
                        medium_vulnerabilities=metrics_data.get(
                            "vulnerability_metrics", {}
                        ).get("medium_vulnerabilities", 0),
                        low_vulnerabilities=metrics_data.get(
                            "vulnerability_metrics", {}
                        ).get("low_vulnerabilities", 0),
                        resolved_vulnerabilities=metrics_data.get(
                            "vulnerability_metrics", {}
                        ).get("resolved_vulnerabilities", 0),
                        scan_frequency=metrics_data.get("performance_metrics", {}).get(
                            "scan_frequency", 0.0
                        ),
                        resolution_rate=metrics_data.get("performance_metrics", {}).get(
                            "resolution_rate", 0.0
                        ),
                        sla_compliance_rate=metrics_data.get(
                            "compliance_metrics", {}
                        ).get("sla_compliance_rate", 0.0),
                        calculated_at=datetime.fromisoformat(
                            metrics_data.get("metadata", {}).get(
                                "calculated_at", datetime.now().isoformat()
                            )
                        ),
                        calculation_period=metrics_data.get("metadata", {}).get(
                            "calculation_period", "30_days"
                        ),
                    )
                    historical_metrics.append(metrics)

                return historical_metrics

        except Exception as e:
            self.logger.error(f"Failed to get historical metrics: {e}")
            return []

    def _save_metrics_snapshot(self, metrics: SecurityMetrics) -> None:
        """Save metrics snapshot to database."""
        try:
            with sqlite3.connect(self.metrics_db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO metrics_snapshots (
                        snapshot_date, metrics_data, calculation_period
                    ) VALUES (?, ?, ?)
                """,
                    (
                        metrics.calculated_at.isoformat(),
                        json.dumps(metrics.to_dict()),
                        metrics.calculation_period,
                    ),
                )

                conn.commit()

        except Exception as e:
            self.logger.error(f"Failed to save metrics snapshot: {e}")

    def _generate_insights(
        self, current_metrics: SecurityMetrics, trend_analysis: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate insights from metrics and trends."""
        insights = []

        # Vulnerability insights
        if current_metrics.critical_vulnerabilities > 0:
            insights.append(
                f"⚠️ {current_metrics.critical_vulnerabilities} critical vulnerabilities require immediate attention"
            )

        if current_metrics.resolution_rate < 80:
            insights.append(
                f"📉 Resolution rate is {current_metrics.resolution_rate:.1f}%, below recommended 80% threshold"
            )

        if current_metrics.sla_compliance_rate < 95:
            insights.append(
                f"⏰ SLA compliance is {current_metrics.sla_compliance_rate:.1f}%, below target 95%"
            )

        # Trend insights
        for trend in trend_analysis:
            if (
                trend["trend_direction"] == "increasing"
                and trend["metric_name"] == "total_vulnerabilities"
            ):
                insights.append(
                    "📈 Vulnerability count is trending upward - consider increasing scan frequency"
                )
            elif (
                trend["trend_direction"] == "decreasing"
                and trend["metric_name"] == "resolution_rate"
            ):
                insights.append(
                    "📉 Resolution rate is declining - review remediation processes"
                )

        # Performance insights
        if current_metrics.scan_frequency < 1.0:
            insights.append("🔍 Scan frequency is below daily recommended rate")

        if not insights:
            insights.append("✅ Security metrics are within acceptable ranges")

        return insights

    def _generate_recommendations(self, current_metrics: SecurityMetrics) -> List[str]:
        """Generate recommendations based on current metrics."""
        recommendations = []

        # Critical vulnerabilities
        if current_metrics.critical_vulnerabilities > 0:
            recommendations.append(
                "Prioritize immediate remediation of critical vulnerabilities within 24 hours"
            )

        # Resolution rate
        if current_metrics.resolution_rate < 80:
            recommendations.append(
                "Implement automated remediation for low-risk vulnerabilities to improve resolution rate"
            )

        # SLA compliance
        if current_metrics.sla_compliance_rate < 95:
            recommendations.append(
                "Review and optimize vulnerability triage process to improve SLA compliance"
            )

        # Scan frequency
        if current_metrics.scan_frequency < 1.0:
            recommendations.append(
                "Increase vulnerability scanning frequency to at least daily"
            )

        # Overdue vulnerabilities
        if current_metrics.overdue_vulnerabilities > 0:
            recommendations.append(
                f"Address {current_metrics.overdue_vulnerabilities} overdue vulnerabilities to prevent SLA violations"
            )

        if not recommendations:
            recommendations.append(
                "Continue current security practices and monitor for changes"
            )

        return recommendations

    def _save_report(self, report: Dict[str, Any], output_file: Path) -> None:
        """Save report to file."""
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2, default=str)
            self.logger.info(f"Metrics report saved to {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save metrics report: {e}")
            raise
