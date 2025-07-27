"""
Vulnerability tracking and management dashboard.

This module provides a comprehensive command-line interface for vulnerability
management operations, status tracking, and security metrics reporting.

Requirements addressed:
- 3.3: Vulnerability prioritization with timeline recommendations
- 4.3: Compliance report generation with vulnerability management evidence
- 4.4: Evidence of proactive security management practices
"""

import argparse
import json
import logging
import sqlite3
import sys
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .assessor import RiskAssessor
from .audit_trail import AuditEvent, AuditEventType, SecurityAuditTrail
from .compliance import ComplianceFramework, SecurityComplianceManager
from .metrics_analyzer import SecurityMetricsAnalyzer
from .models import SecurityReport, VulnerabilitySeverity, Vulnerability
from .reporter import SecurityReporter
from .scanner import VulnerabilityScanner
from .status_tracker import VulnerabilityStatus, VulnerabilityStatusTracker


class VulnerabilityDashboard:
    """
    Comprehensive vulnerability tracking and management dashboard.

    This class provides a command-line interface for managing vulnerabilities,
    tracking their status, and generating security reports and metrics.
    """

    def __init__(
        self,
        audit_db_path: Optional[Path] = None,
        config_file: Optional[Path] = None,
    ) -> None:
        """
        Initialize the vulnerability dashboard.

        Args:
            audit_db_path: Path to audit database
            config_file: Path to configuration file
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize components
        self.scanner = VulnerabilityScanner()
        self.risk_assessor = RiskAssessor()
        self.audit_trail = SecurityAuditTrail(audit_db_path=audit_db_path)
        self.compliance_manager = SecurityComplianceManager(self.audit_trail)
        self.reporter = SecurityReporter()
        self.status_tracker = VulnerabilityStatusTracker(self.audit_trail)
        self.metrics_analyzer = SecurityMetricsAnalyzer(
            self.audit_trail, self.status_tracker
        )

        # Dashboard state
        self.current_report: Optional[SecurityReport] = None
        self.vulnerability_status: Dict[str, str] = {}

        self.logger.info("Initialized VulnerabilityDashboard")

    def scan_vulnerabilities(
        self, output_file: Optional[Path] = None, include_description: bool = True
    ) -> SecurityReport:
        """
        Perform vulnerability scan and update dashboard state.

        Args:
            output_file: Optional file to save scan results
            include_description: Whether to include vulnerability descriptions

        Returns:
            SecurityReport with scan results
        """
        print("🔍 Scanning for vulnerabilities...")

        try:
            # Perform scan
            report = self.scanner.scan_dependencies(
                output_file=output_file, include_description=include_description
            )

            # Update dashboard state
            self.current_report = report

            # Log scan completion
            self.audit_trail.log_scan_completed(
                scan_id=f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                report=report,
                duration=report.scan_duration,
            )

            # Update vulnerability status tracking
            self._update_vulnerability_status(report)

            print(
                f"✅ Scan completed: {report.vulnerability_count} vulnerabilities found"
            )
            print(f"   Critical: {report.critical_count}")
            print(f"   High: {report.high_count}")
            print(f"   Medium: {report.medium_count}")
            print(f"   Low: {report.low_count}")

            return report

        except Exception as e:
            print(f"❌ Scan failed: {e}")
            self.logger.error(f"Vulnerability scan failed: {e}")
            raise

    def show_vulnerability_status(self, vulnerability_id: Optional[str] = None) -> None:
        """
        Display vulnerability status information.

        Args:
            vulnerability_id: Optional specific vulnerability to show
        """
        if not self.current_report:
            print("❌ No scan data available. Run 'scan' command first.")
            return

        if vulnerability_id:
            self._show_single_vulnerability_status(vulnerability_id)
        else:
            self._show_all_vulnerabilities_status()

    def _show_single_vulnerability_status(self, vulnerability_id: str) -> None:
        """Show detailed status for a single vulnerability."""
        if not self.current_report:
            print("❌ No scan data available. Run 'scan' command first.")
            return

        # Find vulnerability in current report
        vulnerability = None
        for vuln in self.current_report.vulnerabilities:
            if vuln.id == vulnerability_id:
                vulnerability = vuln
                break

        if not vulnerability:
            print(f"❌ Vulnerability {vulnerability_id} not found")
            return

        # Get risk assessment
        assessment = self.risk_assessor.assess_vulnerability(vulnerability)

        # Get tracking record
        tracking_record = self.status_tracker.get_tracking_record(vulnerability_id)

        # Get audit trail
        timeline = self.audit_trail.get_vulnerability_timeline(vulnerability_id)

        print(f"\n📊 Vulnerability Status: {vulnerability_id}")
        print("=" * 60)
        print(f"Package: {vulnerability.package_name}")
        print(f"Installed Version: {vulnerability.installed_version}")
        print(f"Severity: {vulnerability.severity.value.upper()}")
        print(f"CVSS Score: {vulnerability.cvss_score or 'N/A'}")
        print(
            f"Fix Versions: {', '.join(vulnerability.fix_versions) if vulnerability.fix_versions else 'None'}"
        )
        print(
            f"Description: {vulnerability.description[:100]}..."
            if len(vulnerability.description) > 100
            else vulnerability.description
        )

        print(f"\n🎯 Risk Assessment:")
        print(f"Risk Score: {assessment.risk_score:.1f}/10.0")
        print(f"Priority: {assessment.priority_level.upper()}")
        print(f"Timeline: {assessment.recommended_timeline}")
        print(f"Confidence: {assessment.confidence_score:.1%}")
        print(f"Business Impact: {assessment.business_impact.upper()}")

        # Show tracking information if available
        if tracking_record:
            print(f"\n📋 Tracking Status:")
            print(f"Current Status: {tracking_record.current_status.value.upper()}")
            print(f"Assigned To: {tracking_record.assigned_to or 'Unassigned'}")
            print(f"Priority Score: {tracking_record.priority_score:.1f}")

            if tracking_record.progress_metrics:
                metrics = tracking_record.progress_metrics
                print(f"Progress: {metrics.progress_percentage:.1f}%")
                print(f"Current Stage: {metrics.current_stage.value}")
                print(f"Time in Status: {metrics.time_in_current_status}")
                print(
                    f"SLA Status: {'⚠️ OVERDUE' if metrics.is_overdue else '✅ On Track'}"
                )

        print(f"\n📈 Timeline ({len(timeline)} events):")
        for event in timeline[-5:]:  # Show last 5 events
            print(
                f"  {event.timestamp.strftime('%Y-%m-%d %H:%M')} - {event.event_type.value}"
            )
            if event.action_taken:
                print(f"    Action: {event.action_taken}")
            if event.outcome:
                print(f"    Outcome: {event.outcome}")

    def _show_all_vulnerabilities_status(self) -> None:
        """Show status overview for all vulnerabilities."""
        if not self.current_report:
            print("❌ No scan data available. Run 'scan' command first.")
            return

        print(f"\n📊 Vulnerability Status Overview")
        print("=" * 60)
        print(f"Total Vulnerabilities: {self.current_report.vulnerability_count}")
        print(
            f"Scan Date: {self.current_report.scan_date.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"Packages Scanned: {self.current_report.total_packages_scanned}")

        # Group by severity
        severity_groups: Dict[VulnerabilitySeverity, List[Vulnerability]] = {
            VulnerabilitySeverity.CRITICAL: [],
            VulnerabilitySeverity.HIGH: [],
            VulnerabilitySeverity.MEDIUM: [],
            VulnerabilitySeverity.LOW: [],
        }

        for vuln in self.current_report.vulnerabilities:
            if vuln.severity in severity_groups:
                severity_groups[vuln.severity].append(vuln)

        # Display by severity
        for severity, vulns in severity_groups.items():
            if vulns:
                print(f"\n🔴 {severity.value.upper()} ({len(vulns)} vulnerabilities):")
                for vuln in vulns[:5]:  # Show first 5
                    status = self.vulnerability_status.get(vuln.id, "new")
                    print(f"  • {vuln.id} - {vuln.package_name} ({status})")
                if len(vulns) > 5:
                    print(f"  ... and {len(vulns) - 5} more")

    def assess_risks(self, show_details: bool = False) -> None:
        """
        Perform risk assessment on current vulnerabilities.

        Args:
            show_details: Whether to show detailed assessment information
        """
        if not self.current_report:
            print("❌ No scan data available. Run 'scan' command first.")
            return

        print("🎯 Performing risk assessment...")

        # Get prioritized vulnerabilities
        prioritized = self.risk_assessor.get_prioritized_vulnerabilities(
            self.current_report
        )

        print(f"\n📊 Risk Assessment Results")
        print("=" * 60)

        for priority, vulns_assessments in prioritized.items():
            if vulns_assessments:
                print(
                    f"\n🔥 {priority.upper()} Priority ({len(vulns_assessments)} vulnerabilities):"
                )

                for vuln, assessment in vulns_assessments[:3]:  # Show top 3
                    print(f"  • {vuln.id} - {vuln.package_name}")
                    print(f"    Risk Score: {assessment.risk_score:.1f}/10.0")
                    print(f"    Timeline: {assessment.recommended_timeline}")

                    if show_details:
                        print(f"    Impact Factors:")
                        for factor, score in assessment.impact_factors.items():
                            print(f"      - {factor}: {score:.2f}")

                if len(vulns_assessments) > 3:
                    print(f"  ... and {len(vulns_assessments) - 3} more")

    def generate_report(
        self,
        report_type: str = "summary",
        output_file: Optional[Path] = None,
        format_type: str = "text",
    ) -> None:
        """
        Generate security reports and metrics.

        Args:
            report_type: Type of report (summary, detailed, compliance, trends)
            output_file: Optional file to save report
            format_type: Report format (text, json, html)
        """
        if not self.current_report:
            print("❌ No scan data available. Run 'scan' command first.")
            return

        print(f"📄 Generating {report_type} report...")

        try:
            if report_type == "summary":
                self._generate_summary_report(output_file, format_type)
            elif report_type == "detailed":
                self._generate_detailed_report(output_file, format_type)
            elif report_type == "compliance":
                self._generate_compliance_report(output_file, format_type)
            elif report_type == "trends":
                self._generate_trends_report(output_file, format_type)
            else:
                print(f"❌ Unknown report type: {report_type}")
                return

            print("✅ Report generated successfully")

        except Exception as e:
            print(f"❌ Report generation failed: {e}")
            self.logger.error(f"Report generation failed: {e}")

    def _generate_summary_report(
        self, output_file: Optional[Path], format_type: str
    ) -> None:
        """Generate summary report."""
        if not self.current_report:
            print("❌ No scan data available. Run 'scan' command first.")
            return

        report_data = {
            "scan_summary": {
                "scan_date": self.current_report.scan_date.isoformat(),
                "total_vulnerabilities": self.current_report.vulnerability_count,
                "critical": self.current_report.critical_count,
                "high": self.current_report.high_count,
                "medium": self.current_report.medium_count,
                "low": self.current_report.low_count,
                "fixable": self.current_report.fixable_count,
                "packages_scanned": self.current_report.total_packages_scanned,
            }
        }

        if format_type == "json":
            self._save_json_report(
                report_data, output_file or Path("vulnerability_summary.json")
            )
        else:
            self._print_text_report(report_data, "Summary Report")

    def _generate_detailed_report(
        self, output_file: Optional[Path], format_type: str
    ) -> None:
        """Generate detailed report."""
        if not self.current_report:
            print("❌ No scan data available. Run 'scan' command first.")
            return

        assessments = self.risk_assessor.assess_report(self.current_report)

        report_data = {
            "scan_details": self.current_report.to_dict(),
            "risk_assessments": [assessment.to_dict() for assessment in assessments],
            "vulnerability_details": [
                vuln.to_dict() for vuln in self.current_report.vulnerabilities
            ],
        }

        if format_type == "json":
            self._save_json_report(
                report_data, output_file or Path("vulnerability_detailed.json")
            )
        else:
            self._print_detailed_text_report(report_data)

    def _generate_compliance_report(
        self, output_file: Optional[Path], format_type: str
    ) -> None:
        """Generate compliance report."""
        if not self.current_report:
            print("❌ No scan data available. Run 'scan' command first.")
            return

        violations, metrics = self.compliance_manager.check_compliance(
            self.current_report
        )

        compliance_report = self.compliance_manager.generate_compliance_report(
            framework=ComplianceFramework.NIST_CSF, output_file=output_file
        )

        if format_type == "json":
            self._save_json_report(
                compliance_report, output_file or Path("compliance_report.json")
            )
        else:
            self._print_compliance_text_report(compliance_report, violations, metrics)

    def _generate_trends_report(
        self, output_file: Optional[Path], format_type: str
    ) -> None:
        """Generate trends analysis report."""
        # Use metrics analyzer for comprehensive trends
        metrics_report = self.metrics_analyzer.generate_metrics_report(
            include_trends=True,
            include_historical=True,
            period_days=30,
            output_file=output_file if format_type == "json" else None,
        )

        if format_type == "json":
            if not output_file:
                self._save_json_report(metrics_report, Path("security_trends.json"))
        else:
            self._print_metrics_text_report(metrics_report)

    def _analyze_security_trends(self, events: List[AuditEvent]) -> Dict[str, Any]:
        """Analyze security trends from audit events."""
        # Group events by date
        daily_stats: Dict[str, Dict[str, int]] = {}
        vulnerability_lifecycle: Dict[str, List[AuditEvent]] = {}

        for event in events:
            date_key = event.timestamp.date().isoformat()

            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    "scans": 0,
                    "vulnerabilities_detected": 0,
                    "vulnerabilities_resolved": 0,
                }

            if event.event_type == AuditEventType.SCAN_COMPLETED:
                daily_stats[date_key]["scans"] += 1
            elif event.event_type == AuditEventType.VULNERABILITY_DETECTED:
                daily_stats[date_key]["vulnerabilities_detected"] += 1
            elif event.event_type == AuditEventType.VULNERABILITY_RESOLVED:
                daily_stats[date_key]["vulnerabilities_resolved"] += 1

            # Track vulnerability lifecycle
            if event.vulnerability_id:
                if event.vulnerability_id not in vulnerability_lifecycle:
                    vulnerability_lifecycle[event.vulnerability_id] = []
                vulnerability_lifecycle[event.vulnerability_id].append(event)

        # Calculate metrics
        total_scans = sum(day["scans"] for day in daily_stats.values())
        total_detected = sum(
            day["vulnerabilities_detected"] for day in daily_stats.values()
        )
        total_resolved = sum(
            day["vulnerabilities_resolved"] for day in daily_stats.values()
        )

        # Calculate mean resolution time
        resolution_times = []
        for vuln_id, vuln_events in vulnerability_lifecycle.items():
            vuln_events.sort(key=lambda e: e.timestamp)
            detected_time = None
            resolved_time = None

            for event in vuln_events:
                if event.event_type == AuditEventType.VULNERABILITY_DETECTED:
                    detected_time = event.timestamp
                elif event.event_type == AuditEventType.VULNERABILITY_RESOLVED:
                    resolved_time = event.timestamp
                    break

            if detected_time and resolved_time:
                resolution_time = (resolved_time - detected_time).total_seconds() / 3600
                resolution_times.append(resolution_time)

        mean_resolution_time = (
            sum(resolution_times) / len(resolution_times) if resolution_times else 0
        )

        return {
            "analysis_period": {
                "start_date": (datetime.now() - timedelta(days=30)).isoformat(),
                "end_date": datetime.now().isoformat(),
            },
            "summary_metrics": {
                "total_scans": total_scans,
                "total_vulnerabilities_detected": total_detected,
                "total_vulnerabilities_resolved": total_resolved,
                "resolution_rate": (
                    (total_resolved / total_detected * 100) if total_detected > 0 else 0
                ),
                "mean_resolution_time_hours": mean_resolution_time,
            },
            "daily_statistics": daily_stats,
            "vulnerability_lifecycle_count": len(vulnerability_lifecycle),
        }

    def _update_vulnerability_status(self, report: SecurityReport) -> None:
        """Update vulnerability status tracking."""
        # Track new vulnerabilities
        for vuln in report.vulnerabilities:
            existing_record = self.status_tracker.get_tracking_record(vuln.id)
            if not existing_record:
                # Start tracking new vulnerability
                assessment = self.risk_assessor.assess_vulnerability(vuln)
                self.status_tracker.track_vulnerability(
                    vulnerability=vuln,
                    initial_status=VulnerabilityStatus.DETECTED,
                    priority_score=assessment.risk_score,
                    tags=[vuln.severity.value, vuln.package_name],
                )
                self.vulnerability_status[vuln.id] = "new"
            else:
                self.vulnerability_status[vuln.id] = (
                    existing_record.current_status.value
                )

    def _load_vulnerability_status(self) -> Dict[str, str]:
        """Load vulnerability status from database."""
        try:
            with sqlite3.connect(self.audit_trail.audit_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT vulnerability_id, outcome 
                    FROM audit_events 
                    WHERE event_type = 'vulnerability_detected'
                    ORDER BY timestamp DESC
                """
                )

                status = {}
                for row in cursor.fetchall():
                    vuln_id, outcome = row
                    if vuln_id and vuln_id not in status:
                        status[vuln_id] = outcome or "detected"

                return status
        except Exception as e:
            self.logger.warning(f"Failed to load vulnerability status: {e}")
            return {}

    def _save_vulnerability_status(self) -> None:
        """Save vulnerability status to database."""
        # Status is automatically saved through audit trail events
        pass

    def _save_json_report(self, data: Dict[str, Any], output_file: Path) -> None:
        """Save report data as JSON."""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"📄 Report saved to: {output_file}")

    def _print_text_report(self, data: Dict[str, Any], title: str) -> None:
        """Print text format report."""
        print(f"\n📊 {title}")
        print("=" * 60)

        if "scan_summary" in data:
            summary = data["scan_summary"]
            print(f"Scan Date: {summary['scan_date']}")
            print(f"Total Vulnerabilities: {summary['total_vulnerabilities']}")
            print(f"  Critical: {summary['critical']}")
            print(f"  High: {summary['high']}")
            print(f"  Medium: {summary['medium']}")
            print(f"  Low: {summary['low']}")
            print(f"Fixable: {summary['fixable']}")
            print(f"Packages Scanned: {summary['packages_scanned']}")

    def _print_detailed_text_report(self, data: Dict[str, Any]) -> None:
        """Print detailed text format report."""
        print(f"\n📊 Detailed Vulnerability Report")
        print("=" * 60)

        scan_details = data["scan_details"]
        print(f"Scan Date: {scan_details['scan_date']}")
        print(f"Scanner Version: {scan_details['scanner_version']}")
        print(f"Scan Duration: {scan_details['scan_duration']:.2f}s")

        print(f"\n🎯 Risk Assessments:")
        for assessment in data["risk_assessments"][:5]:  # Show top 5
            print(f"  • {assessment['vulnerability_id']}")
            print(f"    Risk Score: {assessment['risk_score']:.1f}/10.0")
            print(f"    Priority: {assessment['priority_level']}")
            print(f"    Timeline: {assessment['recommended_timeline_hours']}h")

    def _print_compliance_text_report(
        self, report: Dict[str, Any], violations: List[Any], metrics: Any
    ) -> None:
        """Print compliance text format report."""
        print(f"\n📊 Compliance Report")
        print("=" * 60)

        exec_summary = report.get("executive_summary", {})
        compliance_overview = exec_summary.get("compliance_overview", {})

        print(
            f"Overall Compliance Score: {compliance_overview.get('overall_score', 0):.1f}%"
        )
        print(f"Policy Violations: {compliance_overview.get('policy_violations', 0)}")
        print(
            f"Active Policy Rules: {compliance_overview.get('active_policy_rules', 0)}"
        )

        if violations:
            print(f"\n⚠️  Policy Violations ({len(violations)}):")
            for violation in violations[:5]:  # Show first 5
                print(f"  • {violation.violation_type}: {violation.description}")

    def _print_metrics_text_report(self, report: Dict[str, Any]) -> None:
        """Print metrics text format report."""
        print(f"\n📊 Security Metrics & Trends Analysis")
        print("=" * 60)

        current_metrics = report.get("current_metrics", {})
        vuln_metrics = current_metrics.get("vulnerability_metrics", {})
        perf_metrics = current_metrics.get("performance_metrics", {})

        print(f"Report Generated: {report['report_metadata']['generated_at']}")
        print(
            f"Analysis Period: {report['report_metadata']['analysis_period_days']} days"
        )

        print(f"\n📈 Current Metrics:")
        print(f"Total Vulnerabilities: {vuln_metrics.get('total_vulnerabilities', 0)}")
        print(f"  Critical: {vuln_metrics.get('critical_vulnerabilities', 0)}")
        print(f"  High: {vuln_metrics.get('high_vulnerabilities', 0)}")
        print(f"  Medium: {vuln_metrics.get('medium_vulnerabilities', 0)}")
        print(f"  Low: {vuln_metrics.get('low_vulnerabilities', 0)}")
        print(f"Resolved: {vuln_metrics.get('resolved_vulnerabilities', 0)}")
        print(f"Resolution Rate: {perf_metrics.get('resolution_rate', 0):.1f}%")
        print(f"Scan Frequency: {perf_metrics.get('scan_frequency', 0):.1f} scans/day")

        # Show trends if available
        trends = report.get("trend_analysis", [])
        if trends:
            print(f"\n📊 Trend Analysis:")
            for trend in trends[:3]:  # Show top 3 trends
                print(
                    f"  • {trend['metric_name']}: {trend['trend_direction']} "
                    f"(strength: {trend['trend_strength']:.1%})"
                )

        # Show insights
        insights = report.get("insights", [])
        if insights:
            print(f"\n💡 Key Insights:")
            for insight in insights[:5]:  # Show top 5 insights
                print(f"  • {insight}")

        # Show recommendations
        recommendations = report.get("recommendations", [])
        if recommendations:
            print(f"\n🎯 Recommendations:")
            for rec in recommendations[:3]:  # Show top 3 recommendations
                print(f"  • {rec}")

    def _print_trends_text_report(self, data: Dict[str, Any]) -> None:
        """Print trends text format report."""
        print(f"\n📊 Security Trends Analysis")
        print("=" * 60)

        summary = data["summary_metrics"]
        print(
            f"Analysis Period: {data['analysis_period']['start_date']} to {data['analysis_period']['end_date']}"
        )
        print(f"Total Scans: {summary['total_scans']}")
        print(f"Vulnerabilities Detected: {summary['total_vulnerabilities_detected']}")
        print(f"Vulnerabilities Resolved: {summary['total_vulnerabilities_resolved']}")
        print(f"Resolution Rate: {summary['resolution_rate']:.1f}%")
        print(
            f"Mean Resolution Time: {summary['mean_resolution_time_hours']:.1f} hours"
        )

    def update_vulnerability_status(
        self, vulnerability_id: str, new_status: str, notes: str = ""
    ) -> None:
        """
        Update vulnerability status manually.

        Args:
            vulnerability_id: ID of the vulnerability
            new_status: New status to set
            notes: Optional notes about the status change
        """
        try:
            status_enum = VulnerabilityStatus(new_status.lower())
            success = self.status_tracker.update_status(
                vulnerability_id=vulnerability_id,
                new_status=status_enum,
                changed_by="dashboard_user",
                reason="manual_update",
                notes=notes,
            )

            if success:
                print(f"✅ Updated status for {vulnerability_id} to {new_status}")
                self.vulnerability_status[vulnerability_id] = new_status
            else:
                print(f"❌ Failed to update status for {vulnerability_id}")

        except ValueError:
            print(f"❌ Invalid status: {new_status}")
            print(
                "Valid statuses: new, detected, assessed, assigned, in_progress, testing, resolved, verified, closed, ignored, deferred"
            )

    def show_progress_summary(self) -> None:
        """Show overall progress summary."""
        summary = self.status_tracker.get_progress_summary()

        print(f"\n📊 Progress Summary")
        print("=" * 60)
        print(f"Total Vulnerabilities: {summary['total_vulnerabilities']}")

        print(f"\n📈 Status Distribution:")
        for status, count in summary["status_distribution"].items():
            if count > 0:
                print(f"  {status.replace('_', ' ').title()}: {count}")

        print(f"\n🎯 Progress Metrics:")
        progress = summary["progress_metrics"]
        print(f"Average Progress: {progress['average_progress_percentage']:.1f}%")
        print(f"Completed: {progress['completed_count']}")
        print(f"Overdue: {progress['overdue_count']}")
        print(f"Completion Rate: {progress['completion_rate']:.1f}%")

    def show_overdue_vulnerabilities(self) -> None:
        """Show overdue vulnerabilities."""
        overdue = self.status_tracker.get_overdue_vulnerabilities()

        if not overdue:
            print("✅ No overdue vulnerabilities")
            return

        print(f"\n⚠️  Overdue Vulnerabilities ({len(overdue)})")
        print("=" * 60)

        for record in overdue[:10]:  # Show first 10
            metrics = record.progress_metrics
            if metrics:
                days_overdue = (
                    (datetime.now() - metrics.sla_deadline).days
                    if metrics.sla_deadline
                    else 0
                )
                progress_percentage = metrics.progress_percentage
            else:
                days_overdue = 0
                progress_percentage = 0.0

            print(f"• {record.vulnerability_id} - {record.package_name}")
            print(f"  Severity: {record.severity.value.upper()}")
            print(f"  Status: {record.current_status.value}")
            print(f"  Days Overdue: {days_overdue}")
            print(f"  Progress: {progress_percentage:.1f}%")

    def show_help(self) -> None:
        """Display help information."""
        help_text = """
🛡️  Vulnerability Dashboard Help

COMMANDS:
  scan                    - Scan for vulnerabilities
  status [vuln_id]       - Show vulnerability status (all or specific)
  assess                 - Perform risk assessment
  report <type>          - Generate reports (summary, detailed, compliance, trends)
  progress               - Show overall progress summary
  overdue                - Show overdue vulnerabilities
  update <vuln_id> <status> [notes] - Update vulnerability status
  help                   - Show this help message
  exit                   - Exit the dashboard

REPORT TYPES:
  summary                - Basic vulnerability summary
  detailed               - Detailed vulnerability and risk analysis
  compliance             - Compliance and policy report
  trends                 - Security metrics and trends analysis

STATUS VALUES:
  new, detected, assessed, assigned, in_progress, testing, 
  resolved, verified, closed, ignored, deferred

EXAMPLES:
  scan --output scan_results.json
  status PYSEC-2024-48
  assess --details
  report trends --format json --output trends.json
  update PYSEC-2024-48 in_progress "Started remediation work"
  progress
  overdue

For more information, use: command --help
        """
        print(help_text)


