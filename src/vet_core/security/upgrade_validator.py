"""
Safe dependency upgrade validation system.

This module provides functionality to safely validate dependency upgrades
before applying them, including compatibility checking and rollback mechanisms.
"""

import json
import logging
import os
import shutil
import subprocess  # nosec B404
import sys
import tempfile
import venv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import RemediationAction, Vulnerability, VulnerabilitySeverity
from .subprocess_utils import (  # nosec B404
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
    package_count: int = 0
    is_empty_environment: bool = False
    backup_metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """
        Validate backup integrity.

        Returns:
            True if backup is valid and usable, False otherwise
        """
        try:
            # Check if backup path exists and is a directory
            if not self.backup_path.exists() or not self.backup_path.is_dir():
                return False

            # Check if requirements file exists and is readable
            if (
                not self.requirements_file.exists()
                or not self.requirements_file.is_file()
            ):
                return False

            # Try to read requirements file to ensure it's not corrupted
            try:
                content = self.requirements_file.read_text()
                # Basic validation - should be text content (read_text() always returns str)
            except (OSError, UnicodeDecodeError):
                return False

            # Check pyproject backup if it exists
            if self.pyproject_backup:
                if (
                    not self.pyproject_backup.exists()
                    or not self.pyproject_backup.is_file()
                ):
                    return False
                try:
                    self.pyproject_backup.read_text()
                except (OSError, UnicodeDecodeError):
                    return False

            # Check if backup path has proper permissions
            if not os.access(self.backup_path, os.R_OK | os.W_OK):
                return False

            return True

        except Exception as e:
            logger.warning(f"Error validating backup: {e}")
            return False

    def get_package_list(self) -> List[str]:
        """
        Get list of packages from backup.

        Returns:
            List of package names from the requirements file
        """
        try:
            if not self.requirements_file.exists():
                return []

            content = self.requirements_file.read_text().strip()
            if not content:
                return []

            packages = []
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract package name (before == or >= etc.)
                    package_name = (
                        line.split("==")[0]
                        .split(">=")[0]
                        .split("<=")[0]
                        .split("~=")[0]
                        .split("!=")[0]
                        .strip()
                    )
                    if package_name:
                        packages.append(package_name)

            return packages

        except Exception as e:
            logger.warning(f"Error reading package list from backup: {e}")
            return []

    def cleanup(self) -> None:
        """Clean up backup files with improved error handling."""
        cleanup_errors = []

        try:
            if self.backup_path.exists():
                shutil.rmtree(self.backup_path)
        except Exception as e:
            cleanup_errors.append(
                f"Failed to remove backup directory {self.backup_path}: {e}"
            )

        try:
            if self.requirements_file.exists():
                self.requirements_file.unlink()
        except Exception as e:
            cleanup_errors.append(
                f"Failed to remove requirements file {self.requirements_file}: {e}"
            )

        try:
            if self.pyproject_backup and self.pyproject_backup.exists():
                self.pyproject_backup.unlink()
        except Exception as e:
            cleanup_errors.append(
                f"Failed to remove pyproject backup {self.pyproject_backup}: {e}"
            )

        if cleanup_errors:
            logger.warning(
                f"Cleanup completed with errors: {'; '.join(cleanup_errors)}"
            )
        else:
            logger.debug("Backup cleanup completed successfully")


@dataclass
class ValidationResult:
    """Result of backup validation operations."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RestoreResult:
    """Result of environment restoration operations."""

    success: bool
    strategy_used: str
    error_message: Optional[str] = None
    packages_restored: int = 0
    packages_failed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration: float = 0.0

    @classmethod
    def success_result(
        cls,
        strategy: str,
        packages_restored: int,
        duration: float,
        warnings: Optional[List[str]] = None,
    ) -> "RestoreResult":
        """
        Create a successful restore result.

        Args:
            strategy: Name of the restoration strategy used
            packages_restored: Number of packages successfully restored
            duration: Time taken for restoration in seconds
            warnings: Optional list of warnings during restoration

        Returns:
            RestoreResult instance indicating successful restoration
        """
        return cls(
            success=True,
            strategy_used=strategy,
            packages_restored=packages_restored,
            duration=duration,
            warnings=warnings or [],
        )

    @classmethod
    def failure_result(
        cls,
        strategy: str,
        error_message: str,
        duration: float,
        packages_failed: Optional[List[str]] = None,
        packages_restored: int = 0,
        warnings: Optional[List[str]] = None,
    ) -> "RestoreResult":
        """
        Create a failed restore result.

        Args:
            strategy: Name of the restoration strategy used
            error_message: Description of the failure
            duration: Time taken before failure in seconds
            packages_failed: Optional list of packages that failed to restore
            packages_restored: Number of packages successfully restored before failure
            warnings: Optional list of warnings during restoration

        Returns:
            RestoreResult instance indicating failed restoration
        """
        return cls(
            success=False,
            strategy_used=strategy,
            error_message=error_message,
            duration=duration,
            packages_failed=packages_failed or [],
            packages_restored=packages_restored,
            warnings=warnings or [],
        )


class BackupValidator:
    """Validates backup integrity and completeness."""

    def __init__(self) -> None:
        """Initialize the backup validator."""
        self.logger = logging.getLogger(__name__)

    def validate_backup(self, backup: EnvironmentBackup) -> ValidationResult:
        """
        Validate that backup is complete and usable.

        Args:
            backup: EnvironmentBackup to validate

        Returns:
            ValidationResult containing validation status and details
        """
        errors = []
        warnings = []
        metadata: Dict[str, Any] = {}

        try:
            # Check if backup path exists and is a directory
            if not backup.backup_path.exists():
                errors.append(f"Backup path does not exist: {backup.backup_path}")
            elif not backup.backup_path.is_dir():
                errors.append(f"Backup path is not a directory: {backup.backup_path}")
            else:
                # Check backup path permissions
                if not self.check_backup_permissions(backup.backup_path):
                    errors.append(
                        f"Insufficient permissions for backup path: {backup.backup_path}"
                    )

                metadata["backup_path_exists"] = True
                metadata["backup_path_permissions"] = os.access(
                    backup.backup_path, os.R_OK | os.W_OK
                )

            # Validate requirements file
            requirements_valid = self.validate_requirements_file(
                backup.requirements_file
            )
            if not requirements_valid:
                errors.append(
                    f"Requirements file validation failed: {backup.requirements_file}"
                )
            else:
                metadata["requirements_file_valid"] = True

                # Get package count from requirements file
                try:
                    packages = backup.get_package_list()
                    metadata["actual_package_count"] = len(packages)

                    # Check if package count matches backup metadata
                    if backup.package_count != len(packages):
                        warnings.append(
                            f"Package count mismatch: backup reports {backup.package_count}, "
                            f"but requirements file contains {len(packages)} packages"
                        )
                except Exception as e:
                    warnings.append(f"Could not parse package list: {e}")

            # Validate pyproject backup if it exists
            if backup.pyproject_backup:
                if not backup.pyproject_backup.exists():
                    errors.append(
                        f"Pyproject backup file does not exist: {backup.pyproject_backup}"
                    )
                elif not backup.pyproject_backup.is_file():
                    errors.append(
                        f"Pyproject backup path is not a file: {backup.pyproject_backup}"
                    )
                else:
                    try:
                        content = backup.pyproject_backup.read_text()
                        if not content.strip():
                            warnings.append("Pyproject backup file is empty")
                        metadata["pyproject_backup_valid"] = True
                    except (OSError, UnicodeDecodeError) as e:
                        errors.append(f"Cannot read pyproject backup file: {e}")

            # Validate backup metadata consistency
            if backup.is_empty_environment and backup.package_count > 0:
                warnings.append(
                    f"Inconsistent metadata: marked as empty environment but package_count is {backup.package_count}"
                )

            if not backup.is_empty_environment and backup.package_count == 0:
                warnings.append(
                    "Inconsistent metadata: not marked as empty environment but package_count is 0"
                )

            # Check backup age
            if backup.created_at:
                age_hours = (datetime.now() - backup.created_at).total_seconds() / 3600
                metadata["backup_age_hours"] = age_hours

                if age_hours > 24:
                    warnings.append(
                        f"Backup is {age_hours:.1f} hours old, may be stale"
                    )

            # Validate backup metadata structure
            if backup.backup_metadata:
                required_metadata_keys = ["python_version", "platform", "created_by"]
                missing_keys = [
                    key
                    for key in required_metadata_keys
                    if key not in backup.backup_metadata
                ]
                if missing_keys:
                    warnings.append(f"Missing backup metadata keys: {missing_keys}")

                metadata["backup_metadata_keys"] = list(backup.backup_metadata.keys())
            else:
                warnings.append("Backup metadata is empty or missing")

            is_valid = len(errors) == 0

            return ValidationResult(
                is_valid=is_valid, errors=errors, warnings=warnings, metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"Unexpected error during backup validation: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation failed with unexpected error: {e}"],
                warnings=warnings,
                metadata=metadata,
            )

    def validate_requirements_file(self, requirements_file: Path) -> bool:
        """
        Validate requirements file format and content.

        Args:
            requirements_file: Path to requirements file to validate

        Returns:
            True if requirements file is valid, False otherwise
        """
        try:
            # Check if file exists
            if not requirements_file.exists():
                self.logger.warning(
                    f"Requirements file does not exist: {requirements_file}"
                )
                return False

            # Check if it's a file (not a directory)
            if not requirements_file.is_file():
                self.logger.warning(
                    f"Requirements path is not a file: {requirements_file}"
                )
                return False

            # Check file permissions
            if not os.access(requirements_file, os.R_OK):
                self.logger.warning(
                    f"Cannot read requirements file: {requirements_file}"
                )
                return False

            # Try to read and validate content
            try:
                content = requirements_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                self.logger.warning(
                    f"Requirements file is not valid UTF-8: {requirements_file}"
                )
                return False

            # Validate content format
            lines = content.split("\n")
            for line_num, line in enumerate(lines, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Basic validation of package specification format
                # Should contain package name and optionally version specifiers
                if not self._is_valid_package_line(line):
                    self.logger.warning(
                        f"Invalid package specification at line {line_num}: {line}"
                    )
                    return False

            return True

        except Exception as e:
            self.logger.error(
                f"Error validating requirements file {requirements_file}: {e}"
            )
            return False

    def check_backup_permissions(self, backup_path: Path) -> bool:
        """
        Check that backup files have correct permissions.

        Args:
            backup_path: Path to backup directory to check

        Returns:
            True if permissions are correct, False otherwise
        """
        try:
            # Check if path exists
            if not backup_path.exists():
                return False

            # Check read and write permissions on backup directory
            if not os.access(backup_path, os.R_OK | os.W_OK):
                return False

            # Check permissions on all files in backup directory
            for item in backup_path.iterdir():
                if item.is_file():
                    # Files should be readable and writable
                    if not os.access(item, os.R_OK | os.W_OK):
                        self.logger.warning(
                            f"Insufficient permissions for backup file: {item}"
                        )
                        return False
                elif item.is_dir():
                    # Subdirectories should be readable, writable, and executable
                    if not os.access(item, os.R_OK | os.W_OK | os.X_OK):
                        self.logger.warning(
                            f"Insufficient permissions for backup subdirectory: {item}"
                        )
                        return False

            return True

        except Exception as e:
            self.logger.error(
                f"Error checking backup permissions for {backup_path}: {e}"
            )
            return False

    def _is_valid_package_line(self, line: str) -> bool:
        """
        Validate a single package specification line.

        Args:
            line: Package specification line to validate

        Returns:
            True if line is a valid package specification, False otherwise
        """
        # Remove whitespace
        line = line.strip()

        # Must not be empty
        if not line:
            return False

        # Handle editable installs (git URLs, local paths, etc.)
        if line.startswith("-e "):
            # Editable installs are valid for backup purposes
            # We don't need to validate the URL format strictly for restoration
            return True

        # Handle git+https, git+ssh, etc. URLs
        if any(line.startswith(prefix) for prefix in ["git+", "hg+", "svn+", "bzr+"]):
            return True

        # Handle file:// URLs
        if line.startswith("file://"):
            return True

        # Handle http/https URLs
        if any(line.startswith(prefix) for prefix in ["http://", "https://"]):
            return True

        # Must not start with invalid characters for regular package names
        if line.startswith(("=", "!", "<", ">", "~")):
            return False

        # Should contain at least a package name (letters, numbers, hyphens, underscores, dots)
        import re

        # Basic pattern for package name with optional version specifiers
        # Package name can contain letters, numbers, hyphens, underscores, dots
        # Version specifiers can be ==, >=, <=, >, <, !=, ~=
        pattern = r"^[a-zA-Z0-9][a-zA-Z0-9._-]*(\s*[><=!~]+\s*[a-zA-Z0-9._-]+(\s*,\s*[><=!~]+\s*[a-zA-Z0-9._-]+)*)?$"

        return bool(re.match(pattern, line))


class RestoreLogger:
    """Specialized logger for restoration operations."""

    def __init__(self, name: str = __name__):
        """
        Initialize the restore logger.

        Args:
            name: Logger name (defaults to module name)
        """
        self.logger = logging.getLogger(f"{name}.RestoreLogger")
        self._operation_id: Optional[str] = None
        self._start_time: Optional[float] = None
        self._operation_context: Dict[str, Any] = {}

    def start_operation(self, operation_id: str, backup: EnvironmentBackup) -> None:
        """
        Start logging a restoration operation.

        Args:
            operation_id: Unique identifier for this operation
            backup: EnvironmentBackup being restored
        """
        import time

        self._operation_id = operation_id
        self._start_time = time.time()
        self._operation_context = {
            "backup_path": str(backup.backup_path),
            "requirements_file": str(backup.requirements_file),
            "package_count": backup.package_count,
            "is_empty_environment": backup.is_empty_environment,
            "backup_created_at": (
                backup.created_at.isoformat() if backup.created_at else None
            ),
            "backup_metadata": backup.backup_metadata,
        }

        self.logger.info(
            f"[{operation_id}] Starting environment restoration from backup created at {backup.created_at}"
        )
        self.logger.info(
            f"[{operation_id}] Backup contains {backup.package_count} packages, "
            f"empty_environment={backup.is_empty_environment}"
        )
        self.logger.debug(f"[{operation_id}] Backup path: {backup.backup_path}")
        self.logger.debug(
            f"[{operation_id}] Requirements file: {backup.requirements_file}"
        )

        # Log backup metadata if available
        if backup.backup_metadata:
            self.logger.debug(
                f"[{operation_id}] Backup metadata: {backup.backup_metadata}"
            )

    def log_strategy_attempt(self, strategy_name: str, reason: str) -> None:
        """
        Log an attempt to use a restoration strategy.

        Args:
            strategy_name: Name of the strategy being attempted
            reason: Reason for selecting this strategy
        """
        op_id = self._operation_id or "unknown"
        self.logger.info(f"[{op_id}] Attempting {strategy_name} strategy: {reason}")

        # Log current environment state for debugging
        try:
            import sys

            from .subprocess_utils import secure_subprocess_run  # nosec B404

            result = secure_subprocess_run(
                [sys.executable, "-m", "pip", "list", "--format=freeze"],
                validate_first_arg=False,
                check=False,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                current_packages = [
                    line.strip() for line in result.stdout.split("\n") if line.strip()
                ]
                self.logger.debug(
                    f"[{op_id}] Current environment has {len(current_packages)} packages"
                )
            else:
                self.logger.debug(
                    f"[{op_id}] Could not determine current environment state"
                )

        except Exception as e:
            self.logger.debug(f"[{op_id}] Error checking current environment: {e}")

    def log_strategy_result(self, strategy_name: str, result: RestoreResult) -> None:
        """
        Log the result of a restoration strategy attempt.

        Args:
            strategy_name: Name of the strategy that was attempted
            result: RestoreResult from the strategy attempt
        """
        op_id = self._operation_id or "unknown"
        if result.success:
            self.logger.info(
                f"[{op_id}] {strategy_name} strategy succeeded: "
                f"{result.packages_restored} packages restored in {result.duration:.2f}s"
            )
            if result.warnings:
                for warning in result.warnings:
                    self.logger.warning(f"[{op_id}] {strategy_name} warning: {warning}")

            # Log detailed success information
            self.logger.debug(
                f"[{op_id}] {strategy_name} success details: "
                f"packages_restored={result.packages_restored}, "
                f"duration={result.duration:.3f}s, "
                f"warnings_count={len(result.warnings)}"
            )
        else:
            self.logger.error(
                f"[{op_id}] {strategy_name} strategy failed: {result.error_message}"
            )
            if result.packages_failed:
                failed_count = len(result.packages_failed)
                # Log the package details (combine count and details in one call)
                if failed_count <= 5:
                    self.logger.error(
                        f"[{op_id}] Failed packages: {', '.join(result.packages_failed)}"
                    )
                else:
                    self.logger.error(
                        f"[{op_id}] Failed packages: "
                        f"{', '.join(result.packages_failed[:5])} and {failed_count - 5} more"
                    )

            # Log detailed failure information
            self.logger.debug(
                f"[{op_id}] {strategy_name} failure details: "
                f"packages_restored={result.packages_restored}, "
                f"packages_failed_count={len(result.packages_failed)}, "
                f"duration={result.duration:.3f}s, "
                f"warnings_count={len(result.warnings)}"
            )

    def log_final_result(self, result: RestoreResult) -> None:
        """
        Log the final restoration result.

        Args:
            result: Final RestoreResult from the restoration process
        """
        import time

        op_id = self._operation_id or "unknown"
        total_duration = (
            time.time() - self._start_time if self._start_time else result.duration
        )

        if result.success:
            message = f"[{op_id}] Environment restoration completed successfully using {result.strategy_used} strategy"
            if result.packages_restored > 0:
                message += f" - {result.packages_restored} packages restored"
            if result.warnings:
                message += f" - {len(result.warnings)} warnings"
            message += f" in {total_duration:.2f}s"
            
            self.logger.info(message)
        else:
            message = f"[{op_id}] Environment restoration failed after {total_duration:.2f}s"
            if result.packages_failed:
                message += f" - {len(result.packages_failed)} packages failed"
            message += f": {result.error_message}"
            
            self.logger.error(message)

        # Log operation context for debugging
        self.logger.debug(f"[{op_id}] Operation context: {self._operation_context}")

        # Log detailed summary for debugging (not part of main logging flow)
        if result.success:
            self.logger.debug(
                f"[{op_id}] Restoration summary: {result.packages_restored} packages restored, "
                f"{len(result.warnings)} warnings"
            )
        else:
            self.logger.debug(
                f"[{op_id}] Failure summary: {result.packages_restored} packages restored, "
                f"{len(result.packages_failed)} packages failed, "
                f"strategy_used={result.strategy_used}"
            )

    def log_validation_result(self, validation_result: ValidationResult) -> None:
        """
        Log backup validation results.

        Args:
            validation_result: ValidationResult from backup validation
        """
        op_id = self._operation_id or "unknown"
        if validation_result.is_valid:
            self.logger.info(f"[{op_id}] Backup validation passed")
            if validation_result.metadata:
                self.logger.debug(
                    f"[{op_id}] Validation metadata: {validation_result.metadata}"
                )
        else:
            self.logger.error(f"[{op_id}] Backup validation failed:")
            for error in validation_result.errors:
                self.logger.error(f"[{op_id}]   - {error}")

        for warning in validation_result.warnings:
            self.logger.warning(f"[{op_id}] Validation warning: {warning}")

    def log_package_operation(
        self, operation: str, package: str, success: bool, details: str = ""
    ) -> None:
        """
        Log individual package operations during restoration.

        Args:
            operation: Type of operation (install, uninstall, etc.)
            package: Package name being operated on
            success: Whether the operation succeeded
            details: Additional details about the operation
        """
        op_id = self._operation_id or "unknown"
        status = "succeeded" if success else "failed"
        message = f"[{op_id}] Package {operation} {status}: {package}"

        if details:
            message += f" ({details})"

        if success:
            self.logger.debug(message)
        else:
            self.logger.warning(message)

    def log_environment_state(
        self, state_description: str, package_count: Optional[int] = None
    ) -> None:
        """
        Log the current environment state during restoration.

        Args:
            state_description: Description of the current state
            package_count: Optional count of packages in current state
        """
        op_id = self._operation_id or "unknown"
        message = f"[{op_id}] Environment state: {state_description}"

        if package_count is not None:
            message += f" ({package_count} packages)"

        self.logger.debug(message)

    def log_error_analysis(self, error_analysis: Any) -> None:
        """
        Log error analysis results.

        Args:
            error_analysis: ErrorAnalysis instance with categorized error information
        """
        op_id = self._operation_id or "unknown"

        self.logger.error(
            f"[{op_id}] Error analysis: {error_analysis.category.value} "
            f"(confidence: {error_analysis.confidence:.2f})"
        )
        self.logger.error(f"[{op_id}] Error description: {error_analysis.description}")

        if error_analysis.affected_packages:
            self.logger.error(
                f"[{op_id}] Affected packages: {', '.join(error_analysis.affected_packages[:5])}"
                + (
                    f" and {len(error_analysis.affected_packages) - 5} more"
                    if len(error_analysis.affected_packages) > 5
                    else ""
                )
            )

        if error_analysis.suggested_actions:
            self.logger.info(f"[{op_id}] Suggested recovery actions:")
            for i, action in enumerate(error_analysis.suggested_actions[:3], 1):
                self.logger.info(f"[{op_id}]   {i}. {action}")

        if error_analysis.technical_details:
            self.logger.debug(
                f"[{op_id}] Technical details: {error_analysis.technical_details}"
            )

        recoverable_status = (
            "recoverable" if error_analysis.is_recoverable else "not recoverable"
        )
        self.logger.info(f"[{op_id}] Error is {recoverable_status}")

    def get_operation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current operation for reporting.

        Returns:
            Dictionary containing operation summary information
        """
        import time

        summary = {
            "operation_id": self._operation_id,
            "start_time": self._start_time,
            "duration": time.time() - self._start_time if self._start_time else None,
            "context": self._operation_context.copy(),
        }

        return summary

    def error(self, message: str) -> None:
        """
        Log an error message.

        Args:
            message: Error message to log
        """
        self.logger.error(message)

    def debug(self, message: str) -> None:
        """
        Log a debug message.

        Args:
            message: Debug message to log
        """
        self.logger.debug(message)


class EnvironmentRestorer:
    """Handles environment restoration with multiple strategies."""

    def __init__(self, logger: Optional[RestoreLogger] = None) -> None:
        """
        Initialize the environment restorer.

        Args:
            logger: Optional RestoreLogger instance for detailed logging
        """
        self.logger = logger or RestoreLogger()
        self.backup_validator = BackupValidator()

        # Import error analyzer
        from .error_analyzer import ErrorAnalyzer

        self.error_analyzer = ErrorAnalyzer()

        # Import strategies here to avoid circular imports
        from .restore_strategies import (
            CleanInstallStrategy,
            FallbackStrategy,
            ForceReinstallStrategy,
        )

        # Initialize strategies in order of preference
        self.strategies = [
            ForceReinstallStrategy(),
            CleanInstallStrategy(),
            FallbackStrategy(),
        ]

    def restore_environment(self, backup: EnvironmentBackup) -> RestoreResult:
        """
        Restore environment using the best available strategy.

        This method attempts to restore the environment using different strategies
        in order of preference, falling back to more aggressive strategies if
        earlier ones fail.

        Args:
            backup: EnvironmentBackup to restore from

        Returns:
            RestoreResult indicating success or failure of restoration
        """
        import uuid

        operation_id = str(uuid.uuid4())[:8]

        # Start logging the operation
        self.logger.start_operation(operation_id, backup)

        # Validate backup first
        validation_result = self.backup_validator.validate_backup(backup)
        self.logger.log_validation_result(validation_result)

        if not validation_result.is_valid:
            error_message = (
                f"Backup validation failed: {'; '.join(validation_result.errors)}"
            )
            result = RestoreResult.failure_result(
                strategy="ValidationFailed",
                error_message=error_message,
                duration=0.0,
                warnings=validation_result.warnings,
            )
            self.logger.log_final_result(result)
            return result

        # Try each strategy in order
        last_result = None
        failed_results = []

        for strategy in self.strategies:
            if strategy.can_handle(backup):
                strategy_name = strategy.__class__.__name__.replace("Strategy", "")
                reason = self._get_strategy_selection_reason(
                    strategy, backup, last_result
                )

                self.logger.log_strategy_attempt(strategy_name, reason)

                result = self._try_restore_strategy(strategy, backup)
                self.logger.log_strategy_result(strategy_name, result)

                if result.success:
                    # Add any validation warnings to the successful result
                    if validation_result.warnings:
                        result.warnings.extend(validation_result.warnings)

                    self.logger.log_final_result(result)
                    return result
                else:
                    # Analyze the failure for better debugging
                    error_analysis = self.error_analyzer.analyze_error(result)
                    self.logger.log_error_analysis(error_analysis)

                    # Store failed result for analysis
                    failed_results.append(result)

                last_result = result
            else:
                strategy_name = strategy.__class__.__name__.replace("Strategy", "")
                self.logger.debug(
                    f"[{operation_id}] Skipping {strategy_name} strategy: cannot handle this backup"
                )

        # All strategies failed - perform comprehensive error analysis
        if failed_results:
            categorized_errors = self.error_analyzer.analyze_multiple_failures(
                failed_results
            )

            # Log summary of all failure categories
            self.logger.error(
                f"[{operation_id}] Restoration failed with {len(categorized_errors)} error categories:"
            )
            for category, analyses in categorized_errors.items():
                self.logger.error(
                    f"[{operation_id}]   - {category.value}: {len(analyses)} occurrences"
                )

        # Create final failure result with enhanced error information
        error_message = "All restoration strategies failed"
        if last_result and last_result.error_message:
            # Analyze the last error for the most relevant information
            last_analysis = self.error_analyzer.analyze_error(last_result)
            error_message = f"All restoration strategies failed. Primary issue: {last_analysis.description}"

            # Add recovery suggestions to warnings
            recovery_suggestions = self.error_analyzer.get_recovery_suggestions(
                last_analysis
            )
            validation_result.warnings.extend(
                [
                    f"Recovery suggestion: {suggestion}"
                    for suggestion in recovery_suggestions[:3]
                ]
            )

        final_result = RestoreResult.failure_result(
            strategy="AllStrategiesFailed",
            error_message=error_message,
            duration=sum(getattr(r, "duration", 0) for r in failed_results),
            warnings=validation_result.warnings,
            packages_failed=last_result.packages_failed if last_result else [],
        )

        self.logger.log_final_result(final_result)
        return final_result

    def _try_restore_strategy(
        self, strategy: Any, backup: EnvironmentBackup
    ) -> RestoreResult:
        """
        Try a specific restoration strategy with error handling.

        Args:
            strategy: RestoreStrategy instance to try
            backup: EnvironmentBackup to restore from

        Returns:
            RestoreResult from the strategy attempt
        """
        try:
            result = strategy.restore(backup)
            return result  # type: ignore[no-any-return]
        except Exception as e:
            strategy_name = strategy.__class__.__name__.replace("Strategy", "")
            error_message = f"Unexpected error in {strategy_name} strategy: {e}"
            self.logger.error(error_message)

            return RestoreResult.failure_result(
                strategy=strategy_name, error_message=error_message, duration=0.0
            )

    def _get_strategy_selection_reason(
        self,
        strategy: Any,
        backup: EnvironmentBackup,
        last_result: Optional[RestoreResult],
    ) -> str:
        """
        Get a human-readable reason for selecting a strategy.

        Args:
            strategy: RestoreStrategy being selected
            backup: EnvironmentBackup being restored
            last_result: Result from the previous strategy attempt (if any)

        Returns:
            String describing why this strategy was selected
        """
        strategy_name = strategy.__class__.__name__

        if strategy_name == "ForceReinstallStrategy":
            if backup.is_empty_environment:
                return "empty environment, minimal restoration needed"
            elif backup.package_count <= 10:
                return "small environment, force reinstall is efficient"
            else:
                return "first attempt, force reinstall is least disruptive"

        elif strategy_name == "CleanInstallStrategy":
            if last_result:
                return f"fallback after {last_result.strategy_used} failed"
            else:
                return "clean slate approach for complex environments"

        elif strategy_name == "FallbackStrategy":
            if last_result:
                return f"last resort after {last_result.strategy_used} failed"
            else:
                return "fallback strategy for edge cases"

        else:
            return "strategy selected based on backup characteristics"


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
        Create a backup of the current environment with enhanced validation and metadata.

        Returns:
            EnvironmentBackup object containing backup information

        Raises:
            RuntimeError: If backup creation fails or validation fails
        """
        backup_path = (
            self.temp_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        try:
            backup_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"Failed to create backup directory {backup_path}: {e}")

        # Create requirements file from current environment
        requirements_file = backup_path / "requirements.txt"
        package_count = 0
        is_empty_environment = False

        # Enhanced metadata collection
        backup_metadata: Dict[str, Any] = {
            "python_version": sys.version,
            "python_version_info": {
                "major": sys.version_info.major,
                "minor": sys.version_info.minor,
                "micro": sys.version_info.micro,
            },
            "platform": sys.platform,
            "created_by": "UpgradeValidator",
            "backup_created_at": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "environment_type": self._detect_environment_type(),
        }

        # Create requirements backup with improved error handling
        try:
            # nosec B603
            result = secure_subprocess_run(
                [sys.executable, "-m", "pip", "freeze"],
                validate_first_arg=False,  # sys.executable is trusted
                check=False,  # Don't raise exception, handle return code manually
                capture_output=True,
                text=True,
                timeout=30,  # Add timeout to prevent hanging
            )

            if result.returncode != 0:
                # Handle pip freeze failures gracefully
                error_msg = f"pip freeze failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr.strip()}"

                logger.warning(f"{error_msg}. Creating empty backup.")

                # Create empty requirements file for failed pip freeze
                requirements_file.write_text("")
                is_empty_environment = True
                package_count = 0
                backup_metadata["pip_freeze_failed"] = True
                backup_metadata["pip_freeze_error"] = error_msg

            elif result.stdout.strip():
                # Successfully got package information
                requirements_content = result.stdout.strip()

                try:
                    requirements_file.write_text(requirements_content, encoding="utf-8")
                except Exception as e:
                    # Handle write failure gracefully - create empty backup with error metadata
                    logger.warning(
                        f"Failed to write requirements file: {e}. Creating empty backup."
                    )
                    try:
                        # Try to create an empty file so it exists
                        requirements_file.touch()
                    except Exception as touch_e:
                        # If even touch fails, continue without the file
                        logger.debug(
                            f"Failed to create empty requirements file: {touch_e}"
                        )
                    is_empty_environment = True
                    package_count = 0
                    backup_metadata["pip_freeze_failed"] = True
                    backup_metadata["pip_freeze_error"] = (
                        f"Failed to write requirements file: {e}"
                    )
                    requirements_content = ""  # Set to empty for the rest of the logic

                # Count packages more accurately
                package_lines = [
                    line.strip()
                    for line in requirements_content.split("\n")
                    if line.strip()
                    and not line.strip().startswith("#")
                    and not line.strip().startswith("-")
                ]
                package_count = len(package_lines)

                backup_metadata["total_packages"] = package_count
                backup_metadata["pip_freeze_success"] = True

                # Add sample of packages for debugging (first 5)
                if package_lines:
                    backup_metadata["sample_packages"] = package_lines[:5]

                logger.info(f"Created backup with {package_count} packages")

            else:
                # pip freeze succeeded but returned no packages (empty environment)
                try:
                    requirements_file.write_text("")
                except Exception as e:
                    logger.warning(f"Failed to write empty requirements file: {e}")
                    try:
                        # Try to create an empty file so it exists
                        requirements_file.touch()
                    except Exception as touch_e:
                        # If even touch fails, continue without the file
                        logger.debug(
                            f"Failed to create empty requirements file: {touch_e}"
                        )
                    backup_metadata["requirements_write_failed"] = True
                    backup_metadata["requirements_write_error"] = str(e)
                is_empty_environment = True
                package_count = 0
                backup_metadata["total_packages"] = 0
                backup_metadata["pip_freeze_success"] = True
                backup_metadata["empty_environment_reason"] = (
                    "pip freeze returned no packages"
                )
                logger.info(
                    "Created backup for empty environment (no packages installed)"
                )

        except subprocess.TimeoutExpired:
            # Handle timeout gracefully
            logger.warning("pip freeze timed out. Creating empty backup.")
            try:
                requirements_file.write_text("")
            except Exception as e:
                logger.warning(
                    f"Failed to write empty requirements file after timeout: {e}"
                )
                try:
                    # Try to create an empty file so it exists
                    requirements_file.touch()
                except Exception as touch_e:
                    # If even touch fails, continue without the file
                    logger.debug(
                        f"Failed to create empty requirements file after timeout: {touch_e}"
                    )
                backup_metadata["requirements_write_failed"] = True
                backup_metadata["requirements_write_error"] = str(e)
            is_empty_environment = True
            package_count = 0
            backup_metadata["pip_freeze_failed"] = True
            backup_metadata["pip_freeze_error"] = (
                "pip freeze timed out after 30 seconds"
            )

        except Exception as e:
            # Handle other pip freeze errors
            logger.warning(
                f"pip freeze failed with exception: {e}. Creating empty backup."
            )
            try:
                requirements_file.write_text("")
            except Exception as write_e:
                logger.warning(
                    f"Failed to write empty requirements file after pip freeze error: {write_e}"
                )
                try:
                    # Try to create an empty file so it exists
                    requirements_file.touch()
                except Exception as touch_e:
                    # If even touch fails, continue without the file
                    logger.debug(
                        f"Failed to create empty requirements file after pip freeze error: {touch_e}"
                    )
                backup_metadata["requirements_write_failed"] = True
                backup_metadata["requirements_write_error"] = str(write_e)
            is_empty_environment = True
            package_count = 0
            backup_metadata["pip_freeze_failed"] = True
            backup_metadata["pip_freeze_error"] = str(e)

        # Backup pyproject.toml if it exists
        pyproject_backup = None
        if self.pyproject_path.exists():
            try:
                pyproject_backup_path = backup_path / "pyproject.toml"
                shutil.copy2(self.pyproject_path, pyproject_backup_path)
                pyproject_backup = pyproject_backup_path  # Only set if successful
                backup_metadata["has_pyproject"] = True
                backup_metadata["pyproject_backup_success"] = True
            except Exception as e:
                logger.warning(f"Failed to backup pyproject.toml: {e}")
                pyproject_backup = None  # Ensure it's None on failure
                backup_metadata["has_pyproject"] = True
                backup_metadata["pyproject_backup_success"] = False
                backup_metadata["pyproject_backup_error"] = str(e)
        else:
            backup_metadata["has_pyproject"] = False

        # Create the backup object
        backup = EnvironmentBackup(
            backup_path=backup_path,
            requirements_file=requirements_file,
            pyproject_backup=pyproject_backup,
            package_count=package_count,
            is_empty_environment=is_empty_environment,
            backup_metadata=backup_metadata,
        )

        # Validate backup before returning
        backup_validator = BackupValidator()
        validation_result = backup_validator.validate_backup(backup)

        if not validation_result.is_valid:
            # Log validation errors but don't fail - backup might still be usable
            logger.warning(
                f"Backup validation failed: {'; '.join(validation_result.errors)}"
            )
            backup_metadata["validation_failed"] = True
            backup_metadata["validation_errors"] = validation_result.errors

            # If validation fails due to critical issues, raise an error
            # But don't fail for pyproject backup issues since they're optional
            critical_errors = [
                error
                for error in validation_result.errors
                if (
                    "does not exist" in error
                    or "not a directory" in error
                    or "not a file" in error
                )
                and "Backup path"
                in error  # Only fail for backup path issues, not pyproject issues
            ]
            if critical_errors:
                raise RuntimeError(
                    f"Critical backup validation failures: {'; '.join(critical_errors)}"
                )
        else:
            backup_metadata["validation_passed"] = True

        # Log validation warnings
        for warning in validation_result.warnings:
            logger.warning(f"Backup validation warning: {warning}")

        # Add validation metadata to backup
        backup.backup_metadata.update(
            {
                "validation_warnings": validation_result.warnings,
                "validation_metadata": validation_result.metadata,
            }
        )

        logger.info(f"Successfully created environment backup at {backup_path}")
        return backup

    def _detect_environment_type(self) -> str:
        """
        Detect the type of Python environment (venv, conda, system, etc.).

        Returns:
            String describing the environment type
        """
        # Check for pipenv first (before generic virtual environment check)
        if os.environ.get("PIPENV_ACTIVE"):
            return "pipenv"

        # Check for poetry (before generic virtual environment check)
        if os.environ.get("POETRY_ACTIVE"):
            return "poetry"

        # Check for virtual environment
        if hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        ):
            # Check if it's a conda environment
            if (
                "conda" in sys.prefix
                or "anaconda" in sys.prefix
                or "miniconda" in sys.prefix
            ):
                return "conda"
            else:
                return "virtualenv"

        # Default to system
        return "system"

    def restore_environment(self, backup: EnvironmentBackup) -> bool:
        """
        Restore environment from backup using the new restoration system.

        Args:
            backup: EnvironmentBackup to restore from

        Returns:
            True if restoration was successful, False otherwise
        """
        try:
            # Restore pyproject.toml if backed up (maintain backward compatibility)
            if backup.pyproject_backup and backup.pyproject_backup.exists():
                shutil.copy2(backup.pyproject_backup, self.pyproject_path)

            # Use the new EnvironmentRestorer for restoration
            restorer = EnvironmentRestorer()
            restore_result = restorer.restore_environment(backup)

            # Validate restoration success by comparing package lists
            if restore_result.success:
                validation_success = self._validate_restoration_success(
                    backup, restore_result
                )
                if not validation_success:
                    logger.warning(
                        "Restoration completed but validation failed - packages may not match backup"
                    )
                    # Still return True for backward compatibility, but log the issue

                logger.info(
                    f"Environment successfully restored using {restore_result.strategy_used} strategy"
                )
                logger.info(
                    f"Restored {restore_result.packages_restored} packages in {restore_result.duration:.2f}s"
                )

                # Log any warnings from the restoration process
                for warning in restore_result.warnings:
                    logger.warning(f"Restoration warning: {warning}")

                return True
            else:
                logger.error(
                    f"Failed to restore environment: {restore_result.error_message}"
                )
                logger.error(f"Strategy used: {restore_result.strategy_used}")

                # Log failed packages if available
                if restore_result.packages_failed:
                    failed_count = len(restore_result.packages_failed)
                    logger.error(f"Failed to restore {failed_count} packages")
                    # Log first few failed packages for debugging
                    for pkg in restore_result.packages_failed[:5]:
                        logger.error(f"  - {pkg}")
                    if failed_count > 5:
                        logger.error(f"  ... and {failed_count - 5} more packages")

                return False

        except Exception as e:
            logger.error(f"Unexpected error during environment restoration: {e}")
            return False

    def _validate_restoration_success(
        self, backup: EnvironmentBackup, restore_result: RestoreResult
    ) -> bool:
        """
        Validate that restoration was successful by comparing package lists.

        Args:
            backup: Original EnvironmentBackup that was restored
            restore_result: RestoreResult from the restoration process

        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Get expected packages from backup
            expected_packages = set(backup.get_package_list())

            # Handle empty environment case
            if backup.is_empty_environment or backup.package_count == 0:
                if len(expected_packages) == 0:
                    logger.debug(
                        "Validation passed: empty environment restored correctly"
                    )
                    return True
                else:
                    logger.warning(
                        f"Validation warning: backup marked as empty but contains {len(expected_packages)} packages"
                    )
                    # Don't fail validation for this inconsistency
                    return True

            # Get currently installed packages
            try:
                result = secure_subprocess_run(
                    [sys.executable, "-m", "pip", "list", "--format=freeze"],
                    validate_first_arg=False,  # sys.executable is trusted
                    check=True,
                    capture_output=True,
                    text=True,
                )

                current_packages = set()
                for line in result.stdout.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Extract package name (before ==)
                        package_name = line.split("==")[0].strip()
                        if package_name:
                            current_packages.add(package_name)

            except Exception as e:
                logger.warning(
                    f"Could not get current package list for validation: {e}"
                )
                return False

            # Compare package lists
            missing_packages = expected_packages - current_packages
            extra_packages = current_packages - expected_packages

            # Log validation results
            if not missing_packages and not extra_packages:
                logger.debug("Validation passed: package lists match exactly")
                return True

            if missing_packages:
                logger.warning(
                    f"Validation warning: {len(missing_packages)} expected packages are missing"
                )
                for pkg in list(missing_packages)[:3]:  # Log first 3 missing packages
                    logger.warning(f"  Missing: {pkg}")
                if len(missing_packages) > 3:
                    logger.warning(
                        f"  ... and {len(missing_packages) - 3} more missing packages"
                    )

            if extra_packages:
                logger.info(
                    f"Validation info: {len(extra_packages)} additional packages are installed"
                )
                # Extra packages are less concerning than missing packages

            # Consider validation successful if no packages are missing
            # Extra packages are acceptable as they might be dependencies
            validation_success = len(missing_packages) == 0

            if validation_success:
                logger.debug("Validation passed: all expected packages are present")
            else:
                logger.warning("Validation failed: some expected packages are missing")

            return validation_success

        except Exception as e:
            logger.error(f"Error during restoration validation: {e}")
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
            # nosec B603
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
            # nosec B603
            result = secure_subprocess_run(
                [sys.executable, "-m", "pip", "check"],
                validate_first_arg=False,  # sys.executable is trusted
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                # Parse pip check output to extract meaningful conflict information
                output = (
                    result.stdout.strip() if result.stdout else result.stderr.strip()
                )
                if output:
                    conflicts.append(
                        f"Current environment has dependency issues: {output}"
                    )
                else:
                    conflicts.append(
                        "Current environment has dependency issues (no details available)"
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

            # nosec B603
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
            # or "= 5 passed in 2.34s ="
            if " passed" in line and " in " in line and line.startswith("="):
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed," or part == "passed":
                        test_results["test_count"] = int(parts[i - 1])
                    elif part == "failed," or part == "failed":
                        test_results["failures"] = int(parts[i - 1])
                    elif part == "error," or part == "error":
                        test_results["errors"] = int(parts[i - 1])
                    elif part == "in" and i + 1 < len(parts):
                        # Extract duration from "in 2.34s" format
                        duration_str = parts[i + 1]
                        if duration_str.endswith("s"):
                            try:
                                duration = float(
                                    duration_str[:-1]
                                )  # Remove 's' and convert to float
                                test_results["duration"] = duration
                            except ValueError:
                                pass  # Keep default duration if parsing fails
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
            # nosec B603
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
                # nosec B603
                result = secure_subprocess_run(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        f"{validated_package_name}=={validated_target_version}",
                    ],
                    validate_first_arg=False,  # sys.executable is trusted
                    check=False,  # Don't raise exception, check return code manually
                )

                if result.returncode != 0:
                    error_message = f"Failed to install package: pip install returned {result.returncode}"
                    if result.stderr:
                        error_message = f"Failed to install package: {result.stderr}"

                    return UpgradeResult.failure_result(
                        package_name=package_name,
                        from_version=current_version,
                        to_version=target_version,
                        error_message=error_message,
                        validation_duration=(
                            datetime.now() - start_time
                        ).total_seconds(),
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
                    # Validation failed, rollback
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

        except subprocess.CalledProcessError as e:
            # Handle subprocess errors specifically (e.g., pip install failures)
            if backup:
                rollback_performed = self.restore_environment(backup)

            error_message = f"Failed to install package: {e}"
            return UpgradeResult.failure_result(
                package_name=package_name,
                from_version=(
                    current_version if "current_version" in locals() else "unknown"
                ),
                to_version=target_version,
                error_message=error_message,
                rollback_performed=rollback_performed,
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
