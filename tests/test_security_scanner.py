"""
Tests for security vulnerability scanner.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from vet_core.security.models import VulnerabilitySeverity
from vet_core.security.scanner import (
    ScannerError,
    ScanTimeoutError,
    VulnerabilityScanner,
)


class TestVulnerabilityScanner:
    """Test VulnerabilityScanner class."""

    def test_scanner_initialization(self):
        """Test scanner initialization with default timeout."""
        scanner = VulnerabilityScanner()
        assert scanner.timeout == 300

    def test_scanner_initialization_custom_timeout(self):
        """Test scanner initialization with custom timeout."""
        scanner = VulnerabilityScanner(timeout=600)
        assert scanner.timeout == 600

    @patch("vet_core.security.scanner.secure_subprocess_run")
    def test_scan_dependencies_no_vulnerabilities(self, mock_run):
        """Test scanning when no vulnerabilities are found."""
        # Mock successful pip-audit run with no vulnerabilities
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '{"vulnerabilities": []}'
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        scanner = VulnerabilityScanner()

        with patch.object(
            scanner, "_get_scanner_version", return_value="pip-audit 2.6.0"
        ):
            report = scanner.scan_dependencies()

        assert report.vulnerability_count == 0
        assert report.scanner_version == "pip-audit 2.6.0"
        assert len(report.vulnerabilities) == 0

        # Verify pip-audit was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "pip-audit" in call_args
        assert "--format=json" in call_args
        assert "--desc" in call_args

    @patch("vet_core.security.scanner.secure_subprocess_run")
    def test_scan_dependencies_with_vulnerabilities(self, mock_run):
        """Test scanning when vulnerabilities are found."""
        # Mock pip-audit output with vulnerabilities
        mock_vulnerabilities = [
            {
                "id": "PYSEC-2024-48",
                "package": "black",
                "installed_version": "23.12.1",
                "fix_versions": ["24.3.0"],
                "description": "Test vulnerability in black",
                "cvss": 5.5,
            },
            {
                "id": "PYSEC-2022-43012",
                "package": "setuptools",
                "installed_version": "65.5.0",
                "fix_versions": ["65.5.1", "78.1.1"],
                "description": "Test vulnerability in setuptools",
                "severity": "high",
            },
        ]

        mock_result = Mock()
        mock_result.returncode = 1  # pip-audit returns 1 when vulnerabilities found
        mock_result.stdout = json.dumps({"vulnerabilities": mock_vulnerabilities})
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        scanner = VulnerabilityScanner()

        with patch.object(
            scanner, "_get_scanner_version", return_value="pip-audit 2.6.0"
        ):
            report = scanner.scan_dependencies()

        assert report.vulnerability_count == 2
        assert report.scanner_version == "pip-audit 2.6.0"

        # Check first vulnerability
        vuln1 = report.vulnerabilities[0]
        assert vuln1.id == "PYSEC-2024-48"
        assert vuln1.package_name == "black"
        assert vuln1.installed_version == "23.12.1"
        assert vuln1.fix_versions == ["24.3.0"]
        assert vuln1.cvss_score == 5.5
        assert vuln1.severity == VulnerabilitySeverity.MEDIUM

        # Check second vulnerability
        vuln2 = report.vulnerabilities[1]
        assert vuln2.id == "PYSEC-2022-43012"
        assert vuln2.package_name == "setuptools"
        assert vuln2.installed_version == "65.5.0"
        assert vuln2.fix_versions == ["65.5.1", "78.1.1"]
        assert vuln2.severity == VulnerabilitySeverity.HIGH

    @patch("vet_core.security.scanner.secure_subprocess_run")
    def test_scan_dependencies_with_output_file(self, mock_run):
        """Test scanning with output file specified."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '{"vulnerabilities": []}'
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        scanner = VulnerabilityScanner()
        output_file = Path("/tmp/test-output.json")

        with patch.object(
            scanner, "_get_scanner_version", return_value="pip-audit 2.6.0"
        ):
            report = scanner.scan_dependencies(output_file=output_file)

        # Verify output file was included in command
        call_args = mock_run.call_args[0][0]
        assert "--output" in call_args
        assert str(output_file) in call_args

    @patch("vet_core.security.scanner.secure_subprocess_run")
    def test_scan_dependencies_without_descriptions(self, mock_run):
        """Test scanning without vulnerability descriptions."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '{"vulnerabilities": []}'
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        scanner = VulnerabilityScanner()

        with patch.object(
            scanner, "_get_scanner_version", return_value="pip-audit 2.6.0"
        ):
            report = scanner.scan_dependencies(include_description=False)

        # Verify --desc was not included in command
        call_args = mock_run.call_args[0][0]
        assert "--desc" not in call_args

    @patch("vet_core.security.scanner.secure_subprocess_run")
    def test_scan_dependencies_timeout(self, mock_run):
        """Test scan timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired("pip-audit", 300)

        scanner = VulnerabilityScanner(timeout=300)

        with pytest.raises(ScanTimeoutError) as exc_info:
            scanner.scan_dependencies()

        assert "timed out after 300 seconds" in str(exc_info.value)

    @patch("vet_core.security.scanner.secure_subprocess_run")
    def test_scan_dependencies_command_failure(self, mock_run):
        """Test handling of pip-audit command failure."""
        mock_result = Mock()
        mock_result.returncode = 2  # Command error
        mock_result.stdout = ""
        mock_result.stderr = "pip-audit: command not found"
        mock_run.return_value = mock_result

        scanner = VulnerabilityScanner()

        with pytest.raises(ScannerError) as exc_info:
            scanner.scan_dependencies()

        assert "pip-audit failed" in str(exc_info.value)

    @patch("vet_core.security.scanner.secure_subprocess_run")
    def test_scan_dependencies_invalid_json(self, mock_run):
        """Test handling of invalid JSON output."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = "invalid json output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        scanner = VulnerabilityScanner()

        with pytest.raises(ScannerError) as exc_info:
            scanner.scan_dependencies()

        assert "Failed to parse pip-audit JSON output" in str(exc_info.value)

    def test_scan_from_file_success(self, tmp_path):
        """Test parsing vulnerabilities from existing JSON file."""
        # Create test JSON file
        test_data = {
            "vulnerabilities": [
                {
                    "id": "TEST-001",
                    "package": "test-package",
                    "installed_version": "1.0.0",
                    "fix_versions": ["1.1.0"],
                    "description": "Test vulnerability",
                    "cvss": 7.5,
                }
            ]
        }

        json_file = tmp_path / "test-vulnerabilities.json"
        with open(json_file, "w") as f:
            json.dump(test_data, f)

        scanner = VulnerabilityScanner()
        report = scanner.scan_from_file(json_file)

        assert report.vulnerability_count == 1
        assert report.scanner_version == "unknown"
        assert report.scan_command == f"parsed from {json_file}"

        vuln = report.vulnerabilities[0]
        assert vuln.id == "TEST-001"
        assert vuln.package_name == "test-package"
        assert vuln.cvss_score == 7.5
        assert vuln.severity == VulnerabilitySeverity.HIGH

    def test_scan_from_file_not_found(self):
        """Test handling of missing JSON file."""
        scanner = VulnerabilityScanner()
        non_existent_file = Path("/tmp/does-not-exist.json")

        with pytest.raises(ScannerError) as exc_info:
            scanner.scan_from_file(non_existent_file)

        assert "Failed to parse vulnerability file" in str(exc_info.value)

    def test_scan_from_file_invalid_json(self, tmp_path):
        """Test handling of invalid JSON file."""
        json_file = tmp_path / "invalid.json"
        with open(json_file, "w") as f:
            f.write("invalid json content")

        scanner = VulnerabilityScanner()

        with pytest.raises(ScannerError) as exc_info:
            scanner.scan_from_file(json_file)

        assert "Failed to parse vulnerability file" in str(exc_info.value)

    def test_parse_vulnerabilities_empty_list(self):
        """Test parsing empty vulnerability list."""
        scanner = VulnerabilityScanner()
        result = scanner._parse_vulnerabilities([])
        assert result == []

    def test_parse_vulnerabilities_with_published_date(self):
        """Test parsing vulnerability with published date."""
        vuln_data = [
            {
                "id": "TEST-001",
                "package": "test-package",
                "installed_version": "1.0.0",
                "fix_versions": ["1.1.0"],
                "description": "Test vulnerability",
                "cvss": 6.5,
                "published": "2024-01-15T10:30:00Z",
            }
        ]

        scanner = VulnerabilityScanner()
        vulnerabilities = scanner._parse_vulnerabilities(vuln_data)

        assert len(vulnerabilities) == 1
        vuln = vulnerabilities[0]
        assert vuln.published_date is not None
        assert vuln.published_date.year == 2024
        assert vuln.published_date.month == 1
        assert vuln.published_date.day == 15

    def test_parse_vulnerabilities_malformed_entry(self):
        """Test parsing with malformed vulnerability entry."""
        vuln_data = [
            {
                "id": "GOOD-001",
                "package": "good-package",
                "installed_version": "1.0.0",
                "fix_versions": ["1.1.0"],
                "severity": "medium",
            },
            {
                # Missing required fields
                "id": "BAD-001"
            },
            {
                "id": "GOOD-002",
                "package": "another-good-package",
                "installed_version": "2.0.0",
                "fix_versions": [],
                "severity": "low",
            },
        ]

        scanner = VulnerabilityScanner()
        vulnerabilities = scanner._parse_vulnerabilities(vuln_data)

        # Should parse the good entries and skip the bad one
        assert len(vulnerabilities) == 2
        assert vulnerabilities[0].id == "GOOD-001"
        assert vulnerabilities[1].id == "GOOD-002"

    @patch("vet_core.security.scanner.secure_subprocess_run")
    def test_get_scanner_version_success(self, mock_run):
        """Test getting scanner version successfully."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "pip-audit 2.6.0"
        mock_run.return_value = mock_result

        scanner = VulnerabilityScanner()
        version = scanner._get_scanner_version()

        assert version == "pip-audit 2.6.0"
        # Verify the secure_subprocess_run was called with correct arguments
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["pip-audit", "--version"]
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["capture_output"] == True
        assert call_kwargs["text"] == True
        assert call_kwargs["timeout"] == 10

    @patch("vet_core.security.scanner.secure_subprocess_run")
    def test_get_scanner_version_failure(self, mock_run):
        """Test handling scanner version command failure."""
        mock_run.side_effect = subprocess.TimeoutExpired("pip-audit", 10)

        scanner = VulnerabilityScanner()
        version = scanner._get_scanner_version()

        assert version == "unknown"

    def test_count_scanned_packages_empty(self):
        """Test counting scanned packages with empty data."""
        scanner = VulnerabilityScanner()
        count = scanner._count_scanned_packages({})
        assert count == 0

    def test_count_scanned_packages_with_vulnerabilities(self):
        """Test counting scanned packages with vulnerabilities."""
        scan_data = {
            "vulnerabilities": [
                {"package": "package1"},
                {"package": "package2"},
                {"package": "package1"},  # Duplicate
                {"package": "package3"},
            ]
        }

        scanner = VulnerabilityScanner()
        count = scanner._count_scanned_packages(scan_data)

        # Should count unique packages
        assert count == 3