def create_cli_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Vulnerability Tracking and Management Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--audit-db", type=Path, help="Path to audit database file")

    parser.add_argument("--config", type=Path, help="Path to configuration file")

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan for vulnerabilities")
    scan_parser.add_argument("--output", type=Path, help="Output file for scan results")
    scan_parser.add_argument(
        "--no-description", action="store_true", help="Skip vulnerability descriptions"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show vulnerability status")
    status_parser.add_argument(
        "vulnerability_id", nargs="?", help="Specific vulnerability ID"
    )

    # Assess command
    assess_parser = subparsers.add_parser("assess", help="Perform risk assessment")
    assess_parser.add_argument(
        "--details", action="store_true", help="Show detailed assessment"
    )

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate reports")
    report_parser.add_argument(
        "type",
        choices=["summary", "detailed", "compliance", "trends"],
        help="Type of report to generate",
    )
    report_parser.add_argument("--output", type=Path, help="Output file")
    report_parser.add_argument(
        "--format",
        choices=["text", "json", "html"],
        default="text",
        help="Report format",
    )

    # Interactive command
    subparsers.add_parser("interactive", help="Start interactive dashboard")

    return parser


def main() -> int:
    """Run the vulnerability dashboard CLI."""
    parser = create_cli_parser()
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        # Initialize dashboard
        dashboard = VulnerabilityDashboard(
            audit_db_path=args.audit_db, config_file=args.config
        )

        if not args.command:
            # No command specified, show help
            parser.print_help()
            return 0

        # Execute command
        if args.command == "scan":
            dashboard.scan_vulnerabilities(
                output_file=args.output, include_description=not args.no_description
            )

        elif args.command == "status":
            dashboard.show_vulnerability_status(args.vulnerability_id)

        elif args.command == "assess":
            dashboard.assess_risks(show_details=args.details)

        elif args.command == "report":
            dashboard.generate_report(
                report_type=args.type, output_file=args.output, format_type=args.format
            )

        elif args.command == "interactive":
            run_interactive_dashboard(dashboard)

        return 0

    except KeyboardInterrupt:
        print("\n👋 Dashboard interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        logging.error(f"Dashboard error: {e}", exc_info=True)
        return 1


def run_interactive_dashboard(dashboard: VulnerabilityDashboard) -> None:
    """Run interactive dashboard mode."""
    print("🛡️  Welcome to Vulnerability Dashboard (Interactive Mode)")
    print("Type 'help' for available commands or 'exit' to quit")

    while True:
        try:
            command = input("\nvuln-dashboard> ").strip()

            if not command:
                continue

            parts = command.split()
            cmd = parts[0].lower()

            if cmd == "exit":
                print("👋 Goodbye!")
                break
            elif cmd == "help":
                dashboard.show_help()
            elif cmd == "scan":
                dashboard.scan_vulnerabilities()
            elif cmd == "status":
                vuln_id = parts[1] if len(parts) > 1 else None
                dashboard.show_vulnerability_status(vuln_id)
            elif cmd == "assess":
                show_details = "--details" in parts
                dashboard.assess_risks(show_details)
            elif cmd == "report":
                if len(parts) < 2:
                    print(
                        "❌ Report type required. Use: report <summary|detailed|compliance|trends>"
                    )
                    continue
                report_type = parts[1]
                dashboard.generate_report(report_type)
            elif cmd == "progress":
                dashboard.show_progress_summary()
            elif cmd == "overdue":
                dashboard.show_overdue_vulnerabilities()
            elif cmd == "update":
                if len(parts) < 3:
                    print("❌ Usage: update <vuln_id> <status> [notes]")
                    continue
                vuln_id = parts[1]
                new_status = parts[2]
                notes = " ".join(parts[3:]) if len(parts) > 3 else ""
                dashboard.update_vulnerability_status(vuln_id, new_status, notes)
            else:
                print(f"❌ Unknown command: {cmd}. Type 'help' for available commands.")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Command error: {e}")


if __name__ == "__main__":
    sys.exit(main())
