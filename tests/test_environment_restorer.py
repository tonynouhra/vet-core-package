"""
Tests for EnvironmentRestorer class.

This module tests the EnvironmentRestorer class which handles environment
restoration with strategy selection logic.
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from vet_core.security.upgrade_validator import (
    EnvironmentBackup,
    EnvironmentRestorer,
    RestoreLogger,
    RestoreResult,
    ValidationResult,
)


class TestRestoreLogger(unittest.TestCase):
    """Test the RestoreLogger class."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = RestoreLogger("test_logger")

    def test_initialization(self):
        """Test RestoreLogger initialization."""
        self.assertIsNotNone(self.logger.logger)
        self.assertIsNone(self.logger._operation_id)

    def test_start_operation(self):
        """Test starting a restoration operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text("package1==1.0.0")

            backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                package_count=1,
                created_at=datetime.now(),
            )

            with patch.object(self.logger.logger, "info") as mock_info:
                self.logger.start_operation("test-op-123", backup)

                self.assertEqual(self.logger._operation_id, "test-op-123")
                self.assertEqual(mock_info.call_count, 2)

                # Check that operation start was logged
                call_args = [call[0][0] for call in mock_info.call_args_list]
                self.assertTrue(
                    any(
                        "[test-op-123]" in arg
                        and "Starting environment restoration" in arg
                        for arg in call_args
                    )
                )
                self.assertTrue(
                    any(
                        "[test-op-123]" in arg and "Backup contains 1 packages" in arg
                        for arg in call_args
                    )
                )

    def test_log_strategy_attempt(self):
        """Test logging strategy attempts."""
        self.logger._operation_id = "test-op-456"

        with patch.object(self.logger.logger, "info") as mock_info:
            self.logger.log_strategy_attempt("ForceReinstall", "first attempt")

            mock_info.assert_called_once()
            call_arg = mock_info.call_args[0][0]
            self.assertIn("[test-op-456]", call_arg)
            self.assertIn("Attempting ForceReinstall strategy", call_arg)
            self.assertIn("first attempt", call_arg)

    def test_log_strategy_result_success(self):
        """Test logging successful strategy results."""
        self.logger._operation_id = "test-op-789"

        result = RestoreResult.success_result(
            strategy="ForceReinstall",
            packages_restored=5,
            duration=2.5,
            warnings=["Some warning"],
        )

        with (
            patch.object(self.logger.logger, "info") as mock_info,
            patch.object(self.logger.logger, "warning") as mock_warning,
        ):

            self.logger.log_strategy_result("ForceReinstall", result)

            mock_info.assert_called_once()
            call_arg = mock_info.call_args[0][0]
            self.assertIn("[test-op-789]", call_arg)
            self.assertIn("ForceReinstall strategy succeeded", call_arg)
            self.assertIn("5 packages restored", call_arg)
            self.assertIn("2.50s", call_arg)

            mock_warning.assert_called_once()
            warning_arg = mock_warning.call_args[0][0]
            self.assertIn("[test-op-789]", warning_arg)
            self.assertIn("Some warning", warning_arg)

    def test_log_strategy_result_failure(self):
        """Test logging failed strategy results."""
        self.logger._operation_id = "test-op-abc"

        result = RestoreResult.failure_result(
            strategy="CleanInstall",
            error_message="Installation failed",
            duration=1.0,
            packages_failed=["pkg1", "pkg2", "pkg3", "pkg4", "pkg5", "pkg6"],
        )

        with patch.object(self.logger.logger, "error") as mock_error:
            self.logger.log_strategy_result("CleanInstall", result)

            self.assertEqual(mock_error.call_count, 2)

            # Check error message logging
            error_calls = [call[0][0] for call in mock_error.call_args_list]
            self.assertTrue(
                any(
                    "[test-op-abc]" in arg and "CleanInstall strategy failed" in arg
                    for arg in error_calls
                )
            )
            self.assertTrue(
                any(
                    "[test-op-abc]" in arg
                    and "Failed packages: pkg1, pkg2, pkg3, pkg4, pkg5 and 1 more"
                    in arg
                    for arg in error_calls
                )
            )

    def test_log_final_result_success(self):
        """Test logging final successful result."""
        self.logger._operation_id = "test-op-final"

        result = RestoreResult.success_result(
            strategy="Fallback", packages_restored=3, duration=4.0
        )

        with patch.object(self.logger.logger, "info") as mock_info:
            self.logger.log_final_result(result)

            mock_info.assert_called_once()
            call_arg = mock_info.call_args[0][0]
            self.assertIn("[test-op-final]", call_arg)
            self.assertIn("Environment restoration completed successfully", call_arg)
            self.assertIn("Fallback strategy", call_arg)

    def test_log_final_result_failure(self):
        """Test logging final failed result."""
        self.logger._operation_id = "test-op-fail"

        result = RestoreResult.failure_result(
            strategy="AllStrategiesFailed",
            error_message="All strategies failed",
            duration=10.0,
        )

        with patch.object(self.logger.logger, "error") as mock_error:
            self.logger.log_final_result(result)

            mock_error.assert_called_once()
            call_arg = mock_error.call_args[0][0]
            self.assertIn("[test-op-fail]", call_arg)
            self.assertIn("Environment restoration failed", call_arg)
            self.assertIn("All strategies failed", call_arg)

    def test_log_validation_result_valid(self):
        """Test logging valid backup validation results."""
        self.logger._operation_id = "test-op-valid"

        validation_result = ValidationResult(
            is_valid=True, errors=[], warnings=["Minor warning"], metadata={}
        )

        with (
            patch.object(self.logger.logger, "info") as mock_info,
            patch.object(self.logger.logger, "warning") as mock_warning,
        ):

            self.logger.log_validation_result(validation_result)

            mock_info.assert_called_once()
            info_arg = mock_info.call_args[0][0]
            self.assertIn("[test-op-valid]", info_arg)
            self.assertIn("Backup validation passed", info_arg)

            mock_warning.assert_called_once()
            warning_arg = mock_warning.call_args[0][0]
            self.assertIn("[test-op-valid]", warning_arg)
            self.assertIn("Minor warning", warning_arg)

    def test_log_validation_result_invalid(self):
        """Test logging invalid backup validation results."""
        self.logger._operation_id = "test-op-invalid"

        validation_result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
            metadata={},
        )

        with (
            patch.object(self.logger.logger, "error") as mock_error,
            patch.object(self.logger.logger, "warning") as mock_warning,
        ):

            self.logger.log_validation_result(validation_result)

            self.assertEqual(mock_error.call_count, 3)  # 1 main + 2 errors
            error_calls = [call[0][0] for call in mock_error.call_args_list]
            self.assertTrue(
                any(
                    "[test-op-invalid]" in arg and "Backup validation failed" in arg
                    for arg in error_calls
                )
            )
            self.assertTrue(
                any(
                    "[test-op-invalid]" in arg and "Error 1" in arg
                    for arg in error_calls
                )
            )
            self.assertTrue(
                any(
                    "[test-op-invalid]" in arg and "Error 2" in arg
                    for arg in error_calls
                )
            )

            mock_warning.assert_called_once()
            warning_arg = mock_warning.call_args[0][0]
            self.assertIn("[test-op-invalid]", warning_arg)
            self.assertIn("Warning 1", warning_arg)


class TestEnvironmentRestorer(unittest.TestCase):
    """Test the EnvironmentRestorer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_logger = Mock(spec=RestoreLogger)
        self.restorer = EnvironmentRestorer(logger=self.mock_logger)

    def test_initialization(self):
        """Test EnvironmentRestorer initialization."""
        # Test with provided logger
        self.assertEqual(self.restorer.logger, self.mock_logger)
        self.assertIsNotNone(self.restorer.backup_validator)
        self.assertEqual(len(self.restorer.strategies), 3)

        # Test with default logger
        restorer_default = EnvironmentRestorer()
        self.assertIsInstance(restorer_default.logger, RestoreLogger)

    def test_strategy_order(self):
        """Test that strategies are in the correct order."""
        strategy_names = [
            strategy.__class__.__name__ for strategy in self.restorer.strategies
        ]
        expected_order = [
            "ForceReinstallStrategy",
            "CleanInstallStrategy",
            "FallbackStrategy",
        ]
        self.assertEqual(strategy_names, expected_order)

    @patch("uuid.uuid4")
    def test_restore_environment_validation_failure(self, mock_uuid):
        """Test restoration with backup validation failure."""
        mock_uuid.return_value.hex = "12345678"

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"

            backup = EnvironmentBackup(
                backup_path=backup_path, requirements_file=requirements_file
            )

            # Mock validation failure
            validation_result = ValidationResult(
                is_valid=False,
                errors=["Backup is invalid"],
                warnings=["Some warning"],
                metadata={},
            )

            with patch.object(
                self.restorer.backup_validator,
                "validate_backup",
                return_value=validation_result,
            ):
                result = self.restorer.restore_environment(backup)

                self.assertFalse(result.success)
                self.assertEqual(result.strategy_used, "ValidationFailed")
                self.assertIn("Backup validation failed", result.error_message)
                self.assertEqual(result.warnings, ["Some warning"])

                # Verify logging calls
                self.mock_logger.start_operation.assert_called_once()
                self.mock_logger.log_validation_result.assert_called_once_with(
                    validation_result
                )
                self.mock_logger.log_final_result.assert_called_once_with(result)

    @patch("uuid.uuid4")
    def test_restore_environment_success_first_strategy(self, mock_uuid):
        """Test successful restoration with first strategy."""
        mock_uuid.return_value.hex = "abcdefgh"

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text("package1==1.0.0")

            backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                package_count=1,
            )

            # Mock successful validation
            validation_result = ValidationResult(
                is_valid=True, errors=[], warnings=["Validation warning"], metadata={}
            )

            # Mock successful strategy result
            strategy_result = RestoreResult.success_result(
                strategy="ForceReinstall", packages_restored=1, duration=2.0
            )

            with (
                patch.object(
                    self.restorer.backup_validator,
                    "validate_backup",
                    return_value=validation_result,
                ),
                patch.object(
                    self.restorer.strategies[0], "can_handle", return_value=True
                ),
                patch.object(
                    self.restorer.strategies[0], "restore", return_value=strategy_result
                ),
            ):

                result = self.restorer.restore_environment(backup)

                self.assertTrue(result.success)
                self.assertEqual(result.strategy_used, "ForceReinstall")
                self.assertEqual(result.packages_restored, 1)
                self.assertIn("Validation warning", result.warnings)

                # Verify logging calls
                self.mock_logger.start_operation.assert_called_once()
                self.mock_logger.log_validation_result.assert_called_once()
                self.mock_logger.log_strategy_attempt.assert_called_once()
                self.mock_logger.log_strategy_result.assert_called_once()
                self.mock_logger.log_final_result.assert_called_once()

    @patch("uuid.uuid4")
    def test_restore_environment_fallback_to_second_strategy(self, mock_uuid):
        """Test restoration falling back to second strategy."""
        mock_uuid.return_value.hex = "fallback1"

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text("package1==1.0.0")

            backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                package_count=1,
            )

            # Mock successful validation
            validation_result = ValidationResult(
                is_valid=True, errors=[], warnings=[], metadata={}
            )

            # Mock first strategy failure, second strategy success
            first_failure = RestoreResult.failure_result(
                strategy="ForceReinstall",
                error_message="First strategy failed",
                duration=1.0,
            )

            second_success = RestoreResult.success_result(
                strategy="CleanInstall", packages_restored=1, duration=3.0
            )

            with (
                patch.object(
                    self.restorer.backup_validator,
                    "validate_backup",
                    return_value=validation_result,
                ),
                patch.object(
                    self.restorer.strategies[0], "can_handle", return_value=True
                ),
                patch.object(
                    self.restorer.strategies[0], "restore", return_value=first_failure
                ),
                patch.object(
                    self.restorer.strategies[1], "can_handle", return_value=True
                ),
                patch.object(
                    self.restorer.strategies[1], "restore", return_value=second_success
                ),
            ):

                result = self.restorer.restore_environment(backup)

                self.assertTrue(result.success)
                self.assertEqual(result.strategy_used, "CleanInstall")
                self.assertEqual(result.packages_restored, 1)

                # Verify both strategies were attempted
                self.assertEqual(self.mock_logger.log_strategy_attempt.call_count, 2)
                self.assertEqual(self.mock_logger.log_strategy_result.call_count, 2)

    @patch("uuid.uuid4")
    def test_restore_environment_all_strategies_fail(self, mock_uuid):
        """Test restoration when all strategies fail."""
        mock_uuid.return_value.hex = "allfail1"

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text("package1==1.0.0")

            backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                package_count=1,
            )

            # Mock successful validation
            validation_result = ValidationResult(
                is_valid=True, errors=[], warnings=[], metadata={}
            )

            # Mock all strategies failing
            failure_result = RestoreResult.failure_result(
                strategy="TestStrategy", error_message="Strategy failed", duration=1.0
            )

            with patch.object(
                self.restorer.backup_validator,
                "validate_backup",
                return_value=validation_result,
            ):
                # Mock all strategies to fail
                for strategy in self.restorer.strategies:
                    with (
                        patch.object(strategy, "can_handle", return_value=True),
                        patch.object(strategy, "restore", return_value=failure_result),
                    ):
                        pass

                # Need to patch all at once
                with (
                    patch.object(
                        self.restorer.strategies[0], "can_handle", return_value=True
                    ),
                    patch.object(
                        self.restorer.strategies[0],
                        "restore",
                        return_value=failure_result,
                    ),
                    patch.object(
                        self.restorer.strategies[1], "can_handle", return_value=True
                    ),
                    patch.object(
                        self.restorer.strategies[1],
                        "restore",
                        return_value=failure_result,
                    ),
                    patch.object(
                        self.restorer.strategies[2], "can_handle", return_value=True
                    ),
                    patch.object(
                        self.restorer.strategies[2],
                        "restore",
                        return_value=failure_result,
                    ),
                ):

                    result = self.restorer.restore_environment(backup)

                    self.assertFalse(result.success)
                    self.assertEqual(result.strategy_used, "AllStrategiesFailed")
                    self.assertIn(
                        "All restoration strategies failed", result.error_message
                    )

                    # Verify all strategies were attempted
                    self.assertEqual(
                        self.mock_logger.log_strategy_attempt.call_count, 3
                    )
                    self.assertEqual(self.mock_logger.log_strategy_result.call_count, 3)

    def test_try_restore_strategy_success(self):
        """Test _try_restore_strategy with successful strategy."""
        mock_strategy = Mock()
        success_result = RestoreResult.success_result(
            strategy="TestStrategy", packages_restored=2, duration=1.5
        )
        mock_strategy.restore.return_value = success_result

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"

            backup = EnvironmentBackup(
                backup_path=backup_path, requirements_file=requirements_file
            )

            result = self.restorer._try_restore_strategy(mock_strategy, backup)

            self.assertEqual(result, success_result)
            mock_strategy.restore.assert_called_once_with(backup)

    def test_try_restore_strategy_exception(self):
        """Test _try_restore_strategy with strategy raising exception."""
        mock_strategy = Mock()
        mock_strategy.__class__.__name__ = "TestStrategy"
        mock_strategy.restore.side_effect = Exception("Strategy crashed")

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"

            backup = EnvironmentBackup(
                backup_path=backup_path, requirements_file=requirements_file
            )

            result = self.restorer._try_restore_strategy(mock_strategy, backup)

            self.assertFalse(result.success)
            self.assertEqual(result.strategy_used, "Test")
            self.assertIn("Unexpected error in Test strategy", result.error_message)
            self.assertIn("Strategy crashed", result.error_message)

            # Verify error was logged
            self.mock_logger.error.assert_called_once()

    def test_get_strategy_selection_reason(self):
        """Test _get_strategy_selection_reason method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"

            # Test ForceReinstallStrategy reasons
            empty_backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                is_empty_environment=True,
                package_count=0,
            )

            small_backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                is_empty_environment=False,
                package_count=5,
            )

            large_backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                is_empty_environment=False,
                package_count=50,
            )

            force_strategy = self.restorer.strategies[0]  # ForceReinstallStrategy
            clean_strategy = self.restorer.strategies[1]  # CleanInstallStrategy
            fallback_strategy = self.restorer.strategies[2]  # FallbackStrategy

            # Test ForceReinstallStrategy reasons
            reason = self.restorer._get_strategy_selection_reason(
                force_strategy, empty_backup, None
            )
            self.assertIn("empty environment", reason)

            reason = self.restorer._get_strategy_selection_reason(
                force_strategy, small_backup, None
            )
            self.assertIn("small environment", reason)

            reason = self.restorer._get_strategy_selection_reason(
                force_strategy, large_backup, None
            )
            self.assertIn("first attempt", reason)

            # Test CleanInstallStrategy reasons
            last_result = RestoreResult.failure_result("ForceReinstall", "Failed", 1.0)
            reason = self.restorer._get_strategy_selection_reason(
                clean_strategy, large_backup, last_result
            )
            self.assertIn("fallback after ForceReinstall failed", reason)

            reason = self.restorer._get_strategy_selection_reason(
                clean_strategy, large_backup, None
            )
            self.assertIn("clean slate approach", reason)

            # Test FallbackStrategy reasons
            reason = self.restorer._get_strategy_selection_reason(
                fallback_strategy, large_backup, last_result
            )
            self.assertIn("last resort after ForceReinstall failed", reason)

            reason = self.restorer._get_strategy_selection_reason(
                fallback_strategy, large_backup, None
            )
            self.assertIn("fallback strategy for edge cases", reason)


if __name__ == "__main__":
    unittest.main()
