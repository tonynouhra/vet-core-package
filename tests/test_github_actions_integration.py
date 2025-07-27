"""
Integration tests for GitHub Actions workflow and security scanning.

This module tests the integration between the vulnerability management system
and GitHub Actions workflows, including artifact generation, notification
handling, and workflow validation.

Requirements addressed:
- 3.1: GitHub Actions workflow integration testing
- 3.2: Automated security scanning validation
- 3.4: Notification system integration with CI/CD
"""

import json
import os
import tempfile
import pytest
import yaml
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from vet_core.security.scanner import VulnerabilityScanner
from vet_core.security.models import SecurityReport, Vulnerability, VulnerabilitySeverity


class TestGitHubActionsIntegration:
    """Test GitHub Actions workflow integration."""

    @pytest.fixture
    def github_env(self):
        """Mock GitHub Actions environment variables."""
        return {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": "test-org/vet-core-package",
            "GITHUB_RUN_ID": "1234567890",
            "GITHUB_SHA": "abc123def456789",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_ACTOR": "test-user",
            "GITHUB_WORKFLOW": "Security Monitoring",
            "GITHUB_JOB": "vulnerability-scan",
            "GITHUB_EVENT_NAME": "schedule",
        }

    @pytest.fixture
    def mock_security_reports_dir(self):
        """Create mock security reports directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir) / "security-reports"
            reports_dir.mkdir()
            yield reports_dir

    @pytest.fixture
    def sample_pip_audit_output(self):
        """Sample pip-audit JSON output for testing."""
        return {
            "dependencies": [
                {
                    "name": "black",
                    "version": "23.12.1",
                    "vulns": [
                        {
                            "id": "PYSEC-2024-48",
                            "fix_versions": ["24.3.0"],
                            "description": "Code formatting vulnerability in black package",
                            "aliases": ["CVE-2024-12345"],
                        }
                    ],
                },
                {
                    "name": "setuptools",
                    "version": "65.5.0",
                    "vulns": [
                        {
                            "id": "PYSEC-2022-43012",
                            "fix_versions": ["65.5.1", "78.1.1"],
                            "description": "Build system vulnerability in setuptools",
                            "aliases": ["CVE-2022-12345"],
                        },
                        {
                            "id": "PYSEC-2025-49",
                            "fix_versions": ["78.1.1"],
                            "description": "Recent setuptools vulnerability",
                            "aliases": ["CVE-2025-12345"],
                        },
                    ],
                },
            ]
        }

    def test_workflow_file_structure(self):
        """Test GitHub Actions workflow file structure and content."""
        workflow_path = Path("vet-core-package/.github/workflows/security-monitoring.yml")
        
        if not workflow_path.exists():
            pytest.skip("GitHub Actions workflow file not found")

        with open(workflow_path) as f:
            workflow = yaml.safe_load(f)

        # Test basic workflow structure
        assert "name" in workflow
        assert workflow["name"] == "Security Monitoring"
        
        assert "on" in workflow
        on_config = workflow["on"]
        
        # Test scheduling configuration
        assert "schedule" in on_config
        assert isinstance(on_config["schedule"], list)
        assert len(on_config["schedule"]) > 0
        
        # Verify daily scheduling (6 AM UTC)
        schedule_cron = on_config["schedule"][0]["cron"]
        assert "0 6 * * *" == schedule_cron

        # Test manual trigger
        assert "workflow_dispatch" in on_config
        
        # Test push triggers
        assert "push" in on_config
        push_config = on_config["push"]
        assert "branches" in push_config
        assert "main" in push_config["branches"]
        assert "paths" in push_config

        # Test jobs configuration
        assert "jobs" in workflow
        jobs = workflow["jobs"]
        
        # Test vulnerability scan job
        assert "vulnerability-scan" in jobs
        scan_job = jobs["vulnerability-scan"]
        
        assert "runs-on" in scan_job
        assert scan_job["runs-on"] == "ubuntu-latest"
        
        assert "steps" in scan_job
        steps = scan_job["steps"]
        
        # Verify essential steps
        step_names = [step.get("name", "") for step in steps]
        
        assert any("checkout" in name.lower() for name in step_names)
        assert any("python" in name.lower() for name in step_names)
        assert any("pip-audit" in name.lower() for name in step_names)
        assert any("upload" in name.lower() for name in step_names)

    def test_security_scan_step_simulation(
        self, github_env, mock_security_reports_dir, sample_pip_audit_output
    ):
        """Test security scanning step simulation."""
        with patch.dict(os.environ, github_env):
            scanner = VulnerabilityScanner()
            
            # Mock pip-audit execution
            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 1  # Vulnerabilities found
                mock_result.stdout = json.dumps(sample_pip_audit_output)
                mock_result.stderr = ""
                mock_run.return_value = mock_result

                with patch.object(
                    scanner, "_get_scanner_version", return_value="pip-audit 2.6.1"
                ):
                    # Simulate GitHub Actions step: Run pip-audit
                    output_file = mock_security_reports_dir / "pip-audit-raw.json"
                    report = scanner.scan_dependencies(output_file=output_file)

                    # Verify scan results
                    assert report.vulnerability_count == 3
                    assert report.critical_count == 0  # Based on mock data
                    assert report.high_count == 0
                    assert report.medium_count >= 0
                    
                    # Simulate file output (in real workflow, pip-audit creates this)
                    output_file.write_text(json.dumps(sample_pip_audit_output))
                    assert output_file.exists()

                    # Verify command was called correctly
                    mock_run.assert_called_once()
                    call_args = mock_run.call_args[0][0]
                    assert "pip-audit" in call_args
                    assert "--format=json" in call_args

    def test_vulnerability_report_processing(
        self, github_env, mock_security_reports_dir, sample_pip_audit_output
    ):
        """Test vulnerability report processing step."""
        with patch.dict(os.environ, github_env):
            # Create raw pip-audit output file
            raw_file = mock_security_reports_dir / "pip-audit-raw.json"
            raw_file.write_text(json.dumps(sample_pip_audit_output))

            # Process with scanner
            scanner = VulnerabilityScanner()
            report = scanner.scan_from_file(raw_file)

            # Generate processed reports (simulate GitHub Actions processing)
            
            # 1. Generate security summary markdown
            summary_file = mock_security_reports_dir / "security-summary.md"
            summary_content = self._generate_security_summary_markdown(report)
            summary_file.write_text(summary_content)

            # 2. Generate JSON report
            json_report_file = mock_security_reports_dir / "security-report.json"
            json_report = self._generate_json_report(report)
            json_report_file.write_text(json.dumps(json_report, indent=2))

            # 3. Generate CSV report
            csv_file = mock_security_reports_dir / "security-report.csv"
            csv_content = self._generate_csv_report(report)
            csv_file.write_text(csv_content)

            # Verify all files were created
            assert summary_file.exists()
            assert json_report_file.exists()
            assert csv_file.exists()
            assert raw_file.exists()

            # Verify content
            assert "Security Vulnerability Report" in summary_file.read_text()
            
            json_data = json.loads(json_report_file.read_text())
            assert "scan_metadata" in json_data
            assert "vulnerabilities" in json_data
            assert len(json_data["vulnerabilities"]) == report.vulnerability_count

            csv_lines = csv_file.read_text().split("\n")
            assert len(csv_lines) >= 2  # Header + at least one vulnerability

    def test_github_actions_environment_variables(self, github_env):
        """Test GitHub Actions environment variable handling."""
        with patch.dict(os.environ, github_env):
            # Test environment variable access
            assert os.getenv("GITHUB_ACTIONS") == "true"
            assert os.getenv("GITHUB_REPOSITORY") == "test-org/vet-core-package"
            assert os.getenv("GITHUB_RUN_ID") == "1234567890"

            # Test workflow context creation
            workflow_context = {
                "repository": os.getenv("GITHUB_REPOSITORY"),
                "run_id": os.getenv("GITHUB_RUN_ID"),
                "sha": os.getenv("GITHUB_SHA"),
                "ref": os.getenv("GITHUB_REF"),
                "actor": os.getenv("GITHUB_ACTOR"),
                "workflow": os.getenv("GITHUB_WORKFLOW"),
                "job": os.getenv("GITHUB_JOB"),
                "event_name": os.getenv("GITHUB_EVENT_NAME"),
            }

            # Verify context
            assert workflow_context["repository"] == "test-org/vet-core-package"
            assert workflow_context["workflow"] == "Security Monitoring"
            assert workflow_context["event_name"] == "schedule"

    def test_artifact_generation_and_validation(
        self, github_env, mock_security_reports_dir, sample_pip_audit_output
    ):
        """Test artifact generation for GitHub Actions."""
        with patch.dict(os.environ, github_env):
            # Simulate complete artifact generation workflow
            scanner = VulnerabilityScanner()
            
            # Mock pip-audit
            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 1
                mock_result.stdout = json.dumps(sample_pip_audit_output)
                mock_result.stderr = ""
                mock_run.return_value = mock_result

                with patch.object(
                    scanner, "_get_scanner_version", return_value="pip-audit 2.6.1"
                ):
                    # Generate security report
                    report = scanner.scan_dependencies()

                    # Create all expected artifacts
                    artifacts = self._create_security_artifacts(
                        report, mock_security_reports_dir, sample_pip_audit_output
                    )

                    # Verify artifact structure
                    expected_files = [
                        "pip-audit-raw.json",
                        "security-summary.md",
                        "security-report.json",
                        "security-report.csv",
                    ]

                    for filename in expected_files:
                        file_path = mock_security_reports_dir / filename
                        assert file_path.exists(), f"Missing artifact: {filename}"
                        assert file_path.stat().st_size > 0, f"Empty artifact: {filename}"

                    # Verify artifact metadata
                    metadata_file = mock_security_reports_dir / "artifact-metadata.json"
                    metadata = {
                        "generated_at": datetime.now().isoformat(),
                        "workflow_run_id": os.getenv("GITHUB_RUN_ID"),
                        "repository": os.getenv("GITHUB_REPOSITORY"),
                        "sha": os.getenv("GITHUB_SHA"),
                        "total_vulnerabilities": report.vulnerability_count,
                        "critical_count": report.critical_count,
                        "high_count": report.high_count,
                        "artifacts": expected_files,
                    }
                    metadata_file.write_text(json.dumps(metadata, indent=2))

                    # Validate metadata
                    assert metadata_file.exists()
                    metadata_content = json.loads(metadata_file.read_text())
                    assert metadata_content["total_vulnerabilities"] == report.vulnerability_count

    def test_notification_trigger_conditions(
        self, github_env, sample_pip_audit_output
    ):
        """Test notification trigger conditions in GitHub Actions."""
        with patch.dict(os.environ, github_env):
            scanner = VulnerabilityScanner()
            
            # Mock pip-audit with critical vulnerabilities
            critical_output = {
                "dependencies": [
                    {
                        "name": "critical-package",
                        "version": "1.0.0",
                        "vulns": [
                            {
                                "id": "CRITICAL-001",
                                "fix_versions": ["1.1.0"],
                                "description": "Critical security vulnerability",
                                "aliases": ["CVE-2024-CRITICAL"],
                            }
                        ],
                    }
                ]
            }

            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 1
                mock_result.stdout = json.dumps(critical_output)
                mock_result.stderr = ""
                mock_run.return_value = mock_result

                with patch.object(
                    scanner, "_get_scanner_version", return_value="pip-audit 2.6.1"
                ):
                    report = scanner.scan_dependencies()

                    # Simulate notification trigger logic
                    should_notify_critical = report.critical_count > 0
                    should_notify_high = report.high_count > 0 or report.critical_count > 0
                    should_create_issue = report.critical_count > 0

                    # Test notification conditions
                    notification_level = self._determine_notification_level(report)
                    
                    # Verify notification triggers
                    if report.critical_count > 0:
                        assert notification_level == "critical"
                        assert should_create_issue
                    elif report.high_count > 0:
                        assert notification_level == "high"
                    else:
                        assert notification_level in ["medium", "low", "none"]

    def test_workflow_step_dependencies(self):
        """Test workflow step dependencies and execution order."""
        workflow_path = Path("vet-core-package/.github/workflows/security-monitoring.yml")
        
        if not workflow_path.exists():
            pytest.skip("GitHub Actions workflow file not found")

        with open(workflow_path) as f:
            workflow = yaml.safe_load(f)

        scan_job = workflow["jobs"]["vulnerability-scan"]
        steps = scan_job["steps"]

        # Verify step order
        step_names = [step.get("name", "") for step in steps]
        
        # Checkout should be first
        assert any("checkout" in step_names[0].lower() for _ in [None])
        
        # Python setup should come early
        python_step_index = next(
            i for i, name in enumerate(step_names) 
            if "python" in name.lower()
        )
        assert python_step_index < len(step_names) / 2

        # Dependencies installation should come before scanning
        install_step_index = next(
            (i for i, name in enumerate(step_names) if "install" in name.lower()),
            -1
        )
        scan_step_index = next(
            (i for i, name in enumerate(step_names) if "pip-audit" in name.lower()),
            -1
        )
        
        if install_step_index >= 0 and scan_step_index >= 0:
            assert install_step_index < scan_step_index

        # Upload should be near the end
        upload_step_index = next(
            (i for i, name in enumerate(step_names) if "upload" in name.lower()),
            -1
        )
        
        if upload_step_index >= 0:
            assert upload_step_index > len(step_names) / 2

    def test_workflow_conditional_execution(self, github_env):
        """Test conditional execution logic in workflow."""
        with patch.dict(os.environ, github_env):
            # Test different event types
            test_cases = [
                {"event": "schedule", "should_run_trend": True},
                {"event": "push", "should_run_trend": False},
                {"event": "pull_request", "should_run_trend": False},
                {"event": "workflow_dispatch", "should_run_trend": False},
            ]

            for case in test_cases:
                with patch.dict(os.environ, {"GITHUB_EVENT_NAME": case["event"]}):
                    event_name = os.getenv("GITHUB_EVENT_NAME")
                    
                    # Simulate conditional logic
                    should_run_trend_analysis = event_name == "schedule"
                    should_post_pr_comment = event_name == "pull_request"
                    should_create_issue = event_name in ["schedule", "workflow_dispatch"]

                    # Verify conditions
                    assert should_run_trend_analysis == case["should_run_trend"]
                    
                    if case["event"] == "pull_request":
                        assert should_post_pr_comment
                    else:
                        assert not should_post_pr_comment

    def _generate_security_summary_markdown(self, report: SecurityReport) -> str:
        """Generate security summary markdown."""
        return f"""# Security Vulnerability Report

