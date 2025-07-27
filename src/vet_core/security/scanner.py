"""
Vulnerability scanner for parsing pip-audit output and detecting security issues.

This module provides functionality to execute pip-audit scans and parse the
JSON output into structured vulnerability data.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import SecurityReport, Vulnerability, VulnerabilitySeverity
from .subprocess_utils import SubprocessSecurityError, get_executable_path, secure_subprocess_run

logger = logging.getLogger(__name__)


class ScannerError(Exception):
    """Base exception for scanner-related errors."""

    pass


class ScanTimeoutError(ScannerError):
    """Raised when a scan operation times out."""

    pass


class VulnerabilityScanner:
    """Scanner for detecting vulnerabilities using pip-audit."""

    def __init__(self, timeout: int = 300) -> None:
        """
        Initialize the vulnerability scanner.

        Args:
            timeout: Maximum time in seconds to wait for scan completion
        """
        self.timeout = timeout
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def scan_dependencies(
        self, output_file: Optional[Path] = None, include_description: bool = True
    ) -> SecurityReport:
        """
        Scan dependencies for vulnerabilities using pip-audit.

        Args:
            output_file: Optional path to save the JSON report
            include_description: Whether to include vulnerability descriptions

        Returns:
            SecurityReport containing all found vulnerabilities

        Raises:
            ScannerError: If the scan fails
            ScanTimeoutError: If the scan times out
        """
        start_time = time.time()

        # Build pip-audit command
        cmd = ["pip-audit", "--format=json"]
        if include_description:
            cmd.append("--desc")

        if output_file:
            cmd.extend(["--output", str(output_file)])

        self.logger.info(f"Starting vulnerability scan with command: {' '.join(cmd)}")

        try:
            # Execute pip-audit with secure subprocess wrapper
            # nosec B603: Using secure subprocess wrapper with validation
            result = secure_subprocess_run(
                cmd,
                validate_first_arg=True,  # Validate pip-audit executable path
                timeout=self.timeout,
                check=False,  # Don't raise on non-zero exit (vulnerabilities found)
            )

            scan_duration = time.time() - start_time

            # pip-audit returns non-zero exit code when vulnerabilities are found
            # Only treat it as an error if there's no JSON output or if it's a real error
            has_output = result.stdout or (output_file and output_file.exists())
            if result.returncode != 0 and not has_output:
                error_msg = f"pip-audit failed: {result.stderr}"
                self.logger.error(error_msg)
                raise ScannerError(error_msg)

            # Log stderr as info if it's just reporting vulnerabilities found
            if result.stderr:
                self.logger.info(f"pip-audit: {result.stderr.strip()}")

            # Parse the JSON output
            if result.stdout:
                scan_data = json.loads(result.stdout)
            elif output_file and output_file.exists():
                # When using output file, JSON goes to file instead of stdout
                with open(output_file, "r") as f:
                    scan_data = json.load(f)
            else:
                # No vulnerabilities found
                scan_data = {"dependencies": []}

            # Get pip-audit version
            scanner_version = self._get_scanner_version()

            # Parse vulnerabilities from the new format
            vulnerabilities = self._parse_vulnerabilities_from_dependencies(
                scan_data.get("dependencies", [])
            )

            # Create security report
            report = SecurityReport(
                scan_date=datetime.now(),
                vulnerabilities=vulnerabilities,
                total_packages_scanned=self._count_scanned_packages(scan_data),
                scan_duration=scan_duration,
                scanner_version=scanner_version,
                scan_command=" ".join(cmd),
            )

            self.logger.info(
                f"Scan completed in {scan_duration:.2f}s. "
                f"Found {len(vulnerabilities)} vulnerabilities."
            )

            return report

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse pip-audit JSON output: {e}"
            self.logger.error(error_msg)
            raise ScannerError(error_msg)
        except Exception as e:
            if "timeout" in str(e).lower():
                error_msg = f"Scan timed out after {self.timeout} seconds"
                self.logger.error(error_msg)
                raise ScanTimeoutError(error_msg)
            else:
                error_msg = f"Unexpected error during scan: {e}"
                self.logger.error(error_msg)
                raise ScannerError(error_msg)

    def scan_from_file(self, json_file: Path) -> SecurityReport:
        """
        Parse vulnerabilities from an existing pip-audit JSON file.

        Args:
            json_file: Path to the pip-audit JSON output file

        Returns:
            SecurityReport containing parsed vulnerabilities

        Raises:
            ScannerError: If the file cannot be parsed
        """
        try:
            with open(json_file, "r") as f:
                scan_data = json.load(f)

            # Handle both old and new pip-audit formats
            if "dependencies" in scan_data:
                # New format
                vulnerabilities = self._parse_vulnerabilities_from_dependencies(
                    scan_data.get("dependencies", [])
                )
            else:
                # Old format
                vulnerabilities = self._parse_vulnerabilities(
                    scan_data.get("vulnerabilities", [])
                )

            return SecurityReport(
                scan_date=datetime.now(),
                vulnerabilities=vulnerabilities,
                total_packages_scanned=self._count_scanned_packages(scan_data),
                scan_duration=0.0,  # Unknown from file
                scanner_version="unknown",
                scan_command=f"parsed from {json_file}",
            )

        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            error_msg = f"Failed to parse vulnerability file {json_file}: {e}"
            self.logger.error(error_msg)
            raise ScannerError(error_msg)

    def _parse_vulnerabilities_from_dependencies(
        self, dependencies: List[Dict[str, Any]]
    ) -> List[Vulnerability]:
        """
        Parse vulnerability data from pip-audit JSON output (new format).

        Args:
            dependencies: List of dependency dictionaries from pip-audit

        Returns:
            List of parsed Vulnerability objects
        """
        vulnerabilities = []

        for dep in dependencies:
            package_name = dep.get("name", "")
            package_version = dep.get("version", "")
            vulns = dep.get("vulns", [])

            for vuln in vulns:
                try:
                    # Extract basic information
                    vuln_id = vuln.get("id", "")
                    fix_versions = vuln.get("fix_versions", [])
                    description = vuln.get("description", "")
                    aliases = vuln.get("aliases", [])

                    # Parse severity and CVSS score - not always available in new format
                    cvss_score = None
                    severity = VulnerabilitySeverity.UNKNOWN

                    # Try to derive severity from CVE aliases or description
                    if aliases:
                        # For now, assume medium severity if we have CVE aliases
                        severity = VulnerabilitySeverity.MEDIUM

                    vulnerability = Vulnerability(
                        id=vuln_id,
                        package_name=package_name,
                        installed_version=package_version,
                        fix_versions=fix_versions,
                        severity=severity,
                        cvss_score=cvss_score,
                        description=description,
                        published_date=None,  # Not available in this format
                        discovered_date=datetime.now(),
                    )

                    vulnerabilities.append(vulnerability)

                except Exception as e:
                    self.logger.warning(f"Failed to parse vulnerability {vuln}: {e}")
                    continue

        return vulnerabilities

    def _parse_vulnerabilities(
        self, vuln_data: List[Dict[str, Any]]
    ) -> List[Vulnerability]:
        """
        Parse vulnerability data from pip-audit JSON output.

        Args:
            vuln_data: List of vulnerability dictionaries from pip-audit

        Returns:
            List of parsed Vulnerability objects
        """
        vulnerabilities = []

        for vuln in vuln_data:
            try:
                # Extract basic information
                vuln_id = vuln.get("id", "")
                package_name = vuln.get("package", "")
                installed_version = vuln.get("installed_version", "")
                fix_versions = vuln.get("fix_versions", [])
                description = vuln.get("description", "")

                # Parse severity and CVSS score
                cvss_score = None
                severity = VulnerabilitySeverity.UNKNOWN

                # pip-audit may provide CVSS score in different formats
                if "cvss" in vuln:
                    cvss_score = float(vuln["cvss"])
                    severity = VulnerabilitySeverity.from_cvss_score(cvss_score)
                elif "severity" in vuln:
                    # Try to parse severity directly
                    severity_str = vuln["severity"].lower()
                    try:
                        severity = VulnerabilitySeverity(severity_str)
                    except ValueError:
                        self.logger.warning(f"Unknown severity level: {severity_str}")

                # Parse published date if available
                published_date = None
                if "published" in vuln:
                    try:
                        published_date = datetime.fromisoformat(
                            vuln["published"].replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        self.logger.warning(
                            f"Could not parse published date: {vuln.get('published')}"
                        )

                vulnerability = Vulnerability(
                    id=vuln_id,
                    package_name=package_name,
                    installed_version=installed_version,
                    fix_versions=fix_versions,
                    severity=severity,
                    cvss_score=cvss_score,
                    description=description,
                    published_date=published_date,
                    discovered_date=datetime.now(),
                )

                vulnerabilities.append(vulnerability)

            except Exception as e:
                self.logger.warning(f"Failed to parse vulnerability {vuln}: {e}")
                continue

        return vulnerabilities

    def _get_scanner_version(self) -> str:
        """Get the version of pip-audit being used."""
        try:
            # nosec B603: Using secure subprocess wrapper with validation
            result = secure_subprocess_run(
                ["pip-audit", "--version"], 
                validate_first_arg=True,  # Validate pip-audit executable path
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except SubprocessSecurityError as e:
            self.logger.warning(f"Security validation failed for pip-audit version check: {e}")
        except Exception as e:
            self.logger.warning(f"Could not determine pip-audit version: {e}")

        return "unknown"

    def _count_scanned_packages(self, scan_data: Dict[str, Any]) -> int:
        """Count the total number of packages that were scanned."""
        # New format has dependencies list
        if "dependencies" in scan_data:
            return len(scan_data["dependencies"])

        # Old format - count unique packages from vulnerabilities
        if "vulnerabilities" not in scan_data:
            return 0

        packages = set()
        for vuln in scan_data["vulnerabilities"]:
            if "package" in vuln:
                packages.add(vuln["package"])

        # This is a minimum count - actual scanned packages may be higher
        return len(packages) if packages else 1
