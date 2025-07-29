"""
Tests for environment restoration strategies.

This module tests the different strategies for restoring Python environments
from backups, including edge cases and error scenarios.
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from vet_core.security.restore_strategies import (
    CleanInstallStrategy,
    FallbackStrategy,
    ForceReinstallStrategy,
    RestoreStrategy,
)
from vet_core.security.upgrade_validator import EnvironmentBackup, RestoreResult


class TestRestoreStrategy(unittest.TestCase):
    """Test the abstract RestoreStrategy base class."""

    def test_abstract_methods(self):
        """Test that RestoreStrategy cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            RestoreStrategy()

    def test_get_packages_from_backup(self):
        """Test the _get_packages_from_backup helper method."""
        # Create a concrete strategy for testing
        strategy = ForceReinstallStrategy()

        # Create temporary backup with requirements
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text(
                "package1==1.0.0\npackage2>=2.0.0\n# comment\n\npackage3~=3.0.0"
            )

            backup = EnvironmentBackup(
                backup_path=backup_path, requirements_file=requirements_file
            )

            packages = strategy._get_packages_from_backup(backup)

            expected_packages = [
                "package1==1.0.0",
                "package2>=2.0.0",
                "package3~=3.0.0",
            ]
            self.assertEqual(packages, expected_packages)

    def test_get_packages_from_backup_empty_file(self):
        """Test _get_packages_from_backup with empty requirements file."""
        strategy = ForceReinstallStrategy()

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text("")

            backup = EnvironmentBackup(
                backup_path=backup_path, requirements_file=requirements_file
            )

            packages = strategy._get_packages_from_backup(backup)
            self.assertEqual(packages, [])

    def test_get_packages_from_backup_missing_file(self):
        """Test _get_packages_from_backup with missing requirements file."""
        strategy = ForceReinstallStrategy()

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "nonexistent.txt"

            backup = EnvironmentBackup(
                backup_path=backup_path, requirements_file=requirements_file
            )

            packages = strategy._get_packages_from_backup(backup)
            self.assertEqual(packages, [])


class TestForceReinstallStrategy(unittest.TestCase):
    """Test the ForceReinstallStrategy implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.strategy = ForceReinstallStrategy()

    def test_can_handle_valid_backup(self):
        """Test can_handle with a valid backup."""
        backup = Mock(spec=EnvironmentBackup)
        backup.is_valid.return_value = True

        result = self.strategy.can_handle(backup)
        self.assertTrue(result)
        backup.is_valid.assert_called_once()

    def test_can_handle_invalid_backup(self):
        """Test can_handle with an invalid backup."""
        backup = Mock(spec=EnvironmentBackup)
        backup.is_valid.return_value = False

        result = self.strategy.can_handle(backup)
        self.assertFalse(result)
        backup.is_valid.assert_called_once()

    @patch("vet_core.security.restore_strategies.secure_subprocess_run")
    def test_restore_success(self, mock_subprocess):
        """Test successful restoration."""
        # Setup mock subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Create temporary backup
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text("package1==1.0.0\npackage2==2.0.0")

            backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                package_count=2,
                is_empty_environment=False,
            )

            # Mock backup validation
            with patch.object(backup, "is_valid", return_value=True):
                result = self.strategy.restore(backup)

            # Verify result
            self.assertIsInstance(result, RestoreResult)
            self.assertTrue(result.success)
            self.assertEqual(result.strategy_used, "ForceReinstall")
            self.assertEqual(result.packages_restored, 2)
            self.assertIsNone(result.error_message)

            # Verify subprocess was called correctly (multiple times for pre-check, install, post-check)
            self.assertEqual(mock_subprocess.call_count, 3)

            # Find the main installation call
            install_call = None
            for call in mock_subprocess.call_args_list:
                call_args = call[0][0]
                if "--force-reinstall" in call_args:
                    install_call = call_args
                    break

            self.assertIsNotNone(
                install_call, "Installation call with --force-reinstall not found"
            )
            self.assertIn("--force-reinstall", install_call)
            self.assertIn("--no-deps", install_call)
            self.assertIn("-r", install_call)

    @patch("vet_core.security.restore_strategies.secure_subprocess_run")
    def test_restore_failure(self, mock_subprocess):
        """Test restoration failure."""
        # Setup mock subprocess result
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Installation failed"
        mock_subprocess.return_value = mock_result

        # Create temporary backup
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text("package1==1.0.0")

            backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                package_count=1,
                is_empty_environment=False,
            )

            # Mock backup validation
            with patch.object(backup, "is_valid", return_value=True):
                result = self.strategy.restore(backup)

            # Verify result
            self.assertIsInstance(result, RestoreResult)
            self.assertFalse(result.success)
            self.assertEqual(result.strategy_used, "ForceReinstall")
            self.assertEqual(result.packages_restored, 0)
            self.assertIn("Installation failed", result.error_message)
            self.assertEqual(result.packages_failed, ["package1==1.0.0"])

    def test_restore_empty_environment(self):
        """Test restoration of empty environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text("")

            backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                package_count=0,
                is_empty_environment=True,
            )

            # Mock backup validation
            with patch.object(backup, "is_valid", return_value=True):
                result = self.strategy.restore(backup)

            # Verify result
            self.assertTrue(result.success)
            self.assertEqual(result.packages_restored, 0)
            self.assertIn("no packages restored", result.warnings[0])

    def test_restore_invalid_backup(self):
        """Test restoration with invalid backup."""
        backup = Mock(spec=EnvironmentBackup)
        backup.is_valid.return_value = False

        result = self.strategy.restore(backup)

        self.assertFalse(result.success)
        self.assertEqual(result.strategy_used, "ForceReinstall")
        self.assertIn("Backup validation failed", result.error_message)


