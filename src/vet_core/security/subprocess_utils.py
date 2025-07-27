"""
Secure subprocess utilities for the vet_core security module.

This module provides utilities for safely executing subprocess calls
with proper input validation and security measures.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Union


class SubprocessSecurityError(Exception):
    """Raised when subprocess security validation fails."""

    pass


def validate_package_name(package_name: str) -> str:
    """
    Validate a Python package name for security.

    Args:
        package_name: Package name to validate

    Returns:
        Validated package name

    Raises:
        SubprocessSecurityError: If package name is invalid
    """
    if not package_name or not isinstance(package_name, str):
        raise SubprocessSecurityError("Package name must be a non-empty string")

    # Allow only alphanumeric characters, hyphens, underscores, and dots
    if not re.match(r"^[a-zA-Z0-9._-]+$", package_name):
        raise SubprocessSecurityError(
            f"Invalid package name '{package_name}'. Only alphanumeric characters, "
            "hyphens, underscores, and dots are allowed."
        )

    # Prevent path traversal attempts
    if ".." in package_name or package_name.startswith("/"):
        raise SubprocessSecurityError(
            f"Package name '{package_name}' contains invalid path characters"
        )

    return package_name


def validate_version(version: str) -> str:
    """
    Validate a version string for security.

    Args:
        version: Version string to validate

    Returns:
        Validated version string

    Raises:
        SubprocessSecurityError: If version is invalid
    """
    if not version or not isinstance(version, str):
        raise SubprocessSecurityError("Version must be a non-empty string")

    # Allow version patterns like 1.2.3, 1.2.3a1, 1.2.3.dev0, etc.
    if not re.match(r"^[a-zA-Z0-9._+-]+$", version):
        raise SubprocessSecurityError(
            f"Invalid version '{version}'. Only alphanumeric characters, "
            "dots, hyphens, underscores, and plus signs are allowed."
        )

    # Prevent command injection attempts
    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", '"', "'"]
    if any(char in version for char in dangerous_chars):
        raise SubprocessSecurityError(
            f"Version '{version}' contains potentially dangerous characters"
        )

    return version


def validate_module_name(module_name: str) -> str:
    """
    Validate a Python module name for security.

    Args:
        module_name: Module name to validate

    Returns:
        Validated module name

    Raises:
        SubprocessSecurityError: If module name is invalid
    """
    if not module_name or not isinstance(module_name, str):
        raise SubprocessSecurityError("Module name must be a non-empty string")

    # Allow only valid Python module name characters
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", module_name):
        raise SubprocessSecurityError(
            f"Invalid module name '{module_name}'. Must be a valid Python identifier."
        )

    # Prevent dangerous imports
    dangerous_modules = ["os", "subprocess", "sys", "__import__", "eval", "exec"]
    if module_name in dangerous_modules:
        raise SubprocessSecurityError(
            f"Module '{module_name}' is not allowed for security reasons"
        )

    return module_name


def validate_test_command(test_command: str) -> str:
    """
    Validate a test command for security.

    Args:
        test_command: Test command to validate

    Returns:
        Validated test command

    Raises:
        SubprocessSecurityError: If test command is invalid
    """
    if not test_command or not isinstance(test_command, str):
        raise SubprocessSecurityError("Test command must be a non-empty string")

    # Allow only known safe test commands
    allowed_commands = ["pytest", "unittest", "nose2", "tox"]
    if test_command not in allowed_commands:
        raise SubprocessSecurityError(
            f"Test command '{test_command}' is not in the allowed list: {allowed_commands}"
        )

    return test_command


def get_executable_path(executable: str) -> str:
    """
    Get the full path to an executable, addressing B607 bandit warning.

    Args:
        executable: Name of the executable

    Returns:
        Full path to the executable

    Raises:
        SubprocessSecurityError: If executable is not found
    """
    full_path = shutil.which(executable)
    if not full_path:
        raise SubprocessSecurityError(f"Executable '{executable}' not found in PATH")

    return full_path


def secure_subprocess_run(
    cmd: List[str], validate_first_arg: bool = True, **kwargs
) -> subprocess.CompletedProcess:
    """
    Securely run a subprocess command with validation.

    Args:
        cmd: Command list to execute
        validate_first_arg: Whether to validate the first argument as an executable
        **kwargs: Additional arguments to pass to subprocess.run

    Returns:
        CompletedProcess result

    Raises:
        SubprocessSecurityError: If command validation fails
    """
    if not cmd or not isinstance(cmd, list):
        raise SubprocessSecurityError("Command must be a non-empty list")

    # Validate that we're not using shell=True (security risk)
    if kwargs.get("shell", False):
        raise SubprocessSecurityError("shell=True is not allowed for security reasons")

    # Validate first argument if requested
    if validate_first_arg and cmd[0] != sys.executable:
        # For non-Python executables, ensure we have the full path
        try:
            cmd[0] = get_executable_path(cmd[0])
        except SubprocessSecurityError:
            # If we can't find the executable, let subprocess handle the error
            pass

    # Set secure defaults
    secure_kwargs = {
        "shell": False,  # Never use shell
        "capture_output": True,  # Capture output by default
        "text": True,  # Use text mode by default
        **kwargs,  # Allow overrides
    }

    # nosec B603: This is a controlled subprocess call with validation
    return subprocess.run(cmd, **secure_kwargs)  # nosec
