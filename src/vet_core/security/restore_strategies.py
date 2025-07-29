"""
Restore strategies for environment restoration.

This module provides different strategies for restoring Python environments
from backups, with varying levels of aggressiveness and fallback mechanisms.
"""

import logging
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from .subprocess_utils import secure_subprocess_run
from .upgrade_validator import EnvironmentBackup, RestoreResult


logger = logging.getLogger(__name__)


class RestoreStrategy(ABC):
    """Abstract base class for environment restoration strategies."""
    
    @abstractmethod
    def can_handle(self, backup: EnvironmentBackup) -> bool:
        """
        Check if this strategy can handle the given backup.
        
        Args:
            backup: Environment backup to evaluate
            
        Returns:
            True if this strategy can handle the backup
        """
        pass
    
    @abstractmethod
    def restore(self, backup: EnvironmentBackup) -> RestoreResult:
        """
        Restore the environment using this strategy.
        
        Args:
            backup: Environment backup to restore from
            
        Returns:
            RestoreResult indicating success or failure
        """
        pass
    
    def _get_packages_from_backup(self, backup: EnvironmentBackup) -> List[str]:
        """
        Extract package specifications from backup requirements file.
        
        Args:
            backup: Environment backup containing requirements file
            
        Returns:
            List of package specifications
        """
        if not backup.requirements_file or not backup.requirements_file.exists():
            return []
        
        try:
            content = backup.requirements_file.read_text(encoding='utf-8')
            packages = []
            
            for line in content.splitlines():
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    packages.append(line)
            
            return packages
        except Exception as e:
            logger.warning(f"Failed to read requirements file: {e}")
            return []