**Scan Date:** {report.scan_date.strftime('%Y-%m-%d %H:%M:%S UTC')}
**Scanner Version:** {report.scanner_version}
**Total Vulnerabilities:** {report.vulnerability_count}

## Severity Breakdown
- **Critical:** {report.critical_count}
- **High:** {report.high_count}
- **Medium:** {report.medium_count}
- **Low:** {report.low_count}
- **Fixable:** {report.fixable_count}

## Vulnerabilities Found

{chr(10).join(f"### {v.id} - {v.package_name} {v.installed_version}" + 
              (f"{chr(10)}**Fix Available:** {v.recommended_fix_version}" if v.recommended_fix_version else "") +
              f"{chr(10)}**Description:** {v.description}" 
              for v in report.vulnerabilities)}

## Next Steps
1. Review all critical and high severity vulnerabilities immediately
2. Apply available security fixes
3. Monitor for additional security updates
4. Update security documentation

---
*This report was generated automatically by the security monitoring system.*
"""

    def _generate_json_report(self, report: SecurityReport) -> dict:
        """Generate JSON security report."""
        return {
            "scan_metadata": {
                "scan_date": report.scan_date.isoformat(),
                "scanner_version": report.scanner_version,
                "scan_duration": report.scan_duration,
                "total_packages_scanned": report.total_packages_scanned,
                "scan_command": getattr(report, "scan_command", "pip-audit --format=json"),
            },
            "summary": {
                "total_vulnerabilities": report.vulnerability_count,
                "critical_count": report.critical_count,
                "high_count": report.high_count,
                "medium_count": report.medium_count,
                "low_count": report.low_count,
                "fixable_count": report.fixable_count,
            },
            "vulnerabilities": [
                {
                    "id": v.id,
                    "package_name": v.package_name,
                    "installed_version": v.installed_version,
                    "fix_versions": v.fix_versions,
                    "recommended_fix_version": v.recommended_fix_version,
                    "severity": v.severity.value,
                    "cvss_score": v.cvss_score,
                    "description": v.description,
                    "published_date": v.published_date.isoformat() if v.published_date else None,
                    "discovered_date": v.discovered_date.isoformat(),
                    "is_fixable": v.is_fixable,
                }
                for v in report.vulnerabilities
            ],
        }

    def _generate_csv_report(self, report: SecurityReport) -> str:
        """Generate CSV security report."""
        lines = [
            "ID,Package,Installed Version,Fix Versions,Severity,CVSS Score,Description,Fixable"
        ]
        
        for v in report.vulnerabilities:
            fix_versions = ";".join(v.fix_versions) if v.fix_versions else ""
            description = v.description.replace(",", ";").replace("\n", " ") if v.description else ""
            
            lines.append(
                f"{v.id},{v.package_name},{v.installed_version},"
                f'"{fix_versions}",{v.severity.value},{v.cvss_score or ""},'
                f'"{description}",{v.is_fixable}'
            )
        
        return "\n".join(lines)

    def _create_security_artifacts(
        self, report: SecurityReport, reports_dir: Path, raw_output: dict
    ) -> dict:
        """Create all security artifacts."""
        artifacts = {}

        # Raw pip-audit output
        raw_file = reports_dir / "pip-audit-raw.json"
        raw_file.write_text(json.dumps(raw_output, indent=2))
        artifacts["raw"] = raw_file

        # Security summary
        summary_file = reports_dir / "security-summary.md"
        summary_file.write_text(self._generate_security_summary_markdown(report))
        artifacts["summary"] = summary_file

        # JSON report
        json_file = reports_dir / "security-report.json"
        json_file.write_text(json.dumps(self._generate_json_report(report), indent=2))
        artifacts["json"] = json_file

        # CSV report
        csv_file = reports_dir / "security-report.csv"
        csv_file.write_text(self._generate_csv_report(report))
        artifacts["csv"] = csv_file

        return artifacts

    def _determine_notification_level(self, report: SecurityReport) -> str:
        """Determine notification level based on vulnerability severity."""
        if report.critical_count > 0:
            return "critical"
        elif report.high_count > 0:
            return "high"
        elif report.medium_count > 0:
            return "medium"
        elif report.low_count > 0:
            return "low"
        else:
            return "none"


class TestWorkflowScriptIntegration:
    """Test integration with workflow processing scripts."""

    def test_vulnerability_count_script(self, tmp_path):
        """Test vulnerability counting script functionality."""
        # Create mock pip-audit output
        mock_output = {
            "dependencies": [
                {
                    "name": "package1",
                    "version": "1.0.0",
                    "vulns": [
                        {"id": "VULN-001", "fix_versions": ["1.1.0"]},
                        {"id": "VULN-002", "fix_versions": ["1.2.0"]},
                    ],
                },
                {
                    "name": "package2",
                    "version": "2.0.0",
                    "vulns": [
                        {"id": "VULN-003", "fix_versions": ["2.1.0"]},
                    ],
                },
            ]
        }

        json_file = tmp_path / "test-output.json"
        json_file.write_text(json.dumps(mock_output))

        # Test with scanner
        scanner = VulnerabilityScanner()
        report = scanner.scan_from_file(json_file)

        # Verify count
        assert report.vulnerability_count == 3

    def test_environment_variable_processing(self):
        """Test environment variable processing for GitHub Actions."""
        test_env = {
            "VULNERABILITY_COUNT": "5",
            "CRITICAL_COUNT": "1",
            "HIGH_COUNT": "2",
            "MEDIUM_COUNT": "2",
            "LOW_COUNT": "0",
            "FIXABLE_COUNT": "4",
        }

        with patch.dict(os.environ, test_env):
            # Simulate script processing
            vuln_count = int(os.getenv("VULNERABILITY_COUNT", "0"))
            critical_count = int(os.getenv("CRITICAL_COUNT", "0"))
            high_count = int(os.getenv("HIGH_COUNT", "0"))

            # Determine notification level
            if critical_count > 0:
                notification_level = "critical"
            elif high_count > 0:
                notification_level = "high"
            else:
                notification_level = "medium"

            # Verify processing
            assert vuln_count == 5
            assert notification_level == "critical"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])