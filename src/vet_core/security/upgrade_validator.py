"""
Safe dependency upgrade validation system.

This module provides functionality to safely validate dependency upgrades
before applying them, including compatibility checking and rollback mechanisms.
"""

import json
import logging
import os
import shutil
import sys
import tempfile
import venv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import RemediationAction, Vulnerability, VulnerabilitySeverity
from .subprocess_utils import (
    SubprocessSecurityError,
    secure_subprocess_run,
    validate_package_name,
    validate_test_command,
    validate_version,
)

logger = logging.getLogger(__name__)


@dataclass
class UpgradeResult:
    """Result of a dependency upgrade validation."""

    package_name: str
    from_version: str
    to_version: str
    success: bool
    error_message: str = ""
    test_results: Dict[str, Any] = field(default_factory=dict)
    compatibility_issues: List[str] = field(default_factory=list)
    performance_impact: Optional[Dict[str, float]] = None
    rollback_performed: bool = False
    validation_duration: float = 0.0

    @classmethod
    def success_result(
        cls,
        package_name: str,
        from_version: str,
        to_version: str,
        test_results: Optional[Dict[str, Any]] = None,
        validation_duration: float = 0.0,
    ) -> "UpgradeResult":
        """Create a successful upgrade result."""
        return cls(
            package_name=package_name,
            from_version=from_version,
            to_version=to_version,
            success=True,
            test_results=test_results or {},
            validation_duration=validation_duration,
        )

    @classmethod
    def failure_result(
        cls,
        package_name: str,
        from_version: str,
        to_version: str,
        error_message: str,
        compatibility_issues: Optional[List[str]] = None,
        rollback_performed: bool = False,
        validation_duration: float = 0.0,
    ) -> "UpgradeResult":
        """Create a failed upgrade result."""
        return cls(
            package_name=package_name,
            from_version=from_version,
            to_version=to_version,
            success=False,
            error_message=error_message,
            compatibility_issues=compatibility_issues or [],
            rollback_performed=rollback_performed,
            validation_duration=validation_duration,
        )


@dataclass
class EnvironmentBackup:
    """Backup of a Python environment for rollback purposes."""

    backup_path: Path
    requirements_file: Path
    pyproject_backup: Optional[Path] = None
    created_at: datetime = field(default_factory=datetime.now)

    def cleanup(self) -> None:
        """Clean up backup files."""
        try:
            if self.backup_path.exists():
                shutil.rmtree(self.backup_path)
            if self.requirements_file.exists():
                self.requirements_file.unlink()
            if self.pyproject_backup and self.pyproject_backup.exists():
                self.pyproject_backup.unlink()
        except Exception as e:
            logger.warning(f"Failed to cleanup backup: {e}")


class DependencyConflictError(Exception):
    """Raised when dependency conflicts are detected."""

    pass


class TestFailureError(Exception):
    """Raised when tests fail after upgrade."""

    pass