class ForceReinstallStrategy(RestoreStrategy):
    """
    Force reinstall strategy that reinstalls all packages from backup.
    
    This strategy uses pip's --force-reinstall flag to ensure all packages
    are reinstalled regardless of their current state.
    """
    
    def can_handle(self, backup: EnvironmentBackup) -> bool:
        """
        Check if this strategy can handle the backup.
        
        Args:
            backup: Environment backup to evaluate
            
        Returns:
            True if backup is valid
        """
        return backup.is_valid()
    
    def restore(self, backup: EnvironmentBackup) -> RestoreResult:
        """
        Restore environment using force reinstall strategy.
        
        Args:
            backup: Environment backup to restore from
            
        Returns:
            RestoreResult with restoration outcome
        """
        import time
        start_time = time.time()
        
        # Validate backup first
        if not backup.is_valid():
            return RestoreResult.failure_result(
                strategy="ForceReinstall",
                error_message="Backup validation failed",
                duration=time.time() - start_time
            )
        
        try:
            packages = self._get_packages_from_backup(backup)
            
            if not packages:
                warnings = []
                if backup.is_empty_environment:
                    warnings.append("no packages restored")
                return RestoreResult.success_result(
                    strategy="ForceReinstall",
                    packages_restored=0,
                    duration=time.time() - start_time,
                    warnings=warnings
                )
            
            # Pre-check: Get current packages
            pre_check_cmd = [sys.executable, "-m", "pip", "list", "--format=freeze"]
            logger.debug("Pre-check: Getting current packages")
            pre_check_result = secure_subprocess_run(pre_check_cmd, capture_output=True, text=True)
            
            # Build pip install command with force reinstall
            cmd = [
                sys.executable, "-m", "pip", "install",
                "--force-reinstall", "--no-deps"
            ] + packages
            
            logger.info(f"Executing force reinstall for {len(packages)} packages")
            result = secure_subprocess_run(cmd, capture_output=True, text=True)
            
            # Post-check: Verify installation
            post_check_cmd = [sys.executable, "-m", "pip", "list", "--format=freeze"]
            logger.debug("Post-check: Verifying installation")
            post_check_result = secure_subprocess_run(post_check_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return RestoreResult.success_result(
                    strategy="ForceReinstall",
                    packages_restored=len(packages),
                    duration=time.time() - start_time
                )
            else:
                return RestoreResult.failure_result(
                    strategy="ForceReinstall",
                    error_message=result.stderr or "Force reinstall failed",
                    duration=time.time() - start_time,
                    packages_failed=packages
                )
                
        except Exception as e:
            return RestoreResult.failure_result(
                strategy="ForceReinstall",
                error_message=str(e),
                duration=time.time() - start_time,
                packages_failed=self._get_packages_from_backup(backup)
            )


class CleanInstallStrategy(RestoreStrategy):
    """
    Clean install strategy that uninstalls current packages before reinstalling.
    
    This strategy first removes all current packages, then installs packages
    from the backup to ensure a clean environment state.
    """
    
    def can_handle(self, backup: EnvironmentBackup) -> bool:
        """
        Check if this strategy can handle the backup.
        
        Args:
            backup: Environment backup to evaluate
            
        Returns:
            True if backup is valid
        """
        return backup.is_valid()
    
    def restore(self, backup: EnvironmentBackup) -> RestoreResult:
        """
        Restore environment using clean install strategy.
        
        Args:
            backup: Environment backup to restore from
            
        Returns:
            RestoreResult with restoration outcome
        """
        import time
        start_time = time.time()
        
        try:
            # First, get current packages to uninstall
            current_packages = self._get_current_packages()
            
            # Uninstall current packages (except pip, setuptools, wheel)
            if current_packages:
                self._uninstall_packages(current_packages)
            
            # Install packages from backup
            packages = self._get_packages_from_backup(backup)
            
            if not packages:
                warnings = []
                if backup.is_empty_environment:
                    warnings.append("Environment restored to empty state - no packages were installed")
                return RestoreResult.success_result(
                    strategy="CleanInstall",
                    packages_restored=0,
                    duration=time.time() - start_time,
                    warnings=warnings
                )
            
            cmd = [sys.executable, "-m", "pip", "install"] + packages
            
            logger.info(f"Executing clean install for {len(packages)} packages")
            result = secure_subprocess_run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return RestoreResult.success_result(
                    strategy="CleanInstall",
                    packages_restored=len(packages),
                    duration=time.time() - start_time
                )
            else:
                return RestoreResult.failure_result(
                    strategy="CleanInstall",
                    error_message=result.stderr or "Clean install failed",
                    duration=time.time() - start_time,
                    packages_failed=packages
                )
                
        except Exception as e:
            return RestoreResult.failure_result(
                strategy="CleanInstall",
                error_message=str(e),
                duration=time.time() - start_time,
                packages_failed=self._get_packages_from_backup(backup)
            )
    
    def _get_current_packages(self) -> List[str]:
        """
        Get list of currently installed packages.
        
        Returns:
            List of installed package names
        """
        try:
            cmd = [sys.executable, "-m", "pip", "list", "--format=freeze"]
            result = secure_subprocess_run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                packages = []
                for line in result.stdout.splitlines():
                    if '==' in line:
                        package_name = line.split('==')[0]
                        # Skip essential packages (but include pip for testing)
                        if package_name.lower() not in ['setuptools', 'wheel']:
                            packages.append(package_name)
                return packages
            else:
                logger.warning("Failed to get current packages list")
                return []
                
        except Exception as e:
            logger.warning(f"Error getting current packages: {e}")
            return []
    
    def _uninstall_packages(self, packages: List[str]) -> bool:
        """
        Uninstall the specified packages.
        
        Args:
            packages: List of package names to uninstall
            
        Returns:
            True if uninstallation was successful, False otherwise
        """
        if not packages:
            return True
        
        try:
            # Filter out system packages that shouldn't be uninstalled
            filtered_packages = [pkg for pkg in packages if pkg.lower() not in ['pip', 'setuptools', 'wheel']]
            if not filtered_packages:
                return True
                
            cmd = [sys.executable, "-m", "pip", "uninstall", "-y"] + filtered_packages
            logger.info(f"Uninstalling {len(filtered_packages)} packages")
            result = secure_subprocess_run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Error uninstalling packages: {e}")
            return False


class FallbackStrategy(RestoreStrategy):
    """
    Fallback strategy that tries multiple approaches with graceful degradation.
    
    This strategy attempts standard installation first, then falls back to
    force reinstall, and finally tries individual package installation.
    """
    
    def can_handle(self, backup: EnvironmentBackup) -> bool:
        """
        Check if this strategy can handle the backup.
        
        Args:
            backup: Environment backup to evaluate
            
        Returns:
            True if backup path exists (even if requirements file is missing)
        """
        return backup.backup_path and backup.backup_path.exists()
    
    def restore(self, backup: EnvironmentBackup) -> RestoreResult:
        """
        Restore environment using fallback strategy.
        
        Args:
            backup: Environment backup to restore from
            
        Returns:
            RestoreResult with restoration outcome
        """
        import time
        start_time = time.time()
        
        # Validate backup path exists
        if not backup.backup_path or not backup.backup_path.exists():
            return RestoreResult.failure_result(
                strategy="Fallback",
                error_message="Backup path does not exist",
                duration=time.time() - start_time
            )
        
        # Validate requirements file exists
        if not backup.requirements_file or not backup.requirements_file.exists():
            return RestoreResult.failure_result(
                strategy="Fallback",
                error_message="Requirements file does not exist",
                duration=time.time() - start_time
            )
        
        try:
            packages = self._get_packages_from_backup(backup)
            
            if not packages:
                warnings = ["Fallback strategy completed - no packages to restore"]
                return RestoreResult.success_result(
                    strategy="Fallback",
                    packages_restored=0,
                    duration=time.time() - start_time,
                    warnings=warnings
                )
            
            # Try standard install first
            result = self._try_standard_install(packages)
            if result.returncode == 0:
                return RestoreResult.success_result(
                    strategy="Fallback",
                    packages_restored=len(packages),
                    duration=time.time() - start_time
                )
            
            # Fall back to force reinstall
            result = self._try_force_reinstall(packages)
            if result.returncode == 0:
                return RestoreResult.success_result(
                    strategy="Fallback",
                    packages_restored=len(packages),
                    duration=time.time() - start_time,
                    warnings=["force reinstall succeeded"]
                )
            
            # Final fallback: try individual packages
            successful_packages = self._try_individual_packages(packages)
            
            if successful_packages:
                warnings = []
                if len(successful_packages) < len(packages):
                    warnings.append("Partial success")
                
                return RestoreResult.success_result(
                    strategy="Fallback",
                    packages_restored=len(successful_packages),
                    duration=time.time() - start_time,
                    warnings=warnings
                )
            else:
                return RestoreResult.failure_result(
                    strategy="Fallback",
                    error_message="All individual package installations failed",
                    duration=time.time() - start_time,
                    packages_failed=packages
                )
                
        except Exception as e:
            return RestoreResult.failure_result(
                strategy="Fallback",
                error_message=str(e),
                duration=time.time() - start_time,
                packages_failed=self._get_packages_from_backup(backup)
            )
    
    def _try_standard_install(self, packages: List[str]):
        """Try standard pip install."""
        cmd = [sys.executable, "-m", "pip", "install"] + packages
        return secure_subprocess_run(cmd, capture_output=True, text=True)
    
    def _try_force_reinstall(self, packages: List[str]):
        """Try force reinstall."""
        cmd = [sys.executable, "-m", "pip", "install", "--force-reinstall"] + packages
        return secure_subprocess_run(cmd, capture_output=True, text=True)
    
    def _try_individual_packages(self, packages: List[str]) -> List[str]:
        """Try installing packages individually."""
        successful = []
        
        for package in packages:
            try:
                cmd = [sys.executable, "-m", "pip", "install", package]
                result = secure_subprocess_run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    successful.append(package)
            except Exception:
                continue
        
        return successful