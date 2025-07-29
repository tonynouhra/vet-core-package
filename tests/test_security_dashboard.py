"""Tests for the VulnerabilityDashboard class."""

import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from vet_core.security.dashboard import VulnerabilityDashboard, create_cli_parser, main
from vet_core.security.models import (
    SecurityReport,
    Vulnerability,
    VulnerabilitySeverity,
)
from vet_core.security.audit_trail import AuditEvent, AuditEventType
from vet_core.security.status_tracker import VulnerabilityStatus


class TestVulnerabilityDashboard:
    """Test cases for VulnerabilityDashboard class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = Path(f.name)
        yield temp_path
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def temp_config_path(self):
        """Create a temporary config file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            config_data = {
                "scan_timeout": 300,
                "max_vulnerabilities": 1000,
                "report_formats": ["text", "json"],
            }
            f.write(json.dumps(config_data).encode())
            temp_path = Path(f.name)
        yield temp_path
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with (
            patch("vet_core.security.dashboard.VulnerabilityScanner") as mock_scanner,
            patch("vet_core.security.dashboard.SecurityAuditTrail") as mock_audit,
            patch(
                "vet_core.security.dashboard.VulnerabilityStatusTracker"
            ) as mock_tracker,
            patch("vet_core.security.dashboard.RiskAssessor") as mock_assessor,
            patch(
                "vet_core.security.dashboard.SecurityComplianceManager"
            ) as mock_compliance,
            patch(
                "vet_core.security.dashboard.SecurityMetricsAnalyzer"
            ) as mock_metrics,
            patch("vet_core.security.dashboard.SecurityReporter") as mock_reporter,
        ):

            yield {
                "scanner": mock_scanner,
                "audit": mock_audit,
                "tracker": mock_tracker,
                "assessor": mock_assessor,
                "compliance": mock_compliance,
                "metrics": mock_metrics,
                "reporter": mock_reporter,
            }

    @pytest.fixture
    def dashboard(self, temp_db_path, temp_config_path, mock_dependencies):
        """Create a VulnerabilityDashboard instance with mocked dependencies."""
        return VulnerabilityDashboard(
            audit_db_path=temp_db_path, config_file=temp_config_path
        )

    def test_init_with_default_params(self, mock_dependencies):
        """Test dashboard initialization with default parameters."""
        dashboard = VulnerabilityDashboard()
        assert dashboard is not None

    def test_init_with_custom_params(
        self, temp_db_path, temp_config_path, mock_dependencies
    ):
        """Test dashboard initialization with custom parameters."""
        dashboard = VulnerabilityDashboard(
            audit_db_path=temp_db_path, config_file=temp_config_path
        )
        assert dashboard is not None

    def test_scan_vulnerabilities_default(self, dashboard, mock_dependencies):
        """Test vulnerability scanning with default parameters."""
        # Mock the scanner to return a sample report
        mock_report = SecurityReport(
            scan_date=datetime.now(),
            vulnerabilities=[
                Vulnerability(
                    id="vuln-1",
                    package_name="test-package",
                    installed_version="1.0.0",
                    fix_versions=["1.0.1"],
                    severity=VulnerabilitySeverity.MEDIUM,
                    description="Test description",
                )
            ],
            total_packages_scanned=1,
            scan_duration=10.5,
            scanner_version="1.0.0",
        )

        mock_dependencies["scanner"].return_value.scan_dependencies.return_value = (
            mock_report
        )

        result = dashboard.scan_vulnerabilities()
        assert result is not None
        mock_dependencies["scanner"].return_value.scan_dependencies.assert_called_once()

    def test_scan_vulnerabilities_with_output_file(self, dashboard, mock_dependencies):
        """Test vulnerability scanning with output file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            mock_report = SecurityReport(
                scan_date=datetime.now(),
                vulnerabilities=[],
                total_packages_scanned=0,
                scan_duration=5.0,
                scanner_version="1.0.0",
            )
            mock_dependencies["scanner"].return_value.scan_dependencies.return_value = (
                mock_report
            )

            dashboard.scan_vulnerabilities(
                output_file=output_path, include_description=False
            )
            mock_dependencies[
                "scanner"
            ].return_value.scan_dependencies.assert_called_once()
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_show_vulnerability_status_single(self, dashboard, mock_dependencies):
        """Test showing status for a single vulnerability."""
        mock_record = Mock()
        mock_record.vulnerability_id = "vuln-1"
        mock_record.current_status = VulnerabilityStatus.IN_PROGRESS
        mock_record.assigned_to = "test-user"
        mock_record.created_at = "2023-01-01T00:00:00"
        mock_record.updated_at = "2023-01-02T00:00:00"
        mock_record.priority_score = 7.5
        mock_record.tags = ["security", "urgent"]
        mock_record.status_history = []

        mock_dependencies["tracker"].return_value.get_tracking_record.return_value = (
            mock_record
        )

        dashboard.show_vulnerability_status("vuln-1")
        mock_dependencies[
            "tracker"
        ].return_value.get_tracking_record.assert_called_once_with("vuln-1")

    def test_show_vulnerability_status_all(self, dashboard, mock_dependencies):
        """Test showing status for all vulnerabilities."""
        mock_records = [
            Mock(vulnerability_id="vuln-1", current_status=VulnerabilityStatus.NEW),
            Mock(
                vulnerability_id="vuln-2", current_status=VulnerabilityStatus.RESOLVED
            ),
        ]
        mock_dependencies[
            "tracker"
        ].return_value.get_all_tracking_records.return_value = mock_records

        dashboard.show_vulnerability_status()
        mock_dependencies[
            "tracker"
        ].return_value.get_all_tracking_records.assert_called_once()

    def test_assess_risks_basic(self, dashboard, mock_dependencies):
        """Test basic risk assessment."""
        mock_assessment = Mock()
        mock_assessment.overall_risk_score = 7.5
        mock_assessment.risk_level = "HIGH"
        mock_assessment.critical_vulnerabilities = []
        mock_assessment.recommendations = ["Update dependencies"]

        mock_dependencies["assessor"].return_value.assess_current_risks.return_value = (
            mock_assessment
        )

        dashboard.assess_risks()
        mock_dependencies[
            "assessor"
        ].return_value.assess_current_risks.assert_called_once()

    def test_assess_risks_with_details(self, dashboard, mock_dependencies):
        """Test risk assessment with details."""
        mock_assessment = Mock()
        mock_assessment.overall_risk_score = 7.5
        mock_assessment.risk_level = "HIGH"
        mock_assessment.critical_vulnerabilities = []
        mock_assessment.recommendations = ["Update dependencies"]
        mock_assessment.detailed_analysis = {"category_scores": {"injection": 8.0}}

        mock_dependencies["assessor"].return_value.assess_current_risks.return_value = (
            mock_assessment
        )

        dashboard.assess_risks(show_details=True)
        mock_dependencies[
            "assessor"
        ].return_value.assess_current_risks.assert_called_once()

    def test_generate_report_summary_text(self, dashboard, mock_dependencies):
        """Test generating summary report in text format."""
        mock_report = {"summary": {"total": 5, "high": 1, "medium": 2, "low": 2}}
        mock_dependencies[
            "reporter"
        ].return_value.generate_summary_report.return_value = mock_report

        dashboard.generate_report(report_type="summary", format_type="text")
        mock_dependencies[
            "reporter"
        ].return_value.generate_summary_report.assert_called_once()

    def test_generate_report_summary_json(self, dashboard, mock_dependencies):
        """Test generating summary report in JSON format."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            mock_report = {"summary": {"total": 5, "high": 1, "medium": 2, "low": 2}}
            mock_dependencies[
                "reporter"
            ].return_value.generate_summary_report.return_value = mock_report

            dashboard.generate_report(
                report_type="summary", output_file=output_path, format_type="json"
            )
            mock_dependencies[
                "reporter"
            ].return_value.generate_summary_report.assert_called_once()
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_generate_report_detailed(self, dashboard, mock_dependencies):
        """Test generating detailed report."""
        mock_report = {"vulnerabilities": [], "analysis": {}}
        mock_dependencies[
            "reporter"
        ].return_value.generate_detailed_report.return_value = mock_report

        dashboard.generate_report(report_type="detailed")
        mock_dependencies[
            "reporter"
        ].return_value.generate_detailed_report.assert_called_once()

    def test_generate_report_compliance(self, dashboard, mock_dependencies):
        """Test generating compliance report."""
        mock_report = {"compliance_score": 85.0}
        mock_violations = []
        mock_metrics = Mock()

        mock_dependencies[
            "compliance"
        ].return_value.generate_compliance_report.return_value = mock_report
        mock_dependencies["compliance"].return_value.get_violations.return_value = (
            mock_violations
        )
        mock_dependencies[
            "metrics"
        ].return_value.calculate_current_metrics.return_value = mock_metrics

        dashboard.generate_report(report_type="compliance")
        mock_dependencies[
            "compliance"
        ].return_value.generate_compliance_report.assert_called_once()

    def test_generate_report_trends(self, dashboard, mock_dependencies):
        """Test generating trends report."""
        mock_events = [
            Mock(
                event_type=AuditEventType.VULNERABILITY_DETECTED,
                timestamp="2023-01-01T00:00:00",
            )
        ]
        mock_dependencies["audit"].return_value.get_events.return_value = mock_events

        dashboard.generate_report(report_type="trends")
        mock_dependencies["audit"].return_value.get_events.assert_called_once()

    def test_update_vulnerability_status(self, dashboard, mock_dependencies):
        """Test updating vulnerability status."""
        dashboard.update_vulnerability_status("vuln-1", "resolved", "Fixed the issue")
        mock_dependencies["tracker"].return_value.update_status.assert_called_once()

    def test_show_progress_summary(self, dashboard, mock_dependencies):
        """Test showing progress summary."""
        mock_summary = Mock()
        mock_summary.total_vulnerabilities = 10
        mock_summary.resolved_count = 5
        mock_summary.in_progress_count = 3
        mock_summary.new_count = 2
        mock_summary.completion_percentage = 50.0

        mock_dependencies["tracker"].return_value.get_progress_summary.return_value = (
            mock_summary
        )

        dashboard.show_progress_summary()
        mock_dependencies[
            "tracker"
        ].return_value.get_progress_summary.assert_called_once()

    def test_show_overdue_vulnerabilities(self, dashboard, mock_dependencies):
        """Test showing overdue vulnerabilities."""
        mock_overdue = [
            Mock(vulnerability_id="vuln-1", days_overdue=5),
            Mock(vulnerability_id="vuln-2", days_overdue=10),
        ]
        mock_dependencies[
            "tracker"
        ].return_value.get_overdue_vulnerabilities.return_value = mock_overdue

        dashboard.show_overdue_vulnerabilities()
        mock_dependencies[
            "tracker"
        ].return_value.get_overdue_vulnerabilities.assert_called_once()

    def test_show_help(self, dashboard):
        """Test showing help information."""
        # This method just prints help text, so we test it doesn't raise an exception
        dashboard.show_help()

    def test_analyze_security_trends(self, dashboard):
        """Test analyzing security trends."""
        mock_events = [
            Mock(
                event_type=AuditEventType.VULNERABILITY_DETECTED,
                timestamp="2023-01-01T00:00:00",
                metadata={"severity": "HIGH"},
            ),
            Mock(
                event_type=AuditEventType.VULNERABILITY_RESOLVED,
                timestamp="2023-01-02T00:00:00",
                metadata={"severity": "MEDIUM"},
            ),
        ]

        result = dashboard._analyze_security_trends(mock_events)
        assert isinstance(result, dict)
        assert "detection_trend" in result
        assert "resolution_trend" in result
        assert "severity_distribution" in result

    def test_load_vulnerability_status_file_not_exists(self, dashboard):
        """Test loading vulnerability status when file doesn't exist."""
        # Should not raise an exception when file doesn't exist
        dashboard._load_vulnerability_status()

    def test_save_vulnerability_status(self, dashboard):
        """Test saving vulnerability status."""
        # Should not raise an exception
        dashboard._save_vulnerability_status()

    def test_save_json_report(self, dashboard):
        """Test saving JSON report."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            test_data = {"test": "data", "count": 5}
            dashboard._save_json_report(test_data, output_path)

            # Verify file was created and contains correct data
            assert output_path.exists()
            with open(output_path, "r") as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_print_text_report(self, dashboard, capsys):
        """Test printing text report."""
        test_data = {"summary": {"total": 5}, "details": "test details"}
        dashboard._print_text_report(test_data, "Test Report")

        captured = capsys.readouterr()
        assert "Test Report" in captured.out

    def test_print_detailed_text_report(self, dashboard, capsys):
        """Test printing detailed text report."""
        test_data = {
            "vulnerabilities": [
                {"id": "vuln-1", "title": "Test Vuln", "severity": "HIGH"}
            ],
            "analysis": {"total": 1},
        }
        dashboard._print_detailed_text_report(test_data)

        captured = capsys.readouterr()
        assert "Detailed Security Report" in captured.out


class TestCLIFunctions:
    """Test CLI-related functions."""

    def test_create_cli_parser(self):
        """Test CLI parser creation."""
        parser = create_cli_parser()
        assert parser is not None

        # Test parsing some basic arguments
        args = parser.parse_args(["scan"])
        assert args.command == "scan"

    @patch("vet_core.security.dashboard.VulnerabilityDashboard")
    def test_main_scan_command(self, mock_dashboard_class):
        """Test main function with scan command."""
        mock_dashboard = Mock()
        mock_dashboard_class.return_value = mock_dashboard

        with patch("sys.argv", ["dashboard.py", "scan"]):
            main()

        mock_dashboard.scan_vulnerabilities.assert_called_once()

    @patch("vet_core.security.dashboard.VulnerabilityDashboard")
    def test_main_status_command(self, mock_dashboard_class):
        """Test main function with status command."""
        mock_dashboard = Mock()
        mock_dashboard_class.return_value = mock_dashboard

        with patch("sys.argv", ["dashboard.py", "status"]):
            main()

        mock_dashboard.show_vulnerability_status.assert_called_once()

    @patch("vet_core.security.dashboard.VulnerabilityDashboard")
    def test_main_assess_command(self, mock_dashboard_class):
        """Test main function with assess command."""
        mock_dashboard = Mock()
        mock_dashboard_class.return_value = mock_dashboard

        with patch("sys.argv", ["dashboard.py", "assess"]):
            main()

        mock_dashboard.assess_risks.assert_called_once()

    @patch("vet_core.security.dashboard.VulnerabilityDashboard")
    def test_main_report_command(self, mock_dashboard_class):
        """Test main function with report command."""
        mock_dashboard = Mock()
        mock_dashboard_class.return_value = mock_dashboard

        with patch("sys.argv", ["dashboard.py", "report", "--type", "summary"]):
            main()

        mock_dashboard.generate_report.assert_called_once()

    @patch("vet_core.security.dashboard.VulnerabilityDashboard")
    def test_main_update_command(self, mock_dashboard_class):
        """Test main function with update command."""
        mock_dashboard = Mock()
        mock_dashboard_class.return_value = mock_dashboard

        with patch("sys.argv", ["dashboard.py", "update", "vuln-1", "resolved"]):
            main()

        mock_dashboard.update_vulnerability_status.assert_called_once()

    @patch("vet_core.security.dashboard.VulnerabilityDashboard")
    def test_main_progress_command(self, mock_dashboard_class):
        """Test main function with progress command."""
        mock_dashboard = Mock()
        mock_dashboard_class.return_value = mock_dashboard

        with patch("sys.argv", ["dashboard.py", "progress"]):
            main()

        mock_dashboard.show_progress_summary.assert_called_once()

    @patch("vet_core.security.dashboard.VulnerabilityDashboard")
    def test_main_overdue_command(self, mock_dashboard_class):
        """Test main function with overdue command."""
        mock_dashboard = Mock()
        mock_dashboard_class.return_value = mock_dashboard

        with patch("sys.argv", ["dashboard.py", "overdue"]):
            main()

        mock_dashboard.show_overdue_vulnerabilities.assert_called_once()

    @patch("vet_core.security.dashboard.VulnerabilityDashboard")
    def test_main_help_command(self, mock_dashboard_class):
        """Test main function with help command."""
        mock_dashboard = Mock()
        mock_dashboard_class.return_value = mock_dashboard

        with patch("sys.argv", ["dashboard.py", "help"]):
            main()

        mock_dashboard.show_help.assert_called_once()

    @patch("vet_core.security.dashboard.run_interactive_dashboard")
    @patch("vet_core.security.dashboard.VulnerabilityDashboard")
    def test_main_interactive_command(self, mock_dashboard_class, mock_interactive):
        """Test main function with interactive command."""
        mock_dashboard = Mock()
        mock_dashboard_class.return_value = mock_dashboard

        with patch("sys.argv", ["dashboard.py", "interactive"]):
            main()

        mock_interactive.assert_called_once_with(mock_dashboard)
