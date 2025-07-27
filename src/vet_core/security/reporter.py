"""
Security report generation and formatting module.

This module provides functionality to generate various types of security
reports from vulnerability data, including structured reports, summaries,
and audit trails.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO

from .assessor import RiskAssessment, RiskAssessor
from .models import SecurityReport, Vulnerability, VulnerabilitySeverity

logger = logging.getLogger(__name__)


class SecurityReporter:
    """Generates various types of security reports from vulnerability data."""

    def __init__(self, risk_assessor: Optional[RiskAssessor] = None) -> None:
        """
        Initialize the security reporter.

        Args:
            risk_assessor: Optional risk assessor for priority analysis
        """
        self.risk_assessor = risk_assessor or RiskAssessor()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def generate_json_report(
        self,
        report: SecurityReport,
        output_file: Optional[Path] = None,
        include_risk_assessment: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive JSON report.

        Args:
            report: The security report to format
            output_file: Optional file path to save the report
            include_risk_assessment: Whether to include risk assessments

        Returns:
            Dictionary containing the formatted report
        """
        # Start with basic report data
        json_report = report.to_dict()

        # Add risk assessments if requested
        if include_risk_assessment:
            assessments = self.risk_assessor.assess_report(report)
            prioritized = self.risk_assessor.get_prioritized_vulnerabilities(report)
            priority_summary = self.risk_assessor.generate_priority_summary(prioritized)

            json_report["risk_assessment"] = {
                "assessments": [assessment.to_dict() for assessment in assessments],
                "priority_summary": priority_summary,
                "prioritized_vulnerabilities": {
                    level: [
                        {
                            "vulnerability": vuln.to_dict(),
                            "assessment": assessment.to_dict(),
                        }
                        for vuln, assessment in vulns
                    ]
                    for level, vulns in prioritized.items()
                },
            }

        # Add metadata
        json_report["report_metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "generator": "vet-core-security-reporter",
            "version": "1.0.0",
        }

        # Save to file if requested
        if output_file:
            self._save_json_report(json_report, output_file)

        return json_report

    def generate_markdown_summary(
        self, report: SecurityReport, output_file: Optional[Path] = None
    ) -> str:
        """
        Generate a human-readable markdown summary report.

        Args:
            report: The security report to summarize
            output_file: Optional file path to save the summary

        Returns:
            Markdown-formatted summary string
        """
        # Get risk assessments and prioritization
        prioritized = self.risk_assessor.get_prioritized_vulnerabilities(report)
        priority_summary = self.risk_assessor.generate_priority_summary(prioritized)

        # Build markdown content
        lines = [
            "# Security Vulnerability Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Scan Date:** {report.scan_date.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Scanner:** {report.scanner_version}",
            f"**Scan Duration:** {report.scan_duration:.2f} seconds",
            "",
            "## Executive Summary",
            "",
            f"- **Total Vulnerabilities:** {report.vulnerability_count}",
            f"- **Packages Scanned:** {report.total_packages_scanned}",
            f"- **Fixable Vulnerabilities:** {report.fixable_count}",
            "",
            "### Severity Breakdown",
            "",
            f"- **Critical:** {report.critical_count}",
            f"- **High:** {report.high_count}",
            f"- **Medium:** {report.medium_count}",
            f"- **Low:** {report.low_count}",
            "",
            "### Priority Breakdown",
            "",
            f"- **Immediate (24h):** {priority_summary['priority_counts']['immediate']}",
            f"- **Urgent (72h):** {priority_summary['priority_counts']['urgent']}",
            f"- **Scheduled (1 week):** {priority_summary['priority_counts']['scheduled']}",
            f"- **Planned (1 month):** {priority_summary['priority_counts']['planned']}",
            "",
        ]

        # Add recommendations
        if priority_summary["recommendations"]:
            lines.extend(
                [
                    "## Recommendations",
                    "",
                ]
            )
            for rec in priority_summary["recommendations"]:
                lines.append(f"- {rec}")
            lines.append("")

        # Add detailed vulnerability sections by priority
        for priority_level in ["immediate", "urgent", "scheduled", "planned"]:
            vulns = prioritized[priority_level]
            if not vulns:
                continue

            priority_title = priority_level.title()
            lines.extend(
                [
                    f"## {priority_title} Priority Vulnerabilities",
                    "",
                ]
            )

            for vuln, assessment in vulns:
                lines.extend(
                    [
                        f"### {vuln.id} - {vuln.package_name}",
                        "",
                        f"- **Package:** {vuln.package_name} {vuln.installed_version}",
                        f"- **Severity:** {vuln.severity.value.title()}",
                        f"- **Risk Score:** {assessment.risk_score:.1f}/10.0",
                    ]
                )

                if vuln.cvss_score:
                    lines.append(f"- **CVSS Score:** {vuln.cvss_score}")

                if vuln.fix_versions:
                    fix_versions = ", ".join(vuln.fix_versions)
                    lines.append(f"- **Fix Versions:** {fix_versions}")
                    lines.append(
                        f"- **Recommended Fix:** {vuln.recommended_fix_version}"
                    )
                else:
                    lines.append("- **Fix Available:** No")

                if vuln.description:
                    lines.extend(
                        [
                            f"- **Description:** {vuln.description}",
                        ]
                    )

                lines.append("")

        # Add scan details
        if report.vulnerabilities:
            lines.extend(
                [
                    "## Scan Details",
                    "",
                    f"**Command:** `{report.scan_command}`",
                    "",
                    "### All Vulnerabilities",
                    "",
                    "| ID | Package | Version | Severity | Fix Available |",
                    "|----|---------|---------|------------|---------------|",
                ]
            )

            for vuln in report.vulnerabilities:
                fix_available = "Yes" if vuln.is_fixable else "No"
                lines.append(
                    f"| {vuln.id} | {vuln.package_name} | {vuln.installed_version} | "
                    f"{vuln.severity.value.title()} | {fix_available} |"
                )

        markdown_content = "\n".join(lines)

        # Save to file if requested
        if output_file:
            self._save_text_report(markdown_content, output_file)

        return markdown_content

    def generate_csv_report(
        self, report: SecurityReport, output_file: Optional[Path] = None
    ) -> str:
        """
        Generate a CSV report suitable for spreadsheet analysis.

        Args:
            report: The security report to format
            output_file: Optional file path to save the CSV

        Returns:
            CSV-formatted string
        """
        # Get risk assessments
        assessments = self.risk_assessor.assess_report(report)
        assessment_map = {a.vulnerability_id: a for a in assessments}

        # Prepare CSV data
        csv_data = []
        headers = [
            "Vulnerability ID",
            "Package Name",
            "Installed Version",
            "Severity",
            "CVSS Score",
            "Risk Score",
            "Priority Level",
            "Fix Available",
            "Recommended Fix Version",
            "Description",
            "Published Date",
            "Discovered Date",
        ]

        csv_data.append(headers)

        for vuln in report.vulnerabilities:
            assessment = assessment_map.get(vuln.id)

            row = [
                str(vuln.id),
                str(vuln.package_name),
                str(vuln.installed_version),
                str(vuln.severity.value),
                str(vuln.cvss_score) if vuln.cvss_score is not None else "",
                f"{assessment.risk_score:.1f}" if assessment else "",
                str(assessment.priority_level) if assessment else "",
                "Yes" if vuln.is_fixable else "No",
                (
                    str(vuln.recommended_fix_version)
                    if vuln.recommended_fix_version
                    else ""
                ),
                (
                    vuln.description.replace("\n", " ").replace("\r", "")
                    if vuln.description
                    else ""
                ),
                vuln.published_date.isoformat() if vuln.published_date else "",
                vuln.discovered_date.isoformat(),
            ]
            csv_data.append(row)

        # Convert to CSV string
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(csv_data)
        csv_content = output.getvalue()
        output.close()

        # Save to file if requested
        if output_file:
            self._save_text_report(csv_content, output_file)

        return csv_content

    def generate_audit_trail(
        self, reports: List[SecurityReport], output_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Generate an audit trail from multiple security reports.

        Args:
            reports: List of security reports over time
            output_file: Optional file path to save the audit trail

        Returns:
            Dictionary containing audit trail data
        """
        if not reports:
            return {"error": "No reports provided for audit trail"}

        # Sort reports by scan date
        sorted_reports = sorted(reports, key=lambda r: r.scan_date)

        audit_trail = {
            "audit_period": {
                "start_date": sorted_reports[0].scan_date.isoformat(),
                "end_date": sorted_reports[-1].scan_date.isoformat(),
                "total_scans": len(sorted_reports),
            },
            "vulnerability_trends": self._analyze_vulnerability_trends(sorted_reports),
            "remediation_tracking": self._track_remediation_progress(sorted_reports),
            "compliance_metrics": self._calculate_compliance_metrics(sorted_reports),
            "scan_history": [
                {
                    "scan_date": report.scan_date.isoformat(),
                    "total_vulnerabilities": report.vulnerability_count,
                    "critical": report.critical_count,
                    "high": report.high_count,
                    "medium": report.medium_count,
                    "low": report.low_count,
                    "fixable": report.fixable_count,
                }
                for report in sorted_reports
            ],
            "generated_at": datetime.now().isoformat(),
        }

        # Save to file if requested
        if output_file:
            self._save_json_report(audit_trail, output_file)

        return audit_trail

    def _analyze_vulnerability_trends(
        self, reports: List[SecurityReport]
    ) -> Dict[str, Any]:
        """Analyze trends in vulnerability counts over time."""
        if len(reports) < 2:
            return {"trend": "insufficient_data"}

        first_report = reports[0]
        last_report = reports[-1]

        return {
            "total_change": last_report.vulnerability_count
            - first_report.vulnerability_count,
            "critical_change": last_report.critical_count - first_report.critical_count,
            "high_change": last_report.high_count - first_report.high_count,
            "medium_change": last_report.medium_count - first_report.medium_count,
            "low_change": last_report.low_count - first_report.low_count,
            "trend_direction": (
                "improving"
                if last_report.vulnerability_count < first_report.vulnerability_count
                else "worsening"
            ),
        }

    def _track_remediation_progress(
        self, reports: List[SecurityReport]
    ) -> Dict[str, Any]:
        """Track which vulnerabilities have been remediated over time."""
        if len(reports) < 2:
            return {"remediation_tracking": "insufficient_data"}

        # Track vulnerability IDs across reports
        all_vulns = set()
        report_vulns = []

        for report in reports:
            vuln_ids = {v.id for v in report.vulnerabilities}
            report_vulns.append(vuln_ids)
            all_vulns.update(vuln_ids)

        # Find remediated vulnerabilities
        remediated = []
        for vuln_id in all_vulns:
            first_seen = None
            last_seen = None

            for i, vuln_ids in enumerate(report_vulns):
                if vuln_id in vuln_ids:
                    if first_seen is None:
                        first_seen = i
                    last_seen = i

            if (
                first_seen is not None
                and last_seen is not None
                and last_seen < len(reports) - 1
            ):
                remediated.append(
                    {
                        "vulnerability_id": vuln_id,
                        "first_seen": reports[first_seen].scan_date.isoformat(),
                        "last_seen": reports[last_seen].scan_date.isoformat(),
                    }
                )

        return {
            "total_remediated": len(remediated),
            "remediated_vulnerabilities": remediated,
        }

    def _calculate_compliance_metrics(
        self, reports: List[SecurityReport]
    ) -> Dict[str, Any]:
        """Calculate compliance and performance metrics."""
        if not reports:
            return {}

        latest_report = reports[-1]

        # Calculate mean time between scans
        if len(reports) > 1:
            time_diffs = []
            for i in range(1, len(reports)):
                diff = reports[i].scan_date - reports[i - 1].scan_date
                time_diffs.append(diff.total_seconds() / 3600)  # Convert to hours

            mean_scan_interval = sum(time_diffs) / len(time_diffs)
        else:
            mean_scan_interval = 0

        return {
            "current_vulnerability_count": latest_report.vulnerability_count,
            "current_critical_count": latest_report.critical_count,
            "current_fixable_count": latest_report.fixable_count,
            "mean_scan_interval_hours": mean_scan_interval,
            "compliance_status": (
                "compliant" if latest_report.critical_count == 0 else "non_compliant"
            ),
        }

    def _save_json_report(self, report_data: Dict[str, Any], output_file: Path) -> None:
        """Save JSON report to file."""
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(report_data, f, indent=2, default=str)
            self.logger.info(f"JSON report saved to {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save JSON report to {output_file}: {e}")
            raise

    def _save_text_report(self, content: str, output_file: Path) -> None:
        """Save text-based report to file."""
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                f.write(content)
            self.logger.info(f"Text report saved to {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save text report to {output_file}: {e}")
            raise
