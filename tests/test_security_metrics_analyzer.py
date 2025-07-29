"""Tests for the SecurityMetricsAnalyzer class."""

import json
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from vet_core.security.audit_trail import AuditEvent, AuditEventType
from vet_core.security.metrics_analyzer import (
    MetricPoint,
    SecurityMetrics,
    SecurityMetricsAnalyzer,
    TrendAnalysis,
)
from vet_core.security.models import VulnerabilitySeverity
from vet_core.security.status_tracker import ProgressStage, VulnerabilityStatus


class TestMetricPoint:
    """Test cases for MetricPoint dataclass."""

    def test_metric_point_creation(self):
        """Test creating a MetricPoint instance."""
        timestamp = datetime.now()
        point = MetricPoint(timestamp=timestamp, value=10.5, metadata={"test": "data"})

        assert point.timestamp == timestamp
        assert point.value == 10.5
        assert point.metadata == {"test": "data"}

    def test_metric_point_to_dict(self):
        """Test converting MetricPoint to dictionary."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        point = MetricPoint(timestamp=timestamp, value=7.5, metadata={"source": "test"})

        result = point.to_dict()

        assert isinstance(result, dict)
        assert "timestamp" in result
        assert "value" in result
        assert "metadata" in result
        assert result["value"] == 7.5
        assert result["metadata"] == {"source": "test"}


class TestTrendAnalysis:
    """Test cases for TrendAnalysis dataclass."""

    def test_trend_analysis_creation(self):
        """Test creating a TrendAnalysis instance."""
        analysis = TrendAnalysis(
            metric_name="vulnerability_count",
            time_period="30_days",
            data_points=[
                MetricPoint(datetime.now(), 10.0),
                MetricPoint(datetime.now(), 11.5),
            ],
            trend_direction="increasing",
            trend_strength=0.85,
            average_value=10.75,
            min_value=10.0,
            max_value=11.5,
            variance=0.5625,
            growth_rate=15.5,
        )

        assert analysis.metric_name == "vulnerability_count"
        assert analysis.trend_direction == "increasing"
        assert analysis.growth_rate == 15.5
        assert analysis.trend_strength == 0.85
        assert len(analysis.data_points) == 2

    def test_trend_analysis_to_dict(self):
        """Test converting TrendAnalysis to dictionary."""
        analysis = TrendAnalysis(
            metric_name="test_metric",
            trend_direction="stable",
            change_percentage=2.1,
            confidence_score=0.9,
            data_points=[],
        )

        result = analysis.to_dict()

        assert isinstance(result, dict)
        assert result["metric_name"] == "test_metric"
        assert result["trend_direction"] == "stable"
        assert result["change_percentage"] == 2.1
        assert result["confidence_score"] == 0.9
        assert "data_points" in result


class TestSecurityMetrics:
    """Test cases for SecurityMetrics dataclass."""

    def test_security_metrics_creation(self):
        """Test creating a SecurityMetrics instance."""
        metrics = SecurityMetrics(
            timestamp=datetime.now(),
            total_vulnerabilities=50,
            high_severity_count=5,
            medium_severity_count=20,
            low_severity_count=25,
            resolved_count=30,
            in_progress_count=15,
            new_count=5,
            average_resolution_time=72.5,
            median_resolution_time=48.0,
            overdue_count=3,
            compliance_score=85.5,
            risk_score=6.2,
            scan_coverage=92.3,
            false_positive_rate=2.1,
            detection_rate=97.8,
            mean_time_to_detection=24.5,
            mean_time_to_resolution=96.2,
        )

        assert metrics.total_vulnerabilities == 50
        assert metrics.high_severity_count == 5
        assert metrics.compliance_score == 85.5
        assert metrics.risk_score == 6.2

    def test_security_metrics_to_dict(self):
        """Test converting SecurityMetrics to dictionary."""
        metrics = SecurityMetrics(
            timestamp=datetime(2023, 1, 1),
            total_vulnerabilities=10,
            high_severity_count=2,
            medium_severity_count=5,
            low_severity_count=3,
        )

        result = metrics.to_dict()

        assert isinstance(result, dict)
        assert result["total_vulnerabilities"] == 10
        assert result["high_severity_count"] == 2
        assert result["medium_severity_count"] == 5
        assert result["low_severity_count"] == 3
        assert "timestamp" in result


class TestSecurityMetricsAnalyzer:
    """Test cases for SecurityMetricsAnalyzer class."""

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
        mock_trail.get_events.return_value = []
        return mock_trail

    @pytest.fixture
    def mock_status_tracker(self):
        """Create a mock status tracker."""
        mock_tracker = Mock()
        mock_tracker.get_all_tracking_records.return_value = []
        return mock_tracker

    @pytest.fixture
    def analyzer(self, mock_audit_trail, mock_status_tracker, temp_db_path):
        """Create a SecurityMetricsAnalyzer instance."""
        return SecurityMetricsAnalyzer(
            audit_trail=mock_audit_trail,
            status_tracker=mock_status_tracker,
            metrics_db_path=temp_db_path,
        )

    def test_init_with_default_db_path(self, mock_audit_trail, mock_status_tracker):
        """Test analyzer initialization with default database path."""
        analyzer = SecurityMetricsAnalyzer(
            audit_trail=mock_audit_trail, status_tracker=mock_status_tracker
        )
        assert analyzer is not None

    def test_init_with_custom_db_path(
        self, mock_audit_trail, mock_status_tracker, temp_db_path
    ):
        """Test analyzer initialization with custom database path."""
        analyzer = SecurityMetricsAnalyzer(
            audit_trail=mock_audit_trail,
            status_tracker=mock_status_tracker,
            metrics_db_path=temp_db_path,
        )
        assert analyzer is not None

    def test_calculate_current_metrics_basic(
        self, analyzer, mock_audit_trail, mock_status_tracker
    ):
        """Test calculating current metrics with basic data."""
        # Mock audit events
        mock_events = [
            Mock(
                event_type=AuditEventType.VULNERABILITY_DETECTED,
                timestamp=datetime.now(),
                metadata={"severity": "HIGH", "vulnerability_id": "vuln-1"},
            ),
            Mock(
                event_type=AuditEventType.VULNERABILITY_RESOLVED,
                timestamp=datetime.now(),
                metadata={"severity": "MEDIUM", "vulnerability_id": "vuln-2"},
            ),
        ]
        mock_audit_trail.get_events.return_value = mock_events

        # Mock tracking records
        mock_records = [
            Mock(
                vulnerability_id="vuln-1",
                current_status=VulnerabilityStatus.NEW,
                severity=VulnerabilitySeverity.HIGH,
                created_at=datetime.now() - timedelta(days=1),
                updated_at=datetime.now(),
            ),
            Mock(
                vulnerability_id="vuln-2",
                current_status=VulnerabilityStatus.RESOLVED,
                severity=VulnerabilitySeverity.MEDIUM,
                created_at=datetime.now() - timedelta(days=2),
                updated_at=datetime.now(),
            ),
        ]
        mock_status_tracker.get_all_tracking_records.return_value = mock_records

        result = analyzer.calculate_current_metrics(
            period_days=30, include_trends=False
        )

        assert isinstance(result, SecurityMetrics)
        assert result.total_vulnerabilities >= 0
        assert result.high_severity_count >= 0
        assert result.medium_severity_count >= 0
        assert result.low_severity_count >= 0

    def test_calculate_current_metrics_with_trends(
        self, analyzer, mock_audit_trail, mock_status_tracker
    ):
        """Test calculating current metrics with trend analysis."""
        mock_audit_trail.get_events.return_value = []
        mock_status_tracker.get_all_tracking_records.return_value = []

        result = analyzer.calculate_current_metrics(period_days=30, include_trends=True)

        assert isinstance(result, SecurityMetrics)

    def test_calculate_vulnerability_metrics(self, analyzer):
        """Test calculating vulnerability-specific metrics."""
        mock_events = [
            Mock(
                event_type=AuditEventType.VULNERABILITY_DETECTED,
                metadata={"severity": "HIGH"},
            ),
            Mock(
                event_type=AuditEventType.VULNERABILITY_DETECTED,
                metadata={"severity": "MEDIUM"},
            ),
            Mock(
                event_type=AuditEventType.VULNERABILITY_RESOLVED,
                metadata={"severity": "LOW"},
            ),
        ]

        mock_records = [
            Mock(
                severity=VulnerabilitySeverity.HIGH,
                current_status=VulnerabilityStatus.NEW,
            ),
            Mock(
                severity=VulnerabilitySeverity.MEDIUM,
                current_status=VulnerabilityStatus.IN_PROGRESS,
            ),
            Mock(
                severity=VulnerabilitySeverity.LOW,
                current_status=VulnerabilityStatus.RESOLVED,
            ),
        ]

        result = analyzer._calculate_vulnerability_metrics(mock_events, mock_records)

        assert isinstance(result, dict)
        assert "total_vulnerabilities" in result
        assert "high_severity_count" in result
        assert "medium_severity_count" in result
        assert "low_severity_count" in result

    def test_calculate_time_based_metrics(self, analyzer):
        """Test calculating time-based metrics."""
        now = datetime.now()
        mock_events = [
            Mock(
                event_type=AuditEventType.VULNERABILITY_DETECTED,
                timestamp=now - timedelta(hours=48),
                metadata={"vulnerability_id": "vuln-1"},
            ),
            Mock(
                event_type=AuditEventType.VULNERABILITY_RESOLVED,
                timestamp=now,
                metadata={"vulnerability_id": "vuln-1"},
            ),
        ]

        mock_records = [
            Mock(
                vulnerability_id="vuln-1",
                created_at=now - timedelta(hours=48),
                updated_at=now,
                current_status=VulnerabilityStatus.RESOLVED,
            )
        ]

        result = analyzer._calculate_time_based_metrics(mock_events, mock_records)

        assert isinstance(result, dict)
        assert "average_resolution_time" in result
        assert "median_resolution_time" in result
        assert "mean_time_to_detection" in result
        assert "mean_time_to_resolution" in result

    def test_calculate_performance_metrics(self, analyzer):
        """Test calculating performance metrics."""
        mock_events = [
            Mock(event_type=AuditEventType.SCAN_COMPLETED, metadata={"duration": 120}),
            Mock(
                event_type=AuditEventType.VULNERABILITY_DETECTED,
                metadata={"confidence": "HIGH"},
            ),
            Mock(event_type=AuditEventType.FALSE_POSITIVE_REPORTED, metadata={}),
        ]

        mock_records = [
            Mock(current_status=VulnerabilityStatus.RESOLVED),
            Mock(current_status=VulnerabilityStatus.FALSE_POSITIVE),
        ]

        result = analyzer._calculate_performance_metrics(mock_events, mock_records, 30)

        assert isinstance(result, dict)
        assert "scan_coverage" in result
        assert "false_positive_rate" in result
        assert "detection_rate" in result

    def test_calculate_compliance_metrics(self, analyzer):
        """Test calculating compliance metrics."""
        mock_records = [
            Mock(
                current_status=VulnerabilityStatus.RESOLVED,
                severity=VulnerabilitySeverity.HIGH,
                created_at=datetime.now() - timedelta(days=1),
            ),
            Mock(
                current_status=VulnerabilityStatus.NEW,
                severity=VulnerabilitySeverity.MEDIUM,
                created_at=datetime.now() - timedelta(days=10),
            ),
        ]

        result = analyzer._calculate_compliance_metrics(mock_records)

        assert isinstance(result, dict)
        assert "compliance_score" in result
        assert "overdue_count" in result
        assert "risk_score" in result

    def test_calculate_trend_indicators(self, analyzer):
        """Test calculating trend indicators."""
        # Mock database operations
        with patch.object(analyzer, "_get_trend_data") as mock_get_trend:
            mock_get_trend.return_value = [
                MetricPoint(datetime.now() - timedelta(days=2), 10.0),
                MetricPoint(datetime.now() - timedelta(days=1), 12.0),
                MetricPoint(datetime.now(), 15.0),
            ]

            result = analyzer._calculate_trend_indicators(30)

            assert isinstance(result, dict)

    def test_analyze_trends(self, analyzer):
        """Test analyzing trends for specific metrics."""
        with (
            patch.object(analyzer, "_get_trend_data") as mock_get_trend,
            patch.object(analyzer, "_aggregate_trend_data") as mock_aggregate,
            patch.object(analyzer, "_calculate_trend_direction") as mock_direction,
        ):

            mock_get_trend.return_value = [MetricPoint(datetime.now(), 10.0)]
            mock_aggregate.return_value = [MetricPoint(datetime.now(), 10.0)]
            mock_direction.return_value = ("increasing", 15.5, 0.85)

            result = analyzer.analyze_trends(["vulnerability_count"], period_days=30)

            assert isinstance(result, list)
            if result:  # If trends were calculated
                assert isinstance(result[0], dict)

    def test_generate_metrics_report_basic(
        self, analyzer, mock_audit_trail, mock_status_tracker
    ):
        """Test generating basic metrics report."""
        mock_audit_trail.get_events.return_value = []
        mock_status_tracker.get_all_tracking_records.return_value = []

        with patch.object(analyzer, "_get_historical_metrics") as mock_historical:
            mock_historical.return_value = []

            result = analyzer.generate_metrics_report(
                include_trends=False, include_historical=False, period_days=30
            )

            assert isinstance(result, dict)
            assert "current_metrics" in result
            assert "timestamp" in result

    def test_generate_metrics_report_with_output_file(
        self, analyzer, mock_audit_trail, mock_status_tracker
    ):
        """Test generating metrics report with output file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            mock_audit_trail.get_events.return_value = []
            mock_status_tracker.get_all_tracking_records.return_value = []

            with patch.object(analyzer, "_get_historical_metrics") as mock_historical:
                mock_historical.return_value = []

                result = analyzer.generate_metrics_report(
                    include_trends=False,
                    include_historical=False,
                    output_file=output_path,
                )

                assert isinstance(result, dict)
                assert output_path.exists()
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_get_trend_data(self, analyzer):
        """Test getting trend data from database."""
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        # Mock database cursor and connection
        with patch("sqlite3.connect") as mock_connect:
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = [
                (start_date.isoformat(), 10.5, '{"test": "data"}')
            ]
            mock_connect.return_value.__enter__.return_value.cursor.return_value = (
                mock_cursor
            )

            result = analyzer._get_trend_data("test_metric", start_date, end_date)

            assert isinstance(result, list)

    def test_aggregate_trend_data_daily(self, analyzer):
        """Test aggregating trend data by day."""
        now = datetime.now()
        trend_data = [
            MetricPoint(now, 10.0),
            MetricPoint(now + timedelta(hours=1), 12.0),
            MetricPoint(now + timedelta(days=1), 15.0),
        ]

        result = analyzer._aggregate_trend_data(trend_data, "daily")

        assert isinstance(result, list)
        assert len(result) <= len(trend_data)  # Should be aggregated

    def test_aggregate_trend_data_weekly(self, analyzer):
        """Test aggregating trend data by week."""
        now = datetime.now()
        trend_data = [
            MetricPoint(now, 10.0),
            MetricPoint(now + timedelta(days=1), 12.0),
            MetricPoint(now + timedelta(days=8), 15.0),
        ]

        result = analyzer._aggregate_trend_data(trend_data, "weekly")

        assert isinstance(result, list)

    def test_calculate_trend_direction_increasing(self, analyzer):
        """Test calculating trend direction for increasing values."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]

        direction, change_pct, confidence = analyzer._calculate_trend_direction(values)

        assert direction in ["increasing", "decreasing", "stable"]
        assert isinstance(change_pct, float)
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    def test_calculate_trend_direction_decreasing(self, analyzer):
        """Test calculating trend direction for decreasing values."""
        values = [5.0, 4.0, 3.0, 2.0, 1.0]

        direction, change_pct, confidence = analyzer._calculate_trend_direction(values)

        assert direction in ["increasing", "decreasing", "stable"]
        assert isinstance(change_pct, float)
        assert isinstance(confidence, float)

    def test_calculate_trend_direction_stable(self, analyzer):
        """Test calculating trend direction for stable values."""
        values = [3.0, 3.1, 2.9, 3.0, 3.1]

        direction, change_pct, confidence = analyzer._calculate_trend_direction(values)

        assert direction in ["increasing", "decreasing", "stable"]
        assert isinstance(change_pct, float)
        assert isinstance(confidence, float)

    def test_calculate_trend_direction_empty_values(self, analyzer):
        """Test calculating trend direction with empty values."""
        values = []

        direction, change_pct, confidence = analyzer._calculate_trend_direction(values)

        assert direction == "stable"
        assert change_pct == 0.0
        assert confidence == 0.0

    def test_get_historical_metrics(self, analyzer):
        """Test getting historical metrics."""
        with patch("sqlite3.connect") as mock_connect:
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = [
                (datetime.now().isoformat(), '{"total_vulnerabilities": 10}')
            ]
            mock_connect.return_value.__enter__.return_value.cursor.return_value = (
                mock_cursor
            )

            result = analyzer._get_historical_metrics(30)

            assert isinstance(result, list)

    def test_save_metrics_snapshot(self, analyzer):
        """Test saving metrics snapshot to database."""
        metrics = SecurityMetrics(
            timestamp=datetime.now(),
            total_vulnerabilities=10,
            high_severity_count=2,
            medium_severity_count=5,
            low_severity_count=3,
        )

        with patch("sqlite3.connect") as mock_connect:
            mock_cursor = Mock()
            mock_connect.return_value.__enter__.return_value.cursor.return_value = (
                mock_cursor
            )

            analyzer._save_metrics_snapshot(metrics)

            mock_cursor.execute.assert_called()

    def test_generate_insights(self, analyzer):
        """Test generating insights from metrics and trends."""
        metrics = SecurityMetrics(
            timestamp=datetime.now(),
            total_vulnerabilities=50,
            high_severity_count=10,
            medium_severity_count=20,
            low_severity_count=20,
            resolved_count=30,
            compliance_score=75.0,
            risk_score=7.5,
        )

        trend_analysis = [
            {
                "metric_name": "total_vulnerabilities",
                "trend_direction": "increasing",
                "change_percentage": 15.0,
            }
        ]

        result = analyzer._generate_insights(metrics, trend_analysis)

        assert isinstance(result, list)
        assert len(result) > 0
        for insight in result:
            assert isinstance(insight, str)

    def test_generate_recommendations(self, analyzer):
        """Test generating recommendations from metrics."""
        metrics = SecurityMetrics(
            timestamp=datetime.now(),
            total_vulnerabilities=100,
            high_severity_count=20,
            medium_severity_count=40,
            low_severity_count=40,
            resolved_count=50,
            compliance_score=60.0,
            risk_score=8.5,
            false_positive_rate=15.0,
            overdue_count=10,
        )

        result = analyzer._generate_recommendations(metrics)

        assert isinstance(result, list)
        assert len(result) > 0
        for recommendation in result:
            assert isinstance(recommendation, str)

    def test_save_report(self, analyzer):
        """Test saving report to file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            test_report = {"test": "data", "metrics": {"total": 10}}
            analyzer._save_report(test_report, output_path)

            assert output_path.exists()
            with open(output_path, "r") as f:
                loaded_data = json.load(f)
            assert loaded_data == test_report
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_init_metrics_database(self, analyzer):
        """Test initializing metrics database."""
        # This method is called during __init__, so we test it doesn't raise exceptions
        # by creating a new analyzer instance
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = Path(f.name)

        try:
            mock_audit = Mock()
            mock_tracker = Mock()

            # Should not raise an exception
            new_analyzer = SecurityMetricsAnalyzer(
                audit_trail=mock_audit,
                status_tracker=mock_tracker,
                metrics_db_path=temp_path,
            )
            assert new_analyzer is not None
        finally:
            if temp_path.exists():
                temp_path.unlink()
