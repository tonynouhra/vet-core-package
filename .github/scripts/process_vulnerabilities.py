#!/usr/bin/env python3
"""
GitHub Actions script to process vulnerability scan results.
"""

import json
import sys
from pathlib import Path


def count_vulnerabilities(json_file):
    """Count vulnerabilities from pip-audit JSON output."""
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        # Handle both old and new pip-audit formats
        if "dependencies" in data:
            count = sum(len(dep.get("vulns", [])) for dep in data["dependencies"])
        else:
            count = len(data.get("vulnerabilities", []))

        return count
    except Exception:
        return 0


def process_security_report(reports_dir):
    """Process security report and extract metrics."""
    sys.path.insert(0, "src")

    from vet_core.security.scanner import VulnerabilityScanner
    from vet_core.security.reporter import SecurityReporter

    try:
        # Initialize components
        scanner = VulnerabilityScanner()
        reporter = SecurityReporter()

        # Parse the pip-audit JSON output
        report = scanner.scan_from_file(Path(reports_dir) / "pip-audit-raw.json")

        # Generate comprehensive reports
        reporter.generate_json_report(
            report,
            Path(reports_dir) / "security-report.json",
            include_risk_assessment=True,
        )

        reporter.generate_markdown_summary(
            report, Path(reports_dir) / "security-summary.md"
        )

        reporter.generate_csv_report(report, Path(reports_dir) / "security-report.csv")

        # Output metrics for GitHub Actions
        print(f"CRITICAL_COUNT={report.critical_count}")
        print(f"HIGH_COUNT={report.high_count}")
        print(f"MEDIUM_COUNT={report.medium_count}")
        print(f"LOW_COUNT={report.low_count}")
        print(f"FIXABLE_COUNT={report.fixable_count}")

        # Determine notification level
        if report.critical_count > 0:
            print("NOTIFICATION_LEVEL=critical")
        elif report.high_count > 0:
            print("NOTIFICATION_LEVEL=high")
        elif report.medium_count > 0:
            print("NOTIFICATION_LEVEL=medium")
        else:
            print("NOTIFICATION_LEVEL=low")

    except Exception as e:
        print(f"Error processing vulnerability report: {e}")
        print("NOTIFICATION_LEVEL=error")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: process_vulnerabilities.py <command> [args...]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "count":
        if len(sys.argv) < 3:
            print("Usage: process_vulnerabilities.py count <json_file>")
            sys.exit(1)
        count = count_vulnerabilities(sys.argv[2])
        print(count)

    elif command == "process":
        if len(sys.argv) < 3:
            print("Usage: process_vulnerabilities.py process <reports_dir>")
            sys.exit(1)
        process_security_report(sys.argv[2])

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
