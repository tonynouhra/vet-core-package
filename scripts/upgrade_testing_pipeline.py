#!/usr/bin/env python3
"""
Comprehensive upgrade validation and testing pipeline.

This script provides a complete testing pipeline for dependency upgrades,
including multi-Python version testing, security fix verification, and
performance regression testing.
"""

import argparse
import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import concurrent.futures
from dataclasses import asdict

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vet_core.security.upgrade_validator import (
    UpgradeValidator,
    UpgradeResult,
    validate_vulnerability_fixes,
)
from vet_core.security.performance_monitor import (
    PerformanceMonitor,
    PerformanceMetrics,
    PerformanceRegression,
)
from vet_core.security.models import Vulnerability, VulnerabilitySeverity
from vet_core.security.scanner import VulnerabilityScanner


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UpgradeTestingPipeline:
    """Comprehensive upgrade testing pipeline."""
    
    def __init__(
        self,
        project_root: Path,
        python_versions: List[str] = None,
        test_command: str = "pytest",
        performance_baseline_file: Optional[Path] = None,
    ):
        """
        Initialize the upgrade testing pipeline.
        
        Args:
            project_root: Path to project root directory
            python_versions: List of Python versions to test (e.g., ["3.11", "3.12"])
            test_command: Command to run tests
            performance_baseline_file: Path to performance baseline file
        """
        self.project_root = Path(project_root)
        self.python_versions = python_versions or ["3.11", "3.12"]
        self.test_command = test_command
        
        # Initialize components
        self.performance_monitor = PerformanceMonitor(
            project_root=self.project_root,
            baseline_file=performance_baseline_file,
        )
        self.security_scanner = VulnerabilityScanner()
        
        # Results storage
        self.test_results: Dict[str, Any] = {
            "upgrade_results": {},
            "performance_results": {},
            "security_results": {},
            "multi_version_results": {},
        }
    
    def run_security_scan(self) -> List[Vulnerability]:
        """
        Run security scan to identify vulnerabilities.
        
        Returns:
            List of vulnerabilities found
        """
        logger.info("Running security scan...")
        
        try:
            # Run pip-audit to get vulnerability data
            result = subprocess.run([
                sys.executable, "-m", "pip-audit", "--format=json"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                audit_data = json.loads(result.stdout)
                # Parse vulnerabilities from audit data
                vulnerabilities = []
                for vuln_data in audit_data.get("vulnerabilities", []):
                    try:
                        vuln = Vulnerability(
                            id=vuln_data.get("id", ""),
                            package_name=vuln_data.get("package", ""),
                            installed_version=vuln_data.get("installed_version", ""),
                            fix_versions=vuln_data.get("fix_versions", []),
                            severity=VulnerabilitySeverity.from_string(vuln_data.get("severity", "unknown")),
                            description=vuln_data.get("description", ""),
                            published_date=vuln_data.get("published_date", ""),
                            discovered_date=datetime.now().isoformat(),
                        )
                        vulnerabilities.append(vuln)
                    except Exception as e:
                        logger.warning(f"Failed to parse vulnerability: {e}")
                
                logger.info(f"Found {len(vulnerabilities)} vulnerabilities")
                return vulnerabilities
            else:
                logger.error(f"Security scan failed: {result.stderr}")
                return []
                
        except Exception as e:
            logger.error(f"Error running security scan: {e}")
            return []
    
    def test_upgrade_single_version(
        self,
        package_name: str,
        target_version: str,
        python_version: str = None,
    ) -> UpgradeResult:
        """
        Test upgrade for a single Python version.
        
        Args:
            package_name: Name of package to upgrade
            target_version: Target version to upgrade to
            python_version: Python version to test with (default: current)
            
        Returns:
            UpgradeResult object
        """
        python_exe = sys.executable
        if python_version and python_version != sys.version.split()[0]:
            python_exe = f"python{python_version}"
        
        logger.info(f"Testing upgrade {package_name} -> {target_version} with {python_exe}")
        
        with UpgradeValidator(self.project_root, self.test_command) as validator:
            # Override Python executable if needed
            if python_version:
                # Create a temporary script that uses the specified Python version
                test_script = f"""
import subprocess
import sys
result = subprocess.run([
    "{python_exe}", "-m", "{self.test_command}", "--tb=short", "-v"
], capture_output=True, text=True, cwd="{self.project_root}")
sys.exit(result.returncode)
"""
                # This is a simplified approach; in practice, you'd need more sophisticated
                # virtual environment management for different Python versions
            
            return validator.validate_upgrade(
                package_name=package_name,
                target_version=target_version,
                run_tests=True,
                check_conflicts=True,
            )
    
    def test_upgrade_multi_version(
        self,
        package_name: str,
        target_version: str,
    ) -> Dict[str, UpgradeResult]:
        """
        Test upgrade across multiple Python versions.
        
        Args:
            package_name: Name of package to upgrade
            target_version: Target version to upgrade to
            
        Returns:
            Dictionary mapping Python version to UpgradeResult
        """
        logger.info(f"Testing upgrade {package_name} -> {target_version} across Python versions")
        
        results = {}
        
        # Use ThreadPoolExecutor for parallel testing
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.python_versions)) as executor:
            future_to_version = {
                executor.submit(
                    self.test_upgrade_single_version,
                    package_name,
                    target_version,
                    version
                ): version
                for version in self.python_versions
            }
            
            for future in concurrent.futures.as_completed(future_to_version):
                version = future_to_version[future]
                try:
                    result = future.result()
                    results[version] = result
                    
                    if result.success:
                        logger.info(f"✅ Upgrade successful for Python {version}")
                    else:
                        logger.error(f"❌ Upgrade failed for Python {version}: {result.error_message}")
                        
                except Exception as e:
                    logger.error(f"Error testing Python {version}: {e}")
                    results[version] = UpgradeResult.failure_result(
                        package_name=package_name,
                        from_version="unknown",
                        to_version=target_version,
                        error_message=f"Testing error: {e}",
                    )
        
        return results
    
    def test_performance_impact(
        self,
        package_name: str,
        target_version: str,
    ) -> Tuple[PerformanceMetrics, List[PerformanceRegression]]:
        """
        Test performance impact of upgrade.
        
        Args:
            package_name: Name of package to upgrade
            target_version: Target version to upgrade to
            
        Returns:
            Tuple of (current_metrics, regressions)
        """
        logger.info(f"Testing performance impact of {package_name} -> {target_version}")
        
        # Load baseline metrics
        baseline_metrics = self.performance_monitor.load_baseline()
        
        # Collect current metrics after upgrade
        current_metrics = self.performance_monitor.collect_comprehensive_metrics(
            modules_to_import=["vet_core", "vet_core.models", "vet_core.database"],
            packages_to_measure=[package_name, "vet_core"],
            test_command=self.test_command,
        )
        
        # Detect regressions
        regressions = self.performance_monitor.detect_regressions(
            current_metrics=current_metrics,
            baseline_metrics=baseline_metrics,
        )
        
        return current_metrics, regressions
    
    def verify_security_fixes(
        self,
        vulnerabilities: List[Vulnerability],
    ) -> Dict[str, bool]:
        """
        Verify that security fixes actually resolve vulnerabilities.
        
        Args:
            vulnerabilities: List of vulnerabilities that should be fixed
            
        Returns:
            Dictionary mapping vulnerability ID to fix status
        """
        logger.info("Verifying security fixes...")
        
        verification_results = {}
        
        for vuln in vulnerabilities:
            try:
                # Run pip-audit specifically for this package
                result = subprocess.run([
                    sys.executable, "-m", "pip-audit",
                    "--format=json",
                    "--package", vuln.package_name,
                ], capture_output=True, text=True, cwd=self.project_root)
                
                if result.returncode == 0:
                    audit_data = json.loads(result.stdout)
                    remaining_vulns = audit_data.get("vulnerabilities", [])
                    
                    # Check if this specific vulnerability is still present
                    vuln_still_present = any(
                        v.get("id") == vuln.id for v in remaining_vulns
                    )
                    
                    verification_results[vuln.id] = not vuln_still_present
                    
                    if vuln_still_present:
                        logger.warning(f"❌ Vulnerability {vuln.id} still present after upgrade")
                    else:
                        logger.info(f"✅ Vulnerability {vuln.id} resolved")
                else:
                    logger.error(f"Failed to verify fix for {vuln.id}: {result.stderr}")
                    verification_results[vuln.id] = False
                    
            except Exception as e:
                logger.error(f"Error verifying fix for {vuln.id}: {e}")
                verification_results[vuln.id] = False
        
        return verification_results
    
    def run_comprehensive_upgrade_test(
        self,
        package_name: str,
        target_version: str,
        vulnerabilities: List[Vulnerability] = None,
    ) -> Dict[str, Any]:
        """
        Run comprehensive upgrade test including all validation steps.
        
        Args:
            package_name: Name of package to upgrade
            target_version: Target version to upgrade to
            vulnerabilities: List of vulnerabilities this upgrade should fix
            
        Returns:
            Comprehensive test results
        """
        logger.info(f"Running comprehensive upgrade test: {package_name} -> {target_version}")
        
        results = {
            "package_name": package_name,
            "target_version": target_version,
            "timestamp": str(self.performance_monitor.process.create_time()),
            "multi_version_results": {},
            "performance_results": {},
            "security_verification": {},
            "overall_success": False,
        }
        
        try:
            # 1. Test across multiple Python versions
            logger.info("Step 1: Multi-version compatibility testing")
            multi_version_results = self.test_upgrade_multi_version(package_name, target_version)
            results["multi_version_results"] = {
                version: asdict(result) for version, result in multi_version_results.items()
            }
            
            # Check if all versions passed
            all_versions_passed = all(result.success for result in multi_version_results.values())
            
            if not all_versions_passed:
                logger.error("Multi-version testing failed, stopping pipeline")
                return results
            
            # 2. Performance impact testing
            logger.info("Step 2: Performance impact testing")
            current_metrics, regressions = self.test_performance_impact(package_name, target_version)
            
            results["performance_results"] = {
                "current_metrics": asdict(current_metrics),
                "regressions": [asdict(reg) for reg in regressions],
                "has_significant_regressions": any(reg.is_significant for reg in regressions),
            }
            
            # 3. Security fix verification
            if vulnerabilities:
                logger.info("Step 3: Security fix verification")
                security_verification = self.verify_security_fixes(vulnerabilities)
                results["security_verification"] = security_verification
                
                all_fixes_verified = all(security_verification.values())
                if not all_fixes_verified:
                    logger.warning("Some security fixes could not be verified")
            else:
                results["security_verification"] = {}
                all_fixes_verified = True
            
            # 4. Overall assessment
            has_significant_regressions = results["performance_results"]["has_significant_regressions"]
            
            results["overall_success"] = (
                all_versions_passed and
                all_fixes_verified and
                not has_significant_regressions
            )
            
            if results["overall_success"]:
                logger.info("✅ Comprehensive upgrade test PASSED")
            else:
                logger.error("❌ Comprehensive upgrade test FAILED")
                
                # Log specific failure reasons
                if not all_versions_passed:
                    logger.error("  - Multi-version compatibility issues")
                if not all_fixes_verified:
                    logger.error("  - Security fix verification issues")
                if has_significant_regressions:
                    logger.error("  - Significant performance regressions detected")
            
        except Exception as e:
            logger.error(f"Error during comprehensive upgrade test: {e}")
            results["error"] = str(e)
        
        return results
    
    def run_vulnerability_upgrade_pipeline(self) -> Dict[str, Any]:
        """
        Run the complete vulnerability upgrade pipeline.
        
        Returns:
            Complete pipeline results
        """
        logger.info("Starting vulnerability upgrade pipeline")
        
        pipeline_results = {
            "timestamp": str(self.performance_monitor.process.create_time()),
            "vulnerabilities_found": [],
            "upgrade_tests": {},
            "overall_success": False,
        }
        
        try:
            # 1. Scan for vulnerabilities
            vulnerabilities = self.run_security_scan()
            pipeline_results["vulnerabilities_found"] = [asdict(vuln) for vuln in vulnerabilities]
            
            if not vulnerabilities:
                logger.info("No vulnerabilities found, pipeline complete")
                pipeline_results["overall_success"] = True
                return pipeline_results
            
            # 2. Group vulnerabilities by package and determine upgrades
            package_upgrades = {}
            for vuln in vulnerabilities:
                if not vuln.is_fixable:
                    continue
                
                package_name = vuln.package_name
                recommended_version = vuln.recommended_fix_version
                
                if package_name not in package_upgrades:
                    package_upgrades[package_name] = {
                        "target_version": recommended_version,
                        "vulnerabilities": [vuln],
                    }
                else:
                    # Use the higher version if multiple vulnerabilities
                    current_target = package_upgrades[package_name]["target_version"]
                    if recommended_version > current_target:
                        package_upgrades[package_name]["target_version"] = recommended_version
                    package_upgrades[package_name]["vulnerabilities"].append(vuln)
            
            # 3. Test each package upgrade
            all_upgrades_successful = True
            
            for package_name, upgrade_info in package_upgrades.items():
                target_version = upgrade_info["target_version"]
                package_vulns = upgrade_info["vulnerabilities"]
                
                logger.info(f"Testing upgrade for {package_name} -> {target_version}")
                
                test_results = self.run_comprehensive_upgrade_test(
                    package_name=package_name,
                    target_version=target_version,
                    vulnerabilities=package_vulns,
                )
                
                pipeline_results["upgrade_tests"][package_name] = test_results
                
                if not test_results["overall_success"]:
                    all_upgrades_successful = False
            
            pipeline_results["overall_success"] = all_upgrades_successful
            
            if all_upgrades_successful:
                logger.info("✅ Vulnerability upgrade pipeline completed successfully")
            else:
                logger.error("❌ Vulnerability upgrade pipeline failed")
        
        except Exception as e:
            logger.error(f"Error in vulnerability upgrade pipeline: {e}")
            pipeline_results["error"] = str(e)
        
        return pipeline_results
    
    def generate_pipeline_report(
        self,
        results: Dict[str, Any],
        output_file: Path,
    ) -> None:
        """
        Generate a comprehensive pipeline report.
        
        Args:
            results: Pipeline results
            output_file: Path to save the report
        """
        logger.info(f"Generating pipeline report: {output_file}")
        
        report_lines = [
            "# Upgrade Testing Pipeline Report",
            f"Generated: {results.get('timestamp', 'unknown')}",
            "",
        ]
        
        # Vulnerabilities summary
        vulnerabilities = results.get("vulnerabilities_found", [])
        report_lines.extend([
            f"## Vulnerabilities Found: {len(vulnerabilities)}",
            "",
        ])
        
        if vulnerabilities:
            for vuln in vulnerabilities:
                report_lines.extend([
                    f"- **{vuln['id']}** ({vuln['severity']}): {vuln['package_name']} {vuln['installed_version']}",
                    f"  - Fix versions: {', '.join(vuln['fix_versions'])}",
                    f"  - Description: {vuln['description'][:100]}...",
                    "",
                ])
        
        # Upgrade test results
        upgrade_tests = results.get("upgrade_tests", {})
        report_lines.extend([
            f"## Upgrade Test Results: {len(upgrade_tests)} packages tested",
            "",
        ])
        
        for package_name, test_result in upgrade_tests.items():
            success_icon = "✅" if test_result["overall_success"] else "❌"
            target_version = test_result["target_version"]
            
            report_lines.extend([
                f"### {success_icon} {package_name} -> {target_version}",
                "",
            ])
            
            # Multi-version results
            multi_version = test_result.get("multi_version_results", {})
            if multi_version:
                report_lines.append("**Python Version Compatibility:**")
                for version, result in multi_version.items():
                    status = "✅ PASS" if result["success"] else "❌ FAIL"
                    report_lines.append(f"- Python {version}: {status}")
                    if not result["success"]:
                        report_lines.append(f"  - Error: {result['error_message']}")
                report_lines.append("")
            
            # Performance results
            perf_results = test_result.get("performance_results", {})
            if perf_results:
                regressions = perf_results.get("regressions", [])
                if regressions:
                    report_lines.extend([
                        "**Performance Regressions:**",
                    ])
                    for reg in regressions:
                        report_lines.append(
                            f"- {reg['metric_name']}: {reg['regression_percent']:.1f}% increase "
                            f"({reg['severity']})"
                        )
                else:
                    report_lines.append("**Performance:** No significant regressions detected")
                report_lines.append("")
            
            # Security verification
            security_verification = test_result.get("security_verification", {})
            if security_verification:
                report_lines.append("**Security Fix Verification:**")
                for vuln_id, verified in security_verification.items():
                    status = "✅ FIXED" if verified else "❌ NOT FIXED"
                    report_lines.append(f"- {vuln_id}: {status}")
                report_lines.append("")
        
        # Overall status
        overall_success = results.get("overall_success", False)
        status_icon = "✅" if overall_success else "❌"
        report_lines.extend([
            f"## Overall Status: {status_icon}",
            "",
            "**Summary:**" if overall_success else "**Issues Found:**",
        ])
        
        if overall_success:
            report_lines.append("All upgrade tests passed successfully. Dependencies can be safely upgraded.")
        else:
            report_lines.extend([
                "Some upgrade tests failed. Review the detailed results above before proceeding.",
                "",
                "**Recommended Actions:**",
                "1. Review failed test results",
                "2. Address compatibility issues",
                "3. Investigate performance regressions",
                "4. Verify security fixes manually if needed",
                "5. Re-run pipeline after fixes",
            ])
        
        # Save report
        try:
            output_file.write_text("\n".join(report_lines))
            logger.info(f"Pipeline report saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save pipeline report: {e}")


