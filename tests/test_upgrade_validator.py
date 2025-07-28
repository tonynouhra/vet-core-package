"""
Tests for the upgrade validation system.
"""

import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from vet_core.security.models import Vulnerability, VulnerabilitySeverity
from vet_core.security.upgrade_validator import (
    DependencyConflictError,
    EnvironmentBackup,
    TestFailureError,
    UpgradeResult,
    UpgradeValidator,
    validate_vulnerability_fixes,
)


class TestUpgradeResult:
    """Test UpgradeResult data model."""

    def test_success_result_creation(self):
        """Test creating a successful upgrade result."""
        result = UpgradeResult.success_result(
            package_name="test-package",
            from_version="1.0.0",
            to_version="1.1.0",
            test_results={"success": True, "test_count": 10},
            validation_duration=30.5,
        )

        assert result.package_name == "test-package"
        assert result.from_version == "1.0.0"
        assert result.to_version == "1.1.0"
        assert result.success is True
        assert result.error_message == ""
        assert result.test_results == {"success": True, "test_count": 10}
        assert result.validation_duration == 30.5
        assert result.rollback_performed is False

    def test_failure_result_creation(self):
        """Test creating a failed upgrade result."""
        result = UpgradeResult.failure_result(
            package_name="test-package",
            from_version="1.0.0",
            to_version="1.1.0",
            error_message="Tests failed",
            compatibility_issues=["Conflict with package X"],
            rollback_performed=True,
            validation_duration=45.2,
        )

        assert result.package_name == "test-package"
        assert result.from_version == "1.0.0"
        assert result.to_version == "1.1.0"
        assert result.success is False
        assert result.error_message == "Tests failed"
        assert result.compatibility_issues == ["Conflict with package X"]
        assert result.rollback_performed is True
        assert result.validation_duration == 45.2


class TestEnvironmentBackup:
    """Test EnvironmentBackup functionality."""

    def test_environment_backup_creation(self):
        """Test creating an environment backup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir) / "backup"
            requirements_file = backup_path / "requirements.txt"
            backup_path.mkdir()
            requirements_file.write_text("test-package==1.0.0\n")

            backup = EnvironmentBackup(
                backup_path=backup_path, requirements_file=requirements_file
            )

            assert backup.backup_path == backup_path
            assert backup.requirements_file == requirements_file
            assert backup.pyproject_backup is None
            assert isinstance(backup.created_at, datetime)

    def test_environment_backup_cleanup(self):
        """Test cleaning up environment backup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir) / "backup"
            requirements_file = backup_path / "requirements.txt"
            backup_path.mkdir()
            requirements_file.write_text("test-package==1.0.0\n")

            backup = EnvironmentBackup(
                backup_path=backup_path, requirements_file=requirements_file
            )

            # Verify files exist
            assert backup_path.exists()
            assert requirements_file.exists()

            # Cleanup
            backup.cleanup()

            # Verify files are removed
            assert not backup_path.exists()
            assert not requirements_file.exists()


