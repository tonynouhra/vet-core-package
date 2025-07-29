"""
Tests for RestoreLogger functionality.
"""

import logging
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vet_core.security.upgrade_validator import (
    EnvironmentBackup,
    RestoreLogger,
    RestoreResult,
    ValidationResult,
)


class TestRestoreLogger:
    """Test cases for RestoreLogger."""

    def setup_method(self):
        """Set up test fixtures."""
        self.logger = RestoreLogger("test_logger")

        # Create a temporary backup for testing
        self.temp_dir = Path(tempfile.mkdtemp())
        self.requirements_file = self.temp_dir / "requirements.txt"
        self.requirements_file.write_text("requests==2.28.0\nnumpy==1.21.0\n")

        self.backup = EnvironmentBackup(
            backup_path=self.temp_dir,
            requirements_file=self.requirements_file,
            package_count=2,
            is_empty_environment=False,
            backup_metadata={"python_version": "3.11", "platform": "linux"},
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_start_operation(self, caplog):
        """Test operation start logging."""
        with caplog.at_level(logging.INFO):
            self.logger.start_operation("test-op-123", self.backup)

        # Check that operation was logged
        assert "test-op-123" in caplog.text
        assert "Starting environment restoration" in caplog.text
        assert "2 packages" in caplog.text
        assert "empty_environment=False" in caplog.text

        # Check that operation context was set
        assert self.logger._operation_id == "test-op-123"
        assert self.logger._start_time is not None
        assert self.logger._operation_context["package_count"] == 2

    def test_start_operation_with_empty_environment(self, caplog):
        """Test operation start logging with empty environment."""
        empty_backup = EnvironmentBackup(
            backup_path=self.temp_dir,
            requirements_file=self.requirements_file,
            package_count=0,
            is_empty_environment=True,
        )

        with caplog.at_level(logging.INFO):
            self.logger.start_operation("empty-op", empty_backup)

        assert "empty_environment=True" in caplog.text
        assert "0 packages" in caplog.text

    def test_log_strategy_attempt(self, caplog):
        """Test strategy attempt logging."""
        self.logger._operation_id = "test-op"

        with caplog.at_level(logging.INFO):
            self.logger.log_strategy_attempt("ForceReinstall", "first attempt")

        assert "[test-op]" in caplog.text
        assert "Attempting ForceReinstall strategy" in caplog.text
        assert "first attempt" in caplog.text

    @patch("vet_core.security.upgrade_validator.secure_subprocess_run")
    def test_log_strategy_attempt_with_environment_check(self, mock_subprocess, caplog):
        """Test strategy attempt logging with environment state check."""
        # Mock successful pip list command
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "requests==2.28.0\nnumpy==1.21.0\n"
        mock_subprocess.return_value = mock_result

        self.logger._operation_id = "test-op"

        with caplog.at_level(logging.DEBUG):
            self.logger.log_strategy_attempt("ForceReinstall", "first attempt")

        # The mock should be called and we should see environment package count
        assert "Current environment has" in caplog.text
        assert "packages" in caplog.text

    def test_log_strategy_result_success(self, caplog):
        """Test successful strategy result logging."""
        self.logger._operation_id = "test-op"

        result = RestoreResult.success_result(
            strategy="ForceReinstall",
            packages_restored=5,
            duration=2.5,
            warnings=["Minor warning"],
        )

        with caplog.at_level(logging.INFO):
            self.logger.log_strategy_result("ForceReinstall", result)

        assert "[test-op]" in caplog.text
        assert "ForceReinstall strategy succeeded" in caplog.text
        assert "5 packages restored" in caplog.text
        assert "2.50s" in caplog.text
        assert "Minor warning" in caplog.text

    def test_log_strategy_result_failure(self, caplog):
        """Test failed strategy result logging."""
        self.logger._operation_id = "test-op"

        result = RestoreResult.failure_result(
            strategy="ForceReinstall",
            error_message="Network error",
            duration=1.0,
            packages_failed=[
                "requests",
                "numpy",
                "pandas",
                "scipy",
                "matplotlib",
                "seaborn",
            ],
        )

        with caplog.at_level(logging.ERROR):
            self.logger.log_strategy_result("ForceReinstall", result)

        assert "[test-op]" in caplog.text
        assert "ForceReinstall strategy failed" in caplog.text
        assert "Network error" in caplog.text
        assert "requests, numpy, pandas, scipy, matplotlib and 1 more" in caplog.text

    def test_log_final_result_success(self, caplog):
        """Test final success result logging."""
        self.logger._operation_id = "test-op"
        self.logger._start_time = time.time() - 5.0  # 5 seconds ago

        result = RestoreResult.success_result(
            strategy="ForceReinstall",
            packages_restored=3,
            duration=2.0,
            warnings=["Warning 1", "Warning 2"],
        )

        with caplog.at_level(logging.INFO):
            self.logger.log_final_result(result)

        assert "[test-op]" in caplog.text
        assert "Environment restoration completed successfully" in caplog.text
        assert "ForceReinstall strategy" in caplog.text
        assert "3 packages restored" in caplog.text
        assert "2 warnings" in caplog.text

    def test_log_final_result_failure(self, caplog):
        """Test final failure result logging."""
        self.logger._operation_id = "test-op"
        self.logger._start_time = time.time() - 3.0  # 3 seconds ago

        result = RestoreResult.failure_result(
            strategy="AllStrategiesFailed",
            error_message="All strategies exhausted",
            duration=2.5,
            packages_failed=["requests", "numpy"],
        )

        with caplog.at_level(logging.ERROR):
            self.logger.log_final_result(result)

        assert "[test-op]" in caplog.text
        assert "Environment restoration failed" in caplog.text
        assert "All strategies exhausted" in caplog.text
        assert "2 packages failed" in caplog.text

    def test_log_validation_result_success(self, caplog):
        """Test successful validation result logging."""
        self.logger._operation_id = "test-op"

        validation_result = ValidationResult(
            is_valid=True, warnings=["Minor issue"], metadata={"package_count": 5}
        )

        with caplog.at_level(logging.INFO):
            self.logger.log_validation_result(validation_result)

        assert "[test-op]" in caplog.text
        assert "Backup validation passed" in caplog.text
        assert "Minor issue" in caplog.text

    def test_log_validation_result_failure(self, caplog):
        """Test failed validation result logging."""
        self.logger._operation_id = "test-op"

        validation_result = ValidationResult(
            is_valid=False, errors=["Error 1", "Error 2"], warnings=["Warning 1"]
        )

        with caplog.at_level(
            logging.WARNING
        ):  # Changed to WARNING to capture warning messages
            self.logger.log_validation_result(validation_result)

        assert "[test-op]" in caplog.text
        assert "Backup validation failed" in caplog.text
        assert "Error 1" in caplog.text
        assert "Error 2" in caplog.text
        assert "Warning 1" in caplog.text

    def test_log_package_operation(self, caplog):
        """Test package operation logging."""
        self.logger._operation_id = "test-op"

        with caplog.at_level(logging.DEBUG):
            self.logger.log_package_operation(
                "install", "requests", True, "version 2.28.0"
            )

        assert "[test-op]" in caplog.text
        assert "Package install succeeded: requests" in caplog.text
        assert "version 2.28.0" in caplog.text

        with caplog.at_level(logging.WARNING):
            self.logger.log_package_operation(
                "uninstall", "numpy", False, "permission denied"
            )

        assert "Package uninstall failed: numpy" in caplog.text
        assert "permission denied" in caplog.text

    def test_log_environment_state(self, caplog):
        """Test environment state logging."""
        self.logger._operation_id = "test-op"

        with caplog.at_level(logging.DEBUG):
            self.logger.log_environment_state("pre-restoration", 10)

        assert "[test-op]" in caplog.text
        assert "Environment state: pre-restoration" in caplog.text
        assert "(10 packages)" in caplog.text

        with caplog.at_level(logging.DEBUG):
            self.logger.log_environment_state("post-cleanup")

        assert "Environment state: post-cleanup" in caplog.text

    def test_log_error_analysis(self, caplog):
        """Test error analysis logging."""
        from vet_core.security.error_analyzer import ErrorAnalysis, ErrorCategory

        self.logger._operation_id = "test-op"

        error_analysis = ErrorAnalysis(
            category=ErrorCategory.NETWORK_ERROR,
            confidence=0.9,
            description="Connection timeout",
            suggested_actions=["Check network", "Retry later", "Use cache"],
            affected_packages=["requests", "urllib3"],
            technical_details={"timeout": "30s"},
            is_recoverable=True,
        )

        with caplog.at_level(logging.INFO):  # Changed to INFO to capture all log levels
            self.logger.log_error_analysis(error_analysis)

        assert "[test-op]" in caplog.text
        assert "Error analysis: network_error" in caplog.text
        assert "confidence: 0.90" in caplog.text
        assert "Connection timeout" in caplog.text
        assert "Affected packages: requests, urllib3" in caplog.text
        assert "1. Check network" in caplog.text
        assert "2. Retry later" in caplog.text
        assert "3. Use cache" in caplog.text
        assert "Error is recoverable" in caplog.text

    def test_get_operation_summary(self):
        """Test operation summary generation."""
        self.logger._operation_id = "test-op"
        self.logger._start_time = time.time() - 2.0
        self.logger._operation_context = {"test": "data"}

        summary = self.logger.get_operation_summary()

        assert summary["operation_id"] == "test-op"
        assert summary["start_time"] is not None
        assert summary["duration"] is not None
        assert summary["duration"] > 1.0  # Should be around 2 seconds
        assert summary["context"]["test"] == "data"

    def test_operation_without_id(self, caplog):
        """Test logging operations without setting operation ID."""
        with caplog.at_level(logging.INFO):
            self.logger.log_strategy_attempt("ForceReinstall", "test")

        assert "[unknown]" in caplog.text
        assert "Attempting ForceReinstall strategy" in caplog.text

    def test_multiple_operations(self, caplog):
        """Test handling multiple operations with different IDs."""
        # Start first operation
        with caplog.at_level(logging.INFO):
            self.logger.start_operation("op-1", self.backup)
            self.logger.log_strategy_attempt("ForceReinstall", "first op")

        assert "[op-1]" in caplog.text

        # Start second operation (should replace the first)
        caplog.clear()
        with caplog.at_level(logging.INFO):
            self.logger.start_operation("op-2", self.backup)
            self.logger.log_strategy_attempt("CleanInstall", "second op")

        assert "[op-2]" in caplog.text
        assert "[op-1]" not in caplog.text
