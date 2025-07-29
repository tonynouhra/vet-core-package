"""
Tests for ErrorAnalyzer functionality.
"""

import pytest

from vet_core.security.error_analyzer import ErrorAnalyzer, ErrorAnalysis, ErrorCategory
from vet_core.security.upgrade_validator import RestoreResult


class TestErrorAnalyzer:
    """Test cases for ErrorAnalyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = ErrorAnalyzer()

    def test_analyze_successful_result(self):
        """Test analyzing a successful result."""
        result = RestoreResult.success_result(
            strategy="ForceReinstall", packages_restored=5, duration=2.0
        )

        analysis = self.analyzer.analyze_error(result)

        assert analysis.category == ErrorCategory.UNKNOWN_ERROR
        assert analysis.confidence == 0.0
        assert "successful" in analysis.description.lower()
        assert analysis.is_recoverable is True

    def test_analyze_network_error(self):
        """Test analyzing network-related errors."""
        result = RestoreResult.failure_result(
            strategy="ForceReinstall",
            error_message="Connection timed out while downloading package",
            duration=30.0,
            packages_failed=["requests", "urllib3"],
        )

        analysis = self.analyzer.analyze_error(result)

        assert analysis.category == ErrorCategory.NETWORK_ERROR
        assert analysis.confidence == 0.9
        assert "network connectivity" in analysis.description.lower()
        assert "requests" in analysis.affected_packages
        assert "urllib3" in analysis.affected_packages
        assert analysis.is_recoverable is True
        assert any(
            "internet connection" in action.lower()
            for action in analysis.suggested_actions
        )

    def test_analyze_permission_error(self):
        """Test analyzing permission-related errors."""
        result = RestoreResult.failure_result(
            strategy="CleanInstall",
            error_message="Permission denied: cannot write to /usr/local/lib/python3.11/site-packages",
            duration=1.0,
            packages_failed=["numpy"],
        )

        analysis = self.analyzer.analyze_error(result)

        assert analysis.category == ErrorCategory.PERMISSION_ERROR
        assert analysis.confidence == 0.95
        assert "insufficient permissions" in analysis.description.lower()
        assert "numpy" in analysis.affected_packages
        assert analysis.is_recoverable is True
        assert any(
            "elevated privileges" in action.lower()
            for action in analysis.suggested_actions
        )

    def test_analyze_package_not_found_error(self):
        """Test analyzing package not found errors."""
        result = RestoreResult.failure_result(
            strategy="ForceReinstall",
            error_message="No matching distribution found for nonexistent-package==1.0.0",
            duration=5.0,
            packages_failed=["nonexistent-package"],
        )

        analysis = self.analyzer.analyze_error(result)

        assert analysis.category == ErrorCategory.PACKAGE_NOT_FOUND
        assert analysis.confidence == 0.85
        assert "could not be found" in analysis.description.lower()
        assert "nonexistent-package" in analysis.affected_packages
        assert analysis.is_recoverable is True
        assert any(
            "verify package names" in action.lower()
            for action in analysis.suggested_actions
        )

    def test_analyze_dependency_conflict_error(self):
        """Test analyzing dependency conflict errors."""
        result = RestoreResult.failure_result(
            strategy="ForceReinstall",
            error_message="Cannot satisfy requirement: package-a requires package-b>=2.0 but package-b==1.0 is installed",
            duration=3.0,
            packages_failed=["package-a", "package-b"],
        )

        analysis = self.analyzer.analyze_error(result)

        assert analysis.category == ErrorCategory.DEPENDENCY_CONFLICT
        assert analysis.confidence == 0.8
        assert "dependency conflicts" in analysis.description.lower()
        assert "package-a" in analysis.affected_packages
        assert "package-b" in analysis.affected_packages
        assert analysis.is_recoverable is True
        assert any(
            "dependency resolution" in action.lower()
            for action in analysis.suggested_actions
        )

    def test_analyze_disk_space_error(self):
        """Test analyzing disk space errors."""
        result = RestoreResult.failure_result(
            strategy="CleanInstall",
            error_message="No space left on device: cannot write to /tmp/pip-build-xyz",
            duration=10.0,
            packages_failed=["large-package"],
        )

        analysis = self.analyzer.analyze_error(result)

        assert analysis.category == ErrorCategory.DISK_SPACE_ERROR
        assert analysis.confidence == 0.95
        assert "insufficient disk space" in analysis.description.lower()
        assert "large-package" in analysis.affected_packages
        assert analysis.is_recoverable is True
        assert any(
            "free up disk space" in action.lower()
            for action in analysis.suggested_actions
        )

    def test_analyze_python_version_error(self):
        """Test analyzing Python version incompatibility errors."""
        result = RestoreResult.failure_result(
            strategy="ForceReinstall",
            error_message="Package requires Python >=3.12 but you have Python 3.11",
            duration=2.0,
            packages_failed=["modern-package"],
        )

        analysis = self.analyzer.analyze_error(result)

        assert analysis.category == ErrorCategory.PYTHON_VERSION_INCOMPATIBLE
        assert analysis.confidence == 0.9
        assert "python version incompatibility" in analysis.description.lower()
        assert "modern-package" in analysis.affected_packages
        assert analysis.is_recoverable is False  # May require environment changes
        assert any(
            "python version" in action.lower() for action in analysis.suggested_actions
        )

    def test_analyze_corrupted_package_error(self):
        """Test analyzing corrupted package errors."""
        result = RestoreResult.failure_result(
            strategy="ForceReinstall",
            error_message="Hash mismatch for package.whl: expected abc123 but got def456",
            duration=5.0,
            packages_failed=["corrupted-package"],
        )

        analysis = self.analyzer.analyze_error(result)

        assert analysis.category == ErrorCategory.CORRUPTED_PACKAGE
        assert analysis.confidence == 0.85
        assert "corruption detected" in analysis.description.lower()
        assert "corrupted-package" in analysis.affected_packages
        assert analysis.is_recoverable is True
        assert any(
            "clear" in action.lower() and "cache" in action.lower()
            for action in analysis.suggested_actions
        )

    def test_analyze_backup_invalid_error(self):
        """Test analyzing backup validation errors."""
        result = RestoreResult.failure_result(
            strategy="ValidationFailed",
            error_message="Backup validation failed: requirements file not found",
            duration=0.1,
            packages_failed=[],
        )

        analysis = self.analyzer.analyze_error(result)

        assert analysis.category == ErrorCategory.BACKUP_INVALID
        assert analysis.confidence == 0.9
        assert "backup validation failed" in analysis.description.lower()
        assert analysis.is_recoverable is True
        assert any(
            "recreate" in action.lower() and "backup" in action.lower()
            for action in analysis.suggested_actions
        )

    def test_analyze_system_error(self):
        """Test analyzing system-level errors."""
        result = RestoreResult.failure_result(
            strategy="ForceReinstall",
            error_message="OSError: [Errno 2] No such file or directory: '/usr/bin/python3'",
            duration=1.0,
            packages_failed=["some-package"],
        )

        analysis = self.analyzer.analyze_error(result)

        assert analysis.category == ErrorCategory.SYSTEM_ERROR
        assert analysis.confidence == 0.6
        assert "system-level error" in analysis.description.lower()
        assert "some-package" in analysis.affected_packages
        assert analysis.is_recoverable is True
        assert any(
            "system logs" in action.lower() for action in analysis.suggested_actions
        )

    def test_analyze_unknown_error(self):
        """Test analyzing unrecognized errors."""
        result = RestoreResult.failure_result(
            strategy="ForceReinstall",
            error_message="Some completely unknown error message that doesn't match any patterns",
            duration=2.0,
            packages_failed=["mystery-package"],
        )

        analysis = self.analyzer.analyze_error(result)

        assert analysis.category == ErrorCategory.UNKNOWN_ERROR
        assert analysis.confidence == 0.1
        assert "unrecognized error pattern" in analysis.description.lower()
        assert "mystery-package" in analysis.affected_packages
        assert analysis.is_recoverable is True
        assert any(
            "full error message" in action.lower()
            for action in analysis.suggested_actions
        )

    def test_analyze_multiple_failures(self):
        """Test analyzing multiple failures and grouping by category."""
        results = [
            RestoreResult.failure_result(
                strategy="ForceReinstall",
                error_message="Connection timed out",
                duration=30.0,
                packages_failed=["requests"],
            ),
            RestoreResult.failure_result(
                strategy="CleanInstall",
                error_message="Network unreachable",
                duration=25.0,
                packages_failed=["urllib3"],
            ),
            RestoreResult.failure_result(
                strategy="Fallback",
                error_message="Permission denied",
                duration=1.0,
                packages_failed=["numpy"],
            ),
        ]

        categorized = self.analyzer.analyze_multiple_failures(results)

        assert ErrorCategory.NETWORK_ERROR in categorized
        assert ErrorCategory.PERMISSION_ERROR in categorized
        assert len(categorized[ErrorCategory.NETWORK_ERROR]) == 2
        assert len(categorized[ErrorCategory.PERMISSION_ERROR]) == 1

    def test_get_recovery_suggestions_network_error(self):
        """Test getting recovery suggestions for network errors."""
        analysis = ErrorAnalysis(
            category=ErrorCategory.NETWORK_ERROR,
            confidence=0.9,
            description="Network error",
            suggested_actions=["Base suggestion"],
            is_recoverable=True,
        )

        suggestions = self.analyzer.get_recovery_suggestions(analysis)

        assert "Base suggestion" in suggestions
        assert any(
            "internet connection" in suggestion.lower() for suggestion in suggestions
        )
        assert any("package index" in suggestion.lower() for suggestion in suggestions)
        assert any(
            "cached packages" in suggestion.lower() for suggestion in suggestions
        )

    def test_get_recovery_suggestions_permission_error(self):
        """Test getting recovery suggestions for permission errors."""
        analysis = ErrorAnalysis(
            category=ErrorCategory.PERMISSION_ERROR,
            confidence=0.95,
            description="Permission error",
            suggested_actions=["Base suggestion"],
            is_recoverable=True,
        )

        suggestions = self.analyzer.get_recovery_suggestions(analysis)

        assert "Base suggestion" in suggestions
        assert any(
            "appropriate permissions" in suggestion.lower()
            for suggestion in suggestions
        )
        assert any("sudo" in suggestion.lower() for suggestion in suggestions)
        assert any("write access" in suggestion.lower() for suggestion in suggestions)

    def test_get_recovery_suggestions_package_not_found(self):
        """Test getting recovery suggestions for package not found errors."""
        analysis = ErrorAnalysis(
            category=ErrorCategory.PACKAGE_NOT_FOUND,
            confidence=0.85,
            description="Package not found",
            suggested_actions=["Base suggestion"],
            is_recoverable=True,
        )

        suggestions = self.analyzer.get_recovery_suggestions(analysis)

        assert "Base suggestion" in suggestions
        assert any(
            "verify package names" in suggestion.lower() for suggestion in suggestions
        )
        assert any("pypi" in suggestion.lower() for suggestion in suggestions)
        assert any(
            "alternative package versions" in suggestion.lower()
            for suggestion in suggestions
        )

    def test_get_recovery_suggestions_dependency_conflict(self):
        """Test getting recovery suggestions for dependency conflicts."""
        analysis = ErrorAnalysis(
            category=ErrorCategory.DEPENDENCY_CONFLICT,
            confidence=0.8,
            description="Dependency conflict",
            suggested_actions=["Base suggestion"],
            is_recoverable=True,
        )

        suggestions = self.analyzer.get_recovery_suggestions(analysis)

        assert "Base suggestion" in suggestions
        assert any("dependencies" in suggestion.lower() for suggestion in suggestions)
        assert any("pip-tools" in suggestion.lower() for suggestion in suggestions)
        assert any("individually" in suggestion.lower() for suggestion in suggestions)

    def test_get_recovery_suggestions_disk_space(self):
        """Test getting recovery suggestions for disk space errors."""
        analysis = ErrorAnalysis(
            category=ErrorCategory.DISK_SPACE_ERROR,
            confidence=0.95,
            description="Disk space error",
            suggested_actions=["Base suggestion"],
            is_recoverable=True,
        )

        suggestions = self.analyzer.get_recovery_suggestions(analysis)

        assert "Base suggestion" in suggestions
        assert any(
            "free up disk space" in suggestion.lower() for suggestion in suggestions
        )
        assert any(
            "pip cache purge" in suggestion.lower() for suggestion in suggestions
        )
        assert any(
            "temporary directory" in suggestion.lower() for suggestion in suggestions
        )

    def test_get_recovery_suggestions_python_version(self):
        """Test getting recovery suggestions for Python version errors."""
        analysis = ErrorAnalysis(
            category=ErrorCategory.PYTHON_VERSION_INCOMPATIBLE,
            confidence=0.9,
            description="Python version incompatible",
            suggested_actions=["Base suggestion"],
            is_recoverable=False,
        )

        suggestions = self.analyzer.get_recovery_suggestions(analysis)

        assert "Base suggestion" in suggestions
        assert any(
            "python version compatibility" in suggestion.lower()
            for suggestion in suggestions
        )
        assert any(
            "upgrading or downgrading python" in suggestion.lower()
            for suggestion in suggestions
        )
        assert any(
            "compatible with current python" in suggestion.lower()
            for suggestion in suggestions
        )

    def test_get_recovery_suggestions_corrupted_package(self):
        """Test getting recovery suggestions for corrupted packages."""
        analysis = ErrorAnalysis(
            category=ErrorCategory.CORRUPTED_PACKAGE,
            confidence=0.85,
            description="Corrupted package",
            suggested_actions=["Base suggestion"],
            is_recoverable=True,
        )

        suggestions = self.analyzer.get_recovery_suggestions(analysis)

        assert "Base suggestion" in suggestions
        assert any(
            "pip cache purge" in suggestion.lower() for suggestion in suggestions
        )
        assert any(
            "downloading packages again" in suggestion.lower()
            for suggestion in suggestions
        )
        assert any(
            "package integrity" in suggestion.lower() for suggestion in suggestions
        )

    def test_get_recovery_suggestions_backup_invalid(self):
        """Test getting recovery suggestions for invalid backups."""
        analysis = ErrorAnalysis(
            category=ErrorCategory.BACKUP_INVALID,
            confidence=0.9,
            description="Invalid backup",
            suggested_actions=["Base suggestion"],
            is_recoverable=True,
        )

        suggestions = self.analyzer.get_recovery_suggestions(analysis)

        assert "Base suggestion" in suggestions
        assert any(
            "recreate" in suggestion.lower() and "backup" in suggestion.lower()
            for suggestion in suggestions
        )
        assert any(
            "backup file integrity" in suggestion.lower() for suggestion in suggestions
        )
        assert any(
            "backup file permissions" in suggestion.lower()
            for suggestion in suggestions
        )

    def test_error_pattern_matching_case_insensitive(self):
        """Test that error pattern matching is case insensitive."""
        result = RestoreResult.failure_result(
            strategy="ForceReinstall",
            error_message="CONNECTION TIMED OUT WHILE DOWNLOADING",
            duration=30.0,
            packages_failed=["requests"],
        )

        analysis = self.analyzer.analyze_error(result)

        assert analysis.category == ErrorCategory.NETWORK_ERROR
        assert analysis.confidence == 0.9

    def test_multiple_error_patterns_highest_confidence(self):
        """Test that the highest confidence error category is selected."""
        # This error message could match both network and system error patterns
        result = RestoreResult.failure_result(
            strategy="ForceReinstall",
            error_message="OSError: Connection refused - network unreachable",
            duration=5.0,
            packages_failed=["requests"],
        )

        analysis = self.analyzer.analyze_error(result)

        # Network error should have higher confidence than system error
        assert analysis.category == ErrorCategory.NETWORK_ERROR
        assert analysis.confidence >= 0.8

    def test_empty_error_message(self):
        """Test handling of empty error messages."""
        result = RestoreResult.failure_result(
            strategy="ForceReinstall",
            error_message="",
            duration=1.0,
            packages_failed=["some-package"],
        )

        analysis = self.analyzer.analyze_error(result)

        assert analysis.category == ErrorCategory.UNKNOWN_ERROR
        assert analysis.confidence == 0.1
        assert analysis.is_recoverable is True