class TestUpgradeValidator:
    """Test UpgradeValidator functionality."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory for testing."""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)

        # Create a minimal pyproject.toml
        pyproject_content = """
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "test-project"
version = "0.1.0"
dependencies = ["requests>=2.0.0"]
"""
        (project_path / "pyproject.toml").write_text(pyproject_content)

        # Create a simple test file
        test_dir = project_path / "tests"
        test_dir.mkdir()
        (test_dir / "__init__.py").write_text("")
        (test_dir / "test_simple.py").write_text(
            """
def test_simple():
    assert True

def test_another():
    assert 1 + 1 == 2
"""
        )

        yield project_path

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_validator_initialization(self, temp_project):
        """Test UpgradeValidator initialization."""
        validator = UpgradeValidator(temp_project, "pytest")

        assert validator.project_root == temp_project
        assert validator.test_command == "pytest"
        assert validator.pyproject_path == temp_project / "pyproject.toml"
        assert validator.temp_dir.exists()

        validator.cleanup()
        assert not validator.temp_dir.exists()

    def test_context_manager(self, temp_project):
        """Test UpgradeValidator as context manager."""
        temp_dir = None

        with UpgradeValidator(temp_project) as validator:
            temp_dir = validator.temp_dir
            assert temp_dir.exists()

        # Should be cleaned up after context exit
        assert not temp_dir.exists()

    @patch("vet_core.security.upgrade_validator.secure_subprocess_run")
    def test_create_environment_backup(self, mock_run, temp_project):
        """Test creating environment backup."""
        # Mock pip freeze output
        mock_run.return_value = Mock(
            returncode=0, stdout="test-package==1.0.0\nrequests==2.28.0\n"
        )

        with UpgradeValidator(temp_project) as validator:
            backup = validator.create_environment_backup()

            assert backup.backup_path.exists()
            assert backup.requirements_file.exists()
            assert (
                backup.pyproject_backup.exists()
            )  # pyproject.toml should be backed up

            # Check requirements content
            requirements_content = backup.requirements_file.read_text()
            assert "test-package==1.0.0" in requirements_content
            assert "requests==2.28.0" in requirements_content

            # Verify pip freeze was called with correct parameters
            mock_run.assert_called()
            call_args = mock_run.call_args
            assert call_args[0][0] == [sys.executable, "-m", "pip", "freeze"]
            # Check that the function was called with the expected kwargs
            assert call_args[1]["validate_first_arg"] is False
            assert call_args[1]["check"] is True

    @patch("vet_core.security.upgrade_validator.secure_subprocess_run")
    def test_restore_environment(self, mock_run, temp_project):
        """Test restoring environment from backup."""
        # Mock pip freeze for backup creation
        mock_run.return_value = Mock(returncode=0, stdout="test-package==1.0.0\n")

        with UpgradeValidator(temp_project) as validator:
            backup = validator.create_environment_backup()

            # Mock pip install for restoration
            mock_run.return_value = Mock(returncode=0)

            result = validator.restore_environment(backup)

            assert result is True

            # Verify pip install was called with requirements file
            install_call = None
            for call in mock_run.call_args_list:
                if "install" in call[0][0]:
                    install_call = call
                    break

            assert install_call is not None
            args = install_call[0][0]
            assert "pip" in args
            assert "install" in args
            assert "-r" in args
            assert str(backup.requirements_file) in args

    @patch("vet_core.security.upgrade_validator.secure_subprocess_run")
    def test_check_dependency_conflicts(self, mock_run, temp_project):
        """Test checking for dependency conflicts."""
        with UpgradeValidator(temp_project) as validator:
            # Mock successful dry-run and pip check
            mock_run.side_effect = [
                Mock(returncode=0),  # pip install --dry-run
                Mock(returncode=0),  # pip check
            ]

            conflicts = validator.check_dependency_conflicts("test-package", "2.0.0")

            assert conflicts == []
            assert mock_run.call_count == 2

    @patch("vet_core.security.upgrade_validator.secure_subprocess_run")
    def test_check_dependency_conflicts_with_issues(self, mock_run, temp_project):
        """Test checking for dependency conflicts when issues exist."""
        with UpgradeValidator(temp_project) as validator:
            # Mock failed dry-run
            mock_run.side_effect = [
                Mock(
                    returncode=1, stderr="Could not find a version"
                ),  # pip install --dry-run
                Mock(
                    returncode=1, stdout="package-x has requirement y>1.0"
                ),  # pip check
            ]

            conflicts = validator.check_dependency_conflicts("test-package", "2.0.0")

            assert len(conflicts) == 2
            assert "Could not find a version" in conflicts[0]
            assert "package-x has requirement y>1.0" in conflicts[1]

    @patch("vet_core.security.upgrade_validator.secure_subprocess_run")
    @patch("os.chdir")
    def test_run_tests_success(self, mock_chdir, mock_run, temp_project):
        """Test running tests successfully."""
        with UpgradeValidator(temp_project) as validator:
            # Mock successful test run
            mock_run.return_value = Mock(
                returncode=0, stdout="= 5 passed in 2.34s =", stderr=""
            )

            result = validator.run_tests()

            assert result["success"] is True
            assert result["exit_code"] == 0
            assert result["test_count"] == 5
            assert result["failures"] == 0
            assert result["errors"] == 0
            assert result["duration"] > 0

    @patch("vet_core.security.upgrade_validator.secure_subprocess_run")
    @patch("os.chdir")
    def test_run_tests_failure(self, mock_chdir, mock_run, temp_project):
        """Test running tests with failures."""
        with UpgradeValidator(temp_project) as validator:
            # Mock failed test run
            mock_run.return_value = Mock(
                returncode=1,
                stdout="= 3 passed, 2 failed, 1 error in 5.67s =",
                stderr="Test errors occurred",
            )

            result = validator.run_tests()

            assert result["success"] is False
            assert result["exit_code"] == 1
            assert result["test_count"] == 3
            assert result["failures"] == 2
            assert result["errors"] == 1
            assert "Test errors occurred" in result["stderr"]

    @patch("vet_core.security.upgrade_validator.secure_subprocess_run")
    def test_validate_upgrade_success(self, mock_run, temp_project):
        """Test successful upgrade validation."""
        with UpgradeValidator(temp_project) as validator:
            # Mock pip show (current version)
            # Mock pip freeze (for backup)
            # Mock pip install (upgrade)
            # Mock test run
            mock_run.side_effect = [
                Mock(returncode=0, stdout="Version: 1.0.0\n"),  # pip show
                Mock(returncode=0),  # pip install --dry-run
                Mock(returncode=0),  # pip check
                Mock(
                    returncode=0, stdout="test-package==1.0.0\n"
                ),  # pip freeze (backup)
                Mock(returncode=0),  # pip install (upgrade)
                Mock(returncode=0, stdout="= 5 passed in 2.34s =", stderr=""),  # tests
            ]

            result = validator.validate_upgrade("test-package", "2.0.0")

            assert result.success is True
            assert result.package_name == "test-package"
            assert result.from_version == "1.0.0"
            assert result.to_version == "2.0.0"
            assert result.test_results["success"] is True
            assert result.rollback_performed is False

    @patch("vet_core.security.upgrade_validator.secure_subprocess_run")
    def test_validate_upgrade_test_failure_with_rollback(self, mock_run, temp_project):
        """Test upgrade validation with test failure and rollback."""
        with UpgradeValidator(temp_project) as validator:
            # Mock successful upgrade but failed tests
            mock_run.side_effect = [
                Mock(returncode=0, stdout="Version: 1.0.0\n"),  # pip show
                Mock(returncode=0),  # pip install --dry-run
                Mock(returncode=0),  # pip check
                Mock(
                    returncode=0, stdout="test-package==1.0.0\n"
                ),  # pip freeze (backup)
                Mock(returncode=0),  # pip install (upgrade)
                Mock(
                    returncode=1, stdout="= 3 passed, 2 failed =", stderr="Tests failed"
                ),  # tests
                Mock(returncode=0),  # pip install (rollback)
            ]

            result = validator.validate_upgrade("test-package", "2.0.0")

            assert result.success is False
            assert result.error_message == "Tests failed after upgrade"
            assert result.rollback_performed is True

    @patch("vet_core.security.upgrade_validator.secure_subprocess_run")
    def test_validate_upgrade_dependency_conflicts(self, mock_run, temp_project):
        """Test upgrade validation with dependency conflicts."""
        with UpgradeValidator(temp_project) as validator:
            # Mock dependency conflict
            mock_run.side_effect = [
                Mock(returncode=0, stdout="Version: 1.0.0\n"),  # pip show
                Mock(
                    returncode=1, stderr="Could not find version"
                ),  # pip install --dry-run (conflict)
            ]

            result = validator.validate_upgrade("test-package", "2.0.0")

            assert result.success is False
            assert result.error_message == "Dependency conflicts detected"
            assert len(result.compatibility_issues) > 0

    @patch("vet_core.security.upgrade_validator.secure_subprocess_run")
    def test_validate_multiple_upgrades_success(self, mock_run, temp_project):
        """Test validating multiple upgrades successfully."""
        with UpgradeValidator(temp_project) as validator:
            # Mock all operations as successful
            mock_run.side_effect = [
                # Backup creation
                Mock(returncode=0, stdout="pkg1==1.0.0\npkg2==1.0.0\n"),
                # First package validation
                Mock(returncode=0, stdout="Version: 1.0.0\n"),  # pip show pkg1
                Mock(returncode=0),  # pip install --dry-run pkg1
                Mock(returncode=0),  # pip check
                Mock(returncode=0, stdout="pkg1==1.0.0\n"),  # pip freeze (backup)
                Mock(returncode=0),  # pip install pkg1==2.0.0
                Mock(returncode=0, stdout="= 5 passed =", stderr=""),  # tests
                # Second package validation
                Mock(returncode=0, stdout="Version: 1.0.0\n"),  # pip show pkg2
                Mock(returncode=0),  # pip install --dry-run pkg2
                Mock(returncode=0),  # pip check
                Mock(returncode=0, stdout="pkg2==1.0.0\n"),  # pip freeze (backup)
                Mock(returncode=0),  # pip install pkg2==2.0.0
                Mock(returncode=0, stdout="= 5 passed =", stderr=""),  # tests
            ]

            upgrades = [("pkg1", "2.0.0"), ("pkg2", "2.0.0")]
            results = validator.validate_multiple_upgrades(upgrades)

            assert len(results) == 2
            assert all(r.success for r in results)

    @patch("vet_core.security.upgrade_validator.secure_subprocess_run")
    def test_validate_multiple_upgrades_with_failure(self, mock_run, temp_project):
        """Test validating multiple upgrades with one failure."""
        with UpgradeValidator(temp_project) as validator:
            # Mock first upgrade success, second upgrade failure
            mock_run.side_effect = [
                # Backup creation
                Mock(returncode=0, stdout="pkg1==1.0.0\npkg2==1.0.0\n"),
                # First package validation (success)
                Mock(returncode=0, stdout="Version: 1.0.0\n"),  # pip show pkg1
                Mock(returncode=0),  # pip install --dry-run pkg1
                Mock(returncode=0),  # pip check
                Mock(returncode=0, stdout="pkg1==1.0.0\n"),  # pip freeze (backup)
                Mock(returncode=0),  # pip install pkg1==2.0.0
                Mock(returncode=0, stdout="= 5 passed =", stderr=""),  # tests
                # Second package validation (failure)
                Mock(returncode=0, stdout="Version: 1.0.0\n"),  # pip show pkg2
                Mock(
                    returncode=1, stderr="Could not install"
                ),  # pip install --dry-run pkg2 (conflict)
                # Rollback
                Mock(returncode=0),  # pip install (rollback)
            ]

            upgrades = [("pkg1", "2.0.0"), ("pkg2", "2.0.0")]
            results = validator.validate_multiple_upgrades(upgrades)

            assert len(results) == 2
            assert results[0].success is True
            assert results[1].success is False
            assert results[1].rollback_performed is True


