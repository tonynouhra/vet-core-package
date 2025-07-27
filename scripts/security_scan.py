#!/usr/bin/env python3
"""
Security vulnerability scanning script.

This script demonstrates the vulnerability scanning and reporting infrastructure
by performing a pip-audit scan and generating various types of reports.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

# Add the src directory to the path so we can import vet_core
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vet_core.security import (
    VulnerabilityScanner,
    SecurityReporter,
    RiskAssessor,
)


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> int:
    """Main entry point for the security scanning script."""
    parser = argparse.ArgumentParser(
        description="Scan for security vulnerabilities and generate reports"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("security-reports"),
        help="Directory to save reports (default: security-reports)",
    )
    parser.add_argument(
        "--json-file",
        type=Path,
        help="Parse existing pip-audit JSON file instead of running new scan",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Scan timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--no-descriptions",
        action="store_true",
        help="Skip vulnerability descriptions in scan",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Create output directory
        args.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        scanner = VulnerabilityScanner(timeout=args.timeout)
        risk_assessor = RiskAssessor()
        reporter = SecurityReporter(risk_assessor)

        # Perform scan or parse existing file
        if args.json_file:
            logger.info(f"Parsing existing vulnerability file: {args.json_file}")
            if not args.json_file.exists():
                logger.error(f"File not found: {args.json_file}")
                return 1

            security_report = scanner.scan_from_file(args.json_file)
        else:
            logger.info("Starting vulnerability scan...")

            # Save raw pip-audit output
            raw_output_file = args.output_dir / "pip-audit-raw.json"

            security_report = scanner.scan_dependencies(
                output_file=raw_output_file,
                include_description=not args.no_descriptions,
            )

        # Generate reports
        logger.info("Generating security reports...")

        # JSON report with risk assessment
        json_report = reporter.generate_json_report(
            security_report,
            output_file=args.output_dir / "security-report.json",
            include_risk_assessment=True,
        )

        # Markdown summary
        markdown_summary = reporter.generate_markdown_summary(
            security_report, output_file=args.output_dir / "security-summary.md"
        )

        # CSV report
        csv_report = reporter.generate_csv_report(
            security_report, output_file=args.output_dir / "security-report.csv"
        )

        # Print summary to console
        print("\n" + "=" * 60)
        print("SECURITY VULNERABILITY SCAN RESULTS")
        print("=" * 60)
        print(
            f"Scan completed: {security_report.scan_date.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        print(f"Total vulnerabilities found: {security_report.vulnerability_count}")
        print(f"Packages scanned: {security_report.total_packages_scanned}")
        print(f"Scan duration: {security_report.scan_duration:.2f} seconds")
        print()

        if security_report.vulnerability_count > 0:
            print("Severity breakdown:")
            print(f"  Critical: {security_report.critical_count}")
            print(f"  High:     {security_report.high_count}")
            print(f"  Medium:   {security_report.medium_count}")
            print(f"  Low:      {security_report.low_count}")
            print(f"  Fixable:  {security_report.fixable_count}")
            print()

            # Show priority breakdown
            prioritized = risk_assessor.get_prioritized_vulnerabilities(security_report)
            priority_summary = risk_assessor.generate_priority_summary(prioritized)

            print("Priority breakdown:")
            for level, count in priority_summary["priority_counts"].items():
                if count > 0:
                    print(f"  {level.title()}: {count}")
            print()

            if priority_summary["recommendations"]:
                print("Recommendations:")
                for rec in priority_summary["recommendations"]:
                    print(f"  • {rec}")
                print()

            # Show top 5 highest risk vulnerabilities
            assessments = risk_assessor.assess_report(security_report)
            top_risks = assessments[:5]  # Already sorted by risk score

            if top_risks:
                print("Top vulnerabilities by risk score:")
                for assessment in top_risks:
                    vuln = next(
                        v
                        for v in security_report.vulnerabilities
                        if v.id == assessment.vulnerability_id
                    )
                    print(
                        f"  • {vuln.id} ({vuln.package_name}): {assessment.risk_score:.1f}/10.0 - {assessment.priority_level}"
                    )
                print()

        print(f"Reports saved to: {args.output_dir}")
        print("  • security-report.json (comprehensive JSON report)")
        print("  • security-summary.md (human-readable summary)")
        print("  • security-report.csv (spreadsheet-compatible)")
        if not args.json_file:
            print("  • pip-audit-raw.json (raw pip-audit output)")

        # Return appropriate exit code
        if security_report.critical_count > 0:
            logger.warning("Critical vulnerabilities found!")
            return 2  # Critical vulnerabilities
        elif security_report.vulnerability_count > 0:
            logger.info("Vulnerabilities found but none critical")
            return 1  # Non-critical vulnerabilities
        else:
            logger.info("No vulnerabilities found")
            return 0  # Clean scan

    except KeyboardInterrupt:
        logger.info("Scan interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        if args.verbose:
            logger.exception("Full error details:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
