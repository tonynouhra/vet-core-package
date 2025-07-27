#!/usr/bin/env python3
"""
Security monitoring script for automated vulnerability scanning and notifications.

This script can be used both in CI/CD pipelines and as a standalone tool for
security monitoring and alerting.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vet_core.security.scanner import VulnerabilityScanner
from vet_core.security.reporter import SecurityReporter
from vet_core.security.assessor import RiskAssessor
from vet_core.security.notifications import (
    SecurityNotifier,
    create_notification_config_from_env,
)


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_security_scan(
    output_dir: Path, include_descriptions: bool = True, timeout: int = 300
) -> Optional[Path]:
    """
    Run a comprehensive security scan and generate reports.

    Args:
        output_dir: Directory to save reports
        include_descriptions: Whether to include vulnerability descriptions
        timeout: Scan timeout in seconds

    Returns:
        Path to the main security report JSON file, or None if scan failed
    """
    logger = logging.getLogger(__name__)

    try:
        # Initialize scanner and reporter
        scanner = VulnerabilityScanner(timeout=timeout)
        reporter = SecurityReporter()

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Run vulnerability scan
        logger.info("Starting vulnerability scan...")
        raw_report_path = output_dir / "pip-audit-raw.json"

        report = scanner.scan_dependencies(
            output_file=raw_report_path, include_description=include_descriptions
        )

        logger.info(
            f"Scan completed. Found {report.vulnerability_count} vulnerabilities."
        )

        # Generate comprehensive reports
        logger.info("Generating security reports...")

        # JSON report with risk assessment
        json_report_path = output_dir / "security-report.json"
        json_report = reporter.generate_json_report(
            report, output_file=json_report_path, include_risk_assessment=True
        )

        # Markdown summary
        markdown_path = output_dir / "security-summary.md"
        markdown_summary = reporter.generate_markdown_summary(
            report, output_file=markdown_path
        )

        # CSV export
        csv_path = output_dir / "security-report.csv"
        csv_report = reporter.generate_csv_report(report, output_file=csv_path)

        # Create scan summary for CI/CD
        summary_path = output_dir / "scan-summary.json"
        scan_summary = {
            "scan_date": report.scan_date.isoformat(),
            "total_vulnerabilities": report.vulnerability_count,
            "severity_counts": {
                "critical": report.critical_count,
                "high": report.high_count,
                "medium": report.medium_count,
                "low": report.low_count,
            },
            "fixable_count": report.fixable_count,
            "scan_duration": report.scan_duration,
            "reports_generated": {
                "json_report": str(json_report_path),
                "markdown_summary": str(markdown_path),
                "csv_export": str(csv_path),
                "raw_scan": str(raw_report_path),
            },
        }

        with open(summary_path, "w") as f:
            json.dump(scan_summary, f, indent=2)

        logger.info(f"Reports generated in {output_dir}")
        logger.info(
            f"Summary: {report.vulnerability_count} vulnerabilities "
            f"({report.critical_count} critical, {report.high_count} high)"
        )

        return json_report_path

    except Exception as e:
        logger.error(f"Security scan failed: {e}")
        return None


def send_notifications(
    report_path: Path,
    channels: Optional[List[str]] = None,
    config_file: Optional[Path] = None,
) -> bool:
    """
    Send security notifications based on scan results.

    Args:
        report_path: Path to the security report JSON file
        channels: List of notification channels to use
        config_file: Optional path to notification config file

    Returns:
        True if notifications were sent successfully
    """
    logger = logging.getLogger(__name__)

    try:
        # Load security report
        with open(report_path, "r") as f:
            report_data = json.load(f)

        # Reconstruct SecurityReport object (simplified)
        from vet_core.security.models import (
            SecurityReport,
            Vulnerability,
            VulnerabilitySeverity,
        )
        from datetime import datetime

        vulnerabilities = []
        for vuln_data in report_data.get("vulnerabilities", []):
            vuln = Vulnerability(
                id=vuln_data["id"],
                package_name=vuln_data["package_name"],
                installed_version=vuln_data["installed_version"],
                fix_versions=vuln_data["fix_versions"],
                severity=VulnerabilitySeverity(vuln_data["severity"]),
                cvss_score=vuln_data.get("cvss_score"),
                description=vuln_data.get("description", ""),
                published_date=(
                    datetime.fromisoformat(vuln_data["published_date"])
                    if vuln_data.get("published_date")
                    else None
                ),
                discovered_date=datetime.fromisoformat(vuln_data["discovered_date"]),
            )
            vulnerabilities.append(vuln)

        report = SecurityReport(
            scan_date=datetime.fromisoformat(report_data["scan_date"]),
            vulnerabilities=vulnerabilities,
            total_packages_scanned=report_data["total_packages_scanned"],
            scan_duration=report_data["scan_duration"],
            scanner_version=report_data["scanner_version"],
            scan_command=report_data.get("scan_command", ""),
        )

        # Load notification configuration
        if config_file and config_file.exists():
            # Load from file (JSON format)
            with open(config_file, "r") as f:
                config_data = json.load(f)
            # Convert to NotificationConfig (simplified)
            from vet_core.security.notifications import NotificationConfig

            config = NotificationConfig(**config_data)
        else:
            # Load from environment variables
            config = create_notification_config_from_env()

        # Initialize notifier
        notifier = SecurityNotifier(config)

        # Send notifications
        if report.vulnerability_count > 0:
            logger.info(
                f"Sending notifications for {report.vulnerability_count} vulnerabilities..."
            )
            results = notifier.send_vulnerability_alert(report, channels)

            success_count = sum(1 for success in results.values() if success)
            total_channels = len(results)

            logger.info(
                f"Notifications sent: {success_count}/{total_channels} channels successful"
            )

            if success_count > 0:
                return True
            else:
                logger.warning("All notification channels failed")
                return False
        else:
            logger.info("No vulnerabilities found, skipping notifications")
            return True

    except Exception as e:
        logger.error(f"Failed to send notifications: {e}")
        return False


def main():
    """Main entry point for the security monitoring script."""
    parser = argparse.ArgumentParser(
        description="Security monitoring and vulnerability scanning tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run scan and save reports
  python security_monitoring.py scan --output-dir ./security-reports
  
  # Run scan and send notifications
  python security_monitoring.py scan --output-dir ./security-reports --notify
  
  # Send notifications for existing report
  python security_monitoring.py notify --report ./security-reports/security-report.json
  
  # Run scan with specific notification channels
  python security_monitoring.py scan --output-dir ./reports --notify --channels slack email
        """,
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Run vulnerability scan")
    scan_parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("./security-reports"),
        help="Directory to save reports (default: ./security-reports)",
    )
    scan_parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=300,
        help="Scan timeout in seconds (default: 300)",
    )
    scan_parser.add_argument(
        "--no-descriptions",
        action="store_true",
        help="Skip vulnerability descriptions (faster scan)",
    )
    scan_parser.add_argument(
        "--notify", action="store_true", help="Send notifications after scan"
    )
    scan_parser.add_argument(
        "--channels",
        nargs="+",
        choices=["email", "slack", "github"],
        help="Notification channels to use",
    )
    scan_parser.add_argument(
        "--config", type=Path, help="Path to notification config file"
    )

    # Notify command
    notify_parser = subparsers.add_parser(
        "notify", help="Send notifications for existing report"
    )
    notify_parser.add_argument(
        "--report",
        "-r",
        type=Path,
        required=True,
        help="Path to security report JSON file",
    )
    notify_parser.add_argument(
        "--channels",
        nargs="+",
        choices=["email", "slack", "github"],
        help="Notification channels to use",
    )
    notify_parser.add_argument(
        "--config", type=Path, help="Path to notification config file"
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "scan":
            # Run vulnerability scan
            report_path = run_security_scan(
                output_dir=args.output_dir,
                include_descriptions=not args.no_descriptions,
                timeout=args.timeout,
            )

            if not report_path:
                logger.error("Security scan failed")
                return 1

            # Send notifications if requested
            if args.notify:
                success = send_notifications(
                    report_path=report_path,
                    channels=args.channels,
                    config_file=args.config,
                )
                if not success:
                    logger.warning(
                        "Notifications failed, but scan completed successfully"
                    )

            logger.info("Security monitoring completed successfully")
            return 0

        elif args.command == "notify":
            # Send notifications for existing report
            if not args.report.exists():
                logger.error(f"Report file not found: {args.report}")
                return 1

            success = send_notifications(
                report_path=args.report, channels=args.channels, config_file=args.config
            )

            if success:
                logger.info("Notifications sent successfully")
                return 0
            else:
                logger.error("Failed to send notifications")
                return 1

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