class UpgradeValidator:
    """Validates dependency upgrades safely with rollback capability."""

    def __init__(self, project_root: Path, test_command: str = "pytest"):
        """
        Initialize the upgrade validator.

        Args:
            project_root: Path to the project root directory
            test_command: Command to run tests (default: pytest)
        """
        self.project_root = Path(project_root)
        self.test_command = test_command
        self.pyproject_path = self.project_root / "pyproject.toml"
        self.temp_dir = Path(tempfile.mkdtemp(prefix="upgrade_validation_"))

    def __enter__(self) -> "UpgradeValidator":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - cleanup temporary files."""
        self.cleanup()

    def cleanup(self) -> None:
        """Clean up temporary files and directories."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")

    def create_environment_backup(self) -> EnvironmentBackup:
        """
        Create a backup of the current environment.

        Returns:
            EnvironmentBackup object containing backup information
        """
        backup_path = (
            self.temp_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        backup_path.mkdir(parents=True, exist_ok=True)

        # Create requirements file from current environment
        requirements_file = backup_path / "requirements.txt"
        try:
            # nosec B603: Using secure subprocess wrapper with validation
            result = secure_subprocess_run(
                [sys.executable, "-m", "pip", "freeze"],
                validate_first_arg=False,  # sys.executable is trusted
                check=True,
            )

            requirements_file.write_text(result.stdout)
        except Exception as e:
            raise RuntimeError(f"Failed to create requirements backup: {e}")

        # Backup pyproject.toml if it exists
        pyproject_backup = None
        if self.pyproject_path.exists():
            pyproject_backup = backup_path / "pyproject.toml"
            shutil.copy2(self.pyproject_path, pyproject_backup)

        return EnvironmentBackup(
            backup_path=backup_path,
            requirements_file=requirements_file,
            pyproject_backup=pyproject_backup,
        )

    def restore_environment(self, backup: EnvironmentBackup) -> bool:
        """
        Restore environment from backup.

        Args:
            backup: EnvironmentBackup to restore from

        Returns:
            True if restoration was successful, False otherwise
        """
        try:
            # Restore pyproject.toml if backed up
            if backup.pyproject_backup and backup.pyproject_backup.exists():
                shutil.copy2(backup.pyproject_backup, self.pyproject_path)

            # Reinstall packages from requirements
            # nosec B603: Using secure subprocess wrapper with validation
            secure_subprocess_run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    str(backup.requirements_file),
                ],
                validate_first_arg=False,  # sys.executable is trusted
                check=True,
            )

            logger.info("Environment successfully restored from backup")
            return True

        except Exception as e:
            logger.error(f"Failed to restore environment: {e}")
            return False

    def check_dependency_conflicts(
        self, package_name: str, target_version: str
    ) -> List[str]:
        """
        Check for potential dependency conflicts before upgrade.

        Args:
            package_name: Name of the package to upgrade
            target_version: Target version to upgrade to

        Returns:
            List of conflict descriptions
        """
        conflicts = []

        try:
            # Validate inputs for security
            validated_package_name = validate_package_name(package_name)
            validated_target_version = validate_version(target_version)

            # Use pip-compile or similar to check for conflicts
            # For now, we'll use a simpler approach with pip check

            # First, try to resolve dependencies without installing
            # nosec B603: Using secure subprocess wrapper with validation
            result = secure_subprocess_run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--dry-run",
                    "--no-deps",
                    f"{validated_package_name}=={validated_target_version}",
                ],
                validate_first_arg=False,  # sys.executable is trusted
            )

            if result.returncode != 0:
                conflicts.append(
                    f"Package {package_name}=={target_version} cannot be installed: {result.stderr}"
                )

            # Check current dependency tree
            # nosec B603: Using secure subprocess wrapper with validation
            result = secure_subprocess_run(
                [sys.executable, "-m", "pip", "check"],
                validate_first_arg=False,  # sys.executable is trusted
            )

            if result.returncode != 0:
                conflicts.append(
                    f"Current environment has dependency issues: {result.stdout}"
                )

        except Exception as e:
            conflicts.append(f"Error checking dependencies: {e}")

        return conflicts

    def run_tests(self) -> Dict[str, Any]:
        """
        Run the test suite and return results.

        Returns:
            Dictionary containing test results
        """
        test_results = {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "duration": 0.0,
            "test_count": 0,
            "failures": 0,
            "errors": 0,
        }

        start_time = datetime.now()

        try:
            # Validate test command for security
            validated_test_command = validate_test_command(self.test_command)

            # Change to project root for test execution
            original_cwd = os.getcwd()
            os.chdir(self.project_root)

            # Run tests with coverage and output capture
            cmd = [
                sys.executable,
                "-m",
                validated_test_command,
                "--tb=short",  # Short traceback format
                "-v",  # Verbose output
                "--durations=10",  # Show 10 slowest tests
            ]

            # nosec B603: Using secure subprocess wrapper with validation
            result = secure_subprocess_run(
                cmd,
                validate_first_arg=False,  # sys.executable is trusted
                timeout=300,  # 5 minute timeout
            )

            test_results.update(
                {
                    "success": result.returncode == 0,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "duration": (datetime.now() - start_time).total_seconds(),
                }
            )

            # Parse test output for counts (pytest specific)
            if "pytest" in validated_test_command:
                self._parse_pytest_output(result.stdout, test_results)

        except SubprocessSecurityError as e:
            test_results["stderr"] = f"Security validation failed for test command: {e}"
            test_results["duration"] = 0.0
        except Exception as e:
            test_results["stderr"] = f"Error running tests: {e}"
        finally:
            os.chdir(original_cwd)

        return test_results

    def _parse_pytest_output(self, output: str, test_results: Dict[str, Any]) -> None:
        """Parse pytest output to extract test statistics."""
        lines = output.split("\n")

        for line in lines:
            line = line.strip()

            # Look for summary line like "= 25 passed, 2 failed, 1 error in 10.23s ="
            if " passed" in line and " in " in line and line.startswith("="):
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed,":
                        test_results["test_count"] = int(parts[i - 1])
                    elif part == "failed,":
                        test_results["failures"] = int(parts[i - 1])
                    elif part == "error":
                        test_results["errors"] = int(parts[i - 1])
                break

    def validate_upgrade(
        self,
        package_name: str,
        target_version: str,
        run_tests: bool = True,
        check_conflicts: bool = True,
    ) -> UpgradeResult:
        """
        Validate a dependency upgrade safely.

        Args:
            package_name: Name of the package to upgrade
            target_version: Target version to upgrade to
            run_tests: Whether to run tests after upgrade
            check_conflicts: Whether to check for dependency conflicts

        Returns:
            UpgradeResult containing validation results
        """
        start_time = datetime.now()
        backup = None
        rollback_performed = False

        try:
            # Validate inputs for security
            validated_package_name = validate_package_name(package_name)
            validated_target_version = validate_version(target_version)

            # Get current version
            # nosec B603: Using secure subprocess wrapper with validation
            result = secure_subprocess_run(
                [sys.executable, "-m", "pip", "show", validated_package_name],
                validate_first_arg=False,  # sys.executable is trusted
            )

            current_version = "unknown"
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("Version:"):
                        current_version = line.split(":", 1)[1].strip()
                        break

            logger.info(
                f"Validating upgrade: {package_name} {current_version} -> {target_version}"
            )

            # Check for conflicts first
            conflicts = []
            if check_conflicts:
                conflicts = self.check_dependency_conflicts(
                    package_name, target_version
                )
                if conflicts:
                    return UpgradeResult.failure_result(
                        package_name=package_name,
                        from_version=current_version,
                        to_version=target_version,
                        error_message="Dependency conflicts detected",
                        compatibility_issues=conflicts,
                        validation_duration=(
                            datetime.now() - start_time
                        ).total_seconds(),
                    )

            # Create backup before making changes
            backup = self.create_environment_backup()

            # Perform the upgrade
            try:
                # nosec B603: Using secure subprocess wrapper with validation
                secure_subprocess_run(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        f"{validated_package_name}=={validated_target_version}",
                    ],
                    validate_first_arg=False,  # sys.executable is trusted
                    check=True,
                )

                logger.info(f"Successfully installed {package_name}=={target_version}")

            except Exception as e:
                error_message = f"Failed to install package: {str(e)}"
                if hasattr(e, "stderr") and e.stderr:
                    error_message = f"Failed to install package: {e.stderr}"

                return UpgradeResult.failure_result(
                    package_name=package_name,
                    from_version=current_version,
                    to_version=target_version,
                    error_message=error_message,
                    validation_duration=(datetime.now() - start_time).total_seconds(),
                )

            # Run tests if requested
            test_results = {}
            if run_tests:
                test_results = self.run_tests()

                if not test_results["success"]:
                    # Tests failed, rollback
                    rollback_performed = self.restore_environment(backup)

                    return UpgradeResult.failure_result(
                        package_name=package_name,
                        from_version=current_version,
                        to_version=target_version,
                        error_message="Tests failed after upgrade",
                        rollback_performed=rollback_performed,
                        validation_duration=(
                            datetime.now() - start_time
                        ).total_seconds(),
                    )

            # Success!
            return UpgradeResult.success_result(
                package_name=package_name,
                from_version=current_version,
                to_version=target_version,
                test_results=test_results,
                validation_duration=(datetime.now() - start_time).total_seconds(),
            )

        except Exception as e:
            # Unexpected error, attempt rollback
            if backup:
                rollback_performed = self.restore_environment(backup)

            return UpgradeResult.failure_result(
                package_name=package_name,
                from_version=(
                    current_version if "current_version" in locals() else "unknown"
                ),
                to_version=target_version,
                error_message=f"Unexpected error during validation: {e}",
                rollback_performed=rollback_performed,
                validation_duration=(datetime.now() - start_time).total_seconds(),
            )

        finally:
            # Cleanup backup if successful (keep it if we failed for debugging)
            if backup and not rollback_performed:
                backup.cleanup()

    def validate_multiple_upgrades(
        self, upgrades: List[Tuple[str, str]], run_tests: bool = True
    ) -> List[UpgradeResult]:
        """
        Validate multiple dependency upgrades in sequence.

        Args:
            upgrades: List of (package_name, target_version) tuples
            run_tests: Whether to run tests after each upgrade

        Returns:
            List of UpgradeResult objects
        """
        results = []
        overall_backup = self.create_environment_backup()

        try:
            for package_name, target_version in upgrades:
                result = self.validate_upgrade(
                    package_name=package_name,
                    target_version=target_version,
                    run_tests=run_tests,
                    check_conflicts=True,
                )

                results.append(result)

                # If any upgrade fails, rollback everything and stop
                if not result.success:
                    logger.warning(
                        f"Upgrade failed for {package_name}, rolling back all changes"
                    )
                    self.restore_environment(overall_backup)

                    # Mark rollback in the failed result
                    result.rollback_performed = True
                    break

            return results

        finally:
            overall_backup.cleanup()