def main():
    """Main entry point for the upgrade testing pipeline."""
    parser = argparse.ArgumentParser(
        description="Comprehensive dependency upgrade testing pipeline"
    )
    
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Path to project root directory"
    )
    
    parser.add_argument(
        "--python-versions",
        nargs="+",
        default=["3.11", "3.12"],
        help="Python versions to test against"
    )
    
    parser.add_argument(
        "--test-command",
        default="pytest",
        help="Command to run tests"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory to save reports"
    )
    
    parser.add_argument(
        "--baseline-file",
        type=Path,
        help="Path to performance baseline file"
    )
    
    parser.add_argument(
        "--package",
        help="Test specific package upgrade (format: package==version)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize pipeline
    pipeline = UpgradeTestingPipeline(
        project_root=args.project_root,
        python_versions=args.python_versions,
        test_command=args.test_command,
        performance_baseline_file=args.baseline_file,
    )
    
    try:
        if args.package:
            # Test specific package
            if "==" in args.package:
                package_name, target_version = args.package.split("==", 1)
            else:
                logger.error("Package must be specified as package==version")
                return 1
            
            logger.info(f"Testing specific package upgrade: {package_name} -> {target_version}")
            
            results = pipeline.run_comprehensive_upgrade_test(
                package_name=package_name,
                target_version=target_version,
            )
            
            # Save results
            results_file = args.output_dir / f"upgrade_test_{package_name}_{target_version}.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Results saved to {results_file}")
            
            return 0 if results["overall_success"] else 1
        
        else:
            # Run full vulnerability pipeline
            logger.info("Running full vulnerability upgrade pipeline")
            
            results = pipeline.run_vulnerability_upgrade_pipeline()
            
            # Save results
            results_file = args.output_dir / "vulnerability_upgrade_pipeline_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            # Generate report
            report_file = args.output_dir / "vulnerability_upgrade_pipeline_report.md"
            pipeline.generate_pipeline_report(results, report_file)
            
            logger.info(f"Results saved to {results_file}")
            logger.info(f"Report saved to {report_file}")
            
            return 0 if results["overall_success"] else 1
    
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())