class TestCleanInstallStrategy(unittest.TestCase):
    """Test the CleanInstallStrategy implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.strategy = CleanInstallStrategy()

    def test_can_handle_valid_backup(self):
        """Test can_handle with a valid backup."""
        backup = Mock(spec=EnvironmentBackup)
        backup.is_valid.return_value = True

        result = self.strategy.can_handle(backup)
        self.assertTrue(result)

    @patch("vet_core.security.restore_strategies.secure_subprocess_run")
    def test_get_current_packages(self, mock_subprocess):
        """Test _get_current_packages method."""
        # Setup mock subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "package1==1.0.0\npackage2==2.0.0\npip==21.0.0"
        mock_subprocess.return_value = mock_result

        packages = self.strategy._get_current_packages()

        expected_packages = ["package1", "package2", "pip"]
        self.assertEqual(packages, expected_packages)

        # Verify subprocess was called correctly
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        self.assertIn("pip", call_args)
        self.assertIn("list", call_args)
        self.assertIn("--format=freeze", call_args)

    @patch("vet_core.security.restore_strategies.secure_subprocess_run")
    def test_uninstall_packages(self, mock_subprocess):
        """Test _uninstall_packages method."""
        # Setup mock subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        packages = ["package1", "package2", "pip", "setuptools"]
        result = self.strategy._uninstall_packages(packages)

        self.assertTrue(result)

        # Verify subprocess was called correctly
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        self.assertIn("pip", call_args)
        self.assertIn("uninstall", call_args)
        self.assertIn("-y", call_args)
        # Should exclude system packages
        self.assertIn("package1", call_args)
        self.assertIn("package2", call_args)
        self.assertNotIn("pip", call_args[-2:])  # pip should be filtered out
        self.assertNotIn(
            "setuptools", call_args[-2:]
        )  # setuptools should be filtered out

    @patch("vet_core.security.restore_strategies.secure_subprocess_run")
    def test_restore_success(self, mock_subprocess):
        """Test successful clean install restoration."""

        # Setup mock subprocess results
        def subprocess_side_effect(*args, **kwargs):
            command = args[0]
            mock_result = Mock()
            mock_result.returncode = 0

            if "list" in command:
                mock_result.stdout = "old_package==1.0.0"
            elif "uninstall" in command:
                mock_result.stdout = "Successfully uninstalled old_package"
            elif "install" in command:
                mock_result.stdout = "Successfully installed package1 package2"

            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect

        # Create temporary backup
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text("package1==1.0.0\npackage2==2.0.0")

            backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                package_count=2,
                is_empty_environment=False,
            )

            # Mock backup validation
            with patch.object(backup, "is_valid", return_value=True):
                result = self.strategy.restore(backup)

            # Verify result
            self.assertTrue(result.success)
            self.assertEqual(result.strategy_used, "CleanInstall")
            self.assertEqual(result.packages_restored, 2)

            # Verify subprocess was called multiple times (list, uninstall, install)
            self.assertEqual(mock_subprocess.call_count, 3)

    def test_restore_empty_environment(self):
        """Test restoration to empty environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text("")

            backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                package_count=0,
                is_empty_environment=True,
            )

            with patch.object(backup, "is_valid", return_value=True), patch.object(
                self.strategy, "_get_current_packages", return_value=["package1"]
            ), patch.object(self.strategy, "_uninstall_packages", return_value=True):

                result = self.strategy.restore(backup)

            # Verify result
            self.assertTrue(result.success)
            self.assertEqual(result.packages_restored, 0)
            self.assertIn("empty state", result.warnings[-1])