def test_validate_vulnerability_fixes():
    """Test validating fixes for vulnerabilities."""
    vulnerabilities = [
        Vulnerability(
            id="VULN-001",
            package_name="package1",
            installed_version="1.0.0",
            fix_versions=["1.1.0", "1.2.0"],
            severity=VulnerabilitySeverity.HIGH,
        ),
        Vulnerability(
            id="VULN-002",
            package_name="package2",
            installed_version="2.0.0",
            fix_versions=["2.1.0"],
            severity=VulnerabilitySeverity.MEDIUM,
        ),
        Vulnerability(
            id="VULN-003",
            package_name="package1",  # Same package as VULN-001
            installed_version="1.0.0",
            fix_versions=["1.1.5"],  # Higher version than VULN-001
            severity=VulnerabilitySeverity.LOW,
        ),
        Vulnerability(
            id="VULN-004",
            package_name="unfixable",
            installed_version="1.0.0",
            fix_versions=[],  # No fix available
            severity=VulnerabilitySeverity.HIGH,
        ),
    ]

    with patch(
        "vet_core.security.upgrade_validator.UpgradeValidator"
    ) as mock_validator_class:
        mock_validator = Mock()
        mock_validator_class.return_value.__enter__.return_value = mock_validator

        # Mock successful validation results
        mock_validator.validate_multiple_upgrades.return_value = [
            UpgradeResult.success_result(
                "package1", "1.0.0", "1.2.0"
            ),  # Higher version chosen
            UpgradeResult.success_result("package2", "2.0.0", "2.1.0"),
        ]

        results = validate_vulnerability_fixes(vulnerabilities)

        # Should only validate 2 packages (package1 and package2)
        # unfixable package should be skipped
        # package1 should use version 1.2.0 (higher than both 1.1.0 and 1.1.5)
        assert len(results) == 2

        # Verify the upgrades passed to validator
        call_args = mock_validator.validate_multiple_upgrades.call_args[0][0]
        assert len(call_args) == 2

        # Check that package1 uses the highest version (1.2.0 > 1.1.5)
        package1_upgrade = next((u for u in call_args if u[0] == "package1"), None)
        assert package1_upgrade is not None
        assert package1_upgrade[1] == "1.2.0"

        package2_upgrade = next((u for u in call_args if u[0] == "package2"), None)
        assert package2_upgrade is not None
        assert package2_upgrade[1] == "2.1.0"


class TestIntegration:
    """Integration tests for the upgrade validation system."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_package_validation(self):
        """Test validation with a real package (if available)."""
        # This test requires a real Python environment
        # Skip if not in integration test mode
        pytest.skip("Integration test - requires real environment")

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create minimal project
            (project_path / "pyproject.toml").write_text(
                """
[project]
name = "test-project"
version = "0.1.0"
dependencies = []
"""
            )

            # Create simple test
            test_dir = project_path / "tests"
            test_dir.mkdir()
            (test_dir / "test_simple.py").write_text("def test_simple(): assert True")

            with UpgradeValidator(project_path) as validator:
                # Try to validate a common package upgrade
                result = validator.validate_upgrade(
                    package_name="pip",
                    target_version="23.0.0",  # Use a stable version
                    run_tests=True,
                    check_conflicts=True,
                )

                # Result should be valid (success or failure with proper error)
                assert isinstance(result, UpgradeResult)
                assert result.package_name == "pip"
                assert result.validation_duration > 0