def validate_vulnerability_fixes(
    vulnerabilities: List[Vulnerability],
) -> List[UpgradeResult]:
    """
    Validate upgrades for a list of vulnerabilities.

    Args:
        vulnerabilities: List of vulnerabilities to fix

    Returns:
        List of UpgradeResult objects
    """
    # Group vulnerabilities by package to avoid duplicate upgrades
    package_upgrades: Dict[str, Dict[str, Any]] = {}

    for vuln in vulnerabilities:
        if not vuln.is_fixable:
            continue

        package_name = vuln.package_name
        recommended_version = vuln.recommended_fix_version

        # Skip if no recommended version is available
        if not recommended_version:
            continue

        if package_name not in package_upgrades:
            package_upgrades[package_name] = {
                "current_version": vuln.installed_version,
                "target_version": recommended_version,
                "vulnerabilities": [vuln],
            }
        else:
            # If we already have an upgrade for this package, use the higher version
            existing_target = package_upgrades[package_name]["target_version"]
            if existing_target and recommended_version > existing_target:
                package_upgrades[package_name]["target_version"] = recommended_version
            package_upgrades[package_name]["vulnerabilities"].append(vuln)

    # Perform validation
    upgrades = [(pkg, info["target_version"]) for pkg, info in package_upgrades.items()]

    with UpgradeValidator(Path.cwd()) as validator:
        return validator.validate_multiple_upgrades(upgrades)