class TestFallbackStrategy(unittest.TestCase):
    """Test the FallbackStrategy implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.strategy = FallbackStrategy()

    def test_can_handle_existing_backup_path(self):
        """Test can_handle with existing backup path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"

            backup = EnvironmentBackup(
                backup_path=backup_path, requirements_file=requirements_file
            )

            result = self.strategy.can_handle(backup)
            self.assertTrue(result)

    def test_can_handle_nonexistent_backup_path(self):
        """Test can_handle with nonexistent backup path."""
        backup_path = Path("/nonexistent/path")
        requirements_file = backup_path / "requirements.txt"

        backup = EnvironmentBackup(
            backup_path=backup_path, requirements_file=requirements_file
        )

        result = self.strategy.can_handle(backup)
        self.assertFalse(result)

    def test_restore_missing_backup_path(self):
        """Test restoration with missing backup path."""
        backup_path = Path("/nonexistent/path")
        requirements_file = backup_path / "requirements.txt"

        backup = EnvironmentBackup(
            backup_path=backup_path, requirements_file=requirements_file
        )

        result = self.strategy.restore(backup)

        self.assertFalse(result.success)
        self.assertEqual(result.strategy_used, "Fallback")
        self.assertIn("Backup path does not exist", result.error_message)

    def test_restore_missing_requirements_file(self):
        """Test restoration with missing requirements file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "nonexistent.txt"

            backup = EnvironmentBackup(
                backup_path=backup_path, requirements_file=requirements_file
            )

            result = self.strategy.restore(backup)

            self.assertFalse(result.success)
            self.assertIn("Requirements file does not exist", result.error_message)

    def test_restore_empty_environment(self):
        """Test restoration of empty environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text("")

            backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                package_count=0,
                is_empty_environment=True,
            )

            result = self.strategy.restore(backup)

            self.assertTrue(result.success)
            self.assertEqual(result.packages_restored, 0)
            self.assertIn("no packages to restore", result.warnings[0])

    @patch("vet_core.security.restore_strategies.secure_subprocess_run")
    def test_restore_standard_install_success(self, mock_subprocess):
        """Test successful restoration with standard pip install."""
        # Setup mock subprocess result for successful standard install
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text("package1==1.0.0\npackage2==2.0.0")

            backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                package_count=2,
                is_empty_environment=False,
            )

            result = self.strategy.restore(backup)

            self.assertTrue(result.success)
            self.assertEqual(result.strategy_used, "Fallback")
            self.assertEqual(result.packages_restored, 2)

            # Should only call subprocess once for standard install
            self.assertEqual(mock_subprocess.call_count, 1)
            call_args = mock_subprocess.call_args[0][0]
            self.assertIn("install", call_args)
            self.assertNotIn("--force-reinstall", call_args)  # Standard install first

    @patch("vet_core.security.restore_strategies.secure_subprocess_run")
    def test_restore_fallback_to_force_reinstall(self, mock_subprocess):
        """Test fallback to force reinstall when standard install fails."""

        # Setup mock subprocess results
        def subprocess_side_effect(*args, **kwargs):
            command = args[0]
            mock_result = Mock()

            if "--force-reinstall" in command:
                # Force reinstall succeeds
                mock_result.returncode = 0
            else:
                # Standard install fails
                mock_result.returncode = 1
                mock_result.stderr = "Standard install failed"

            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text("package1==1.0.0")

            backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                package_count=1,
                is_empty_environment=False,
            )

            result = self.strategy.restore(backup)

            self.assertTrue(result.success)
            self.assertEqual(result.packages_restored, 1)
            # Check that we have warnings about the fallback process
            warning_text = " ".join(result.warnings)
            self.assertIn("force reinstall succeeded", warning_text)

            # Should call subprocess twice (standard install, then force reinstall)
            self.assertEqual(mock_subprocess.call_count, 2)

    @patch("vet_core.security.restore_strategies.secure_subprocess_run")
    def test_restore_individual_package_fallback(self, mock_subprocess):
        """Test fallback to individual package installation."""

        # Setup mock subprocess results
        def subprocess_side_effect(*args, **kwargs):
            command = args[0]
            mock_result = Mock()

            if len(command) > 5 and command[5] == "package1==1.0.0":
                # Individual package install succeeds
                mock_result.returncode = 0
            else:
                # Batch installs fail
                mock_result.returncode = 1
                mock_result.stderr = "Batch install failed"

            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text("package1==1.0.0")

            backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                package_count=1,
                is_empty_environment=False,
            )

            result = self.strategy.restore(backup)

            self.assertTrue(result.success)
            self.assertEqual(result.packages_restored, 1)
            # Check that we have warnings about the partial success
            warning_text = " ".join(result.warnings)
            self.assertIn("Partial success", warning_text)

            # Should call subprocess 3 times (standard, force reinstall, individual)
            self.assertEqual(mock_subprocess.call_count, 3)

    @patch("vet_core.security.restore_strategies.secure_subprocess_run")
    def test_restore_complete_failure(self, mock_subprocess):
        """Test complete restoration failure."""
        # Setup mock subprocess result for all failures
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "All installations failed"
        mock_subprocess.return_value = mock_result

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir)
            requirements_file = backup_path / "requirements.txt"
            requirements_file.write_text("package1==1.0.0")

            backup = EnvironmentBackup(
                backup_path=backup_path,
                requirements_file=requirements_file,
                package_count=1,
                is_empty_environment=False,
            )

            result = self.strategy.restore(backup)

            self.assertFalse(result.success)
            self.assertEqual(result.strategy_used, "Fallback")
            self.assertIn(
                "All individual package installations failed", result.error_message
            )
            self.assertEqual(result.packages_failed, ["package1==1.0.0"])


if __name__ == "__main__":
    unittest.main()
